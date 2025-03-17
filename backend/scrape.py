"""
Modul pro stahování cen elektřiny a jejich ukládání do databáze.

Vstup: Data o cenách a množství elektřiny z API OTE-ČR.
Výstup: Aktualizovaná tabulka `energy_prices` v databázi.
Spolupracuje s: database.

Změny názvů funkcí a proměnných:
- fetch_prices → fetchPrices
"""

# Standardní knihovny
import datetime

# Externí knihovny
import requests
import sqlite3

# Lokální importy
from database import getDb

# Konstanta API URL
apiUrl = "https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data"

def fetchPrices():
    """fetchPrices"""
    response = requests.get(apiUrl)
    if response.status_code != 200:
        print(f"⚠️ Chyba při stahování dat: {response.status_code} – {response.text}")
        return
    
    data = response.json()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    energyData = {}
    priceData = {}

    for line in data["data"]["dataLine"]:
        if line["title"] == "Množství (MWh)":
            for point in line["point"]:
                hour = int(point["x"]) - 1
                energyData[hour] = point["y"]

        elif line["title"] == "Cena (EUR/MWh)":
            for point in line["point"]:
                hour = int(point["x"]) - 1
                priceData[hour] = point["y"]

    conn = getDb()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM energy_prices WHERE datum = ?", (tomorrow,))
    existingCount = cursor.fetchone()[0]

    if existingCount > 0:
        print(f"🔄 Data pro {tomorrow} již existují, aktualizuji je...")

        for hour in range(24):
            cena = priceData.get(hour, None)
            mnozstvi = energyData.get(hour, None)

            cursor.execute("""
                UPDATE energy_prices 
                SET cena = ?, mnozstvi = ? 
                WHERE datum = ? AND hodina = ?;
            """, (cena, mnozstvi, tomorrow, hour))
    else:
        print(f"➕ Vkládám nové hodnoty pro {tomorrow}...")

        for hour in range(24):
            cena = priceData.get(hour, None)
            mnozstvi = energyData.get(hour, None)

            cursor.execute("""
                INSERT INTO energy_prices (datum, hodina, cena, mnozstvi)
                VALUES (?, ?, ?, ?);
            """, (tomorrow, hour, cena, mnozstvi))

    conn.commit()
    conn.close()
    print(f"✅ Ceny a množství elektřiny pro {tomorrow} byly úspěšně aktualizovány nebo vloženy.")

if __name__ == "__main__":
    fetchPrices()
