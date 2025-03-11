import requests
import sqlite3
import datetime
from database import get_db

API_URL = "https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh/@@chart-data"  # SPRÁVNÁ URL API

def fetch_prices():
    """Stáhne ceny elektřiny a množství energie na zítřejší den a uloží je do databáze."""
    response = requests.get(API_URL)
    if response.status_code != 200:
        print(f"⚠️ Chyba při stahování dat: {response.status_code} – {response.text}")
        return
    
    data = response.json()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    energy_data = {}
    price_data = {}

    for line in data["data"]["dataLine"]:
        if line["title"] == "Množství (MWh)":
            for point in line["point"]:
                hour = int(point["x"]) - 1
                energy_data[hour] = point["y"]

        elif line["title"] == "Cena (EUR/MWh)":
            for point in line["point"]:
                hour = int(point["x"]) - 1
                price_data[hour] = point["y"]

    conn = get_db()
    cursor = conn.cursor()

    # Zjistíme, jestli už máme data pro zítřek
    cursor.execute("SELECT COUNT(*) FROM energy_prices WHERE datum = ?", (tomorrow,))
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        print(f"🔄 Data pro {tomorrow} již existují, aktualizuji je...")

        for hour in range(24):
            cena = price_data.get(hour, None)
            mnozstvi = energy_data.get(hour, None)

            cursor.execute("""
                UPDATE energy_prices 
                SET cena = ?, mnozstvi = ? 
                WHERE datum = ? AND hodina = ?;
            """, (cena, mnozstvi, tomorrow, hour))
    else:
        print(f"➕ Vkládám nové hodnoty pro {tomorrow}...")

        for hour in range(24):
            cena = price_data.get(hour, None)
            mnozstvi = energy_data.get(hour, None)

            cursor.execute("""
                INSERT INTO energy_prices (datum, hodina, cena, mnozstvi)
                VALUES (?, ?, ?, ?);
            """, (tomorrow, hour, cena, mnozstvi))

    conn.commit()
    conn.close()
    print(f"✅ Ceny a množství elektřiny pro {tomorrow} byly úspěšně aktualizovány nebo vloženy.")

if __name__ == "__main__":
    fetch_prices()
