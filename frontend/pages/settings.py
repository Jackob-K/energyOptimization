import reflex as rx
import requests
import re
from typing import List, Dict
from frontend.templates import template  # Import dekorátoru pro šablonu
from frontend.components.card import card  # ✅ Import card komponenty

BACKEND_URL = "http://localhost:8000"  # 🔹 Opravený backend URL

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
                print(f"🔄 Načteno z DB: {self.fve_fields}")  # ✅ Zobrazíme skutečnou hodnotu
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
        """Umožní zadávat pouze čísla a desetinnou tečku, blokuje text."""
        
        value = value.replace(",", ".")  # Nahrazení čárky tečkou
        value = re.sub(r"[^\d.]", "", value)  # Odstranění nečíselných znaků (kromě tečky)
        
        # Povolit maximálně jednu desetinnou tečku
        if value.count(".") > 1:
            value = value.replace(".", "", value.count(".") - 1)

        updated_fields = self.fve_fields.copy()
        updated_fields[index] = updated_fields[index] | {key: value}  # Aktualizace hodnoty
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

# Použití šablony pro tuto stránku
@template(
    route="/settings",  # Definování cesty pro tuto stránku
    title="Settings",
    description="Manage your energy settings here."
)

def page() -> rx.Component:
    return rx.container(
        rx.heading("Nastavení FVE", size="5"),

        # ✅ Tlačítka "Přidat pole" a "Uložit změny" umístěná vpravo nahoře
        rx.hstack(
            rx.button("Přidat další FVE", on_click=SettingsState.add_field, size="3"),
            rx.button("Uložit parametry", on_click=SettingsState.submit_form, size="3", background="green", color="white"),
            spacing="4",
            justify="end",
            width="100%",
            margin_bottom="20px",
        ),
        

        rx.vstack(
            rx.foreach(
                SettingsState.fve_fields,
                lambda fve, index: card(
                    rx.heading(f"FVE {index + 1}", size="3"),

                    # ✅ Použití `rx.grid` pro automatické zarovnání textů
                    rx.grid(
                        rx.text("Zeměpisná šířka:", size="3"),
                        rx.input(placeholder="Zeměpisná šířka", name=f"latitude_{index}", value=fve["latitude"], 
                                 on_change=lambda val, idx=index: SettingsState.update_field(idx, "latitude", val)),
                        
                        rx.text("Zeměpisná délka:", size="3"),
                        rx.input(placeholder="Zeměpisná délka", name=f"longitude_{index}", value=fve["longitude"], 
                                 on_change=lambda val, idx=index: SettingsState.update_field(idx, "longitude", val)),

                        rx.text("Náklon panelů (°):", size="3"),
                        rx.input(placeholder="Náklon panelů (°)", name=f"tilt_{index}", value=fve["tilt"], 
                                 on_change=lambda val, idx=index: SettingsState.update_field(idx, "tilt", val)),

                        rx.text("Orientace panelů (°):", size="3"),
                        rx.input(placeholder="Orientace panelů (°)", name=f"azimuth_{index}", value=fve["azimuth"], 
                                 on_change=lambda val, idx=index: SettingsState.update_field(idx, "azimuth", val)),

                        rx.text("Výkon této části (kWp):", size="3"),
                        rx.input(placeholder="Výkon této části (kWp)", name=f"power_{index}", value=fve["power"], 
                                 on_change=lambda val, idx=index: SettingsState.update_field(idx, "power", val)),

                        spacing="3",  # ✅ Mezera mezi jednotlivými řádky
                        columns="1fr 1fr",  # ✅ Automatická šířka pro popisky, zbytek pro vstupy
                        width="100%",  # ✅ Aby grid byl široký jako karta
                    ),

                    # ✅ Tlačítko "Odstranit pole" správně umístěno
                    rx.box(
                        rx.cond(
                            SettingsState.fve_fields.length() > 1,  # ✅ Správná kontrola délky seznamu v Reflexu
                            rx.button("Odstranit pole", on_click=lambda idx=index: SettingsState.remove_field(idx), 
                                    style={"background": "red", "color": "white"})
                        ),
                        margin_top="10px",
                        justify="end",
                    ),


                    flex="1",  # ✅ Karta nyní zabírá celou dostupnou šířku
                )
            ),
            spacing="6",
        ),

        on_mount=SettingsState.load_fve_data  # ✅ UI se aktualizuje při startu
    )
