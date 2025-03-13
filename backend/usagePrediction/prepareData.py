import numpy as np
import pandas as pd
from backend.database import get_db
from backend.usagePrediction.dataProcessor import getHistoricalData

def getAllDailyData():
    """Načte denní souhrnná data (hour = 24) z databáze."""
    with get_db() as conn:
        query = """
        SELECT date, fveProduction, consumption, temperatureMax, temperatureMin
        FROM historicalData
        WHERE hour = 24  -- Pouze souhrnné denní záznamy
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn)

    return df if not df.empty else None

def splitDailyConsumption(df):
    """Rozdělí denní spotřebu na hodinové hodnoty podle odhadu denního profilu."""
    profile = np.array([0.05, 0.04, 0.03, 0.02, 0.02, 0.03, 0.05, 0.07, 0.09, 0.1, 0.1, 0.08,
                        0.07, 0.06, 0.06, 0.06, 0.07, 0.09, 0.1, 0.09, 0.07, 0.06, 0.05, 0.05])
    profile = profile / profile.sum()  # Normalizace na 100%

    hourly_data = []
    for _, row in df.iterrows():
        date = row["date"]
        dailyConsumption = row["consumption"]
        hourlyConsumption = dailyConsumption * profile  # Rozdělíme denní spotřebu

        for hour in range(24):
            hourly_data.append((date, hour, row["fveProduction"], hourlyConsumption[hour], row["temperatureMax"], row["temperatureMin"]))

    return hourly_data

def saveHourlyData(hourly_data):
    """Uloží vygenerovaná hodinová data zpět do databáze."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Vložíme nové hodnoty
        cursor.executemany("""
            INSERT INTO historicalData (date, hour, fveProduction, consumption, temperatureMax, temperatureMin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, hourly_data)

        conn.commit()
        print(f"✅ Uloženo {len(hourly_data)} hodinových záznamů do databáze.")

def prepareData():
    """Hlavní funkce - načte denní data, převede je na hodinová a uloží je do DB."""
    df_daily = getAllDailyData()

    if df_daily is None:
        print("⚠️ Nebyla nalezena žádná denní data v databázi!")
        return

    hourly_data = splitDailyConsumption(df_daily)
    saveHourlyData(hourly_data)

# Pokud spustíme tento soubor samostatně, otestujeme funkci
if __name__ == "__main__":
    prepareData()
