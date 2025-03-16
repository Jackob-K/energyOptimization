import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backend.database import get_db
from backend.usagePrediction.dataProcessor import add_temperature_features

def load_model(model_path="backend/usagePrediction/Models/xgboost_model.pkl"):
    """Načte trénovaný model."""
    return joblib.load(model_path)

def check_existing_predictions():
    """Zjistí, zda jsou v databázi chybějící predikce a zda je třeba je doplnit."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(date) FROM energyData WHERE consumptionPredicted IS NULL;
        """)
        first_missing_date = cursor.fetchone()[0]

    if first_missing_date is not None:
        print(f"✅ Chybí predikce od {first_missing_date}, budeme je generovat.")
        return first_missing_date  # Vrátíme první chybějící datum
    else:
        print("✅ Všechny historické predikce jsou doplněny, není třeba generovat nové.")
        return None  # Predikce už jsou kompletní

def get_processed_data():
    """Načte zpracovaná data z `processedData` pro predikci a převede typy."""
    with get_db() as conn:
        query = """
        SELECT date, hour, month, day_of_week, is_weekend,
               consumption_lag_1, consumption_lag_2, consumption_lag_3, consumption_lag_24,
               consumption_roll_3h, consumption_roll_6h, consumption_roll_12h, consumption_roll_24h,
               temperature, temperature_lag_1, temperature_lag_2, temperature_lag_3, temperature_lag_24,
               temperature_roll_3h, temperature_roll_6h, temperature_roll_12h, temperature_roll_24h
        FROM processedData
        WHERE hour < 24  -- ✅ Načteme všechna historická data, nejen týden dopředu
        ORDER BY date, hour;
        """
        df = pd.read_sql_query(query, conn)

    # ✅ Oprava: Převod `date` zpět na `datetime`
    df["date"] = pd.to_datetime(df["date"])

    # ✅ Převod číselných sloupců na `float`
    cols_to_convert = [
        "consumption_lag_1", "consumption_lag_2", "consumption_lag_3", "consumption_lag_24",
        "consumption_roll_3h", "consumption_roll_6h", "consumption_roll_12h", "consumption_roll_24h",
        "temperature", "temperature_lag_1", "temperature_lag_2", "temperature_lag_3", "temperature_lag_24",
        "temperature_roll_3h", "temperature_roll_6h", "temperature_roll_12h", "temperature_roll_24h"
    ]
    df[cols_to_convert] = df[cols_to_convert].apply(pd.to_numeric, errors="coerce")

    print("📊 Datové typy po opravě:\n", df.dtypes)

    return df

def save_predictions_to_db(predictions, processed_df):
    """Uloží predikce do databáze se zaokrouhlením na dvě desetinná místa."""
    with get_db() as conn:
        cursor = conn.cursor()
        for i, prediction in enumerate(predictions):
            date_str = processed_df.iloc[i]["date"].strftime("%Y-%m-%d")  # ✅ Převod na string
            hour = int(processed_df.iloc[i]["hour"])  # ✅ Převod na integer
            rounded_prediction = round(float(prediction), 2)  # ✅ Zaokrouhlení na dvě desetinná místa

            print(f"Ukládám predikci: {date_str} {hour}:00 → {rounded_prediction:.2f}")  # ✅ Debugging výstup

            query = """
            UPDATE energyData
            SET consumptionPredicted = ?
            WHERE date(date) = date(?) AND hour = ?;
            """
            cursor.execute(query, (rounded_prediction, date_str, hour))

        conn.commit()
        print("✅ Všechny predikce byly uloženy do databáze se zaokrouhlením na 2 desetinná místa!")



if __name__ == "__main__":
    # ✅ Zjistíme první den, kde chybí predikce
    first_missing_date = check_existing_predictions()

    if first_missing_date is not None:
        # ✅ Načtení zpracovaných dat z `processedData`
        processed_df = get_processed_data()
        if processed_df is None or processed_df.empty:
            print("❌ Nelze provést predikci: Chybí vstupní data v `processedData`!")
        else:
            # ✅ Načtení modelu
            model = load_model()

            # ✅ Ověření správného pořadí sloupců
            expected_columns = model.get_booster().feature_names
            print("✅ Model očekává tyto sloupce:", expected_columns)

            # ✅ Odfiltrujeme pouze data od `first_missing_date`, ale `date` zachováme!
            processed_df = processed_df[processed_df["date"] >= first_missing_date]

            # ✅ Seřadíme sloupce podle trénovacích dat modelu (bez odstranění `date`)
            model_input = processed_df[expected_columns]

            # ✅ Provádění predikce
            predictions = model.predict(model_input)

            # ✅ Uložení predikcí do databáze
            print("📊 Prvních 10 predikcí:", predictions[:10])
            save_predictions_to_db(predictions, processed_df)

            print("✅ Předpověď spotřeby byla doplněna od prvního chybějícího data až do dneška +7 dní.")
