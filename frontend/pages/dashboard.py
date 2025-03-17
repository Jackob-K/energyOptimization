"""
Modul pro hlavní stránku dashboardu s grafy.

Vstup: Stavy grafů (MainChartState, PriceChartState).
Výstup: Dashboard zobrazující hlavní graf spotřeby/výroby a cenový graf.
Spolupracuje s: Reflex (UI framework), frontend.templates (šablona), mainChart, priceChart.
"""

import reflex as rx
from ..templates import template
from ..components.mainChart import mainChart, MainChartState
from ..components.priceChart import priceChart, PriceChartState

def resetButton():
    """resetButton"""
    return rx.box(
        rx.button(
            "🔄 Restart na dnešní datum",
            on_click=[MainChartState.setToday, PriceChartState.setToday],
            size="3",
            color_scheme="blue",
        ),
        style={
            "position": "absolute",
            "top": "1rem",
            "right": "1rem",
            "z_index": "1000"
        }
    )

@template(route="/dashboard", title="Dashboard", on_load=[MainChartState.setToday, PriceChartState.setToday])
def page() -> rx.Component:
    """page"""
    return rx.vstack(
        resetButton(),
        mainChart(),
        rx.hstack(
            priceChart(),
            spacing="4",
            width="100%",
        ),
        spacing="8",
        width="100%",
    )
