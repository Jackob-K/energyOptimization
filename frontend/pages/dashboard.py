import reflex as rx
from ..templates import template
from ..components.mainChart import mainChart, MainChartState
from ..components.priceChart import priceChart, PriceChartState

def resetButton():
    """Tlačítko pro reset na dnešní datum."""
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

@template(route="/dashboard", title="Dashboard")
def page() -> rx.Component:
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
