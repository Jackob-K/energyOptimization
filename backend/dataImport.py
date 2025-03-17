import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import database
import pandas as pd
import os
import base64
import httpx
from typing import List, Optional
import mqttListener

# ✅ Nastavení loggeru
logger = logging.getLogger(__name__)

router = APIRouter()

class FVEData(BaseModel):
    id: Optional[int] = None  # ✅ Volitelné ID panelu
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    power: float

class SolarParams(BaseModel):
    fve_fields: List[FVEData]  # ✅ Seznam panelů FVE

# ✅ Povinné sloupce v souboru
REQUIRED_COLUMNS = {"date", "hour", "consumption", "temperature", "fveProduction"}
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileUploadModel(BaseModel):
    filename: str
    filedata: str  # Base64 encoded file content

@router.post("/upload/")
async def upload_file(file: FileUploadModel):
    """Nahraje soubor do složky a automaticky spustí jeho zpracování."""
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    
    file_content = base64.b64decode(file.filedata)
    with open(file_location, "wb") as buffer:
        buffer.write(file_content)

    logger.info(f"✅ Soubor {file.filename} nahrán do {file_location}")

    # ✅ Opravené volání API na `process-file`
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/process-file/",
            json={"file_location": file_location}  # Posíláme jako JSON objekt
        )

    if response.status_code == 200:
        logger.info(f"✅ Soubor {file.filename} úspěšně zpracován!")
    else:
        logger.error(f"❌ Chyba při zpracování souboru: {response.text}")

    return response.json()

class ProcessFileModel(BaseModel):
    file_location: str

@router.post("/process-file/")
async def process_uploaded_file(payload: ProcessFileModel):
    """Zpracuje soubor, ověří správnost a uloží do databáze."""
    file_location = payload.file_location

    if not os.path.exists(file_location):
        raise HTTPException(status_code=400, detail=f"❌ Soubor nebyl nalezen: {file_location}")

    logger.info(f"🔄 Zpracovávám soubor: {file_location}")

    try:
        if file_location.endswith(".csv"):
            df = pd.read_csv(file_location)
        elif file_location.endswith(".xlsx"):
            df = pd.read_excel(file_location)
        else:
            raise HTTPException(status_code=400, detail="Nepodporovaný formát souboru")
        
        if not REQUIRED_COLUMNS.issubset(df.columns):
            missing_columns = REQUIRED_COLUMNS - set(df.columns)
            raise HTTPException(status_code=400, detail=f"❌ Chybějící sloupce: {', '.join(missing_columns)}")

        df["date"] = pd.to_datetime(df["date"]).dt.date  
        df["hour"] = df["hour"].fillna(24).astype(int)

        df = df[["date", "hour", "fveProduction", "consumption", "temperature"]]
        
        # ✅ Uložení dat do databáze
        database.save_historical_data(df)

        # ✅ Smazání souboru po zpracování
        os.remove(file_location)

        return {"message": "✅ Data byla úspěšně nahrána a uložena!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Chyba při zpracování: {str(e)}")

@router.post("/import-settings/")
async def import_settings(solar_params: SolarParams):
    """Uloží nastavení FVE a panely do databáze."""

    updated_panels = []
    for fve in solar_params.fve_fields:
        panel_id = database.save_fve_panel(
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
async def get_settings():
    """Vrací uložené parametry FVE zpět do UI."""
    data = database.get_fve_data()
    return data

# ✅ Model pro MQTT nastavení
class MQTTSettingsModel(BaseModel):
    broker: str
    port: int
    topic: str
    username: str
    password: str


@router.get("/get-mqtt-settings/")
def get_mqtt_settings():
    """Vrátí aktuální uložené MQTT nastavení."""
    return mqttListener.get_mqtt_settings()  # Teď je to správně synchronní


@router.post("/save-mqtt-settings/")
async def save_mqtt_settings(data: MQTTSettingsModel):
    """Uloží nové MQTT nastavení do databáze."""
    try:
        mqttListener.save_mqtt_settings(data.dict())
        return {"message": "✅ MQTT nastavení bylo uloženo"}
    except Exception as e:
        logger.error(f"❌ Chyba při ukládání MQTT nastavení: {e}")
        raise HTTPException(status_code=500, detail="Chyba při ukládání")


@router.post("/test-mqtt-connection/")
async def test_mqtt_connection(data: MQTTSettingsModel):
    """Otestuje připojení k MQTT brokeru."""
    return mqttListener.test_mqtt_connection(data.dict())