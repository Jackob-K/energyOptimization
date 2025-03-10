import sqlite3
from contextlib import closing

DB_NAME = "energy_optimization.db"

def get_db():
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    return db

def create_database():
    with closing(get_db()) as db, db:
        cursor = db.cursor()
        
        # ✅ Tabulka pro nastavení FVE (pouze jeden řádek)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                totalPower REAL
            )
        """)
        
        # ✅ Tabulka pro panely FVE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fve_panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                settings_id INTEGER,
                latitude REAL,
                longitude REAL,
                tilt REAL,
                azimuth REAL,
                power REAL,
                FOREIGN KEY (settings_id) REFERENCES settings (id) ON DELETE CASCADE
            )
        """)
        
        # ✅ Tabulka pro historická data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historicalData (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                hour INTEGER,
                consumption REAL NOT NULL,
                fve_generated REAL NOT NULL,
                temperature_min REAL,
                temperature_max REAL
            )
        """)

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

def save_historical_data(data):
    """Ukládá historická data do databáze."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.executemany("""
    INSERT INTO historicalData (date, fveProduction, consumption, temperatureMax, temperatureMin)
    VALUES (?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()
    print("✅ Historická data byla úspěšně importována.")

if __name__ == "__main__":
    create_database()