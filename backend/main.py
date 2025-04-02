"""
Hlavní API server aplikace.

Spouští:
- FastAPI backend server
- MQTT listener (běžící ve vlákně)
- Denní pipeline (naplánovaná pomocí APScheduler)

Vstup:
- API požadavky z klientské aplikace

Výstup:
- Data o spotřebě, optimalizovaný plán, MQTT nastavení

Spolupracuje s:
- database.py, apiHandlers.py, mqttListener.py, scrape.py, fvePrediction.py, dataProcessor.py, usagePrediction.py, optimization.py
"""

# 📦 Standardní knihovny
import os
import json
import threading
import logging

# 🌐 Externí knihovny
import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

# 🧩 Lokální moduly
from database import getEnergyData, createDatabase
import apiHandlers as apiHandlers
from mqttListener import startMqttListener
from scrape import fetchPrices
from fvePrediction import main as fvePredictionMain
from dataProcessor import main as dataProcessorMain
from usagePrediction import main as usagePredictionMain
from optimization import main as optimizationMain

# 📝 Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🚀 Inicializace FastAPI aplikace
app = FastAPI()

# 🌍 CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📡 API Endpointy
@app.get("/")
async def root():
    return {"message": "✅ Backend běží správně!"}


@app.get("/energy-data")
async def energyData():
    return getEnergyData()


@app.get("/optimizedSchedule")
async def optimizedSchedule():
    """Vrací JSON s optimalizovaným plánem ze souboru."""
    path = os.path.join(os.path.dirname(__file__), "optimizedSchedule.json")
    try:
        with open(path, "r") as file:
            data = json.load(file)
        return Response(content=json.dumps(data, indent=4, ensure_ascii=False), media_type="application/json")
    except FileNotFoundError:
        return {"error": "❌ Soubor optimizedSchedule.json nebyl nalezen."}


# 🔄 Denní pipeline funkcí
def runDailyPipeline():
    logger.info("🚀 Spouštím denní pipeline...")

    try:
        fetchPrices()
        logger.info("✅ [1/5] Načteny ceny")

        fvePredictionMain()
        logger.info("✅ [2/5] Predikce FVE dokončena")

        dataProcessorMain()
        logger.info("✅ [3/5] Zpracování dat dokončeno")

        usagePredictionMain()
        logger.info("✅ [4/5] Predikce spotřeby dokončena")

        optimizationMain()
        logger.info("✅ [5/5] Optimalizace dokončena")

        logger.info("🎯 Denní pipeline úspěšně dokončena")

    except Exception as e:
        logger.error(f"❌ Chyba v denní pipeline: {e}")


# ⚙️ FastAPI startup event
@app.on_event("startup")
def startupEvent():
    logger.info("🚀 Spouštím MQTT listener (startup)")
    mqttThread = threading.Thread(target=startMqttListener, daemon=True)
    mqttThread.start()

    scheduler = BackgroundScheduler()
    scheduler.add_job(runDailyPipeline, "cron", hour=14, minute=47)
    scheduler.start()
    logger.info("📅 Denní pipeline naplánována na 14:47")


# 📡 Načtení dalších API endpointů
app.include_router(apiHandlers.router)


# 🧪 Lokální spuštění skriptu
if __name__ == "__main__":
    print("🚀 Spouštím backend + MQTT listener...")
    createDatabase()

    mqttThread = threading.Thread(target=startMqttListener, daemon=True)
    mqttThread.start()

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
