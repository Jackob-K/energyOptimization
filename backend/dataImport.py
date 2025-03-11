import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import database  # ✅ Importujeme modul pro databázi

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
    totalPower: float
    fve_fields: List[FVEData]  # ✅ Seznam panelů FVE

@router.post("/import-settings/")
async def import_settings(solar_params: SolarParams):
    """Uloží nastavení FVE a panely do databáze a ověří, že staré panely se neimportují zpět."""
    logger.info(f"✅ Přijatá data pro uložení: {solar_params.dict()}")

    # ✅ Uložíme nastavení (totalPower) a získáme settings_id
    settings_id = database.save_settings(solar_params.totalPower)
    logger.info(f"✅ Uložené settings_id: {settings_id}")

    # ✅ Načteme panely z databáze, abychom ověřili existující ID
    existing_panels = {panel["id"] for panel in database.get_fve_data()["fve_fields"]}
    logger.info(f"📌 Panely existující v databázi před uložením: {existing_panels}")

    updated_panels = []

    for fve in solar_params.fve_fields:
        # ✅ Pokud je panel ve frontendových datech, ale NEEXISTUJE v DB, neukládáme ho zpět!
        if fve.id in existing_panels or fve.id is None:
            logger.info(f"📌 Ukládám/aktualizuji FVE: {fve}")
            panel_id = database.save_fve_panel(
                panel_id=fve.id if fve.id is not None else None,
                settings_id=settings_id,
                latitude=fve.latitude,
                longitude=fve.longitude,
                tilt=fve.tilt,
                azimuth=fve.azimuth,
                power=fve.power
            )
            logger.info(f"✅ Panel ID: {panel_id} byl úspěšně uložen.")
            updated_panels.append(panel_id)
        else:
            logger.warning(f"❌ Panel ID {fve.id} byl smazán z databáze, neukládáme ho zpět!")

    return {"message": "✅ Parametry FVE byly úspěšně uloženy", "saved_panels": updated_panels}


@router.get("/get-settings/")
async def get_settings():
    """Vrací uložené parametry FVE zpět do UI se správně očíslovanými ID."""
    settings = database.get_fve_data()

    # ✅ Debug log pro kontrolu v konzoli
    logger.info(f"📡 Vrácené nastavení: {settings}")

    # ✅ Pokud databáze vrátila panely, nastavíme ID správně
    for index, fve in enumerate(settings["fve_fields"], start=1):
        fve["id"] = index  # ✅ Přepíšeme ID podle správného pořadí

    return settings



@router.delete("/delete-fve/{panel_id}")
async def delete_fve(panel_id: int):
    """Smaže konkrétní FVE panel z databáze podle jeho ID."""
    success = database.delete_fve_panel(panel_id)

    if not success:
        return {"message": f"❌ FVE panel s ID {panel_id} neexistuje!"}

    return {"message": f"✅ FVE panel s ID {panel_id} byl úspěšně smazán."}
