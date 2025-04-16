"""
Stránka DataFeed pro nahrávání historických dat a správu MQTT nastavení.

Vstup: Uživatel nahrává soubor (CSV/XLSX) pro zpracování nebo upravuje MQTT nastavení.
Výstup: Data jsou odeslána na backend ke zpracování, MQTT nastavení je uloženo a připojení testováno.
Spolupracuje s: Backend API pro upload souborů a nastavení MQTT.
"""

import httpx
import reflex as rx
import base64
import asyncio
import logging
from frontend.templates import template
from frontend.components.card import card
from frontend.components.settingField import generateSettingComponent, MqttSettingsState

# 🌐 Backend adresa
BACKEND_URL = "http://localhost:8000"

# 🛠️ Logging nastavení
enableLogging = 1
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class FileUploadState(rx.State):
    """Stav pro nahrávání souboru"""
    fileName: str = ""
    uploading: bool = False
    touched: bool = False

    @rx.event
    async def checkIfTouched(self):
        await asyncio.sleep(2)  # čekej 2s po nahrání stránky
        if self.fileName == "":
            self.touched = True

    @rx.event(background=True)
    async def handleUpload(self, files: list[rx.UploadFile]):
        """Zpracuje nahrávání souboru"""
        async with self:
            if self.uploading:
                return
            self.uploading = True

        try:
            for file in files:
                fileData = file  
                fileBase64 = base64.b64encode(fileData).decode("utf-8")
                fileName = getattr(file, "name", "uploaded_file.xlsx")

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{BACKEND_URL}/upload/",
                        json={"filename": fileName, "filedata": fileBase64},
                    )

                async with self:
                    if response.status_code == 200:
                        self.fileName = fileName
                        if enableLogging:
                            logging.info(f"✅ Soubor {fileName} úspěšně nahrán!")
                    else:
                        if enableLogging:
                            logging.error(f"❌ Chyba při nahrávání: {response.text}")

        except Exception as e:
            if enableLogging:
                logging.exception(f"❌ Chyba v handleUpload: {e}")

        async with self:
            self.uploading = False


class MQTTSettingsState(rx.State):
    """Stav pro MQTT nastavení"""
    broker: str = "test.mosquitto.org"
    port: int = 1883
    topic: str = "energy/data"
    username: str = ""
    password: str = ""
    connectionStatus: str = "❓ Neznámý stav"

    def updateField(self, key: str, value: str):
        """Aktualizuje hodnotu pole podle klíče"""
        self.__dict__[key] = value  

    async def loadMqttSettings(self):
        """Načte MQTT nastavení z backendu"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BACKEND_URL}/get-mqtt-settings/")
            if response.status_code == 200:
                data = response.json()
                for key in ["broker", "port", "topic", "username", "password"]:
                    if key in data and data[key] is not None:
                        setattr(self, key, data[key])
                if enableLogging:
                    logging.info("✅ MQTT nastavení načteno")
            else:
                if enableLogging:
                    logging.error("❌ Chyba při načítání MQTT nastavení")
        except Exception as e:
            if enableLogging:
                logging.exception(f"❌ Chyba API: {e}")

    async def saveMqttSettings(self):
        """Uloží MQTT nastavení na backend"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BACKEND_URL}/save-mqtt-settings/",
                    json={
                        "broker": self.broker,
                        "port": self.port,
                        "topic": self.topic,
                        "username": self.username,
                        "password": self.password
                    }
                )
            if response.status_code == 200:
                if enableLogging:
                    logging.info("✅ MQTT nastavení uloženo")
                return rx.window_alert("✅ MQTT nastavení bylo uloženo!")
            else:
                if enableLogging:
                    logging.error("❌ Chyba při ukládání MQTT nastavení")
        except Exception as e:
            if enableLogging:
                logging.exception(f"❌ Chyba API: {e}")

    async def testMqttConnection(self):
        """Otestuje MQTT připojení"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BACKEND_URL}/test-mqtt-connection/",
                    json={
                        "broker": self.broker,
                        "port": self.port,
                        "topic": self.topic,
                        "username": self.username,
                        "password": self.password
                    }
                )
            if response.status_code == 200:
                self.connectionStatus = "✅ Připojení úspěšné"
            else:
                self.connectionStatus = "❌ Připojení selhalo"
        except Exception as e:
            self.connectionStatus = "❌ Chyba při připojení"
            if enableLogging:
                logging.exception(f"❌ Chyba API: {e}")


@template(
    route="/datafeed",
    title="Datafeed",
    description="Stránka pro nahrávání souborů a správu MQTT."
)
def page() -> rx.Component:
    """Hlavní komponenta stránky"""
    return rx.hstack(
        rx.container(
            card(
                rx.heading("📂 Nahrajte soubor pro zpracování", size="4", margin_bottom="10px"),
                rx.vstack(
                    rx.upload(
                        rx.vstack(rx.text("Přetáhněte nebo klikněte pro výběr .csv / .xlsx"), width="105%"),
                        id="upload_xlsx",
                        multiple=False,
                        accept={
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                            "text/csv": [".csv"]
                        },
                        max_files=1,
                        on_drop=FileUploadState.handleUpload,
                    ),

                    rx.cond(
                        FileUploadState.uploading,
                        rx.text("⏳ Nahrávání..."),
                        rx.cond(
                            FileUploadState.fileName != "",
                            rx.text("✅ Hotovo!"),
                            rx.cond(
                                FileUploadState.touched,
                                rx.text("❌ Žádný soubor nenahrán"),
                                rx.text("")  # Pokud se nic nedělo, nezobrazuj nic
                            )
                        )
                    ),
                ),
            ),
            width="400px"
        ),
        rx.container(
            generateSettingComponent(MqttSettingsState, [11, 12, 13, 14, 15], "📡 MQTT", "💾 Uložit MQTT nastavení", cardWidth="350px"),
            rx.hstack(
                rx.button("🔍 Test připojení", on_click=MQTTSettingsState.testMqttConnection),
                spacing="4",
                margin_top="20px",
                margin_bottom="20px",
            ),
            rx.text(MQTTSettingsState.connectionStatus, size="4"),
        ),
        spacing="4",
        align="start",
        on_mount=[
            FileUploadState.checkIfTouched,
            MQTTSettingsState.loadMqttSettings
        ],
    )
