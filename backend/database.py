"""
Program inicializuje databázi, spravuje tabulky a umožňuje práci s fotovoltaickými panely,
historickými energetickými daty a jejich predikcemi.

Vstup: Data pro FVE panely, historická spotřeba energie, predikce.
Výstup: Aktualizovaná databáze se správnými tabulkami a daty.
Spolupracuje s: backend.database.getDb, backend.usagePrediction.dataProcessor.
"""

# 📦 Standardní knihovny
import os
import sqlite3
import datetime
import logging
from contextlib import closing
from typing import Optional

# 🌐 Externí knihovny
import pandas as pd

# 🛠️ Logging
enableLogging = 1
logger = logging.getLogger(__name__)
if enableLogging:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 📁 Umístění databáze
baseDir = os.path.dirname(os.path.abspath(__file__))
dbName = os.path.join(baseDir, "database.db")


# 🔌 Připojení a inicializace databáze -----------------------------------------

def getDb():
    """Vrátí připojení k databázi"""
    db = sqlite3.connect(dbName, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def createDatabase():
    """Vytvoří všechny potřebné tabulky v databázi"""
    with getDb() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paramName TEXT UNIQUE,
            value TEXT,
            placeHolder TEXT
        );
        """)

        default_settings = [
            (1, "breakerCurrentPerPhase", "Proud jističe [A]", "např. 25"),
            (2, "phases", "Počet fází [1/3]", "např. 1 nebo 3"),
            (3, "overrideMode", "Režim řízení [0/1]", "0 = automatický, 1 = ruční"),
            (11, "mqttBroker", "MQTT broker", "např. test.mosquitto.org"),
            (12, "mqttPort", "MQTT port", "např. 1883"),
            (13, "mqttTopic", "MQTT topic", "např. energy/data"),
            (14, "mqttUserName", "MQTT uživatel", "např. homeassistant"),
            (15, "mqttPassword", "MQTT heslo", "••••••••••••"),
            (16, "batteryCapacityKWh", "Kapacita baterie [kWh]", "např. 10"),
            (17, "batteryEfficiency", "Účinnost baterie [0–1]", "např. 0.9"),
            (18, "batteryMaxChargeKW", "Max. nabíjení [kW]", "např. 3.5"),
            (19, "batteryMaxDischargeKW", "Max. vybíjení [kW]", "např. 3.5"),
            (20, "batterySocMin", "Minimální SoC [%]", "např. 10"),
            (21, "batterySocMax", "Maximální SoC [%]", "např. 90"),
            (26, "daysToPredict", "Dny predikce [dní]", "max 16, např. 5"),
        ]

        for id_, param, label, placeholder in default_settings:
            cursor.execute("""
                INSERT INTO settings (id, paramName, label, placeHolder)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(paramName) DO UPDATE SET
                    label = excluded.label,
                    placeHolder = excluded.placeHolder;
            """, (id_, param, label, placeholder))

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
        if enableLogging:
            logger.info("✅ Tabulky byly úspěšně vytvořeny nebo aktualizovány.")


# ☀️ FVE Panely ----------------------------------------------------------------

def saveFvePanel(panel_id: Optional[int], latitude: float, longitude: float, tilt: float, azimuth: float, power: float):
    """Uloží nebo aktualizuje FVE panel"""
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
    """Vrátí seznam FVE panelů a celkový výkon"""
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
    """Smaže FVE panel a přepočítá ID"""
    with closing(getDb()) as db, db:
        cursor = db.cursor()

        cursor.execute("SELECT id FROM fvePanels WHERE id = ?", (panel_id,))
        existing = cursor.fetchone()

        if not existing:
            if enableLogging:
                logger.warning(f"❌ FVE panel s ID {panel_id} neexistuje!")
            return False

        cursor.execute("DELETE FROM fvePanels WHERE id = ?", (panel_id,))
        db.commit()

        if enableLogging:
            logger.info(f"✅ FVE panel s ID {panel_id} byl smazán.")

        cursor.execute("SELECT id FROM fvePanels ORDER BY id ASC")
        panels = cursor.fetchall()

        if panels:
            newId = 1
            for row in panels:
                oldId = row["id"]
                cursor.execute("UPDATE fvePanels SET id = ? WHERE id = ?", (newId, oldId))
                newId += 1

            db.commit()
            if enableLogging:
                logger.info("🔄 ID panelů bylo přepočítáno.")

        return True


# 📊 Historická data -----------------------------------------------------------

def saveHistoricalData(df: pd.DataFrame):
    """Uloží historická data o spotřebě a výrobě energie"""
    with closing(getDb()) as db:
        cursor = db.cursor()

        df = df.where(pd.notnull(df), None)

        df["fveProduction"] = df["fveProduction"].astype(float).round(2)
        df["consumption"] = df["consumption"].astype(float).round(2)

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
        if enableLogging:
            logger.info("✅ Historická data byla uložena pomocí timestampu.")


def getEnergyData():
    """Vrátí denní hodnoty spotřeby a výroby"""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT timestamp, fveProduction, consumption 
            FROM energyData 
            WHERE time(timestamp) = '23:59:59'
            ORDER BY timestamp ASC
        """)
        return [
            {"timestamp": row["timestamp"], "production": row["fveProduction"], "consumption": row["consumption"]}
            for row in cursor.fetchall()
        ]


# ⚙️ Obecné nastavení (tabulka settings) ----------------------------------------

def getSettings():
    """Získá všechna nastavení z databáze"""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT id, paramName, value FROM settings")
        settings = cursor.fetchall()

        return [
            {"id": row["id"], "paramName": row["paramName"], "value": row["value"]}
            for row in settings
        ]


def updateSetting(setting_id: int, new_value: str):
    """Aktualizuje hodnotu parametru"""
    with closing(getDb()) as db, db:
        cursor = db.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE id = ?", (new_value, setting_id))
        db.commit()
        if enableLogging:
            logger.info(f"✅ Nastavení ID {setting_id} bylo aktualizováno na hodnotu {new_value}.")


def getSetting(paramName: str):
    """Vrátí konkrétní hodnotu nastavení podle názvu"""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT value FROM settings WHERE paramName = ?", (paramName,))
        result = cursor.fetchone()
        return result["value"] if result else None


# ⚡ Ceny energie & baterie -----------------------------------------------------

def getTomorrowPrices():
    """Vrátí ceny energie na zítřejší den"""
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


def insertBatteryPlan(timestamp: str, action: str, powerTargetKw: float):
    """Vloží záznam o plánu baterie"""
    with closing(getDb()) as db:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO batteryPlan (timestamp, action, powerTargetKw)
            VALUES (?, ?, ?)
        """, (timestamp, action, powerTargetKw))
        db.commit()


# 🚀 Vytvoření databáze při spuštění --------------------------------------------

if __name__ == "__main__":
    createDatabase()
