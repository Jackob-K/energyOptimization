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
import datetime

# Externí knihovny
import pandas as pd
from typing import Optional

# Nastavení cesty na databázi relativně k `backend/`
baseDir = os.path.dirname(os.path.abspath(__file__))  # Absolutní cesta ke složce backend/
dbName = os.path.join(baseDir, "database.db")  # Cesta k databázi

def getDb():
    """getDb"""
    db = sqlite3.connect(dbName, check_same_thread=False)
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
        CREATE TABLE IF NOT EXISTS fvePanels (
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
            timestamp TEXT PRIMARY KEY,
            fveProduction REAL,
            fvePredicted REAL,
            consumption REAL,
            consumptionPredicted REAL,
            temperature REAL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS energyPrices (
            timestamp TEXT PRIMARY KEY,
            price REAL,
            quantity REAL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS processedData (
            timestamp TEXT PRIMARY KEY,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            hour INTEGER,
            dayOfWeek INTEGER,
            isWeekend INTEGER,
            consumption REAL,
            consumptionLag1 REAL,
            consumptionLag2 REAL,
            consumptionLag3 REAL,
            consumptionLag24 REAL,
            consumptionRoll3h REAL,
            consumptionRoll6h REAL,
            consumptionRoll12h REAL,
            consumptionRoll24h REAL,
            temperature REAL,
            temperatureLag1 REAL,
            temperatureLag2 REAL,
            temperatureLag3 REAL,
            temperatureLag24 REAL,
            temperatureRoll3h REAL,
            temperatureRoll6h REAL,
            temperatureRoll12h REAL,
            temperatureRoll24h REAL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS batteryPlan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT CHECK(action IN ('charge', 'discharge', 'idle')) NOT NULL,
            powerTargetKw REAL NOT NULL DEFAULT 0
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS optimizationLog (
            date TEXT PRIMARY KEY,
            baselineCost REAL,
            optimizedCost REAL,
            saving REAL,
            created_at TEXT
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
                UPDATE fvePanels 
                SET latitude = ?, longitude = ?, tilt = ?, azimuth = ?, power = ?
                WHERE id = ?
            """, (latitude, longitude, tilt, azimuth, power, panel_id))
        else:
            cursor.execute("SELECT COUNT(*) FROM fvePanels")
            count = cursor.fetchone()[0]
            newId = count + 1  

            cursor.execute("""
                INSERT INTO fvePanels (id, latitude, longitude, tilt, azimuth, power) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (newId, latitude, longitude, tilt, azimuth, power))
            
            panel_id = newId  
        
        db.commit()
        return panel_id

def getFveData():
    """getFveData"""
    with closing(getDb()) as db:
        cursor = db.cursor()

        cursor.execute("SELECT SUM(power) AS totalPower FROM fvePanels")
        totalPowerData = cursor.fetchone()
        totalPower = totalPowerData["totalPower"] if totalPowerData and totalPowerData["totalPower"] is not None else 0

        cursor.execute("SELECT id, latitude, longitude, tilt, azimuth, power FROM fvePanels")
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

        cursor.execute("SELECT id FROM fvePanels WHERE id = ?", (panel_id,))
        existing = cursor.fetchone()

        if not existing:
            print(f"❌ FVE panel s ID {panel_id} neexistuje!")
            return False  

        cursor.execute("DELETE FROM fvePanels WHERE id = ?", (panel_id,))
        db.commit()
        print(f"✅ FVE panel s ID {panel_id} byl smazán.")

        cursor.execute("SELECT id FROM fvePanels ORDER BY id ASC")
        panels = cursor.fetchall()

        if panels:
            newId = 1
            for row in panels:
                oldId = row["id"]
                cursor.execute("UPDATE fvePanels SET id = ? WHERE id = ?", (newId, oldId))
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

        # Pokud timestamp ještě není, vytvoříme ho ze sloupců date a hour
        if "timestamp" not in df.columns:
            def to_timestamp(row):
                base = datetime.datetime.strptime(row["date"], "%Y-%m-%d")
                if row["hour"] == 24:
                    dt = base.replace(hour=23, minute=59, second=59)
                else:
                    dt = base.replace(hour=row["hour"])
                return dt.isoformat()
            df["timestamp"] = df.apply(to_timestamp, axis=1)

        data = df[["timestamp", "fveProduction", "consumption", "temperature"]].values.tolist()

        cursor.executemany("""
        INSERT INTO energyData (timestamp, fveProduction, consumption, temperature)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(timestamp) DO UPDATE SET 
            fveProduction = excluded.fveProduction,
            consumption = excluded.consumption,
            temperature = excluded.temperature;
        """, data)

        db.commit()
        print("✅ Historická data byla uložena pomocí timestampu.")


def getEnergyData():
    """getEnergyData"""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT timestamp, fveProduction, consumption 
            FROM energyData 
            WHERE time(timestamp) = '23:59:59'
            ORDER BY timestamp ASC
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

def getSetting(paramName):
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT value FROM settings WHERE paramName = ?", (paramName,))
        result = cursor.fetchone()
        return result["value"] if result else None



def getTomorrowPrices():
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date().isoformat()
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT timestamp, price
            FROM energyPrices
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp ASC
        """, (tomorrow,))
        return cursor.fetchall()


def insertBatteryPlan(timestamp, action, powerTargetKw):
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO batteryPlan (timestamp, action, powerTargetKw)
            VALUES (?, ?, ?)
        """, (timestamp, action, powerTargetKw))
        db.commit()

if __name__ == "__main__":
    createDatabase()
