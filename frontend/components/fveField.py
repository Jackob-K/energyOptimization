import reflex as rx
import requests
import re
from typing import List, Dict
from frontend.components.card import card

BACKEND_URL = "http://localhost:8000"

class FveFieldState(rx.State):
    fveFields: List[Dict[str, str]] = []

    def loadFveData(self):
        """Načte data FVE z databáze a aktualizuje UI."""
        try:
            response = requests.get(f"{BACKEND_URL}/get-settings/")
            if response.status_code == 200:
                data = response.json()
                self.set_fveFields(data["fveFields"])
            else:
                print("❌ Chyba při načítání dat.")
        except Exception as e:
            print(f"❌ Chyba API: {e}")

    def add_field(self):
        """Přidá nové pole pro další FVE a automaticky zkopíruje polohu, pokud už je vyplněna."""
        new_field = {
            "id": None,
            "latitude": self.fveFields[0]["latitude"] if self.fveFields else "",
            "longitude": self.fveFields[0]["longitude"] if self.fveFields else "",
            "tilt": "",
            "azimuth": "",
            "power": ""
        }
        self.set_fveFields(self.fveFields + [new_field])

    def remove_field(self, index: int):
        """Odstraní pole FVE z UI a z databáze, pokud má ID."""
        if len(self.fveFields) > 1:
            panel_id = self.fveFields[index].get("id")
            updated_fields = self.fveFields[:index] + self.fveFields[index+1:]
            self.set_fveFields(updated_fields)

            if panel_id:
                try:
                    response = requests.delete(f"{BACKEND_URL}/delete-fve/{panel_id}")
                    if response.status_code == 200:
                        print(f"🗑 Panel ID {panel_id} smazán z DB.")
                    else:
                        print(f"❌ Chyba při mazání panelu ID {panel_id}")
                except Exception as e:
                    print(f"❌ Chyba API: {e}")

    def update_field(self, index: int, key: str, value: str):
        """Umožní zadávat pouze čísla a desetinnou tečku, blokuje text."""
        value = value.replace(",", ".")
        value = re.sub(r"[^\d.]", "", value)
        
        if value.count(".") > 1:
            value = value.replace(".", "", value.count(".") - 1)

        updated_fields = self.fveFields.copy()
        updated_fields[index] = updated_fields[index] | {key: value}
        self.set_fveFields(updated_fields)

    def submit_form(self):
        """Odesílá data na backend přes API a poté obnoví UI."""
        try:
            fve_data = [
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
                json={"fveFields": fve_data}
            )

            if response.status_code == 200:
                print("✅ Parametry byly uloženy, aktualizuji UI...")
                self.loadFveData()
                return rx.window_alert("✅ Parametry byly uloženy!")
            else:
                return rx.window_alert("❌ Chyba při ukládání.")

        except Exception as e:
            return rx.window_alert(f"❌ Chyba: {str(e)}")

def fveFieldsForm() -> rx.Component:
    """Vrací komponentu s FVE poli"""
    return rx.box(  # ✅ Přidá obal s max_width
        rx.vstack(
            rx.foreach(
                FveFieldState.fveFields,
                lambda fve, index: card(
                    rx.heading(f"FVE {index + 1}", size="3"),

                    rx.grid(
                        rx.text("Zeměpisná šířka:", size="3"),
                        rx.input(
                            placeholder="Zeměpisná šířka",
                            name=f"latitude_{index}",
                            value=fve["latitude"],
                            on_change=lambda val, idx=index: FveFieldState.update_field(idx, "latitude", val),
                        ),
                        rx.text("Zeměpisná délka:", size="3"),
                        rx.input(
                            placeholder="Zeměpisná délka",
                            name=f"longitude_{index}",
                            value=fve["longitude"],
                            on_change=lambda val, idx=index: FveFieldState.update_field(idx, "longitude", val),
                        ),
                        rx.text("Náklon panelů (°):", size="3"),
                        rx.input(
                            placeholder="Náklon panelů (°)",
                            name=f"tilt_{index}",
                            value=fve["tilt"],
                            on_change=lambda val, idx=index: FveFieldState.update_field(idx, "tilt", val),
                        ),
                        rx.text("Orientace panelů (°):", size="3"),
                        rx.input(
                            placeholder="Orientace panelů (°)",
                            name=f"azimuth_{index}",
                            value=fve["azimuth"],
                            on_change=lambda val, idx=index: FveFieldState.update_field(idx, "azimuth", val),
                        ),
                        rx.text("Výkon této části (kWp):", size="3"),
                        rx.input(
                            placeholder="Výkon této části (kWp)",
                            name=f"power_{index}",
                            value=fve["power"],
                            on_change=lambda val, idx=index: FveFieldState.update_field(idx, "power", val),
                        ),
                        spacing="3",
                        columns="1fr 1fr",
                        width="100%",
                    ),

                    rx.box(
                        rx.cond(
                            FveFieldState.fveFields.length() > 1,
                            rx.button("Odstranit pole", on_click=lambda idx=index: FveFieldState.remove_field(idx),
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
        width="100%",
        max_width="500px",  # ✅ Omezí šířku
    )
