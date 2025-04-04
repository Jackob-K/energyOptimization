# 📄 Tento soubor obsahuje komponenty a stav pro správu nastavení aplikace (obecné, MQTT, baterie).
# ✅ Vstupy: seznam ID nastavení, vstupní hodnoty od uživatele.
# ✅ Výstupy: komponenty s formulářem a uložení změn přes backend.
# 🔄 Spolupracuje s backendem na adrese http://localhost:8000.

import reflex as rx
import httpx
import logging
from frontend.components.card import card

# 🌐 Adresa backendu
BACKEND_URL = "http://localhost:8000"

# 🛠️ Konfigurace logování
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
enableLogging = 1 

### 🔧 Pomocné funkce pro zpracování nastavení

def updateField(settingsData: list[dict], index: int, value: str) -> list[dict]:
    """
    Aktualizuje hodnotu pole v seznamu nastavení.
    """
    updated = settingsData.copy()
    updated[index]["value"] = value
    return updated


async def fetchSettings(ids: list[int]) -> list[dict]:
    """
    Načte nastavení z backendu podle ID.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/get-settings-values/",
                json={"ids": ids},
            )
        if response.status_code == 200:
            if enableLogging:
                logging.info("📊 Nastavení úspěšně načteno.")
            return response.json()
        else:
            if enableLogging:
                logging.error(f"❌ Chyba při načítání: {response.status_code}")
    except Exception as e:
        if enableLogging:
            logging.error(f"❌ Výjimka při načítání: {e}")
    return []


async def saveSettingsData(settingsData: list[dict]):
    """
    Uloží data nastavení na backend.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/save-settings-values/",
                json={"settings": settingsData},
            )
        if response.status_code == 200:
            if enableLogging:
                logging.info("✅ Nastavení bylo uloženo.")
            return rx.window_alert("✅ Nastavení bylo uloženo!")
        else:
            if enableLogging:
                logging.error(f"❌ Ukládání selhalo: {response.status_code}")
            return rx.window_alert("❌ Chyba při ukládání.")
    except Exception as e:
        if enableLogging:
            logging.error(f"❌ Výjimka při ukládání: {e}")
        return rx.window_alert(f"❌ Chyba: {str(e)}")


### 📦 Stavové třídy pro jednotlivé části nastavení

class MqttSettingsState(rx.State):
    """
    Stav pro MQTT nastavení.
    """
    settingsData: list[dict] = []
    ids: list[int] = []

    class Config:
        name = "mqtt_settings"

    async def initSettings(self, ids: list[int]):
        self.ids = ids
        self.settingsData = await fetchSettings(ids)

    def updateField(self, index: int, value: str):
        self.settingsData = updateField(self.settingsData, index, value)

    async def saveSettings(self):
        return await saveSettingsData(self.settingsData)


class GeneralSettingsState(rx.State):
    """
    Stav pro obecná nastavení.
    """
    settingsData: list[dict] = []
    ids: list[int] = []

    class Config:
        name = "general_settings"

    async def initSettings(self, ids: list[int]):
        self.ids = ids
        self.settingsData = await fetchSettings(ids)

    def updateField(self, index: int, value: str):
        self.settingsData = updateField(self.settingsData, index, value)

    async def saveSettings(self):
        return await saveSettingsData(self.settingsData)


class BatterySettingsState(rx.State):
    """
    Stav pro nastavení baterie.
    """
    settingsData: list[dict] = []
    ids: list[int] = []

    class Config:
        name = "battery_settings"

    async def initSettings(self, ids: list[int]):
        self.ids = ids
        self.settingsData = await fetchSettings(ids)

    def updateField(self, index: int, value: str):
        self.settingsData = updateField(self.settingsData, index, value)

    async def saveSettings(self):
        return await saveSettingsData(self.settingsData)


def generateSettingComponent(
    state: type[rx.State],
    ids: list[int],
    heading: str,
    buttonLabel: str,
    cardWidth: str = "100%",
):
    """
    Vygeneruje UI komponentu pro daný stav a ID nastavení.
    """
    return rx.center(  # Zarovná kartu na střed
        card(
            rx.vstack(
                rx.heading(heading, size="4"),
                rx.foreach(
                    state.settingsData,
                    lambda setting, index: rx.hstack(
                        rx.text(
                            setting["label"],
                            size="3",
                            width="100%",
                            overflow="hidden",
                            white_space="nowrap",
                            text_align="left",
                            flex="1"
                        ),
                        rx.input(
                            placeholder=setting["placeHolder"],
                            value=rx.cond(setting["value"] != "", setting["value"], ""),
                            on_change=lambda val, i=index: state.updateField(i, val),
                            min_width="100px",
                            max_width="150px",
                            flex="1",
                        ),
                        width="100%",
                        spacing="3",
                        align="center",
                    ),
                ),
                rx.button(buttonLabel, on_click=state.saveSettings),
                spacing="4",
                width="100%",
            ),
            width="100%",
        ),
        width=cardWidth,
        on_mount=state.initSettings(ids),
    )
