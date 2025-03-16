import reflex as rx
from datetime import datetime, timedelta
from backend.database import get_db
from ..components.card import card
from .. import styles

class PriceChartState(rx.State):
    """Správa stavu grafu ceny elektřiny."""
    currentDate: str = datetime.today().strftime("%Y-%m-%d")
    priceChartData: list = []

    def fetchData(self):
        """Načítá data z databáze pro graf ceny elektřiny."""
        conn = get_db()
        cursor = conn.cursor()
        query = """
            SELECT hodina+1, cena, mnozstvi
            FROM energy_prices
            WHERE datum = ?
            ORDER BY hodina ASC
        """
        cursor.execute(query, (self.currentDate,))
        priceData = cursor.fetchall()
        conn.close()

        self.priceChartData = [{"hour": row[0], "price": row[1], "quantity": row[2]} for row in priceData]

    def shiftDay(self, direction: str):
        """Posune datum o jeden den vpřed nebo vzad."""
        dateObj = datetime.strptime(self.currentDate, "%Y-%m-%d")
        dateObj += timedelta(days=1 if direction == "next" else -1)
        self.currentDate = dateObj.strftime("%Y-%m-%d")
        self.fetchData()

    def setToday(self):
        """Nastaví datum na dnešní den."""
        self.currentDate = datetime.today().strftime("%Y-%m-%d")
        self.fetchData()

def priceChart():
    """Komponenta zobrazující denní ceny elektřiny."""
    return rx.box(
        rx.heading(f"Výsledky denního trhu ČR - {PriceChartState.currentDate}", size="4"),
        card(
            rx.vstack(
                # 🔄 Navigace šipkami pro přepínání dnů
                rx.hstack(
                    rx.button(rx.icon("chevron-left"), on_click=lambda: PriceChartState.shiftDay("prev"), style=styles.button_style),
                    rx.text(PriceChartState.currentDate),
                    rx.button(rx.icon("chevron-right"), on_click=lambda: PriceChartState.shiftDay("next"), style=styles.button_style),
                    spacing="4",
                ),

                # 📈 Graf ceny elektřiny (line chart) + Množství (bar chart)
                rx.recharts.composed_chart(
                    rx.recharts.line(
                        data_key="price",
                        stroke=styles.graphPriceColor,
                        stroke_width=3,
                        dot=True,
                    ),
                    rx.recharts.bar(
                        data_key="quantity",
                        fill=styles.graphQuantityFill, 
                        bar_size=15,
                        y_axis_id="right",
                    ),
                    rx.recharts.x_axis(
                        data_key="hour",
                        tick_size=10,
                        tick_line=False,
                    ),
                    rx.recharts.y_axis(
                        tick_line=False,
                        label={
                            "value": "Cena (EUR/MWh)",
                            "angle": -90,
                            "position": "outsideLeft",
                            "dx": -20,
                        },
                    ),
                    rx.recharts.y_axis(
                        tick_line=False,
                        y_axis_id="right",
                        orientation="right",
                        label={
                            "value": "Množství (MWh)",
                            "angle": 90,
                            "position": "outsideRight",
                            "dx": 30,
                        },
                    ),
                    rx.recharts.cartesian_grid(
                        stroke_dasharray="3 3",
                        vertical=False,
                    ),
                    rx.recharts.legend(),
                    rx.recharts.graphing_tooltip(),
                    data=PriceChartState.priceChartData,
                    width="100%",
                    height=500,
                    margin={"left": 10, "right": 10},
                ),
                width="100%",
            ),
            width="100%",
            max_width="100%",
        ),
        width="55%",
    )
