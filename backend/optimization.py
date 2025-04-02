import json
import os
import numpy as np
from datetime import datetime, timedelta
from database import getDb, getSetting, insertBatteryPlan

jsonOutputPath = os.path.join(os.path.dirname(__file__), "optimizedSchedule.json")

def logOptimizationResult(date, baseline, optimized, saving):
    """Uloží denní úsporu do tabulky optimizationLog"""
    with getDb() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimizationLog (
                date TEXT PRIMARY KEY,
                baselineCost REAL,
                optimizedCost REAL,
                saving REAL,
                created_at TEXT
            );
        """)
        cursor.execute("""
            INSERT INTO optimizationLog (date, baselineCost, optimizedCost, saving, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                baselineCost = excluded.baselineCost,
                optimizedCost = excluded.optimizedCost,
                saving = excluded.saving,
                created_at = excluded.created_at;
        """, (date, baseline, optimized, saving, datetime.now().isoformat()))
        conn.commit()

def fetchData():
    with getDb() as conn:
        cursor = conn.cursor()

        breakerCurrent = int(getSetting("breakerCurrentPerPhase"))
        phases = int(getSetting("phases"))
        overrideMode = int(getSetting("overrideMode"))
        maxPower = breakerCurrent * 230 * phases

        batteryMaxCharge = float(getSetting("batteryMaxChargeKW"))
        batteryMaxDischarge = float(getSetting("batteryMaxDischargeKW"))

        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()

        cursor.execute("""
            SELECT timestamp, consumptionPredicted, fvePredicted
            FROM energyData
            WHERE DATE(timestamp) = ?
        """, (tomorrow,))
        energyData = cursor.fetchall()

        cursor.execute("""
            SELECT STRFTIME('%H', timestamp) as hour, price
            FROM energyPrices
            WHERE DATE(timestamp) = ? AND price IS NOT NULL
        """, (tomorrow,))
        priceRows = cursor.fetchall()

    if not energyData:
        print("❌ Chybí predikovaná data v `energyData` pro zítřek.")
        return None

    if not priceRows:
        print("❌ Chybí ceny v `energyPrices` pro zítřek.")
        return None

    priceData = {int(row["hour"]): row["price"] for row in priceRows}
    pricesOnly = list(priceData.values())

    if not pricesOnly:
        print("❌ Nebyly nalezeny žádné validní ceny pro výpočet.")
        return None

    lowThreshold = np.percentile(pricesOnly, 25)
    highThreshold = np.percentile(pricesOnly, 75)

    return energyData, priceData, overrideMode, batteryMaxCharge, batteryMaxDischarge, lowThreshold, highThreshold


def optimizeConsumption():
    fetched = fetchData()
    if not fetched:
        print("❌ Optimalizace neproběhla – chybějící nebo nekompletní data.")
        return None

    energyData, priceData, overrideMode, maxCharge, maxDischarge, lowThres, highThres = fetched
    schedule = []
    total_no_opt = 0
    total_opt = 0

    for row in energyData:
        timestamp = row["timestamp"]
        hour = int(timestamp[11:13])
        consumption = row["consumptionPredicted"] or 0
        fve = row["fvePredicted"] or 0
        price = priceData.get(hour)

        if price is None:
            print(f"⚠️ Přeskakuji hodinu {hour}: chybí cena.")
            continue

        netConsumption = max(consumption - fve, 0)
        baseline_cost = netConsumption * price / 1000
        total_no_opt += baseline_cost

        if price <= lowThres:
            batteryAction = "charge"
            batteryPower = maxCharge
        elif price >= highThres:
            batteryAction = "discharge"
            batteryPower = maxDischarge
        else:
            batteryAction = "idle"
            batteryPower = 0

        adjusted_power = netConsumption
        if batteryAction == "charge":
            adjusted_power += batteryPower
        elif batteryAction == "discharge":
            adjusted_power -= batteryPower

        adjusted_power = max(adjusted_power, 0)
        optimized_cost = adjusted_power * price / 1000
        total_opt += optimized_cost

        insertBatteryPlan(timestamp, batteryAction, batteryPower)

        schedule.append({
            "hour": hour,
            "power_kW": round(adjusted_power, 2),
            "price": price,
            "batteryAction": batteryAction,
            "batteryPowerTargetKw": batteryPower
        })

    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    saving = round(total_no_opt - total_opt, 2)
    logOptimizationResult(tomorrow, round(total_no_opt, 2), round(total_opt, 2), saving)

    return {"date": tomorrow, "overrideMode": overrideMode, "recommendedHours": schedule}


def saveToJson(data):
    with open(jsonOutputPath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Optimalizace uložena do {jsonOutputPath}")

def main():
    optimizedSchedule = optimizeConsumption()
    if optimizedSchedule:
        saveToJson(optimizedSchedule)

if __name__ == "__main__":
    main()
