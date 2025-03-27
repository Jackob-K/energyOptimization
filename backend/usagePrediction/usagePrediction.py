"""
Program načte předzpracovaná data z databáze, ověří existenci chybějících predikcí,
doplní chybějící predikce pomocí uloženého XGBoost modelu a uloží výsledné predikce
spotřeby energie zpět do databáze energyData.

Vstup: data z databáze processedData, uložený model (xgboostModel.pkl)
Výstup: aktualizované predikce v databázi energyData (sloupec consumptionPredicted)
Spolupracuje s: backend.database.getDb, backend.usagePrediction.dataProcessor
"""

import joblib
import pandas as pd
from backend.database import getDb

def loadModel(modelPath="backend/usagePrediction/Models/xgboostModel.pkl"):
    return joblib.load(modelPath)

def checkExistingPredictions():
    with getDb() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(DATE(timestamp)) FROM energyData 
            WHERE consumptionPredicted IS NULL 
            AND time(timestamp) != '23:59:59';
        """)
        firstMissingDate = cursor.fetchone()[0]

    if firstMissingDate:
        print(f"✅ Chybí predikce od {firstMissingDate}, budeme je generovat.")
        return firstMissingDate
    else:
        print("✅ Všechny predikce jsou doplněny.")
        return None

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

    print("📊 Načteno z processedData:\n", df.dtypes)
    return df

def savePredictionsToDb(predictions, processedDf):
    with getDb() as conn:
        cursor = conn.cursor()

        # Uložíme hodinové predikce
        for i, prediction in enumerate(predictions):
            timestampStr = processedDf.iloc[i]["timestamp"].isoformat()
            roundedPrediction = round(float(prediction), 2)

            print(f"Ukládám predikci: {timestampStr} → {roundedPrediction:.2f}")
            cursor.execute("""
                UPDATE energyData
                SET consumptionPredicted = ?
                WHERE timestamp = ?;
            """, (roundedPrediction, timestampStr))

        # Vytvoříme denní souhrn (timestamp = 23:59:59)
        processedDf["prediction"] = predictions
        processedDf["date"] = processedDf["timestamp"].dt.date

        dailySums = processedDf.groupby("date")["prediction"].sum().reset_index()

        for _, row in dailySums.iterrows():
            dateStr = row["date"].strftime("%Y-%m-%d")
            sumPrediction = round(float(row["prediction"]), 2)
            fullTimestamp = f"{dateStr}T23:59:59"

            print(f"➕ Ukládám souhrn za den {dateStr} → {sumPrediction:.2f}")

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
        print("✅ Všechny predikce byly uloženy, včetně denních souhrnů (23:59:59)!")

if __name__ == "__main__":
    firstMissingDate = checkExistingPredictions()

    if firstMissingDate is not None:
        processedDf = getProcessedData()
        
        if processedDf is None or processedDf.empty:
            print("❌ Nelze provést predikci: Chybí vstupní data v `processedData`!")
        else:
            model = loadModel()
            expectedColumns = model.get_booster().feature_names

            processedDf = processedDf[processedDf["timestamp"] >= firstMissingDate]
            modelInput = processedDf[expectedColumns]

            predictions = model.predict(modelInput)

            print("📊 Prvních 10 predikcí:", predictions[:10])
            savePredictionsToDb(predictions, processedDf)

            print("✅ Předpověď spotřeby byla doplněna od prvního chybějícího data až do dneška +7 dní.")
    else:
        print("✅ Žádná predikce nechybí. Není třeba nic aktualizovat.")
