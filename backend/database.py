"""
Program inicializuje databázi, spravuje tabulky a umožňuje práci s fotovoltaickými panely,
historickými energetickými daty a jejich predikcemi.

Vstup: Data pro FVE panely, historická spotřeba energie, predikce.
Výstup: Aktualizovaná databáze se správnými tabulkami a daty.
Spolupracuje s: backend.database.getDb, backend.usagePrediction.dataProcessor.

"""

# Standardní knihovny
import os
import sqlite3
from contextlib import closing

# Externí knihovny
import pandas as pd
from typing import Optional

# Nastavení cesty na databázi relativně k `backend/`
baseDir = os.path.dirname(os.path.abspath(__file__))  # Absolutní cesta ke složce backend/
dbName = os.path.join(baseDir, "database.db")  # Cesta k databázi

def getDb():
    """getDb"""
    db = sqlite3.connect(dbName)
    db.row_factory = sqlite3.Row
    return db

def createDatabase():
    """createDatabase"""
    with getDb() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paramName TEXT UNIQUE,
            value TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fve_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL,
            longitude REAL,
            tilt REAL,
            azimuth REAL,
            power REAL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS energyData (
            date TEXT,
            hour INTEGER,
            fveProduction REAL,
            fvePredicted REAL,
            consumption REAL,
            consumptionPredicted REAL,
            temperature REAL,
            PRIMARY KEY (date, hour)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS energyPrices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            hodina INTEGER NOT NULL CHECK(hodina >= 0 AND hodina <= 23),
            cena REAL,
            mnozstvi REAL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS processedData (
            date TEXT,
            hour INTEGER,
            month INTEGER,
            day_of_week INTEGER,
            is_weekend INTEGER,
            consumption REAL,
            consumption_lag_1 REAL,
            consumption_lag_2 REAL,
            consumption_lag_3 REAL,
            consumption_lag_24 REAL,
            consumption_roll_3h REAL,
            consumption_roll_6h REAL,
            consumption_roll_12h REAL,
            consumption_roll_24h REAL,
            temperature REAL,
            temperature_lag_1 REAL,
            temperature_lag_2 REAL,
            temperature_lag_3 REAL,
            temperature_lag_24 REAL,
            temperature_roll_3h REAL,
            temperature_roll_6h REAL,
            temperature_roll_12h REAL,
            temperature_roll_24h REAL,
            PRIMARY KEY (date, hour)
        );
        """)

        conn.commit()
        print("✅ Tabulky byly úspěšně vytvořeny nebo aktualizovány.")

def saveFvePanel(panel_id: Optional[int], latitude: float, longitude: float, tilt: float, azimuth: float, power: float):
    """saveFvePanel"""
    with closing(getDb()) as db, db:
        cursor = db.cursor()
        
        if panel_id:
            cursor.execute("""
                UPDATE fve_panels 
                SET latitude = ?, longitude = ?, tilt = ?, azimuth = ?, power = ?
                WHERE id = ?
            """, (latitude, longitude, tilt, azimuth, power, panel_id))
        else:
            cursor.execute("SELECT COUNT(*) FROM fve_panels")
            count = cursor.fetchone()[0]
            newId = count + 1  

            cursor.execute("""
                INSERT INTO fve_panels (id, latitude, longitude, tilt, azimuth, power) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (newId, latitude, longitude, tilt, azimuth, power))
            
            panel_id = newId  
        
        db.commit()
        return panel_id

def getFveData():
    """getFveData"""
    with closing(getDb()) as db:
        cursor = db.cursor()

        cursor.execute("SELECT SUM(power) AS totalPower FROM fve_panels")
        totalPowerData = cursor.fetchone()
        totalPower = totalPowerData["totalPower"] if totalPowerData and totalPowerData["totalPower"] is not None else 0

        cursor.execute("SELECT id, latitude, longitude, tilt, azimuth, power FROM fve_panels")
        fvePanels = cursor.fetchall()

        return {
            "totalPower": totalPower,
            "fveFields": [
                {
                    "id": row["id"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "tilt": row["tilt"],
                    "azimuth": row["azimuth"],
                    "power": row["power"]
                }
                for row in fvePanels
            ]
        }

def deleteFvePanel(panel_id: int):
    """deleteFvePanel"""
    with closing(getDb()) as db, db:
        cursor = db.cursor()

        cursor.execute("SELECT id FROM fve_panels WHERE id = ?", (panel_id,))
        existing = cursor.fetchone()

        if not existing:
            print(f"❌ FVE panel s ID {panel_id} neexistuje!")
            return False  

        cursor.execute("DELETE FROM fve_panels WHERE id = ?", (panel_id,))
        db.commit()
        print(f"✅ FVE panel s ID {panel_id} byl smazán.")

        cursor.execute("SELECT id FROM fve_panels ORDER BY id ASC")
        panels = cursor.fetchall()

        if panels:
            newId = 1
            for row in panels:
                oldId = row["id"]
                cursor.execute("UPDATE fve_panels SET id = ? WHERE id = ?", (newId, oldId))
                newId += 1

            db.commit()
            print("🔄 ID panelů bylo přepočítáno.")

        return True  

def saveHistoricalData(df: pd.DataFrame):
    """saveHistoricalData"""
    with closing(getDb()) as db:
        cursor = db.cursor()

        df = df.where(pd.notnull(df), None)

        df["fveProduction"] = df["fveProduction"].astype(float).round(2)
        df["consumption"] = df["consumption"].astype(float).round(2)

        data = df[["date", "hour", "fveProduction", "consumption", "temperature"]].values.tolist()

        cursor.executemany("""
        INSERT INTO energyData (date, hour, fveProduction, consumption, temperature)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date, hour) DO UPDATE SET 
            fveProduction = excluded.fveProduction,
            consumption = excluded.consumption,
            temperature = excluded.temperature;
        """, data)

        db.commit()
        print("✅ Historická data byla úspěšně importována do databáze.")

def getEnergyData():
    """getEnergyData"""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT date, fveProduction, consumption 
            FROM energyData 
            WHERE hour = 24  
            ORDER BY date ASC
        """)

        return [
            {"timestamp": row["date"], "production": row["fveProduction"], "consumption": row["consumption"]}
            for row in cursor.fetchall()
        ]

def getSettings():
    """Získá všechna nastavení z databáze."""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT id, paramName, value FROM settings")
        settings = cursor.fetchall()

        return [
            {"id": row["id"], "paramName": row["paramName"], "value": row["value"]}
            for row in settings
        ]

def updateSetting(setting_id: int, new_value: str):
    """Aktualizuje hodnotu parametru v databázi."""
    with closing(getDb()) as db, db:
        cursor = db.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE id = ?", (new_value, setting_id))
        db.commit()
        print(f"✅ Nastavení ID {setting_id} bylo aktualizováno na hodnotu {new_value}.")

if __name__ == "__main__":
    createDatabase()
