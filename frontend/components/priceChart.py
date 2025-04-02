import reflex as rx
from datetime import datetime, timedelta
from backend.database import getDb
from ..components.card import card
from .. import styles

class PriceChartState(rx.State):
    """Správa stavu grafu ceny elektřiny."""
    currentDate: str = datetime.today().strftime("%Y-%m-%d")
    priceChartData: list = []

    def fetchData(self):
        """Načítá data z databáze pro graf ceny elektřiny."""
        conn = getDb()
        cursor = conn.cursor()
        query = """
            SELECT strftime('%H', timestamp) AS hour, price, quantity
            FROM energyPrices
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (self.currentDate,))
        priceData = cursor.fetchall()
        conn.close()

        self.priceChartData = [
            {
                "hour": int(row[0]) + 1,
                "Cena [EUR/MWh]": row[1],
                "Množství [MWh]": row[2]
            }
            for row in priceData
        ]

    def shiftDay(self, direction: str):
        """Posune datum vpřed nebo vzad jen na dny s dostupnými daty."""
        conn = getDb()
        cursor = conn.cursor()

        if direction == "next":
            query = """
                SELECT MIN(DATE(timestamp)) FROM energyPrices
                WHERE DATE(timestamp) > ? AND price IS NOT NULL AND quantity IS NOT NULL
            """
        else:  # "prev"
            query = """
                SELECT MAX(DATE(timestamp)) FROM energyPrices
                WHERE DATE(timestamp) < ? AND price IS NOT NULL AND quantity IS NOT NULL
            """

        cursor.execute(query, (self.currentDate,))
        nextAvailableDate = cursor.fetchone()[0]
        conn.close()

        if nextAvailableDate:
            self.currentDate = nextAvailableDate  # Nastavíme nové dostupné datum
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
                    rx.button(rx.icon("chevron-left"), on_click=lambda: PriceChartState.shiftDay("prev"), style=styles.buttonStyle),
                    rx.text(PriceChartState.currentDate),
                    rx.button(rx.icon("chevron-right"), on_click=lambda: PriceChartState.shiftDay("next"), style=styles.buttonStyle),
                    spacing="4",
                ),

                # 📈 Graf ceny elektřiny (line chart) + Množství [MWh] (bar chart)
                rx.recharts.composed_chart(
                    rx.recharts.line(
                        data_key="Cena [EUR/MWh]",
                        stroke=styles.graphPriceColor,
                        stroke_width=3,
                        dot=True,
                    ),
                    rx.recharts.bar(
                        data_key="Množství [MWh]",
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
                            "value": "Cena [EUR/MWh]",
                            "angle": -90,
                            "position": "outsideLeft",
                            "dx": -20,
                        },
                        padding= {"top": 10}
                    ),
                    rx.recharts.y_axis(
                        tick_line=False,
                        y_axis_id="right",
                        orientation="right",
                        label={
                            "value": "Množství [MWh]",
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
