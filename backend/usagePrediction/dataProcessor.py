"""
Program načítá historická data spotřeby energie a teploty z databáze,
vytváří doplňkové atributy (lagy, klouzavé průměry, časové atributy)
a připravuje data pro trénování ML modelu nebo je aktualizuje zpět do databáze.

Vstup: Data z databáze energyData
Výstup: Upravená data (X_train, X_test, y_train, y_test) nebo aktualizovaná tabulka processedData
Spolupracuje s: backend.database.getDb
"""

import pandas as pd
from backend.database import getDb

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
    print("🧪 Sloupce použité při trénování:")
    print(list(xTrain.columns)) 
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

if __name__ == "__main__":
    updateProcessedData()
    print("✅ Tabulka processedData byla úspěšně aktualizována!")