"""
Stránka Settings pro správu nastavení FVE, obecných parametrů a baterie.

Vstup: Uživatel upravuje konfiguraci FVE polí, obecné hodnoty a bateriové parametry.
Výstup: Změny jsou odeslány na backend ke zpracování.
Spolupracuje s: Stavové třídy FveFieldState, GeneralSettingsState a BatterySettingsState.
"""

import reflex as rx
import logging
from frontend.templates import template
from frontend.components.fveField import FveFieldState, fveFieldsForm
from frontend.components.settingField import generateSettingComponent, BatterySettingsState, GeneralSettingsState

# 🛠️ Logging
enableLogging = 1
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@template(
    route="/settings",
    title="Settings",
    description="Manage your energy settings here."
)
def page() -> rx.Component:
    """
    Hlavní komponenta pro stránku nastavení. Obsahuje sekce pro:
    - FVE pole (dynamická formulářová pole)
    - Obecné nastavení
    - Nastavení baterií
    """
    if enableLogging:
        logging.info("🚀 Stránka Settings byla načtena.")

    return rx.grid(
        # 🧩 Tři komponenty – FVE, obecné, baterie
        rx.box(
            rx.vstack(
                rx.heading("Nastavení FVE", size="5"),
                rx.hstack(
                    rx.button("Přidat další FVE", on_click=FveFieldState.add_field, size="3"),
                    rx.button("Uložit parametry", on_click=FveFieldState.submit_form, size="3", background="green", color="white"),
                    spacing="4",
                    justify="start",
                    width="100%",
                ),
                fveFieldsForm(),
                spacing="4",
            ),
        ),

        generateSettingComponent(
            GeneralSettingsState,
            [1, 2, 3],
            "⚙️ Obecné",
            "💾 Uložit obecné nastavení",
            cardWidth="300px"
        ),

        generateSettingComponent(
            BatterySettingsState,
            [16, 17, 18, 19, 20, 21],
            "🔋 Baterie",
            "💾 Uložit baterii",
            cardWidth="400px"
        ),

        # ✅ AŽ TEĎ přidáváme grid parametry
        columns="repeat(3, auto)",
        gap="32px",
        align="start",
        justify="start",
        width="100%",
    )
