"""
Modul pro optimalizaci spotřeby energie na základě predikovaných dat a cen elektřiny.

Vstup: Predikce spotřeby a výroby FVE, ceny elektřiny, parametry jističe.
Výstup: Optimalizovaný plán spotřeby uložený v JSON souboru.
Spolupracuje s: SQLite databází.
"""

# Standardní knihovny
import os
import json
import sqlite3
from datetime import datetime, timedelta

# Konstanty
dbName = os.path.abspath("backend/database.db")  # Absolutní cesta
jsonOutputPath = "optimized_schedule.json"

def fetchSetting(paramName, dataType=int):
    """fetchSetting"""
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE paramName = ?", (paramName,))
    result = cursor.fetchone()
    conn.close()
    return dataType(result[0]) if result else None  

def fetchData():
    """fetchData"""
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()

    breakerCurrent = fetchSetting("breakerCurrentPerPhase", int)
    phases = fetchSetting("phases", int)
    overrideMode = fetchSetting("overrideMode", int)
    maxPower = breakerCurrent * 230 * phases  

    cursor.execute("SELECT hour, consumptionPredicted, fvePredicted FROM energyData WHERE date = date('now', '+1 day')")
    energyData = cursor.fetchall()
    
    cursor.execute("SELECT hodina, cena FROM energy_prices WHERE datum = date('now', '+1 day')")
    priceData = dict(cursor.fetchall())  
    
    conn.close()
    
    energyData = [(hour, consumption if consumption is not None else 0, fve if fve is not None else 0)
                   for hour, consumption, fve in energyData]
    
    return energyData, priceData, maxPower, overrideMode

def optimizeConsumption():
    """optimizeConsumption"""
    energyData, priceData, maxPower, overrideMode = fetchData()
    schedule = []
    
    for hour, consumption, fve in energyData:
        netConsumption = max(consumption - fve, 0)  
        price = priceData.get(hour, 0)
        schedule.append({"hour": hour, "power_kW": round(min(netConsumption, maxPower / 1000), 2), "price": price})
    
    schedule.sort(key=lambda x: x["price"])  

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    return {"date": tomorrow, "overrideMode": overrideMode, "recommendedHours": schedule}

def saveToJson(data):
    """saveToJson"""
    with open(jsonOutputPath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Optimalizace uložena do {jsonOutputPath}")

if __name__ == "__main__":
    optimizedSchedule = optimizeConsumption()
    saveToJson(optimizedSchedule)
