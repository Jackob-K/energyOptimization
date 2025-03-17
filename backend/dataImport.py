"""
API modul pro práci s fotovoltaickými panely, zpracování nahraných souborů,
správu MQTT nastavení a komunikaci s databází.

Vstup: JSON data pro FVE panely, soubory s historickými daty (CSV, XLSX).
Výstup: Aktualizovaná databáze, odpovědi na API požadavky.
Spolupracuje s: database, mqttListener.

Změny názvů funkcí a proměnných:
- get_mqtt_settings → getMqttSettings
- save_mqtt_settings → saveMqttSettings
- test_mqtt_connection → testMqttConnection
- upload_file → uploadFile
- process_uploaded_file → processUploadedFile
- import_settings → importSettings
- get_settings → getSettings
"""

# Standardní knihovny
import os
import base64
import logging

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
uploadDir = "uploads"
os.makedirs(uploadDir, exist_ok=True)

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

@router.post("/upload/")
async def uploadFile(file: FileUploadModel):
    """uploadFile"""
    fileLocation = os.path.join(uploadDir, file.filename)
    
    fileContent = base64.b64decode(file.filedata)
    with open(fileLocation, "wb") as buffer:
        buffer.write(fileContent)

    logger.info(f"✅ Soubor {file.filename} nahrán do {fileLocation}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/process-file/",
            json={"fileLocation": fileLocation}
        )

    if response.status_code == 200:
        logger.info(f"✅ Soubor {file.filename} úspěšně zpracován!")
    else:
        logger.error(f"❌ Chyba při zpracování souboru: {response.text}")

    return response.json()

class ProcessFileModel(BaseModel):
    """ProcessFileModel"""
    fileLocation: str

@router.post("/process-file/")
async def processUploadedFile(payload: ProcessFileModel):
    """processUploadedFile"""
    fileLocation = payload.fileLocation

    if not os.path.exists(fileLocation):
        raise HTTPException(status_code=400, detail=f"❌ Soubor nebyl nalezen: {fileLocation}")

    logger.info(f"🔄 Zpracovávám soubor: {fileLocation}")

    try:
        if fileLocation.endswith(".csv"):
            df = pd.read_csv(fileLocation)
        elif fileLocation.endswith(".xlsx"):
            df = pd.read_excel(fileLocation)
        else:
            raise HTTPException(status_code=400, detail="Nepodporovaný formát souboru")
        
        if not requiredColumns.issubset(df.columns):
            missingColumns = requiredColumns - set(df.columns)
            raise HTTPException(status_code=400, detail=f"❌ Chybějící sloupce: {', '.join(missingColumns)}")

        df["date"] = pd.to_datetime(df["date"]).dt.date  
        df["hour"] = df["hour"].fillna(24).astype(int)

        df = df[["date", "hour", "fveProduction", "consumption", "temperature"]]
        
        database.saveHistoricalData(df)

        os.remove(fileLocation)

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
