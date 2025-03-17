"""
Stránka nastavení FVE umožňuje správu a konfiguraci fotovoltaických panelů.

Vstup: Uživatel zadává zeměpisné souřadnice, náklon, orientaci a výkon jednotlivých panelů.
Výstup: Data jsou uložena v databázi a aktualizují se v UI.
Spolupracuje s: Backend API pro načítání, ukládání a mazání FVE panelů.
"""

import reflex as rx
import requests
import re
from typing import List, Dict
from frontend.templates import template  
from frontend.components.card import card  

BACKEND_URL = "http://localhost:8000"

class SettingsState(rx.State):
    """SettingsState"""
    fveFields: List[Dict[str, str]] = []

    def loadFveData(self):
        """loadFveData"""
        try:
            response = requests.get(f"{BACKEND_URL}/get-settings/")
            if response.status_code == 200:
                data = response.json()
                self.set_fveFields(data["fveFields"])  
            else:
                print("❌ Chyba při načítání dat.")
        except Exception as e:
            print(f"❌ Chyba API: {e}")

    def addField(self):
        """addField"""
        newField = {
            "id": None,
            "latitude": self.fveFields[0]["latitude"] if self.fveFields else "",
            "longitude": self.fveFields[0]["longitude"] if self.fveFields else "",
            "tilt": "",
            "azimuth": "",
            "power": ""
        }
        self.set_fveFields(self.fveFields + [newField])  

    def removeField(self, index: int):
        """removeField"""
        if len(self.fveFields) > 1:
            panelId = self.fveFields[index].get("id")
            updatedFields = self.fveFields[:index] + self.fveFields[index+1:]
            self.set_fveFields(updatedFields)

            if panelId:
                try:
                    response = requests.delete(f"{BACKEND_URL}/delete-fve/{panelId}")
                    if response.status_code == 200:
                        print(f"🗑 Panel ID {panelId} smazán z DB.")
                    else:
                        print(f"❌ Chyba při mazání panelu ID {panelId}")
                except Exception as e:
                    print(f"❌ Chyba API: {e}")

    def updateField(self, index: int, key: str, value: str):
        """updateField"""
        value = value.replace(",", ".")  
        value = re.sub(r"[^\d.]", "", value)  

        if value.count(".") > 1:
            value = value.replace(".", "", value.count(".") - 1)

        updatedFields = self.fveFields.copy()
        updatedFields[index] = updatedFields[index] | {key: value}  
        self.set_fveFields(updatedFields)
        
    def submitForm(self):
        """submitForm"""
        try:
            fveData = [
                {
                    "id": fve["id"],
                    "latitude": float(fve["latitude"]),
                    "longitude": float(fve["longitude"]),
                    "tilt": float(fve["tilt"]),
                    "azimuth": float(fve["azimuth"]),
                    "power": float(fve["power"])
                }
                for fve in self.fveFields
            ]

            response = requests.post(
                f"{BACKEND_URL}/import-settings/",
                json={"fveFields": fveData}
            )

            if response.status_code == 200:
                print("✅ Parametry byly uloženy, aktualizuji UI...")
                self.loadFveData()  
                return rx.window_alert("✅ Parametry byly uloženy!")
            else:
                return rx.window_alert("❌ Chyba při ukládání.")

        except Exception as e:
            return rx.window_alert(f"❌ Chyba: {str(e)}")

@template(
    route="/settings",
    title="Settings",
    description="Manage your energy settings here."
)
def page() -> rx.Component:
    """page"""
    return rx.container(
        rx.heading("Nastavení FVE", size="5"),

        rx.hstack(
            rx.button("Přidat další FVE", on_click=SettingsState.addField, size="3"),
            rx.button("Uložit parametry", on_click=SettingsState.submitForm, size="3", background="green", color="white"),
            spacing="4",
            justify="end",
            width="100%",
            margin_bottom="20px",
        ),

        rx.vstack(
            rx.foreach(
                SettingsState.fveFields,
                lambda fve, index: card(
                    rx.heading(f"FVE {index + 1}", size="3"),

                    rx.grid(
                        rx.text("Zeměpisná šířka:", size="3"),
                        rx.input(placeholder="Zeměpisná šířka", name=f"latitude_{index}", value=fve["latitude"], 
                                 on_change=lambda val, idx=index: SettingsState.updateField(idx, "latitude", val)),
                        
                        rx.text("Zeměpisná délka:", size="3"),
                        rx.input(placeholder="Zeměpisná délka", name=f"longitude_{index}", value=fve["longitude"], 
                                 on_change=lambda val, idx=index: SettingsState.updateField(idx, "longitude", val)),

                        rx.text("Náklon panelů (°):", size="3"),
                        rx.input(placeholder="Náklon panelů (°)", name=f"tilt_{index}", value=fve["tilt"], 
                                 on_change=lambda val, idx=index: SettingsState.updateField(idx, "tilt", val)),

                        rx.text("Orientace panelů (°):", size="3"),
                        rx.input(placeholder="Orientace panelů (°)", name=f"azimuth_{index}", value=fve["azimuth"], 
                                 on_change=lambda val, idx=index: SettingsState.updateField(idx, "azimuth", val)),

                        rx.text("Výkon této části (kWp):", size="3"),
                        rx.input(placeholder="Výkon této části (kWp)", name=f"power_{index}", value=fve["power"], 
                                 on_change=lambda val, idx=index: SettingsState.updateField(idx, "power", val)),

                        spacing="3",
                        columns="1fr 1fr",
                        width="100%",
                    ),

                    rx.box(
                        rx.cond(
                            SettingsState.fveFields.length() > 1,  
                            rx.button("Odstranit pole", on_click=lambda idx=index: SettingsState.removeField(idx), 
                                    style={"background": "red", "color": "white"})
                        ),
                        margin_top="10px",
                        justify="end",
                    ),

                    flex="1",  
                )
            ),
            spacing="6",
        ),

        on_mount=SettingsState.loadFveData  
    )
