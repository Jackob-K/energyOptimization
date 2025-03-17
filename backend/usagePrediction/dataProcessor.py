"""
Program načítá historická data spotřeby energie a teploty z databáze,
vytváří doplňkové atributy (lagy, klouzavé průměry, časové atributy)
a připravuje data pro trénování ML modelu nebo je aktualizuje zpět do databáze.

Vstup: Data z databáze energyData
Výstup: Upravená data (X_train, X_test, y_train, y_test) nebo aktualizovaná tabulka processedData
Spolupracuje s: backend.database.getDb
"""

import pandas as pd
import numpy as np
from backend.database import getDb


def getHistoricalData():
    """getHistoricalData"""
    with getDb() as conn:
        query = """
        SELECT date, hour, consumption, temperature
        FROM energyData
        WHERE hour < 24
        ORDER BY date, hour
        """
        df = pd.read_sql_query(query, conn)

    df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    return df


def addLagFeatures(df, lags=[1, 2, 3, 24]):
    """addLagFeatures"""
    for lag in lags:
        df[f"consumption_lag_{lag}"] = df["consumption"].shift(lag)
    return df


def addRollingFeatures(df, windowSizes=[3, 6, 12, 24]):
    """addRollingFeatures"""
    for window in windowSizes:
        df[f"consumption_roll_{window}h"] = df["consumption"].rolling(window=window, min_periods=1).mean()
    return df


def addTemperatureFeatures(df, lags=[1, 2, 3, 24], windowSizes=[3, 6, 12, 24]):
    """addTemperatureFeatures"""
    for lag in lags:
        df[f"temperature_lag_{lag}"] = df["temperature"].shift(lag)

    for window in windowSizes:
        df[f"temperature_roll_{window}h"] = df["temperature"].rolling(window=window, min_periods=1).mean()
    return df


def addTimeFeatures(df):
    """addTimeFeatures"""
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.weekday
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    return df


def handleMissingValues(df):
    """handleMissingValues"""
    df.interpolate(method="linear", inplace=True)
    return df


def prepareTrainTestData():
    """prepareTrainTestData"""
    df = getHistoricalData()
    df = addLagFeatures(df)
    df = addRollingFeatures(df)
    df = addTemperatureFeatures(df)
    df = addTimeFeatures(df)

    df.dropna(inplace=True)

    features = [col for col in df.columns if col not in ["date", "consumption", "year"]]
    X = df[features]
    y = df["consumption"]

    XTrain = X[df["year"] < 2025]
    yTrain = y[df["year"] < 2025]
    XTest = X[df["year"] == 2025]
    yTest = y[df["year"] == 2025]

    print(f"Data připravena! Trénovací sada: {XTrain.shape}, Testovací sada: {XTest.shape}")
    print(f"Chybějící hodnoty po opravě:\n{XTrain.isnull().sum()}")

    return XTrain, XTest, yTrain, yTest


def updateProcessedData():
    """updateProcessedData"""
    with getDb() as conn:
        query = """
        SELECT date, hour, consumption, temperature
        FROM energyData
        WHERE hour < 24
        ORDER BY date, hour
        """
        df = pd.read_sql_query(query, conn)

    df["date"] = pd.to_datetime(df["date"])

    df = addLagFeatures(df)
    df = addRollingFeatures(df)
    df = addTemperatureFeatures(df)
    df = addTimeFeatures(df)

    df.bfill(inplace=True)

    # 6️⃣ **Zaokrouhlení hodnot**
    df = df.round({
        "consumption": 2,
        "consumption_lag_1": 2, "consumption_lag_2": 2, "consumption_lag_3": 2, "consumption_lag_24": 2,
        "consumption_roll_3h": 2, "consumption_roll_6h": 2, "consumption_roll_12h": 2, "consumption_roll_24h": 2,
        "temperature": 1, "temperature_lag_1": 1, "temperature_lag_2": 1, "temperature_lag_3": 1, "temperature_lag_24": 1,
        "temperature_roll_3h": 1, "temperature_roll_6h": 1, "temperature_roll_12h": 1, "temperature_roll_24h": 1
    })

    # 7️⃣ Uložit data do `processedData`
    with getDb() as conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            query = """
            INSERT INTO processedData (
                date, hour, consumption,
                consumption_lag_1, consumption_lag_2, consumption_lag_3, consumption_lag_24,
                consumption_roll_3h, consumption_roll_6h, consumption_roll_12h, consumption_roll_24h,
                temperature, temperature_lag_1, temperature_lag_2, temperature_lag_3, temperature_lag_24,
                temperature_roll_3h, temperature_roll_6h, temperature_roll_12h, temperature_roll_24h,
                month, day_of_week, is_weekend
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, hour) DO UPDATE SET
                consumption=excluded.consumption,
                consumption_lag_1=excluded.consumption_lag_1,
                consumption_lag_2=excluded.consumption_lag_2,
                consumption_lag_3=excluded.consumption_lag_3,
                consumption_lag_24=excluded.consumption_lag_24,
                consumption_roll_3h=excluded.consumption_roll_3h,
                consumption_roll_6h=excluded.consumption_roll_6h,
                consumption_roll_12h=excluded.consumption_roll_12h,
                consumption_roll_24h=excluded.consumption_roll_24h,
                temperature=excluded.temperature,
                temperature_lag_1=excluded.temperature_lag_1,
                temperature_lag_2=excluded.temperature_lag_2,
                temperature_lag_3=excluded.temperature_lag_3,
                temperature_lag_24=excluded.temperature_lag_24,
                temperature_roll_3h=excluded.temperature_roll_3h,
                temperature_roll_6h=excluded.temperature_roll_6h,
                temperature_roll_12h=excluded.temperature_roll_12h,
                temperature_roll_24h=excluded.temperature_roll_24h,
                month=excluded.month,
                day_of_week=excluded.day_of_week,
                is_weekend=excluded.is_weekend;
            """
            cursor.execute(query, (
                row["date"].strftime("%Y-%m-%d"),  # ✅ Oprava: Převod na string
                row["hour"], row["consumption"],
                row["consumption_lag_1"], row["consumption_lag_2"], row["consumption_lag_3"], row["consumption_lag_24"],
                row["consumption_roll_3h"], row["consumption_roll_6h"], row["consumption_roll_12h"], row["consumption_roll_24h"],
                row["temperature"], row["temperature_lag_1"], row["temperature_lag_2"], row["temperature_lag_3"], row["temperature_lag_24"],
                row["temperature_roll_3h"], row["temperature_roll_6h"], row["temperature_roll_12h"], row["temperature_roll_24h"],
                row["month"], row["day_of_week"], row["is_weekend"]
            ))
        conn.commit()

if __name__ == "__main__":
    updateProcessedData()
    print("✅ Tabulka processedData byla úspěšně aktualizována!")
