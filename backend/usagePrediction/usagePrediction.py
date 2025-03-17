"""
Program načte předzpracovaná data z databáze, ověří existenci chybějících predikcí,
doplní chybějící predikce pomocí uloženého XGBoost modelu a uloží výsledné predikce
spotřeby energie zpět do databáze energyData.

Vstup: data z databáze processedData, uložený model (xgboost_model.pkl)
Výstup: aktualizované predikce v databázi energyData (sloupec consumptionPredicted)
Spolupracuje s: backend.database.getDb, backend.usagePrediction.dataProcessor
"""
# Externí knihovny
import joblib
import pandas as pd

# Lokální importy
from backend.database import getDb

def loadModel(modelPath="backend/usagePrediction/Models/xgboost_model.pkl"):
    """loadModel"""
    return joblib.load(modelPath)

def checkExistingPredictions():
    """checkExistingPredictions"""
    with getDb() as conn:
        cursor = conn.cursor()
        
        # Výpis prvních 10 hodnot pro kontrolu
        cursor.execute("""
            SELECT MIN(date) FROM energyData 
            WHERE consumptionPredicted IS NULL 
            AND hour < 24;
        """)
        results = cursor.fetchall()
        print("🔍 Kontrola hodnot v databázi:")
        for row in results:
            print(row)

        # Kontrola chybějících predikcí
        cursor.execute("""
            SELECT MIN(date) FROM energyData 
            WHERE consumptionPredicted IS NULL 
            AND hour < 24;
        """)
        firstMissingDate = cursor.fetchone()[0]

    if firstMissingDate is not None:
        print(f"✅ Chybí predikce od {firstMissingDate}, budeme je generovat.")
        return firstMissingDate
    else:
        print("✅ Všechny historické predikce jsou doplněny, není třeba generovat nové.")
        return None


def getProcessedData():
    """getProcessedData"""
    with getDb() as conn:
        query = """
        SELECT date, hour, month, day_of_week, is_weekend,
               consumption_lag_1, consumption_lag_2, consumption_lag_3, consumption_lag_24,
               consumption_roll_3h, consumption_roll_6h, consumption_roll_12h, consumption_roll_24h,
               temperature, temperature_lag_1, temperature_lag_2, temperature_lag_3, temperature_lag_24,
               temperature_roll_3h, temperature_roll_6h, temperature_roll_12h, temperature_roll_24h
        FROM processedData
        WHERE hour < 24
        ORDER BY date, hour;
        """
        processedDf = pd.read_sql_query(query, conn)

    processedDf["date"] = pd.to_datetime(processedDf["date"])

    numericCols = [
        "consumption_lag_1", "consumption_lag_2", "consumption_lag_3", "consumption_lag_24",
        "consumption_roll_3h", "consumption_roll_6h", "consumption_roll_12h", "consumption_roll_24h",
        "temperature", "temperature_lag_1", "temperature_lag_2", "temperature_lag_3", "temperature_lag_24",
        "temperature_roll_3h", "temperature_roll_6h", "temperature_roll_12h", "temperature_roll_24h"
    ]
    processedDf[numericCols] = processedDf[numericCols].apply(pd.to_numeric, errors="coerce")

    print("📊 Datové typy po opravě:\n", processedDf.dtypes)

    return processedDf

def savePredictionsToDb(predictions, processedDf):
    """savePredictionsToDb"""
    with getDb() as conn:
        cursor = conn.cursor()
        for i, prediction in enumerate(predictions):
            dateStr = processedDf.iloc[i]["date"].strftime("%Y-%m-%d")
            hour = int(processedDf.iloc[i]["hour"])
            roundedPrediction = round(float(prediction), 2)

            print(f"Ukládám predikci: {dateStr} {hour}:00 → {roundedPrediction:.2f}")

            query = """
            UPDATE energyData
            SET consumptionPredicted = ?
            WHERE date(date) = date(?) AND hour = ?;
            """
            cursor.execute(query, (roundedPrediction, dateStr, hour))

        conn.commit()
        print("✅ Všechny predikce byly uloženy do databáze se zaokrouhlením na 2 desetinná místa!")

if __name__ == "__main__":
    # Zjistíme první den, kde chybí predikce
    firstMissingDate = checkExistingPredictions()

    if firstMissingDate is not None:
        # Načtení zpracovaných dat z `processedData`
        processedDf = getProcessedData()
        
        if processedDf is None or processedDf.empty:
            print("❌ Nelze provést predikci: Chybí vstupní data v `processedData`!")
        else:
            # Načtení modelu
            model = loadModel()

            # Ověření správného pořadí sloupců
            expectedColumns = model.get_booster().feature_names
            print("✅ Model očekává tyto sloupce:", expectedColumns)

            # Odfiltrujeme pouze data od `firstMissingDate`, ale `date` zachováme!
            processedDf = processedDf[processedDf["date"] >= firstMissingDate]

            # Seřadíme sloupce podle trénovacích dat modelu (bez odstranění `date`)
            modelInput = processedDf[expectedColumns]

            # Provádění predikce
            predictions = model.predict(modelInput)

            # Uložení predikcí do databáze
            print("📊 Prvních 10 predikcí:", predictions[:10])
            savePredictionsToDb(predictions, processedDf)

            print("✅ Předpověď spotřeby byla doplněna od prvního chybějícího data až do dneška +7 dní.")
    else:
        print("✅ Žádná predikce nechybí. Není třeba nic aktualizovat.")
