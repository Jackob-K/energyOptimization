import reflex as rx
import requests
from ..templates import template  # Import nové šablony
from ..components.card import card
from .. import styles

API_URL = "http://localhost:8000/energy-data"  # Backend API pro získání dat

def fetch_energy_data():
    """Načítá surová data z backendu a umožňuje filtraci."""
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            return response.json()  # ✅ Vrací všechna data
    except Exception as e:
        print(f"❌ Chyba API: {e}")
    return []

def energy_chart():
    """Komponenta zobrazující graf spotřeby a výroby elektřiny s vyplněnou oblastí."""
    full_data = fetch_energy_data()  # ✅ Načteme kompletní data

    # ✅ Filtrování dat: například každý druhý den
    data = full_data[::2]  # Můžeme změnit na `::3` pro každý třetí den

    return card(
        rx.vstack(
            rx.heading("Denní spotřeba vs. výroba elektřiny", size="4"),
            rx.recharts.area_chart(  # ✅ Použijeme area_chart místo line_chart!
                # ✅ První čára - Spotřeba elektřiny
                rx.recharts.area(
                    data_key="consumption",
                    type_="basis",
                    stroke=styles.accent_text_color,
                    stroke_width=3,
                    fill="rgba(255, 99, 132, 0.3)",  # ✅ Červená výplň
                    fill_opacity=0.3,
                    dot=False,
                ),
                # ✅ Druhá čára - Výroba FVE
                rx.recharts.area(
                    data_key="production",
                    type_="basis",
                    stroke=styles.accent_color,
                    stroke_width=3,
                    fill="rgba(54, 162, 235, 0.3)",  # ✅ Modrá výplň
                    fill_opacity=0.3,
                    dot=False,
                ),
                rx.recharts.x_axis(
                    data_key="timestamp",
                    angle=-45,
                    dy=20,
                    tick_size=10,
                    tick_line=False,
                ),
                rx.recharts.y_axis(
                    tick_line=False,
                    domain=["auto", "auto"],
                ),
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    vertical=False,
                ),
                rx.recharts.graphing_tooltip(),
                data=data,  # ✅ Používáme filtrovaná data!
                width="100%",
                height=500,
            ),
            width="100%",
        ),
        width="115%",
        max_width="115%",
    )


@template(route="/dashboard", title="Dashboard")
def page() -> rx.Component:
    """Dashboard stránka zobrazující pouze graf."""
    return rx.vstack(
        energy_chart(),
        spacing="8",
        width="100%",
    )