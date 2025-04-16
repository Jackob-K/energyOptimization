"""
Program načte předzpracovaná data z databáze, ověří existenci chybějících predikcí,
doplní chybějící predikce pomocí uloženého XGBoost modelu a uloží výsledné predikce
spotřeby energie zpět do databáze energyData.

Vstup: data z databáze processedData, uložený model (xgboostModel.pkl)
Výstup: aktualizované predikce v databázi energyData (sloupec consumptionPredicted)
Spolupracuje s: database.getDb, dataProcessor
"""

import joblib
import pandas as pd
from database import getDb

from datetime import datetime

def loadModel(modelPath="backend/Models/xgboostModel.pkl"):
    return joblib.load(modelPath)

def getProcessedData():
    with getDb() as conn:
        query = """
        SELECT timestamp, month, dayOfWeek, isWeekend, hour, day,
               consumptionLag1, consumptionLag2, consumptionLag3, consumptionLag24,
               consumptionRoll3h, consumptionRoll6h, consumptionRoll12h, consumptionRoll24h,
               temperature, temperatureLag1, temperatureLag2, temperatureLag3, temperatureLag24,
               temperatureRoll3h, temperatureRoll6h, temperatureRoll12h, temperatureRoll24h
        FROM processedData
        ORDER BY timestamp;
        """
        df = pd.read_sql_query(query, conn)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    numericCols = df.columns.difference(["timestamp"])
    df[numericCols] = df[numericCols].apply(pd.to_numeric, errors="coerce")

    return df

def savePredictionsToDb(predictions, processedDf):
    with getDb() as conn:
        cursor = conn.cursor()

        for i, prediction in enumerate(predictions):
            timestampStr = processedDf.iloc[i]["timestamp"].isoformat()
            roundedPrediction = round(float(prediction), 2)

            cursor.execute("""
                UPDATE energyData
                SET consumptionPredicted = ?
                WHERE timestamp = ?;
            """, (roundedPrediction, timestampStr))

        processedDf = processedDf.copy()
        processedDf.loc[:, "prediction"] = predictions
        processedDf.loc[:, "date"] = processedDf["timestamp"].dt.date

        dailySums = processedDf.groupby("date")["prediction"].sum().reset_index()

        for _, row in dailySums.iterrows():
            dateStr = row["date"].strftime("%Y-%m-%d")
            sumPrediction = round(float(row["prediction"]), 2)
            fullTimestamp = f"{dateStr}T23:59:59"

            cursor.execute("""
                UPDATE energyData
                SET consumptionPredicted = ?
                WHERE timestamp = ?;
            """, (sumPrediction, fullTimestamp))

            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO energyData (timestamp, consumptionPredicted)
                    VALUES (?, ?);
                """, (fullTimestamp, sumPrediction))

        conn.commit()

def main():
    processedDf = getProcessedData()

    # Zjistíme poslední timestamp, pro který máme vstupní teplotu
    validDf = processedDf.dropna(subset=["temperature"])  # nebo i lagy teploty
    if validDf.empty:
        print("❌ Žádná validní data pro predikci (chybí teploty).")
        return

    lastTimestamp = validDf["timestamp"].max()
    print(f"✅ Provádím predikci až do {lastTimestamp}")

    # Filtrovaná data pro predikci
    model = loadModel()
    expectedColumns = model.get_booster().feature_names
    modelInputDf = processedDf[(processedDf["timestamp"] <= lastTimestamp)]
    modelInput = modelInputDf[expectedColumns]

    predictions = model.predict(modelInput)

    savePredictionsToDb(predictions, modelInputDf)
    print("✅ Predikce proběhla úspěšně!")

if __name__ == "__main__":
    main()
