"""
Modul pro správu MQTT připojení a příjem dat.

Vstup: MQTT zprávy s údaji o spotřebě a výrobě energie.
Výstup: Data uložená v databázi.
Spolupracuje s: database.
"""

# Standardní knihovny
import logging
import json
import sqlite3

# Externí knihovny
import paho.mqtt.client as mqtt

# Lokální importy
from database import getDb

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Globální proměnné pro MQTT klienta
mqttClient = None
settings = {}

def loadSettings():
    """loadSettings"""
    global settings
    settings = {
        "broker": "test.mosquitto.org",
        "port": 1883,
        "topic": "energy/data",
        "username": None,
        "password": None
    }

    try:
        with getDb() as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, value FROM settings WHERE id BETWEEN 11 AND 15")
            rows = cursor.fetchall()

            for rowId, value in rows:
                if rowId == 11:
                    settings["broker"] = value
                elif rowId == 12:
                    settings["port"] = int(value) if value.isdigit() else 1883
                elif rowId == 13:
                    settings["topic"] = value
                elif rowId == 14:
                    settings["username"] = value if value else None
                elif rowId == 15:
                    settings["password"] = value if value else None

    except sqlite3.Error as e:
        logging.error(f"❌ Chyba při načítání MQTT nastavení z databáze: {e}")

    return settings

def saveMqttSettings(newSettings):
    """saveMqttSettings"""
    global settings
    if settings == newSettings:
        logging.info("⚠️ Nastavení MQTT se nezměnilo, restart není nutný.")
        return {"message": "⚠️ Nastavení zůstalo stejné."}

    try:
        with getDb() as db:
            cursor = db.cursor()
            
            for key, value in newSettings.items():
                settingId = {
                    "broker": 11,
                    "port": 12,
                    "topic": 13,
                    "username": 14,
                    "password": 15
                }.get(key)

                if settingId:
                    cursor.execute("""
                        INSERT INTO settings (id, value) VALUES (?, ?)
                        ON CONFLICT(id) DO UPDATE SET value = excluded.value;
                    """, (settingId, str(value)))

            db.commit()

        logging.info("✅ MQTT nastavení bylo úspěšně uloženo")
        settings = newSettings  
        restartMqttClient()  
        return {"message": "✅ MQTT nastavení bylo uloženo"}

    except sqlite3.Error as e:
        logging.error(f"❌ Chyba při ukládání MQTT nastavení: {e}")
        raise Exception("Chyba při ukládání do databáze")

def testMqttConnection(settingsData):
    """testMqttConnection"""
    try:
        testClient = mqtt.Client()
        if settingsData["username"] and settingsData["password"]:
            testClient.username_pw_set(settingsData["username"], settingsData["password"])

        testClient.connect(settingsData["broker"], int(settingsData["port"]), 60)
        testClient.disconnect()
        return {"message": "✅ Připojení k MQTT brokeru úspěšné"}
    
    except Exception as e:
        logging.error(f"❌ Chyba při testování MQTT připojení: {e}")
        return {"message": "❌ Připojení selhalo", "error": str(e)}

def restartMqttClient():
    """restartMqttClient"""
    global mqttClient, settings

    if not settings:
        settings = loadSettings()
    else:
        logging.info("ℹ️ Používám již načtené MQTT nastavení.")

    if mqttClient:
        mqttClient.disconnect()

    mqttClient = mqtt.Client()
    mqttClient.on_connect = onConnect
    mqttClient.on_message = onMessage
    mqttClient.on_disconnect = onDisconnect

    if settings["username"] and settings["password"]:
        mqttClient.username_pw_set(settings["username"], settings["password"])

    try:
        logging.info("🔄 Restart MQTT klienta s novým nastavením...")
        mqttClient.connect(settings["broker"], settings["port"], 60)
        mqttClient.loop_start()
    except Exception as e:
        logging.error(f"❌ Chyba při restartování MQTT klienta: {e}")

def onConnect(client, userdata, flags, rc):
    """onConnect"""
    if rc == 0:
        logging.info("✅ MQTT připojeno.")
        client.subscribe(settings["topic"])
    else:
        logging.error(f"❌ Chyba při připojení, kód: {rc}")

def onMessage(client, userdata, msg):
    """onMessage"""
    rawPayload = msg.payload.decode("utf-8")
    logging.info(f"📩 SUROVÁ PŘIJATÁ ZPRÁVA: {rawPayload}")

    try:
        jsonStart = rawPayload.find("{")
        cleanJson = rawPayload[jsonStart:] if jsonStart != -1 else rawPayload

        logging.info(f"🛠 OPRAVENÁ ZPRÁVA PRO DEKÓDOVÁNÍ: {cleanJson}")

        data = json.loads(cleanJson)

        logging.info(f"📥 PŘEVEDENÁ JSON ZPRÁVA: {json.dumps(data, indent=2)}")

        requiredKeys = {"timestamp", "fveProduction", "consumption", "temperature"}
        if requiredKeys.issubset(data.keys()):
            logging.info("✅ ZPRÁVA OBSAHUJE VŠECHNA POŽADOVANÁ DATA!")
            saveToDatabase(data)
        else:
            missingKeys = requiredKeys - set(data.keys())
            logging.warning(f"⚠️ CHYBĚJÍCÍ DATA VE ZPRÁVĚ: {missingKeys}")

    except json.JSONDecodeError as e:
        logging.error(f"❌ CHYBA PŘI DEKÓDOVÁNÍ JSON: {e}")

def saveToDatabase(data):
    """saveToDatabase"""
    try:
        # Očekáváme timestamp např. "2025-03-29T14:00:00"
        timestamp = data.get("timestamp")
        if not timestamp:
            raise ValueError("❌ Ve zprávě chybí pole 'timestamp'!")

        with getDb() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO energyData (timestamp, fveProduction, consumption, temperature) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(timestamp) DO UPDATE SET
                    fveProduction = excluded.fveProduction,
                    consumption = excluded.consumption,
                    temperature = excluded.temperature;
            """, (
                timestamp,
                data.get("fveProduction"),
                data.get("consumption"),
                data.get("temperature")
            ))

            db.commit()
        logging.info(f"✅ Data uložena do DB: {timestamp}")

    except (sqlite3.Error, ValueError) as e:
        logging.error(f"❌ Chyba při ukládání do databáze: {e}")

def onDisconnect(client, userdata, rc):
    """onDisconnect"""
    logging.warning("⚠️ MQTT odpojeno.")

def startMqttListener():
    logging.info("🚀 Spouštím MQTT listener...")
    restartMqttClient()
