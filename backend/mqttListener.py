import paho.mqtt.client as mqtt
import json
import logging
import sqlite3
from fastapi import APIRouter, HTTPException
from database import get_db

# Nastavení logování
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Cesta k databázi
DB_PATH = "backend/database.db"

# API router pro MQTT služby
router = APIRouter()

# Globální proměnné pro MQTT klienta
mqtt_client = None
settings = {}

def load_settings():
    """ Načítá aktuální MQTT nastavení z databáze """
    global settings
    settings = {
        "broker": "test.mosquitto.org",
        "port": 1883,
        "topic": "energy/data",
        "username": None,
        "password": None
    }

    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, value FROM settings WHERE id BETWEEN 11 AND 15")
            rows = cursor.fetchall()

            for row_id, value in rows:
                if row_id == 11:
                    settings["broker"] = value
                elif row_id == 12:
                    settings["port"] = int(value) if value.isdigit() else 1883
                elif row_id == 13:
                    settings["topic"] = value
                elif row_id == 14:
                    settings["username"] = value if value else None
                elif row_id == 15:
                    settings["password"] = value if value else None

    except sqlite3.Error as e:
        logging.error(f"❌ Chyba při načítání MQTT nastavení z databáze: {e}")

    return settings

def save_mqtt_settings(new_settings):
    """ Uloží nové MQTT nastavení do databáze a restartuje připojení pouze pokud došlo ke změně """
    global settings
    if settings == new_settings:
        logging.info("⚠️ Nastavení MQTT se nezměnilo, restart není nutný.")
        return {"message": "⚠️ Nastavení zůstalo stejné."}

    try:
        with get_db() as db:
            cursor = db.cursor()
            
            for key, value in new_settings.items():
                setting_id = {
                    "broker": 11,
                    "port": 12,
                    "topic": 13,
                    "username": 14,
                    "password": 15
                }.get(key)

                if setting_id:
                    # ✅ Použijeme INSERT ON CONFLICT pro správné uložení
                    cursor.execute("""
                        INSERT INTO settings (id, value) VALUES (?, ?)
                        ON CONFLICT(id) DO UPDATE SET value = excluded.value;
                    """, (setting_id, str(value)))

            db.commit()

        logging.info("✅ MQTT nastavení bylo úspěšně uloženo")
        settings = new_settings  # Aktualizujeme globální proměnnou
        restart_mqtt_client()  # Restartujeme jen při změně
        return {"message": "✅ MQTT nastavení bylo uloženo"}

    except sqlite3.Error as e:
        logging.error(f"❌ Chyba při ukládání MQTT nastavení: {e}")
        raise HTTPException(status_code=500, detail="Chyba při ukládání do databáze")


def test_mqtt_connection(settings_data):
    """ Otestuje připojení k MQTT brokeru """
    try:
        test_client = mqtt.Client()
        if settings_data["username"] and settings_data["password"]:
            test_client.username_pw_set(settings_data["username"], settings_data["password"])

        test_client.connect(settings_data["broker"], int(settings_data["port"]), 60)
        test_client.disconnect()
        return {"message": "✅ Připojení k MQTT brokeru úspěšné"}
    
    except Exception as e:
        logging.error(f"❌ Chyba při testování MQTT připojení: {e}")
        return {"message": "❌ Připojení selhalo", "error": str(e)}


def restart_mqtt_client():
    """ Restartuje MQTT klienta s novým nastavením """
    global mqtt_client
    settings = load_settings()

    if mqtt_client:
        mqtt_client.disconnect()

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    if settings["username"] and settings["password"]:
        mqtt_client.username_pw_set(settings["username"], settings["password"])

    try:
        logging.info("🔄 Restart MQTT klienta s novým nastavením...")
        mqtt_client.connect(settings["broker"], settings["port"], 60)
        mqtt_client.loop_start()
    except Exception as e:
        logging.error(f"❌ Chyba při restartování MQTT klienta: {e}")

def on_connect(client, userdata, flags, rc):
    """ Callback při připojení k brokeru """
    if rc == 0:
        logging.info("✅ MQTT připojeno.")
        client.subscribe(settings["topic"])
    else:
        logging.error(f"❌ Chyba při připojení, kód: {rc}")

def on_message(client, userdata, msg):
    """ Callback při přijetí zprávy z MQTT """
    raw_payload = msg.payload.decode("utf-8")  # Převod byte zprávy na string
    logging.info(f"📩 SUROVÁ PŘIJATÁ ZPRÁVA: {raw_payload}")  # ✅ Výpis raw zprávy

    # 🛠 Pokusíme se extrahovat JSON část ze zprávy
    try:
        json_start = raw_payload.find("{")  # Najdeme začátek JSONu
        if json_start != -1:
            clean_json = raw_payload[json_start:]  # Ořízneme text před JSONem
        else:
            clean_json = raw_payload  # Pokud není nalezen '{', použijeme celý text

        logging.info(f"🛠 OPRAVENÁ ZPRÁVA PRO DEKÓDOVÁNÍ: {clean_json}")  # ✅ Výpis opravené zprávy

        # Převedení na Python slovník
        data = json.loads(clean_json)

        logging.info(f"📥 PŘEVEDENÁ JSON ZPRÁVA: {json.dumps(data, indent=2)}")  # ✅ Formátovaný výstup JSON

        # ✅ Ověření, zda zpráva obsahuje požadovaná pole
        required_keys = {"date", "hour", "fveProduction", "consumption", "temperature"}
        if required_keys.issubset(data.keys()):
            logging.info("✅ ZPRÁVA OBSAHUJE VŠECHNA POŽADOVANÁ DATA!")
            save_to_database(data)  # Uložit do DB
        else:
            missing_keys = required_keys - set(data.keys())
            logging.warning(f"⚠️ CHYBĚJÍCÍ DATA VE ZPRÁVĚ: {missing_keys}")

    except json.JSONDecodeError as e:
        logging.error(f"❌ CHYBA PŘI DEKÓDOVÁNÍ JSON: {e}")


def save_to_database(data):
    """ Uložení přijatých dat do tabulky energyData """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO energyData (date, hour, fveProduction, consumption, temperature) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date, hour) DO UPDATE SET
                fveProduction = excluded.fveProduction,
                consumption = excluded.consumption,
                temperature = excluded.temperature
            """, (data["date"], data["hour"], data["fveProduction"], data["consumption"], data["temperature"]))

            db.commit()

        logging.info(f"✅ Data uložena: {data}")

    except sqlite3.Error as e:
        logging.error(f"❌ Chyba při ukládání do databáze: {e}")

def on_disconnect(client, userdata, rc):
    """ Callback při odpojení """
    logging.warning("⚠️ MQTT odpojeno.")

@router.get("/get-mqtt-settings/")
def get_mqtt_settings():
    """ API endpoint pro načtení MQTT nastavení """
    return load_settings()  # ✅ Nyní je to synchronní a správně volané

@router.post("/save-mqtt-settings/")
async def save_mqtt_settings_api(data: dict):
    """ API endpoint pro uložení MQTT nastavení """
    return save_mqtt_settings(data)

@router.post("/test-mqtt-connection/")
async def test_mqtt_connection_api(data: dict):
    """ API endpoint pro test připojení """
    return test_mqtt_connection(data)

if __name__ == "__main__":
    restart_mqtt_client()