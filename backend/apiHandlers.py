"""
API modul pro práci s fotovoltaickými panely, zpracování nahraných souborů,
správu MQTT nastavení a komunikaci s databází.

Vstup: JSON data pro FVE panely, soubory s historickými daty (CSV, XLSX).
Výstup: Aktualizovaná databáze, odpovědi na API požadavky.
Spolupracuje s: database, mqttListener.
"""

# 📦 Standardní knihovny
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Optional

# 🌐 Externí knihovny
import pandas as pd
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 📁 Lokální moduly
import database
import mqttListener

# 🛠️ Logging
enableLogging = 1
logger = logging.getLogger(__name__)
if enableLogging:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🚀 FastAPI router
router = APIRouter()

# 📑 Globální konstanty
requiredColumns = {"date", "hour", "consumption", "temperature", "fveProduction"}


# 🧩 MODELY -----------------------------------------------------------------------

class FveData(BaseModel):
    """Model pro jedno FVE pole"""
    id: Optional[int] = None
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    power: float


class SolarParams(BaseModel):
    """Model pro import více FVE polí"""
    fveFields: List[FveData]


class FileUploadModel(BaseModel):
    """Model pro přenos souboru"""
    filename: str
    filedata: str  # base64 string


class ProcessFileModel(BaseModel):
    filename: str
    filedata: str


class MqttSettingsModel(BaseModel):
    """Model pro MQTT nastavení"""
    broker: str
    port: int
    topic: str
    username: str
    password: str


class SettingItem(BaseModel):
    id: int
    value: str


# 📤 UPLOAD A ZPRACOVÁNÍ SOUBORŮ -------------------------------------------------

@router.post("/upload/")
async def uploadFile(file: FileUploadModel):
    """Předá nahraný soubor endpointu pro zpracování"""
    if enableLogging:
        logger.info(f"📂 Přijímám soubor {file.filename}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/process-file/",
            json={"filename": file.filename, "filedata": file.filedata}
        )

    if response.status_code == 200:
        if enableLogging:
            logger.info(f"✅ Soubor {file.filename} úspěšně zpracován!")
    else:
        if enableLogging:
            logger.error(f"❌ Chyba při zpracování souboru: {response.text}")

    return response.json()


@router.post("/process-file/")
async def processUploadedFile(payload: ProcessFileModel):
    """Zpracuje nahraný soubor a uloží do databáze"""
    try:
        if enableLogging:
            logger.info(f"🔄 Zpracovávám soubor z paměti: {payload.filename}")

        decoded = base64.b64decode(payload.filedata)

        if payload.filename.endswith(".csv"):
            from io import StringIO
            df = pd.read_csv(StringIO(decoded.decode("utf-8")))
        elif payload.filename.endswith(".xlsx"):
            from io import BytesIO
            df = pd.read_excel(BytesIO(decoded))
        else:
            raise HTTPException(status_code=400, detail="Nepodporovaný formát souboru")

        if not requiredColumns.issubset(df.columns):
            missing = requiredColumns - set(df.columns)
            raise HTTPException(status_code=400, detail=f"❌ Chybějící sloupce: {', '.join(missing)}")

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["hour"] = df["hour"].fillna(24).astype(int)

        df["timestamp"] = df.apply(
            lambda row: (
                datetime.combine(row["date"], datetime.min.time()) +
                (timedelta(hours=23, minutes=59, seconds=59) if row["hour"] == 24 else timedelta(hours=row["hour"]))
            ).isoformat(),
            axis=1
        )

        df = df[["timestamp", "fveProduction", "consumption", "temperature"]]
        database.saveHistoricalData(df)

        return {"message": "✅ Data byla úspěšně nahrána a uložena!"}

    except Exception as e:
        if enableLogging:
            logger.exception("❌ Výjimka při zpracování souboru")
        raise HTTPException(status_code=500, detail=f"❌ Chyba při zpracování: {str(e)}")


# ⚙️ FVE NASTAVENÍ ---------------------------------------------------------------

@router.post("/import-settings/")
async def importSettings(solar_params: SolarParams):
    """Uloží FVE pole do databáze"""
    updated_panels = []
    for fve in solar_params.fveFields:
        panel_id = database.saveFvePanel(
            panel_id=fve.id if fve.id is not None else None,
            latitude=fve.latitude,
            longitude=fve.longitude,
            tilt=fve.tilt,
            azimuth=fve.azimuth,
            power=fve.power
        )
        updated_panels.append(panel_id)

    return {"message": "✅ Parametry FVE byly úspěšně uloženy", "saved_panels": updated_panels}


@router.get("/get-settings/")
async def getSettings():
    """Vrátí všechna uložená FVE data"""
    return database.getFveData()

@router.delete("/delete-fve/{panel_id}")
def delete_fve(panel_id: int):
    return database.deleteFvePanel(panel_id)



# 📡 MQTT NASTAVENÍ --------------------------------------------------------------

@router.get("/get-mqtt-settings/")
def getMqttSettings():
    """Načte aktuální MQTT nastavení"""
    return mqttListener.loadSettings()


@router.post("/save-mqtt-settings/")
async def saveMqttSettings(data: MqttSettingsModel):
    """Uloží MQTT nastavení"""
    try:
        mqttListener.saveMqttSettings(data.dict())
        if enableLogging:
            logger.info("✅ MQTT nastavení bylo uloženo")
        return {"message": "✅ MQTT nastavení bylo uloženo"}
    except Exception as e:
        if enableLogging:
            logger.exception("❌ Chyba při ukládání MQTT")
        raise HTTPException(status_code=500, detail="Chyba při ukládání")


@router.post("/test-mqtt-connection/")
async def testMqttConnection(data: MqttSettingsModel):
    """Otestuje MQTT připojení"""
    return mqttListener.testMqttConnection(data.dict())


# ⚙️ OBECNÉ NASTAVENÍ (settings tabulka) -----------------------------------------

@router.post("/get-settings-values/")
async def getSettingsValues(payload: dict):
    """Vrátí nastavení pro zadaná ID včetně labelu a placeholderu."""
    ids = payload.get("ids", [])
    try:
        with database.getDb() as db:
            cursor = db.cursor()
            query = f"""
                SELECT id, paramName, value, label, placeHolder
                FROM settings
                WHERE id IN ({','.join('?' for _ in ids)})
            """
            cursor.execute(query, ids)
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "paramName": row["paramName"],
                    "value": row["value"],
                    "label": row["label"],
                    "placeHolder": row["placeHolder"]
                }
                for row in rows
            ]
    except Exception as e:
        if enableLogging:
            logger.exception("❌ Chyba při načítání settings hodnot")
        raise HTTPException(status_code=500, detail=f"❌ Chyba při načítání: {str(e)}")


@router.post("/save-settings-values/")
async def saveSettingsValues(payload: dict):
    """Uloží více hodnot nastavení najednou."""
    settings = payload.get("settings", [])
    try:
        with database.getDb() as db:
            cursor = db.cursor()
            for setting in settings:
                setting_id = setting["id"]
                value = setting["value"]
                cursor.execute("UPDATE settings SET value = ? WHERE id = ?", (value, setting_id))
            db.commit()
            if enableLogging:
                logger.info("✅ Obecné nastavení bylo uloženo")
            return {"message": "✅ Nastavení byla uložena"}
    except Exception as e:
        if enableLogging:
            logger.exception("❌ Chyba při ukládání settings")
        raise HTTPException(status_code=500, detail=f"❌ Chyba při ukládání: {str(e)}")
