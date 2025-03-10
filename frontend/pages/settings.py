import reflex as rx
import requests
from typing import List, Dict

BACKEND_URL = "http://localhost:8000"  # 🔹 Opravený backend URL (používáme základní adresu)

class SettingsState(rx.State):
    fve_fields: List[Dict[str, str]] = []

    def load_fve_data(self):
        """Načte data FVE z databáze a aktualizuje UI."""
        try:
            response = requests.get(f"{BACKEND_URL}/get-settings/")
            if response.status_code == 200:
                data = response.json()
                self.set_fve_fields(data["fve_fields"])  # ✅ Synchronizujeme UI
                print(f"🔄 Načteno z DB: {data}")
            else:
                print("❌ Chyba při načítání dat.")
        except Exception as e:
            print(f"❌ Chyba API: {e}")

    def add_field(self):
        """Přidá nové pole pro další FVE a automaticky zkopíruje polohu, pokud už je vyplněna."""
        new_field = {
            "id": None,  # ✅ Nové pole nemá ID, dokud není uloženo
            "latitude": self.fve_fields[0]["latitude"] if self.fve_fields else "",
            "longitude": self.fve_fields[0]["longitude"] if self.fve_fields else "",
            "tilt": "",
            "azimuth": "",
            "power": ""
        }
        self.set_fve_fields(self.fve_fields + [new_field])  # ✅ Aktualizace UI

    def remove_field(self, index: int):
        """Odstraní pole FVE z UI a z databáze, pokud má ID."""
        if len(self.fve_fields) > 1:
            panel_id = self.fve_fields[index].get("id")
            updated_fields = self.fve_fields[:index] + self.fve_fields[index+1:]
            self.set_fve_fields(updated_fields)

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
        """Aktualizuje hodnotu v dynamicky přidávaném poli."""
        updated_fields = self.fve_fields.copy()
        updated_fields[index] = updated_fields[index] | {key: value}  # ✅ Aktualizace hodnoty
        self.set_fve_fields(updated_fields)

    def submit_form(self):
        """Odesílá data na backend přes API a poté obnoví UI."""
        try:
            total_power = sum(float(fve["power"]) for fve in self.fve_fields if fve["power"])
            fve_data = [
                {
                    "id": fve["id"],  # ✅ Pokud ID existuje, použije se pro update
                    "latitude": float(fve["latitude"]),
                    "longitude": float(fve["longitude"]),
                    "tilt": float(fve["tilt"]),
                    "azimuth": float(fve["azimuth"]),
                    "power": float(fve["power"])
                }
                for fve in self.fve_fields
            ]

            response = requests.post(
                f"{BACKEND_URL}/import-settings/",
                json={"totalPower": total_power, "fve_fields": fve_data}
            )

            if response.status_code == 200:
                print("✅ Parametry byly uloženy, aktualizuji UI...")
                self.load_fve_data()  # ✅ Po uložení obnovíme UI
                return rx.window_alert("✅ Parametry byly uloženy!")
            else:
                return rx.window_alert("❌ Chyba při ukládání.")

        except Exception as e:
            return rx.window_alert(f"❌ Chyba: {str(e)}")

def page() -> rx.Component:
    return rx.container(
        rx.heading("Nastavení FVE", size="2"),
        rx.foreach(
            SettingsState.fve_fields,
            lambda fve, index: rx.box(
                rx.heading(f"FVE {index + 1}"),
                rx.input(placeholder="Zeměpisná šířka", name=f"latitude_{index}", value=fve["latitude"], 
                         on_change=lambda val, idx=index: SettingsState.update_field(idx, "latitude", val)),
                rx.input(placeholder="Zeměpisná délka", name=f"longitude_{index}", value=fve["longitude"], 
                         on_change=lambda val, idx=index: SettingsState.update_field(idx, "longitude", val)),
                rx.input(placeholder="Náklon panelů (°)", name=f"tilt_{index}", value=fve["tilt"], 
                         on_change=lambda val, idx=index: SettingsState.update_field(idx, "tilt", val)),
                rx.input(placeholder="Orientace panelů (°)", name=f"azimuth_{index}", value=fve["azimuth"], 
                         on_change=lambda val, idx=index: SettingsState.update_field(idx, "azimuth", val)),
                rx.input(placeholder="Výkon této části (kWp)", name=f"power_{index}", value=fve["power"], 
                         on_change=lambda val, idx=index: SettingsState.update_field(idx, "power", val)),

                # ✅ Tlačítko "Odstranit pole"
                rx.button("Odstranit pole", on_click=lambda idx=index: SettingsState.remove_field(idx), style={"background": "red", "color": "white"}),

                padding="20px", border_radius="md", box_shadow="md", background="lightgray",
            )
        ),

        rx.button("Přidat další FVE", on_click=SettingsState.add_field),
        rx.button("Uložit parametry", on_click=SettingsState.submit_form),
        on_mount=SettingsState.load_fve_data  # ✅ UI se aktualizuje při startu
    )
