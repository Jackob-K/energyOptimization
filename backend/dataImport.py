from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
import database

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