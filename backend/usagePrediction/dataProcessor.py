import numpy as np
import pandas as pd
from backend.database import get_db


def getHistoricalData(date: str, hour: int = None):
    """Načte historická data z databáze.
    
    - Pokud je `hour` zadána, vrátí konkrétní hodinová data.
    - Pokud `hour=None`, vrátí denní souhrn (`hour=24`).
    """
    conn = get_db()
    query = """
    SELECT date, hour, fveProduction, consumption, temperatureMax, temperatureMin
    FROM historicalData
    WHERE date = ?
    """
    
    params = [date]
    if hour is not None:
        query += " AND hour = ?"
        params.append(hour)
    else:
        query += " AND hour = 24"  # Pokud nejsou dostupná hodinová data, vezmeme denní sumu

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df if not df.empty else None

def splitDailyConsumption(df):
    """Rozdělí sumární denní spotřebu na hodinové hodnoty podle odhadu denního profilu."""
    profile = np.array([0.05, 0.04, 0.03, 0.02, 0.02, 0.03, 0.05, 0.07, 0.09, 0.1, 0.1, 0.08,
                        0.07, 0.06, 0.06, 0.06, 0.07, 0.09, 0.1, 0.09, 0.07, 0.06, 0.05, 0.05])
    profile = profile / profile.sum()  # Normalizace na 100%

    hourlyConsumption = df["consumption"].iloc[0] * profile
    hourlyDF = pd.DataFrame({"hour": range(24), "consumption": hourlyConsumption})

    return hourlyDF

def testDailyConsumptionSplit(date: str):
    """Testovací funkce - vypíše rozdělené denní hodnoty na hodinové."""
    df = getHistoricalData(date, 24)  # Načteme denní sumu
    
    if df is None:
        print(f"⚠️ Pro datum {date} nejsou dostupná data v DB!")
        return
    
    hourlyData = splitDailyConsumption(df)
    print(f"\nRozdělení denní spotřeby pro {date} na hodinové hodnoty:\n")
    print(hourlyData)

# Pokud spustíme tento soubor samostatně, otestuje funkci
if __name__ == "__main__":
    testDailyConsumptionSplit("2024-03-13")
