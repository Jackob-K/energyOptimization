"""
Stránka DataFeed pro nahrávání historických dat a správu MQTT nastavení.

Vstup: Uživatel nahrává soubor (CSV/XLSX) pro zpracování nebo upravuje MQTT nastavení.
Výstup: Data jsou odeslána na backend ke zpracování, MQTT nastavení je uloženo a připojení testováno.
Spolupracuje s: Backend API pro upload souborů a nastavení MQTT.
"""

import httpx
import reflex as rx
import base64
import requests
from frontend.templates import template
from frontend.components.card import card 

BACKEND_URL = "http://localhost:8000"

class FileUploadState(rx.State):
    """FileUploadState"""
    fileName: str = ""
    uploading: bool = False

    @rx.event(background=True)
    async def handleUpload(self, files: list[rx.UploadFile]):
        """handleUpload"""
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
                        print(f"✅ Soubor {fileName} úspěšně nahrán!")
                    else:
                        print(f"❌ Chyba při nahrávání: {response.text}")

        except Exception as e:
            print(f"❌ Chyba v handleUpload: {e}")

        async with self:
            self.uploading = False

class MQTTSettingsState(rx.State):
    """MQTTSettingsState"""
    broker: str = "test.mosquitto.org"
    port: int = 1883
    topic: str = "energy/data"
    username: str = ""
    password: str = ""
    connectionStatus: str = "❓ Neznámý stav"

    def updateField(self, key: str, value: str):
        """updateField"""
        self.__dict__[key] = value  

    def loadMqttSettings(self):
        """loadMqttSettings"""
        try:
            response = requests.get(f"{BACKEND_URL}/get-mqtt-settings/")
            if response.status_code == 200:
                data = response.json()
                for key in ["broker", "port", "topic", "username", "password"]:
                    if key in data and data[key] is not None:
                        setattr(self, key, data[key])
                print("✅ MQTT nastavení načteno")
            else:
                print("❌ Chyba při načítání MQTT nastavení")
        except Exception as e:
            print(f"❌ Chyba API: {e}")

    def saveMqttSettings(self):
        """saveMqttSettings"""
        try:
            response = requests.post(
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
                print("✅ MQTT nastavení uloženo")
                return rx.window_alert("✅ MQTT nastavení bylo uloženo!")
            else:
                print("❌ Chyba při ukládání MQTT nastavení")
        except Exception as e:
            print(f"❌ Chyba API: {e}")

    def testMqttConnection(self):
        """testMqttConnection"""
        try:
            response = requests.post(
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
            print(f"❌ Chyba API: {e}")

@template(
    route="/datafeed",
    title="DataFeed",
    description="Stránka pro nahrávání souborů a správu MQTT."
)
def page() -> rx.Component:
    """page"""
    return rx.hstack(
        rx.container(
            rx.heading("📂 Nahraj soubor pro zpracování", size="4", margin_bottom="10px"),
            card(
                rx.vstack(
                    rx.upload(
                        rx.vstack(
                            rx.button("Vybrat soubor"),
                            rx.text("Přetáhněte nebo klikněte pro výběr .csv / .xlsx"),
                        ),
                        id="upload_xlsx",
                        multiple=False,
                        accept={
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                            "text/csv": [".csv"]
                        },
                        max_files=1,
                        on_drop=FileUploadState.handleUpload,
                    ),
                    rx.hstack(
                        rx.cond(FileUploadState.fileName != "", rx.text(f"📄 {FileUploadState.fileName}"), rx.text("❌ Žádný soubor nenahrán")),
                        rx.cond(FileUploadState.uploading, rx.text("⏳ Nahrávání..."), rx.text("✅ Hotovo!")),
                        spacing="2",
                    ),
                    spacing="4",
                    align="center",
                ),
            ),
            flex="1",
        ),
        rx.container(
            rx.heading("🔧 Nastavení MQTT", size="4", margin_bottom="10px"),
            card(
                rx.grid(
                    rx.text("Broker Address:", min_width="150px"),  
                    rx.input(
                        placeholder="Zadejte adresu brokera",
                        value=MQTTSettingsState.broker, 
                        on_change=lambda val: MQTTSettingsState.updateField("broker", val),
                        width="250px",
                    ),
                    rx.text("Port:", min_width="150px"),
                    rx.input(
                        placeholder="Např. 1883",
                        value=MQTTSettingsState.port, 
                        on_change=lambda val: MQTTSettingsState.updateField("port", val),
                        width="100px",
                    ),
                    rx.text("Topic:", min_width="150px"),
                    rx.input(
                        placeholder="Zadejte MQTT topic",
                        value=MQTTSettingsState.topic, 
                        on_change=lambda val: MQTTSettingsState.updateField("topic", val),
                        width="250px",
                    ),
                    rx.text("Username:", min_width="150px"),
                    rx.input(
                        placeholder="Zadejte uživatelské jméno",
                        value=MQTTSettingsState.username, 
                        on_change=lambda val: MQTTSettingsState.updateField("username", val),
                        width="250px",
                    ),
                    rx.text("Password:", min_width="150px"),
                    rx.input(
                        placeholder="Zadejte heslo",
                        value=MQTTSettingsState.password, 
                        type="password",
                        on_change=lambda val: MQTTSettingsState.updateField("password", val),
                        width="250px",
                    ),
                    spacing="2",
                    columns="auto 1fr",
                    width="100%",
                ),
                rx.hstack(
                    rx.button("💾 Uložit nastavení", on_click=MQTTSettingsState.saveMqttSettings, background="green", color="white"),
                    rx.button("🔍 Test připojení", on_click=MQTTSettingsState.testMqttConnection),
                    spacing="4",
                    margin_top="20px",
                    margin_bottom="20px",
                ),
                rx.text(MQTTSettingsState.connectionStatus, size="4"),
            ),
            flex="1",
        ),
        spacing="4",
        align="start",
        on_mount=MQTTSettingsState.loadMqttSettings
    )
