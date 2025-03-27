"""
Modul pro stahování cen elektřiny a jejich ukládání do databáze.

Vstup: Data o cenách a množství elektřiny z API OTE-ČR.
Výstup: Aktualizovaná tabulka `energyPrices` v databázi s timestampem.
Spolupracuje s: database.
"""

import datetime
import requests
from database import getDb

# URL pro stažení dat
apiUrl = "https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data"

def fetchPrices():
    response = requests.get(apiUrl)
    if response.status_code != 200:
        print(f"⚠️ Chyba při stahování dat: {response.status_code} – {response.text}")
        return

    data = response.json()
    tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)

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

    with getDb() as conn:
        cursor = conn.cursor()

        # Zjistíme, kolik záznamů už existuje pro daný den
        cursor.execute("""
            SELECT COUNT(*) FROM energyPrices
            WHERE DATE(timestamp) = ?;
        """, (tomorrow_date.isoformat(),))
        existingCount = cursor.fetchone()[0]

        if existingCount > 0:
            print(f"🔄 Data pro {tomorrow_date} již existují, aktualizuji je...")
        else:
            print(f"➕ Vkládám nové hodnoty pro {tomorrow_date}...")

        for hour in range(24):
            timestamp = datetime.datetime.combine(tomorrow_date, datetime.time(hour=hour)).isoformat()
            cena = priceData.get(hour)
            mnozstvi = energyData.get(hour)

            if existingCount > 0:
                cursor.execute("""
                    UPDATE energyPrices
                    SET price = ?, quantity = ?
                    WHERE timestamp = ?;
                """, (cena, mnozstvi, timestamp))
            else:
                cursor.execute("""
                    INSERT INTO energyPrices (timestamp, price, quantity)
                    VALUES (?, ?, ?);
                """, (timestamp, cena, mnozstvi))

        conn.commit()

    print(f"✅ Ceny a množství elektřiny pro {tomorrow_date} byly úspěšně uloženy.")

if __name__ == "__main__":
    fetchPrices()
