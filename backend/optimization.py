import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_NAME = os.path.abspath("backend/database.db")  # Absolutní cesta
JSON_OUTPUT_PATH = "optimized_schedule.json"

def fetch_setting(param_name, data_type=int):
    """Získá hodnotu parametru z tabulky settings a převede ji na požadovaný typ."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE paramName = ?", (param_name,))
    result = cursor.fetchone()
    conn.close()
    return data_type(result[0]) if result else None  # Konverze na zadaný datový typ

def fetch_data():
    """Načte potřebná data z databáze."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Načtení nastavení (jistič, fáze, override)
    breaker_current = fetch_setting("breakerCurrentPerPhase", int)
    phases = fetch_setting("phases", int)
    override_mode = fetch_setting("overrideMode", int)
    max_power = breaker_current * 230 * phases  # Výpočet max. výkonu v W

    # Načtení predikce spotřeby a výroby FVE
    cursor.execute("SELECT hour, consumptionPredicted, fvePredicted FROM energyData WHERE date = date('now', '+1 day')")
    energy_data = cursor.fetchall()
    
    # Načtení cen elektřiny
    cursor.execute("SELECT hodina, cena FROM energy_prices WHERE datum = date('now', '+1 day')")
    price_data = dict(cursor.fetchall())  # Převod na slovník {hodina: cena}
    
    conn.close()
    
    # Oprava None hodnot (aby se neobjevila TypeError chyba)
    energy_data = [(hour, consumption if consumption is not None else 0, fve if fve is not None else 0)
                   for hour, consumption, fve in energy_data]
    
    return energy_data, price_data, max_power, override_mode

def optimize_consumption():
    """Vypočítá optimální odběr elektřiny."""
    energy_data, price_data, max_power, override_mode = fetch_data()
    schedule = []
    
    for hour, consumption, fve in energy_data:
        net_consumption = max(consumption - fve, 0)  # Pokud je přebytek, nečerpáme ze sítě
        price = price_data.get(hour, 0)
        schedule.append({"hour": hour, "power_kW": round(min(net_consumption, max_power / 1000), 2), "price": price})
    
    # Seřadit podle ceny elektřiny (nejlevnější první)
    schedule.sort(key=lambda x: x["price"])

    # Přidání data
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    return {"date": tomorrow, "overrideMode": override_mode, "recommendedHours": schedule}

def save_to_json(data):
    """Uloží optimalizovaný plán do JSON."""
    with open(JSON_OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Optimalizace uložena do {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    optimized_schedule = optimize_consumption()
    save_to_json(optimized_schedule)
