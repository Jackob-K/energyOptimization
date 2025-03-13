import sqlite3
import requests
import pvlib
import datetime
import numpy as np
from database import get_db

# 🌞 Parametry FVE panelů
def get_fve_panels():
    """Načte parametry všech FVE panelů z databáze."""
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT id, latitude, longitude, tilt, azimuth, power FROM fve_panels")
        panels = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "tilt": row["tilt"],
            "azimuth": row["azimuth"],
            "power": row["power"]
        }
        for row in panels
    ]

def convert_azimuth_for_open_meteo(azimuth):
    """Převede azimut z klasického systému (0° = Sever, 180° = Jih) na Open-Meteo (-90° = Východ, 0° = Jih, 90° = Západ)."""
    return azimuth - 180  # Posuneme systém, aby 0° byl Jih


def get_weather_forecast(lat, lon, tilt, azimuth):
    """Načte hodinovou předpověď počasí a vrátí pouze prvních 24 hodin (zítřek)."""
    
    corrected_azimuth = convert_azimuth_for_open_meteo(azimuth)  # ✅ Oprava azimutu!

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,shortwave_radiation"
        f"&models=icon_seamless"
        f"&tilt={tilt}&azimuth={corrected_azimuth}"  # ✅ Použijeme opravený azimut
        f"&timezone=Europe/Prague"
    )

    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()

        # ✅ Bereme jen prvních 24 hodin (zítřek)
        times = data["hourly"]["time"][:24]
        temperatures = data["hourly"]["temperature_2m"][:24]
        solar_radiation = data["hourly"]["shortwave_radiation"][:24]

        print(f"✅ Načteno {len(times)} hodinových hodnot s opraveným azimutem {corrected_azimuth}°.")

        return {
            "time": times,
            "temperature": temperatures,
            "solar_radiation": solar_radiation
        }
    
    else:
        print(f"⚠ Chyba při načítání předpovědi: {response.status_code}")
        print(f"🛠 Detaily chyby: {response.text}")
        return None



# ⚡ Výpočet výroby pomocí pvlib
def calculate_production(panel, weather):
    """Vypočítá hodinovou výrobu FVE pomocí pvlib."""
    times = [datetime.datetime.fromisoformat(t) for t in weather["time"]]
    
    location = pvlib.location.Location(
        latitude=panel["latitude"], 
        longitude=panel["longitude"]
    )
    
    solar_position = location.get_solarposition(times)
    poa_irrad = weather["solar_radiation"]

    panel_power = panel["power"]
    tilt = panel["tilt"]
    azimuth = panel["azimuth"]

    # Korekce podle úhlu dopadu světla (předběžná metoda)
    effective_irrad = poa_irrad * np.cos(np.radians(solar_position["zenith"] - tilt))

    # Výstupní výkon
    production = (effective_irrad / 1000) * panel_power  # Přepočet na kW
    
    return production

def save_predictions(date, fve_id, hourly_production):
    """Přepíše data pro existující datum nebo přidá nová data pod stávající predikce."""
    with get_db() as db:
        cursor = db.cursor()

        # 🚨 Nejprve smažeme existující data pro daný den a FVE panel
        print(f"🗑 Odstraňuji staré predikce pro FVE {fve_id} na {date}...")
        cursor.execute("""
            DELETE FROM predictions WHERE date = ? AND fve_id = ?
        """, (date, fve_id))

        # ✅ Vložíme nové predikce
        print(f"📊 Ukládám nová data pro FVE {fve_id} na {date}...")
        for hour, production in enumerate(hourly_production):
            corrected_production = max(0, production)  # ✅ Oprava: záporné hodnoty nastavíme na 0
            
            print(f"✅ Ukládám: date={date}, hour={hour}, fve_id={fve_id}, production={corrected_production}")
            cursor.execute("""
                INSERT INTO predictions (date, hour, fve_id, predicted_production)
                VALUES (?, ?, ?, ?)
            """, (date, hour, fve_id, corrected_production))
        
        # ✅ Uložíme součet jako "denní predikci" (hour=24)
        total_production = sum(max(0, p) for p in hourly_production)  # ✅ Ujistíme se, že suma neobsahuje záporné hodnoty
        print(f"✅ Ukládám denní sumu: date={date}, hour=24, fve_id={fve_id}, production={total_production}")
        cursor.execute("""
            INSERT INTO predictions (date, hour, fve_id, predicted_production)
            VALUES (?, 24, ?, ?)
        """, (date, fve_id, total_production))

        db.commit()
        print(f"✅ Predikce pro FVE {fve_id} byla úspěšně aktualizována.")


# 🚀 Hlavní funkce
def main():
    """Hlavní funkce pro výpočet a uložení predikce výroby FVE."""
    print("🔄 Spouštím predikci výroby FVE...")

    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    panels = get_fve_panels()

    for panel in panels:
        print(f"📡 Načítám počasí pro FVE {panel['id']}...")
        weather = get_weather_forecast(
            panel["latitude"], panel["longitude"], panel["tilt"], panel["azimuth"]
        )
        
        if weather:
            print(f"⚡ Vypočítávám výrobu pro FVE {panel['id']}...")
            hourly_production = calculate_production(panel, weather)
            save_predictions(tomorrow, panel["id"], hourly_production)



    print("✅ Predikce výroby dokončena!")

if __name__ == "__main__":
    main()
