from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
import database
import pandas as pd
import sqlite3
from io import BytesIO, StringIO
import shutil
from pathlib import Path
import os
from pydantic import BaseModel
import base64
import httpx

app = FastAPI()
router = APIRouter()

class FVEData(BaseModel):
    id: int | None = None  # ✅ Přidáme volitelný ID panelu
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    power: float

class SolarParams(BaseModel):
    totalPower: float
    fve_fields: list[FVEData]

@app.post("/import-settings/")
async def import_settings(solar_params: SolarParams):
    print("✅ Přijatá data:", solar_params.dict())

    database.create_database()  # Automaticky vytvoří databázi, pokud chybí

    settings_id = database.save_settings(solar_params.totalPower)
    print(f"🔹 Uložen settings_id: {settings_id}")

    updated_panels = []

    for fve in solar_params.fve_fields:
        print(f"📌 Ukládám/aktualizuji FVE: {fve}")
        panel_id = database.save_fve_panel(
            panel_id=fve.id if fve.id is not None else None,
            settings_id=settings_id,
            latitude=fve.latitude,
            longitude=fve.longitude,
            tilt=fve.tilt,
            azimuth=fve.azimuth,
            power=fve.power
        )
        print(f"✅ Panel ID: {panel_id} byl úspěšně uložen.")
        updated_panels.append(panel_id)

    # ✅ Ověříme, zda se panely vrátily z databáze
    saved_data = database.get_fve_data()
    print(f"📌 Data v databázi po uložení: {saved_data}")

    return {"message": "Parametry FVE byly úspěšně uloženy", "settings": saved_data}

@app.delete("/delete-fve/{panel_id}")
async def delete_fve(panel_id: int):
    """Smaže konkrétní FVE panel z databáze."""
    database.delete_fve_panel(panel_id)
    return {"message": "FVE pole bylo smazáno"}

@app.get("/get-settings/")
async def get_settings():
    """Vrací uložené parametry FVE zpět do UI."""
    data = database.get_fve_data()
    return data

# ✅ Povinné sloupce v souboru
REQUIRED_COLUMNS = {"date", "fveProduction", "consumption", "temperatureMax", "temperatureMin"}

# ✅ Složka pro ukládání souborů
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileUploadModel(BaseModel):
    filename: str
    filedata: str  # Base64 encoded file content

@app.post("/upload/")
async def upload_file(file: FileUploadModel):
    """Nahraje soubor do složky a automaticky spustí jeho zpracování."""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    
    file_content = base64.b64decode(file.filedata)
    with open(file_location, "wb") as buffer:
        buffer.write(file_content)

    print(f"✅ Soubor {file.filename} nahrán do {file_location}")

    # ✅ Opravené volání API - posíláme JSON správně
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/process-file/",
            json={"file_location": file_location}  # Posíláme jako JSON objekt
        )

    if response.status_code == 200:
        print(f"✅ Soubor {file.filename} úspěšně zpracován!")
    else:
        print(f"❌ Chyba při zpracování souboru: {response.text}")

    return response.json()


class ProcessFileModel(BaseModel):
    file_location: str  # Očekáváme JSON objekt {"file_location": "uploads/uploaded_file.xlsx"}

@app.post("/process-file/")
async def process_uploaded_file(payload: ProcessFileModel):
    """Zpracuje soubor, ověří správnost a uloží do databáze."""
    file_location = payload.file_location  # Extrahujeme file_location z JSON

    if not os.path.exists(file_location):
        raise HTTPException(status_code=400, detail=f"❌ Soubor nebyl nalezen: {file_location}")

    print(f"🔄 Zpracovávám soubor na cestě: {file_location}")

    try:
        # Rozpoznání formátu souboru
        if file_location.endswith(".csv"):
            df = pd.read_csv(file_location)
        elif file_location.endswith(".xlsx"):
            df = pd.read_excel(file_location)
        else:
            raise HTTPException(status_code=400, detail="Nepodporovaný formát souboru")

        print(f"📊 Načtený soubor:\n{df.head()}")  # Debug výstup
        
        # Kontrola sloupců
        REQUIRED_COLUMNS = {"date", "fveProduction", "consumption", "temperatureMax", "temperatureMin"}
        if not REQUIRED_COLUMNS.issubset(df.columns):
            missing_columns = REQUIRED_COLUMNS - set(df.columns)
            raise HTTPException(status_code=400, detail=f"❌ Chybějící sloupce: {', '.join(missing_columns)}")

        # Převod `date` na správný formát
        df["date"] = pd.to_datetime(df["date"]).dt.date  

        # Ověření `hour`
        if "hour" in df.columns:
            df["hour"] = pd.to_numeric(df["hour"], errors="coerce").fillna(24).astype(int)  
        else:
            df["hour"] = 24  

        # Výběr relevantních sloupců
        columns_to_save = ["date", "hour", "fveProduction", "consumption", "temperatureMax", "temperatureMin"]
        df = df[columns_to_save]

        print(f"📊 Po úpravě dat:\n{df.head()}")  # Debug výstup
        
        # ✅ Uložení dat do databáze
        database.save_historical_data(df)

        # ✅ Smazání souboru po zpracování
        os.remove(file_location)

        return {"message": "✅ Data byla úspěšně nahrána a uložena!"}

    except Exception as e:
        print(f"❌ Chyba při zpracování souboru: {str(e)}")
        return HTTPException(status_code=500, detail=f"❌ Chyba při zpracování: {str(e)}")