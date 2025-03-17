# frontend/pages/datafeed.py
import httpx
import reflex as rx
import base64
import requests
from frontend.templates import template  # Import dekorátoru pro šablonu
from frontend.components.card import card 

BACKEND_URL = "http://localhost:8000"

# Třída pro stav nahrávání souboru
class FileUploadState(rx.State):
    """Ukládá stav nahrávání souboru."""
    file_name: str = ""
    uploading: bool = False

    @rx.event(background=True)
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Pošle vybraný soubor na backend jako Base64 JSON."""
        async with self:
            if self.uploading:
                return

            self.uploading = True

        try:
            for file in files:
                file_data = file  # Reflex již posílá bytes, takže nepoužíváme file.read()

                # Zakódujeme soubor do Base64
                file_base64 = base64.b64encode(file_data).decode("utf-8")
                
                # Získáme název souboru
                file_name = getattr(file, "name", "uploaded_file.xlsx")

                # Pošleme JSON do backendu
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://127.0.0.1:8000/upload/",
                        json={"filename": file_name, "filedata": file_base64},
                    )

                async with self:
                    if response.status_code == 200:
                        self.file_name = file_name
                        print(f"✅ Soubor {file_name} úspěšně nahrán!")
                    else:
                        error_text = response.text
                        print(f"❌ Chyba při nahrávání: {error_text}")

        except Exception as e:
            print(f"❌ Chyba v handle_upload: {e}")

        async with self:
            self.uploading = False

class MQTTSettingsState(rx.State):
    """Ukládá stav MQTT nastavení a umožňuje jeho správu."""
    broker: str = "test.mosquitto.org"
    port: int = 1883
    topic: str = "energy/data"
    username: str = ""
    password: str = ""
    connection_status: str = "❓ Neznámý stav"

    def update_field(self, key: str, value: str):
        """Aktualizuje konkrétní pole v MQTT nastavení."""
        self.__dict__[key] = value  # ✅ Reflexově správná aktualizace

    def load_mqtt_settings(self):
        """Načte uložené MQTT nastavení z databáze."""
        try:
            response = requests.get(f"{BACKEND_URL}/get-mqtt-settings/")
            if response.status_code == 200:
                data = response.json()
                
                # ✅ Nastavíme hodnoty pouze pokud existují v odpovědi API
                for key in ["broker", "port", "topic", "username", "password"]:
                    if key in data and data[key] is not None:
                        setattr(self, key, data[key])

                print("✅ MQTT nastavení načteno")
            else:
                print("❌ Chyba při načítání MQTT nastavení")
        except Exception as e:
            print(f"❌ Chyba API: {e}")

    def save_mqtt_settings(self):
        """Odešle MQTT nastavení do databáze."""
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

    def test_mqtt_connection(self):
        """Ověří připojení k MQTT brokeru."""
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
                self.connection_status = "✅ Připojení úspěšné"
            else:
                self.connection_status = "❌ Připojení selhalo"
        except Exception as e:
            self.connection_status = "❌ Chyba při připojení"
            print(f"❌ Chyba API: {e}")

# Použití šablony pro tuto stránku
@template(
    route="/datafeed",  # Definování cesty pro tuto stránku
    title="DataFeed",
    description="This is the Data Feed page for uploading historical data."
)

def page() -> rx.Component:
    return rx.hstack(
        # ✅ Kontejner pro nahrávání souboru
        rx.container(
            rx.heading("📂 Nahraj soubor pro zpracování", size="4", margin_bottom="10px"),  # ✅ Nadpis umístěný nad kartou
            
            card(
                rx.vstack(
                    rx.upload(
                        rx.vstack(
                            rx.button("Vybrat soubor"),
                            rx.text("Můžeš přetáhnout nebo kliknout pro výběr .csv / .xlsx"),
                        ),
                        id="upload_xlsx",
                        multiple=False,
                        accept={
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                            "text/csv": [".csv"]
                        },
                        max_files=1,
                        on_drop=FileUploadState.handle_upload,
                        

                    ),

                    # ✅ Místo pro úpravy zobrazení informací o nahrávání souboru
                    rx.hstack(
                        rx.cond(FileUploadState.file_name != "", rx.text(f"📄 {FileUploadState.file_name}"), rx.text("❌ Žádný soubor nenahrán")),
                        rx.cond(FileUploadState.uploading, rx.text("⏳ Nahrávání..."), rx.text("✅ Hotovo!")),
                        spacing="2",
                    ),

                    spacing="4",
                    align="center",
                ),
            ),
            flex="1",
        ),
        
        # ✅ Druhý kontejner pro Nastavení MQTT
        rx.container(
            rx.heading("🔧 Nastavení MQTT", size="4", margin_bottom="10px"),  # ✅ Nadpis umístěný nad kartou
            
            card(
                rx.grid(
                    rx.text("Broker Address:", min_width="150px"),  
                    rx.input(
                        placeholder="Zadejte adresu brokera",
                        value=MQTTSettingsState.broker, 
                        on_change=lambda val: MQTTSettingsState.update_field("broker", val),
                        width="250px",
                    ),

                    rx.text("Port:", min_width="150px"),
                    rx.input(
                        placeholder="Např. 1883",
                        value=MQTTSettingsState.port, 
                        on_change=lambda val: MQTTSettingsState.update_field("port", val),
                        width="100px",
                    ),

                    rx.text("Topic:", min_width="150px"),
                    rx.input(
                        placeholder="Zadejte MQTT topic",
                        value=MQTTSettingsState.topic, 
                        on_change=lambda val: MQTTSettingsState.update_field("topic", val),
                        width="250px",
                    ),

                    rx.text("Username:", min_width="150px"),
                    rx.input(
                        placeholder="Zadejte uživatelské jméno",
                        value=MQTTSettingsState.username, 
                        on_change=lambda val: MQTTSettingsState.update_field("username", val),
                        width="250px",
                    ),

                    rx.text("Password:", min_width="150px"),
                    rx.input(
                        placeholder="Zadejte heslo",
                        value=MQTTSettingsState.password, 
                        type="password",
                        on_change=lambda val: MQTTSettingsState.update_field("password", val),
                        width="250px",
                    ),

                    spacing="2",
                    columns="auto 1fr",
                    width="100%",
                ),

                rx.hstack(
                    rx.button("💾 Uložit nastavení", on_click=MQTTSettingsState.save_mqtt_settings, background="green", color="white"),
                    rx.button("🔍 Test připojení", on_click=MQTTSettingsState.test_mqtt_connection),
                    spacing="4",
                    margin_top="20px",
                    margin_bottom="20px",
                ),

                rx.text(MQTTSettingsState.connection_status, size="4"),
            ),
            flex="1",
        ),

        spacing="4",
        align="start",
        on_mount=MQTTSettingsState.load_mqtt_settings
    )
