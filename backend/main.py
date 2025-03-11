import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import get_energy_data
import dataImport  # ✅ Importujeme router

# ✅ Nastavení loggeru
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Backend běží správně!"}

@app.get("/energy-data")
async def energy_data():
    return get_energy_data()

# ✅ Připojení API endpointů z `dataImport.py`
app.include_router(dataImport.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
