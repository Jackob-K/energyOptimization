import requests
import pvlib
import datetime
import numpy as np
from database import getDb

"""
Tento program slouží k predikci výroby elektrické energie z fotovoltaických panelů (FVE).
Vstupy:
  - Parametry FVE panelů uložené v databázi (souřadnice, výkon, sklon, azimut).
  - Meteorologická předpověď (teplota, solární radiace) získaná z Open-Meteo API.

Výstupy:
  - Aktualizované hodnoty predikované výroby elektřiny v tabulce `energyData` pro následujících 24 hodin.
  - Celková denní predikce výroby elektřiny (záznam s `hour = 24`).

Spolupráce:
  - Spolupracuje s databází SQLite (tabulky `fvePanels`, `energyData`).
  - Využívá API Open-Meteo pro získání předpovědi počasí.
  - Používá knihovnu `pvlib` k výpočtu výroby FVE.
"""


# Načtení parametrů FVE panelů z databáze
def getFvePanels():
    """Načte parametry všech FVE panelů z databáze."""
    with getDb() as db:
        cursor = db.cursor()
        cursor.execute("SELECT id, latitude, longitude, tilt, azimuth, power FROM fvePanels")
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


# 🔄 Konverze azimutu pro Open-Meteo
def convertAzimuthForOpenMeteo(azimuth):
    """Převede azimut z klasického systému (0° = Sever, 180° = Jih) na Open-Meteo (-90° = Východ, 0° = Jih, 90° = Západ)."""
    return azimuth - 180  # Posuneme systém, aby 0° byl Jih


# ☁️ Získání předpovědi počasí
def getWeatherForecast(lat, lon, tilt, azimuth):
    """Načte hodinovou předpověď počasí pro danou lokalitu a vrátí hodnoty pro zítřek."""
    
    correctedAzimuth = convertAzimuthForOpenMeteo(azimuth)  # ✅ Oprava azimutu

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,shortwave_radiation"
        f"&models=icon_seamless"
        f"&tilt={tilt}&azimuth={correctedAzimuth}"  # ✅ Použijeme opravený azimut
        f"&timezone=Europe/Prague"
    )

    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()

        # ✅ Bereme jen prvních 24 hodin (zítřek)
        times = data["hourly"]["time"][:24]
        temperatures = data["hourly"]["temperature_2m"][:24]
        solarRadiation = data["hourly"]["shortwave_radiation"][:24]

        print(f"✅ Načteno {len(times)} hodinových hodnot s opraveným azimutem {correctedAzimuth}°.")

        return {
            "time": times,
            "temperature": temperatures,
            "solarRadiation": solarRadiation
        }
    
    else:
        print(f"⚠ Chyba při načítání předpovědi: {response.status_code}")
        print(f"🛠 Detaily chyby: {response.text}")
        return None


# ⚡ Výpočet výroby pomocí pvlib
def calculateProduction(panel, weather):
    """Vypočítá hodinovou výrobu FVE pomocí knihovny pvlib na základě solární radiace."""
    times = [datetime.datetime.fromisoformat(t) for t in weather["time"]]
    
    location = pvlib.location.Location(
        latitude=panel["latitude"], 
        longitude=panel["longitude"]
    )
    
    solarPosition = location.get_solarposition(times)
    poaIrrad = weather["solarRadiation"]

    panelPower = panel["power"]
    tilt = panel["tilt"]
    azimuth = panel["azimuth"]

    # Korekce podle úhlu dopadu světla (předběžná metoda)
    effectiveIrrad = poaIrrad * np.cos(np.radians(solarPosition["zenith"] - tilt))

    # Výstupní výkon, zaokrouhlený na dvě desetinná místa
    production = np.round((effectiveIrrad / 1000) * panelPower, 2)  # Přepočet na kW
    
    return production


# 📊 Uložení predikovaných hodnot do databáze
def savePredictions(baseDate, hourlyProduction):
    """Uloží predikovanou výrobu FVE do databáze pro jednotlivé hodiny i celkový denní součet."""
    with getDb() as db:
        cursor = db.cursor()

        for hour in range(24):
            timestamp = datetime.datetime.combine(baseDate, datetime.time(hour)).isoformat()
            totalProduction = sum(max(0, prod.iloc[hour]) for prod in hourlyProduction)
            totalProduction = round(totalProduction, 2)

            cursor.execute("""
                INSERT INTO energyData (timestamp, fvePredicted)
                VALUES (?, ?)
                ON CONFLICT(timestamp) DO UPDATE SET
                    fvePredicted = excluded.fvePredicted;
            """, (timestamp, totalProduction))

        # Záznam pro celý den (23:59:59)
        end_of_day = datetime.datetime.combine(baseDate, datetime.time(23, 59, 59)).isoformat()
        dailyTotal = sum(sum(max(0, p) for p in prod) for prod in hourlyProduction)
        dailyTotal = round(dailyTotal, 2)

        cursor.execute("""
            INSERT INTO energyData (timestamp, fvePredicted)
            VALUES (?, ?)
            ON CONFLICT(timestamp) DO UPDATE SET
                fvePredicted = excluded.fvePredicted;
        """, (end_of_day, dailyTotal))

        db.commit()



# 🚀 Hlavní spouštěcí funkce
def main():
    print("🔄 Spouštím predikci výroby FVE...")

    # Zítřejší den jako `date` objekt
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    panels = getFvePanels()
    allHourlyProductions = []

    for panel in panels:
        weather = getWeatherForecast(
            panel["latitude"], panel["longitude"],
            panel["tilt"], panel["azimuth"]
        )
        if weather:
            hourly = calculateProduction(panel, weather)
            allHourlyProductions.append(hourly)

    if allHourlyProductions:
        savePredictions(tomorrow, allHourlyProductions)

    print("✅ Predikce výroby dokončena!")



if __name__ == "__main__":
    main()
