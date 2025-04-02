"""
Program načítá historická data spotřeby energie a teploty z databáze,
vytváří doplňkové atributy (lagy, klouzavé průměry, časové atributy)
a připravuje data pro trénování ML modelu nebo je aktualizuje zpět do databáze.

Vstup: Data z databáze energyData
Výstup: Upravená data (X_train, X_test, y_train, y_test) nebo aktualizovaná tabulka processedData
Spolupracuje s: database.getDb
"""

import pandas as pd
from database import getDb
import requests
import datetime

def getHistoricalData():
    with getDb() as conn:
        query = """
        SELECT timestamp, consumption, temperature
        FROM energyData
        WHERE time(timestamp) != '23:59:59'
        ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["year"] = df["timestamp"].dt.year
    return df

def addTemperatureFeatures(df, lags=[1, 2, 3, 24], windows=[3, 6, 12, 24]):
    for lag in lags:
        df[f"temperatureLag{lag}"] = df["temperature"].shift(lag)
    for window in windows:
        df[f"temperatureRoll{window}h"] = df["temperature"].rolling(window=window, min_periods=1).mean()
    return df

def addTimeFeatures(df):
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["day"] = df["timestamp"].dt.day
    df["dayOfWeek"] = df["timestamp"].dt.weekday
    df["isWeekend"] = df["dayOfWeek"].isin([5, 6]).astype(int)
    df["hour"] = df["timestamp"].dt.hour
    return df

def prepareTrainTestData():
    df = getHistoricalData()
    df = addTemperatureFeatures(df)
    df = addTimeFeatures(df)

    df.dropna(inplace=True)

    features = [col for col in df.columns if col not in ["timestamp", "consumption", "year"]]
    X = df[features]
    y = df["consumption"]

    xTrain = X[df["year"] < 2025]
    yTrain = y[df["year"] < 2025]
    xTest = X[df["year"] == 2025]
    yTest = y[df["year"] == 2025]

    print(f"Data připravena! Trénovací sada: {xTrain.shape}, Testovací sada: {xTest.shape}")
    print(f"Chybějící hodnoty po opravě:\n{xTrain.isnull().sum()}")
    return xTrain, xTest, yTrain, yTest

def updateProcessedData():
    with getDb() as conn:
        query = """
        SELECT timestamp, consumption, temperature
        FROM energyData
        WHERE time(timestamp) != '23:59:59'
        ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df = addTemperatureFeatures(df)
    df = addTimeFeatures(df)
    df.bfill(inplace=True)
    df = df.round(2)

    with getDb() as conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            query = """
            INSERT INTO processedData (
                timestamp, consumption,
                temperature, temperatureLag1, temperatureLag2, temperatureLag3, temperatureLag24,
                temperatureRoll3h, temperatureRoll6h, temperatureRoll12h, temperatureRoll24h,
                month, dayOfWeek, isWeekend, year, hour, day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(timestamp) DO UPDATE SET
                consumption=excluded.consumption,
                temperature=excluded.temperature,
                temperatureLag1=excluded.temperatureLag1,
                temperatureLag2=excluded.temperatureLag2,
                temperatureLag3=excluded.temperatureLag3,
                temperatureLag24=excluded.temperatureLag24,
                temperatureRoll3h=excluded.temperatureRoll3h,
                temperatureRoll6h=excluded.temperatureRoll6h,
                temperatureRoll12h=excluded.temperatureRoll12h,
                temperatureRoll24h=excluded.temperatureRoll24h,
                month=excluded.month,
                dayOfWeek=excluded.dayOfWeek,
                isWeekend=excluded.isWeekend,
                year=excluded.year,
                hour=excluded.hour,
                day=excluded.day
            """
            cursor.execute(query, (
                row["timestamp"].isoformat(), row["consumption"],
                row["temperature"], row["temperatureLag1"], row["temperatureLag2"], row["temperatureLag3"], row["temperatureLag24"],
                row["temperatureRoll3h"], row["temperatureRoll6h"], row["temperatureRoll12h"], row["temperatureRoll24h"],
                row["month"], row["dayOfWeek"], row["isWeekend"], row["year"], row["hour"], row["day"]
            ))
        conn.commit()

############################################################
#       PROZATIMNÍ PŘEDPOVĚD POČASÍ NA 16 DNÍ DOPŘEDU      #
############################################################
def getFveCoordinates():
    with getDb() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT latitude, longitude FROM fvePanels WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return row["latitude"], row["longitude"]
        else:
            raise ValueError("❌ FVE panel s ID 1 nebyl nalezen.")

def fetchTemperatureForecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m"
        f"&forecast_days=16"
        f"&timezone=Europe/Prague"
    )

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        times = data["hourly"]["time"]
        temps = data["hourly"]["temperature_2m"]
        return list(zip(times, temps))
    else:
        raise RuntimeError(f"❌ Chyba při načítání teplot: {response.status_code} - {response.text}")

def saveTemperatures(forecast_data):
    with getDb() as conn:
        cursor = conn.cursor()

        for time_str, temp in forecast_data:
            timestamp = datetime.datetime.fromisoformat(time_str).replace(minute=0, second=0).isoformat(timespec="seconds")

            if timestamp.endswith("T23:59:59"):
                continue

            cursor.execute("""
                SELECT temperature FROM energyData WHERE timestamp = ?
            """, (timestamp,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE energyData SET temperature = ? WHERE timestamp = ?
                """, (temp, timestamp))
            else:
                cursor.execute("""
                    INSERT INTO energyData (timestamp, temperature)
                    VALUES (?, ?)
                """, (timestamp, temp))

        conn.commit()
        print(f"✅ Teploty z Open-Meteo byly úspěšně zapsány do tabulky energyData.")
        
def main():
    lat, lon = getFveCoordinates()
    forecast_data = fetchTemperatureForecast(lat, lon)
    saveTemperatures(forecast_data)
    updateProcessedData()
    print("✅ Tabulka processedData byla úspěšně aktualizována!")

if __name__ == "__main__":
    main()