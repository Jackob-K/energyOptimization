import sqlite3
from contextlib import closing
import pandas as pd

DB_NAME = "energy_optimization.db"

def get_db():
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    return db

def create_database():
    """Inicializuje databázi a vytvoří tabulky, pokud neexistují."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ✅ Tabulka pro nastavení
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        totalPower REAL
    )
    """)

    # ✅ Tabulka pro FVE panely
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fve_panels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        settings_id INTEGER,
        latitude REAL,
        longitude REAL,
        tilt REAL,
        azimuth REAL,
        power REAL,
        FOREIGN KEY (settings_id) REFERENCES settings (id)
    )
    """)

    # ✅ OPRAVENÁ tabulka `historicalData` (přidán sloupec `hour`)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historicalData (
        date TEXT,
        hour INTEGER,  -- Přidán sloupec pro hodinová data
        fveProduction REAL,
        consumption REAL,
        temperatureMax REAL,
        temperatureMin REAL,
        PRIMARY KEY (date, hour)  -- Každý záznam má unikátní kombinaci date + hour
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Tabulky byly úspěšně vytvořeny nebo aktualizovány.")

def save_settings(totalPower: float):
    with closing(get_db()) as db, db:
        cursor = db.cursor()
        cursor.execute("INSERT INTO settings (id, totalPower) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET totalPower = excluded.totalPower", (totalPower,))
        db.commit()
        return 1

def save_fve_panel(panel_id: int | None, settings_id: int, latitude: float, longitude: float, tilt: float, azimuth: float, power: float):
    with closing(get_db()) as db, db:
        cursor = db.cursor()
        if panel_id:
            cursor.execute("""
                UPDATE fve_panels 
                SET latitude = ?, longitude = ?, tilt = ?, azimuth = ?, power = ?
                WHERE id = ?
            """, (latitude, longitude, tilt, azimuth, power, panel_id))
        else:
            cursor.execute("""
                INSERT INTO fve_panels (settings_id, latitude, longitude, tilt, azimuth, power) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (settings_id, latitude, longitude, tilt, azimuth, power))
            panel_id = cursor.lastrowid
        
        db.commit()
        return panel_id

def delete_fve_panel(panel_id: int):
    with closing(get_db()) as db, db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM fve_panels WHERE id = ?", (panel_id,))
        db.commit()

def get_fve_data():
    with closing(get_db()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT totalPower FROM settings WHERE id = 1")
        settings_data = cursor.fetchone()

        cursor.execute("SELECT id, latitude, longitude, tilt, azimuth, power FROM fve_panels")
        fve_panels = cursor.fetchall()

        return {
            "totalPower": settings_data["totalPower"] if settings_data else 0,
            "fve_fields": [
                {"id": row["id"], "latitude": row["latitude"], "longitude": row["longitude"], "tilt": row["tilt"], "azimuth": row["azimuth"], "power": row["power"]}
                for row in fve_panels
            ]
        }

def get_all_fve_panel_ids(settings_id: int):
    with closing(get_db()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM fve_panels WHERE settings_id = ?", (settings_id,))
        return [row["id"] for row in cursor.fetchall()]

def save_historical_data(df: pd.DataFrame):
    """Ukládá historická data do databáze a přepisuje existující záznamy."""

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if "hour" in df.columns:
        df["hour"] = df["hour"].fillna(24).astype(int)
    else:
        df["hour"] = 24  

    data = df[["date", "hour", "fveProduction", "consumption", "temperatureMax", "temperatureMin"]].values.tolist()

    print(f"🔄 Ukládám {len(data)} řádků do databáze...")

    cursor.executemany("""
    INSERT OR REPLACE INTO historicalData (date, hour, fveProduction, consumption, temperatureMax, temperatureMin)
    VALUES (?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()
    print("✅ Historická data byla úspěšně importována do databáze.")


if __name__ == "__main__":
    create_database()