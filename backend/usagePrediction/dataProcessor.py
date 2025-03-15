import pandas as pd
import numpy as np
from backend.database import get_db

def get_historical_data():
    """Načte historická data z databáze a zajistí správné datové typy."""
    with get_db() as conn:
        query = """
        SELECT date, hour, consumption, temperature
        FROM energyData
        WHERE hour < 24
        ORDER BY date, hour
        """
        df = pd.read_sql_query(query, conn)

    # ✅ Oprava typů – všechny hodnoty převedeme na čísla
    df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")

    df["date"] = pd.to_datetime(df["date"])  # Převod datumu na datetime
    df["year"] = df["date"].dt.year  # Přidání sloupce s rokem

    return df

def add_lag_features(df, lags=[1, 2, 3, 24]):
    """Přidá posunuté (lag) hodnoty spotřeby."""
    for lag in lags:
        df[f"consumption_lag_{lag}"] = df["consumption"].shift(lag)
    return df

def add_rolling_features(df, window_sizes=[3, 6, 12, 24]):
    """Přidá klouzavé průměry spotřeby."""
    for window in window_sizes:
        df[f"consumption_roll_{window}h"] = df["consumption"].rolling(window=window, min_periods=1).mean()
    return df

def add_temperature_features(df, lags=[1, 2, 3, 24], window_sizes=[3, 6, 12, 24]):
    """Přidá lagy a klouzavé průměry teploty."""
    for lag in lags:
        df[f"temperature_lag_{lag}"] = df["temperature"].shift(lag)

    for window in window_sizes:
        df[f"temperature_roll_{window}h"] = df["temperature"].rolling(window=window, min_periods=1).mean()

    return df

def add_time_features(df):
    """Přidá časové proměnné (den v týdnu, měsíc, pracovní den)."""
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.weekday
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    return df

def handle_missing_values(df):
    """Vyplní chybějící hodnoty lineární interpolací."""
    df.interpolate(method="linear", inplace=True)
    return df

def prepare_train_test_data():
    """Připraví data pro trénování modelu ML s dělením podle roku."""
    df = get_historical_data()

    # ✅ Přidáme feature engineering prvky
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_temperature_features(df)
    df = add_time_features(df)

    # ✅ Odstraníme řádky s NaN hodnotami (způsobené lagy)
    df.dropna(inplace=True)

    # ✅ Vybereme relevantní proměnné
    features = [col for col in df.columns if col not in ["date", "consumption", "year"]]
    X = df[features]
    y = df["consumption"]

    # ✅ Rozdělení trénovacích a testovacích dat podle roku
    X_train = X[df["year"] < 2025]  # Trénujeme na všech datech před 2025
    y_train = y[df["year"] < 2025]
    X_test = X[df["year"] == 2025]  # Testujeme na datech z roku 2025
    y_test = y[df["year"] == 2025]

    print(f"✅ Data připravena! Trénovací sada: {X_train.shape}, Testovací sada: {X_test.shape}")
    print(f"📌 Chybějící hodnoty po opravě:\n{X_train.isnull().sum()}")

    return X_train, X_test, y_train, y_test

import pandas as pd
from backend.database import get_db

def update_processed_data():
    """Načte data z energyData, provede výpočty, zaokrouhlí je a uloží do processedData."""
    with get_db() as conn:
        # 1️⃣ Načíst data z `energyData`
        query = """
        SELECT date, hour, consumption, temperature
        FROM energyData
        WHERE hour < 24  -- Nebereme souhrnnou hodinu 24
        ORDER BY date, hour;
        """
        df = pd.read_sql_query(query, conn)

    # 2️⃣ Převést `date` na datetime formát
    df["date"] = pd.to_datetime(df["date"])

    # 3️⃣ Přidat lagy a klouzavé průměry
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_temperature_features(df)

    # 4️⃣ Přidat časové proměnné
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.weekday
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # 5️⃣ Vyplnit chybějící hodnoty (backfill pro lagy)
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
    with get_db() as conn:
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
    update_processed_data()
    print("✅ Tabulka processedData byla úspěšně aktualizována!")
