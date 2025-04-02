"""
Modul pro stahování cen elektřiny a jejich ukládání do databáze.

Vstup: Data o cenách a množství elektřiny z API OTE-ČR.
Výstup: Aktualizovaná tabulka `energyPrices` v databázi s timestampem.
Spolupracuje s: database.
"""

import datetime
import re
import requests
from database import getDb

# URL pro stažení dat
apiUrl = "https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data"

def extract_date_from_title(title):
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", title)
    if match:
        day, month, year = map(int, match.groups())
        return datetime.date(year, month, day)
    else:
        raise ValueError("❌ Nelze najít datum v názvu grafu.")

def fetchPrices():
    response = requests.get(apiUrl)
    if response.status_code != 200:
        print(f"⚠️ Chyba při stahování dat: {response.status_code} – {response.text}")
        return

    data = response.json()

    try:
        title = data.get("graph", {}).get("title", "")
        if not title:
            raise ValueError("Chybí klíč 'title' v části 'graph'.")
        target_date = extract_date_from_title(title)
    except Exception as e:
        print(f"❌ Chyba při získávání data z názvu grafu: {e}")
        return

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

        cursor.execute("""
            SELECT COUNT(*) FROM energyPrices
            WHERE DATE(timestamp) = ?;
        """, (target_date.isoformat(),))
        existingCount = cursor.fetchone()[0]

        if existingCount > 0:
            print(f"🔄 Data pro {target_date} již existují, aktualizuji je...")
        else:
            print(f"➕ Vkládám nové hodnoty pro {target_date}...")

        for hour in range(24):
            timestamp = datetime.datetime.combine(target_date, datetime.time(hour=hour)).isoformat()
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

    print(f"✅ Ceny a množství elektřiny pro {target_date} byly úspěšně uloženy.")

if __name__ == "__main__":
    fetchPrices()
