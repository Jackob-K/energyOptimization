"""
Hlavní API server aplikace. 

Vstup: API volání z klientské aplikace.
Výstup: Data o spotřebě energie, FVE a MQTT nastavení.
Spolupracuje s: database, apiHandlers.
"""

# Standardní knihovny
import logging

# Externí knihovny
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Lokální importy
from database import getEnergyData
import apiHandlers as apiHandlers  # Importujeme router

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializace FastAPI aplikace
app = FastAPI()

# Middleware pro CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """root"""
    return {"message": "Backend běží správně!"}

@app.get("/energy-data")
async def energyData():
    """energyData"""
    return getEnergyData()

# Připojení API endpointů z `apiHandlers.py`
app.include_router(apiHandlers.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
