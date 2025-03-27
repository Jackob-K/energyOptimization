"""
API modul pro práci s fotovoltaickými panely, zpracování nahraných souborů,
správu MQTT nastavení a komunikaci s databází.

Vstup: JSON data pro FVE panely, soubory s historickými daty (CSV, XLSX).
Výstup: Aktualizovaná databáze, odpovědi na API požadavky.
Spolupracuje s: database, mqttListener.
"""

# Standardní knihovny
import os
import base64
import logging
from datetime import datetime, timedelta

# Externí knihovny
import pandas as pd
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Lokální importy
import database
import mqttListener

# Logger
logger = logging.getLogger(__name__)

# FastAPI router
router = APIRouter()

# Povinné sloupce v souboru
requiredColumns = {"date", "hour", "consumption", "temperature", "fveProduction"}

class FveData(BaseModel):
    """FveData"""
    id: Optional[int] = None
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    power: float

class SolarParams(BaseModel):
    """SolarParams"""
    fveFields: List[FveData]

class FileUploadModel(BaseModel):
    """FileUploadModel"""
    filename: str
    filedata: str

class ProcessFileModel(BaseModel):
    filename: str
    filedata: str  # base64 string

@router.post("/upload/")
async def uploadFile(file: FileUploadModel):
    """uploadFile"""
    logger.info(f"✅ Přijímám soubor {file.filename}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/process-file/",
            json={"filename": file.filename, "filedata": file.filedata}
        )

    if response.status_code == 200:
        logger.info(f"✅ Soubor {file.filename} úspěšně zpracován!")
    else:
        logger.error(f"❌ Chyba při zpracování souboru: {response.text}")

    return response.json()


@router.post("/process-file/")
async def processUploadedFile(payload: ProcessFileModel):
    """processUploadedFile"""
    try:
        logger.info(f"🔄 Zpracovávám soubor z paměti: {payload.filename}")

        decoded = base64.b64decode(payload.filedata)

        # Načtení přímo z paměti (bez ukládání)
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
        raise HTTPException(status_code=500, detail=f"❌ Chyba při zpracování: {str(e)}")


@router.post("/import-settings/")
async def importSettings(solar_params: SolarParams):
    """importSettings"""
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
    """getSettings"""
    data = database.getFveData()
    return data

class MqttSettingsModel(BaseModel):
    """MqttSettingsModel"""
    broker: str
    port: int
    topic: str
    username: str
    password: str

@router.get("/get-mqtt-settings/")
def getMqttSettings():
    """getMqttSettings"""
    return mqttListener.getMqttSettings()

@router.post("/save-mqtt-settings/")
async def saveMqttSettings(data: MqttSettingsModel):
    """saveMqttSettings"""
    try:
        mqttListener.saveMqttSettings(data.dict())
        return {"message": "✅ MQTT nastavení bylo uloženo"}
    except Exception as e:
        logger.error(f"❌ Chyba při ukládání MQTT nastavení: {e}")
        raise HTTPException(status_code=500, detail="Chyba při ukládání")

@router.post("/test-mqtt-connection/")
async def testMqttConnection(data: MqttSettingsModel):
    """testMqttConnection"""
    return mqttListener.testMqttConnection(data.dict())


