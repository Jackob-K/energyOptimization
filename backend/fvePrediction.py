"""
Program pro predikci výroby fotovoltaických panelů na základě počasí.

Vstup: Informace o FVE panelech z databáze, předpověď počasí z open-meteo API.
Výstup: Predikovaná výroba energie uložená v databázi.
Spolupracuje s: backend.database, open-meteo.com, pvlib.
"""

import requests
import pvlib
import datetime
import numpy as np
import logging
from collections import defaultdict
from database import getDb

# 🛠️ Logging
enableLogging = 1
logger = logging.getLogger(__name__)
if enableLogging:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# ☀️ FVE panely -----------------------------------------------------------------

def getFvePanels():
    """Načte FVE panely z databáze"""
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


# 🌤️ Práce s předpovědí počasí --------------------------------------------------

def convertAzimuthForOpenMeteo(azimuth):
    """Konverze azimutu podle požadavku API"""
    return azimuth - 180


def getWeatherForecast(lat, lon, tilt, azimuth):
    """Stáhne hodinovou předpověď počasí pro danou lokaci"""
    correctedAzimuth = convertAzimuthForOpenMeteo(azimuth)
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,shortwave_radiation"
        f"&models=icon_seamless"
        f"&tilt={tilt}&azimuth={correctedAzimuth}"
        f"&timezone=Europe/Prague"
    )

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if enableLogging:
            logger.info(f"✅ Načteno {len(data['hourly']['time'])} hodinových hodnot s azimutem {correctedAzimuth}°.")
        return {
            "time": data["hourly"]["time"],
            "temperature": data["hourly"]["temperature_2m"],
            "solarRadiation": data["hourly"]["shortwave_radiation"]
        }
    else:
        if enableLogging:
            logger.error(f"❌ Chyba při načítání počasí: {response.status_code}")
            logger.error(f"🛠 Detaily: {response.text}")
        return None


def splitWeatherByDate(weather):
    """Rozdělí počasí podle data (YYYY-MM-DD)"""
    result = defaultdict(lambda: {"time": [], "temperature": [], "solarRadiation": []})
    for i, t in enumerate(weather["time"]):
        day = t.split("T")[0]
        result[day]["time"].append(t)
        result[day]["temperature"].append(weather["temperature"][i])
        result[day]["solarRadiation"].append(weather["solarRadiation"][i])
    return result


# ⚡ Výpočet výroby -----------------------------------------------------------------

def calculateProduction(panel, weather):
    """Spočítá očekávanou výrobu na základě počasí a sklonu panelu"""
    times = [datetime.datetime.fromisoformat(t) for t in weather["time"]]
    location = pvlib.location.Location(panel["latitude"], panel["longitude"])
    solarPosition = location.get_solarposition(times)
    poaIrrad = weather["solarRadiation"]

    effectiveIrrad = poaIrrad * np.cos(np.radians(solarPosition["zenith"] - panel["tilt"]))
    production = np.round((effectiveIrrad / 1000) * panel["power"], 2)
    return production


# 💾 Práce s databází ------------------------------------------------------------

def isPredictionAvailableFor(date):
    """Zjistí, zda je v DB už uložena predikce pro daný den"""
    start = datetime.datetime.combine(date, datetime.time(0)).isoformat()
    with getDb() as db:
        cursor = db.cursor()
        cursor.execute("SELECT fvePredicted FROM energyData WHERE timestamp = ?", (start,))
        row = cursor.fetchone()
        return row is not None and row["fvePredicted"] is not None


def savePredictions(baseDate, hourlyProduction):
    """Uloží hodinové i denní predikce do databáze"""
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

        end_of_day = datetime.datetime.combine(baseDate, datetime.time(23, 59, 59)).isoformat()
        dailyTotal = sum(sum(max(0, p) for p in prod.tolist()) for prod in hourlyProduction)
        dailyTotal = round(dailyTotal, 2)
        cursor.execute("""
            INSERT INTO energyData (timestamp, fvePredicted)
            VALUES (?, ?)
            ON CONFLICT(timestamp) DO UPDATE SET
                fvePredicted = excluded.fvePredicted;
        """, (end_of_day, dailyTotal))

        db.commit()
        if enableLogging:
            logger.info(f"💾 Predikce pro {baseDate} byla uložena.")


# 🚀 Hlavní funkce ---------------------------------------------------------------

def main():
    if enableLogging:
        logger.info("🔄 Spouštím predikci výroby FVE...")

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    panels = getFvePanels()
    weather_cache = {}

    hourlyProductionsToday = []
    hourlyProductionsTomorrow = []

    for panel in panels:
        key = (panel["latitude"], panel["longitude"], panel["tilt"], panel["azimuth"])
        weather = weather_cache.get(key)

        if not weather:
            weather = getWeatherForecast(*key)
            weather_cache[key] = weather

        if not weather:
            continue

        split = splitWeatherByDate(weather)

        # Dnešek
        if str(today) in split:
            productionToday = calculateProduction(panel, split[str(today)])
            if len(productionToday) == 24:
                hourlyProductionsToday.append(productionToday)
            else:
                if enableLogging:
                    logger.warning(f"⚠️ Nedostatek dat pro dnešek – {len(productionToday)} hodin")

        # Zítřek
        if str(tomorrow) in split:
            productionTomorrow = calculateProduction(panel, split[str(tomorrow)])
            if len(productionTomorrow) == 24:
                hourlyProductionsTomorrow.append(productionTomorrow)
            else:
                if enableLogging:
                    logger.warning(f"⚠️ Nedostatek dat pro zítřek – {len(productionTomorrow)} hodin")

    if not isPredictionAvailableFor(today):
        if hourlyProductionsToday:
            if enableLogging:
                logger.info("📉 Chybí predikce pro dnešek. Ukládám...")
            savePredictions(today, hourlyProductionsToday)
        else:
            if enableLogging:
                logger.warning("❌ Dnešní data nejsou k dispozici.")
    else:
        if enableLogging:
            logger.info("✅ Dnešní predikce je již v databázi.")

    if hourlyProductionsTomorrow:
        if enableLogging:
            logger.info("📆 Ukládám predikci na zítřek...")
        savePredictions(tomorrow, hourlyProductionsTomorrow)
    else:
        if enableLogging:
            logger.warning("❌ Zítřejší data nejsou k dispozici.")

    if enableLogging:
        logger.info("✅ Predikce výroby dokončena!")


if __name__ == "__main__":
    main()
