import os
import sqlite3
from contextlib import closing
import pandas as pd
from typing import Optional

# Nastavení cesty na databázi relativně k `backend/`
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Absolutní cesta ke složce backend/
DB_NAME = os.path.join(BASE_DIR, "energy_optimization.db")  # Cesta k databázi

def get_db():
    """Vrátí připojení k databázi s absolutní cestou."""
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

    # ✅ Tabulka pro predikované hodnoty výroby FVE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        date TEXT,
        hour INTEGER CHECK(hour BETWEEN 0 AND 24),  -- 0-23 pro hodinová data, 24 pro denní součet
        fve_id INTEGER,
        predicted_production REAL,
        correction_factor REAL DEFAULT 1.0,
        PRIMARY KEY (date, hour, fve_id),
        FOREIGN KEY (fve_id) REFERENCES fve_panels (id)
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            hodina INTEGER NOT NULL CHECK(hodina >= 0 AND hodina <= 23),
            cena REAL,
            mnozstvi REAL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Tabulky byly úspěšně vytvořeny nebo aktualizovány.")

def save_settings(totalPower: float):
    """Uloží celkový výkon FVE (totalPower) do databáze."""
    with closing(get_db()) as db, db:
        cursor = db.cursor()

        # ✅ Nejprve ověříme, zda existuje settings ID
        cursor.execute("SELECT id FROM settings WHERE id = 1")
        existing = cursor.fetchone()

        if existing:
            cursor.execute("UPDATE settings SET totalPower = ? WHERE id = 1", (totalPower,))
        else:
            cursor.execute("INSERT INTO settings (id, totalPower) VALUES (1, ?)", (totalPower,))
        
        db.commit()
        return 1  # ✅ Vždy vracíme settings_id = 1

def save_fve_panel(panel_id: Optional[int], settings_id: int, latitude: float, longitude: float, tilt: float, azimuth: float, power: float):
    """Uloží nebo aktualizuje FVE panel v databázi a zajistí správné číslování ID."""
    with closing(get_db()) as db, db:
        cursor = db.cursor()
        
        if panel_id:
            cursor.execute("""
                UPDATE fve_panels 
                SET latitude = ?, longitude = ?, tilt = ?, azimuth = ?, power = ?
                WHERE id = ?
            """, (latitude, longitude, tilt, azimuth, power, panel_id))
        else:
            # ✅ Nastavíme nové ID podle aktuálního počtu panelů
            cursor.execute("SELECT COUNT(*) FROM fve_panels")
            count = cursor.fetchone()[0]
            new_id = count + 1  # ✅ Nastavíme nové ID jako nejmenší dostupné číslo

            cursor.execute("""
                INSERT INTO fve_panels (id, settings_id, latitude, longitude, tilt, azimuth, power) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_id, settings_id, latitude, longitude, tilt, azimuth, power))
            
            panel_id = new_id  # ✅ Vrátíme správné ID
        
        db.commit()
        return panel_id


def get_fve_data():
    """Načte uložené parametry FVE z databáze."""
    with closing(get_db()) as db:
        cursor = db.cursor()

        # ✅ Získání celkového výkonu FVE
        cursor.execute("SELECT totalPower FROM settings WHERE id = 1")
        settings_data = cursor.fetchone()

        # ✅ Načtení všech FVE panelů
        cursor.execute("SELECT id, latitude, longitude, tilt, azimuth, power FROM fve_panels")
        fve_panels = cursor.fetchall()

        # ✅ Debug log - vypíše do konzole, co se načetlo
        print(f"🔍 Načtené nastavení: {settings_data}")
        print(f"🔍 Načtené panely: {fve_panels}")

        # ✅ Opravený návratový formát pro API
        return {
            "totalPower": settings_data["totalPower"] if settings_data else 0,
            "fve_fields": [
                {
                    "id": row["id"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "tilt": row["tilt"],
                    "azimuth": row["azimuth"],
                    "power": row["power"]
                }
                for row in fve_panels
            ]
        }

def delete_fve_panel(panel_id: int):
    """Smaže FVE panel a přepočítá ID všech zbývajících panelů."""
    with closing(get_db()) as db, db:
        cursor = db.cursor()

        # ✅ Ověříme, zda panel existuje
        cursor.execute("SELECT id FROM fve_panels WHERE id = ?", (panel_id,))
        existing = cursor.fetchone()

        if not existing:
            print(f"❌ FVE panel s ID {panel_id} neexistuje!")
            return False  # ✅ Panel neexistuje

        # ✅ Smažeme panel
        cursor.execute("DELETE FROM fve_panels WHERE id = ?", (panel_id,))
        db.commit()
        print(f"✅ FVE panel s ID {panel_id} byl smazán.")

        # ✅ Přepočítání ID zbývajících panelů
        cursor.execute("SELECT id FROM fve_panels ORDER BY id ASC")
        panels = cursor.fetchall()

        if panels:
            new_id = 1
            for row in panels:
                old_id = row["id"]
                cursor.execute("UPDATE fve_panels SET id = ? WHERE id = ?", (new_id, old_id))
                new_id += 1

            db.commit()
            print("🔄 ID panelů bylo přepočítáno.")

        return True  # ✅ Úspěšné smazání a přepočet




import sqlite3

def save_historical_data(df: pd.DataFrame):
    """Ukládá historická data do databáze správně a přepisuje existující záznamy."""
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Ověříme, zda soubor obsahuje `hour`
    if "hour" in df.columns:
        df["hour"] = df["hour"].fillna(24).astype(int)  # Pokud je prázdné → 24 (denní součet)
    else:
        df["hour"] = 24  # Přidáme defaultní hodnotu pro denní data

    data = df[["date", "hour", "fveProduction", "consumption", "temperatureMax", "temperatureMin"]].values.tolist()

    cursor.executemany("""
    INSERT OR REPLACE INTO historicalData (date, hour, fveProduction, consumption, temperatureMax, temperatureMin)
    VALUES (?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()
    print("✅ Historická data byla úspěšně importována do databáze.")

def get_energy_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, fveProduction, consumption 
        FROM historicalData 
        WHERE hour = 24  -- Pouze denní souhrnná data
        ORDER BY date ASC
    """)

    data = cursor.fetchall()
    conn.close()

    formatted_data = [
        {"timestamp": row[0], "production": row[1], "consumption": row[2]}
        for row in data
    ]

    return formatted_data  # ✅ Vracíme všechna data, žádné filtrování!



if __name__ == "__main__":
    create_database()