import reflex as rx
import sqlite3
from datetime import datetime, timedelta
from ..templates import template
from ..components.card import card
from ..components.charts import ChartState
from .. import styles
from backend.database import get_db  # ✅ Načteme vaši funkci pro DB připojení

# ✅ Stavy pro datum a interval
class EnergyChartState(rx.State):
    """Správa stavu hlavního grafu (výroba/spotřeba)."""
    current_date: str = datetime.today().strftime("%Y-%m-%d")
    selected_interval: str = "month"
    chart_data: list = []

    def fetch_data(self):
        """Načítá data z databáze pro hlavní graf."""
        conn = get_db()
        cursor = conn.cursor()
        end_date = datetime.strptime(self.current_date, "%Y-%m-%d")

        if self.selected_interval == "week":
            start_date = (end_date - timedelta(days=end_date.weekday())).strftime("%Y-%m-%d")
            end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
        elif self.selected_interval == "month":
            start_date = end_date.replace(day=1).strftime("%Y-%m-%d")
            end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            end_date = end_date.strftime("%Y-%m-%d")
        else:  # "year"
            start_date = end_date.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_date = end_date.replace(month=12, day=31).strftime("%Y-%m-%d")

        query = """
            SELECT date, SUM(fveProduction), SUM(consumption)
            FROM energyData 
            WHERE date BETWEEN ? AND ? AND hour = 24
            GROUP BY date
            ORDER BY date ASC
        """
        cursor.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        conn.close()

        self.chart_data = [{"timestamp": row[0], "production": row[1], "consumption": row[2]} for row in data]

    def shift_date(self, direction: str):
        """Posune datum dopředu nebo dozadu podle intervalu."""
        date_obj = datetime.strptime(self.current_date, "%Y-%m-%d")

        if self.selected_interval == "week":
            delta = timedelta(weeks=1)
        elif self.selected_interval == "month":
            delta = timedelta(days=32)
        else:  # "year"
            delta = timedelta(days=365)

        if direction == "next":
            date_obj += delta
        else:
            date_obj -= delta

        if self.selected_interval == "week":
            date_obj -= timedelta(days=date_obj.weekday())
        elif self.selected_interval == "month":
            date_obj = date_obj.replace(day=1)
        else:
            date_obj = date_obj.replace(month=1, day=1)

        self.current_date = date_obj.strftime("%Y-%m-%d")
        self.fetch_data()

    def set_selected_interval(self, interval: str):
        """Změní interval a aktualizuje data."""
        self.selected_interval = interval
        self.fetch_data()

    def set_today(self):
        """Nastaví datum na dnešní den."""
        self.current_date = datetime.today().strftime("%Y-%m-%d")
        self.fetch_data()


class PriceChartState(rx.State):
    """Správa stavu grafu ceny elektřiny."""
    current_date: str = datetime.today().strftime("%Y-%m-%d")
    price_chart_data: list = []

    def fetch_data(self):
        """Načítá data z databáze pro graf ceny elektřiny."""
        conn = get_db()
        cursor = conn.cursor()
        query = """
            SELECT hodina+1, cena, mnozstvi
            FROM energy_prices
            WHERE datum = ?
            ORDER BY hodina ASC
        """
        cursor.execute(query, (self.current_date,))
        price_data = cursor.fetchall()
        conn.close()

        self.price_chart_data = [{"hour": row[0], "price": row[1], "quantity": row[2]} for row in price_data]

    def shift_day(self, direction: str):
        """Posune datum o jeden den vpřed nebo vzad."""
        date_obj = datetime.strptime(self.current_date, "%Y-%m-%d")
        date_obj += timedelta(days=1 if direction == "next" else -1)
        self.current_date = date_obj.strftime("%Y-%m-%d")
        self.fetch_data()

    def set_today(self):
        """Nastaví datum na dnešní den."""
        self.current_date = datetime.today().strftime("%Y-%m-%d")
        self.fetch_data()



############################################################
#                        HLAVNÍ GRAF                       #
############################################################

def energy_chart():
    """Komponenta zobrazující graf s možností přepínání období."""
    return card(
        rx.vstack(
            rx.heading("Spotřeba vs. Výroba elektřiny", size="4"),

            # 🔽 Dropdown pro volbu intervalu (odstraněn denní graf)
            rx.hstack(
                rx.text("Zvolte období:"),
                rx.select(
                    ["week", "month", "year"],  # ✅ Odebrán "day"
                    value=EnergyChartState.selected_interval,
                    on_change=EnergyChartState.set_selected_interval,
                ),
                spacing="4",
            ),

            # 🔄 Navigace šipkami pro posun
            rx.hstack(
                rx.button("⬅️", on_click=lambda: EnergyChartState.shift_date("prev")),
                rx.text(EnergyChartState.current_date),
                rx.button("➡️", on_click=lambda: EnergyChartState.shift_date("next")),
                spacing="4",
            ),

            # 📈 Graf s daty
            rx.recharts.area_chart(
                rx.recharts.area(
                    data_key="consumption",
                    type_="basis",
                    stroke=styles.accent_text_color,
                    stroke_width=3,
                    fill="rgba(255, 99, 132, 0.3)",  # Červená výplň
                    fill_opacity=0.3,
                    dot=False,
                ),
                rx.recharts.area(
                    data_key="production",
                    type_="basis",
                    stroke=styles.accent_color,
                    stroke_width=3,
                    fill="rgba(54, 162, 235, 0.3)",  # Modrá výplň
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
                data=EnergyChartState.chart_data,
                width="100%",
                height=500,
            ),
            width="100%",
        ),
        width="115%",
        max_width="115%",
    )

############################################################
#                         GRAF CEN                        #
############################################################

def price_chart():
    """Komponenta zobrazující denní ceny elektřiny."""
    return card(
        rx.vstack(
            rx.heading(f"Výsledky denního trhu ČR - {PriceChartState.current_date}", size="4"),

            # 🔄 Navigace šipkami pro přepínání dnů
            rx.hstack(
                rx.button("⬅️", on_click=lambda: PriceChartState.shift_day("prev")),
                rx.text(PriceChartState.current_date),
                rx.button("➡️", on_click=lambda: PriceChartState.shift_day("next")),
                spacing="4",
            ),

            # 📈 Graf ceny elektřiny (line chart) + Množství (bar chart)
            rx.recharts.composed_chart(
                rx.recharts.line(
                    data_key="price",
                    stroke=styles.graph_price_color,  # ✅ Oranžová čára
                    stroke_width=3,
                    dot=True,
                ),
                rx.recharts.bar(
                    data_key="quantity",
                    fill=styles.graph_quantity_fill,  # ✅ Zelená výplň
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
                    domain=["0", "auto"],
                    label={
                        "value": "Cena (EUR/MWh)",
                        "angle": -90,
                        "position": "left"
                    },
                ),
                rx.recharts.y_axis(
                    tick_line=False,
                    domain=["0", "auto"],
                    y_axis_id="right",
                    orientation="right",
                    label={
                        "value": "Množství MWh",
                        "angle": -90,
                        "position": "right"
                    },
                ),
                rx.recharts.cartesian_grid(
                    stroke_dasharray="3 3",
                    vertical=False,
                ),
                rx.recharts.legend(),  # ✅ Přidáme legendu
                rx.recharts.graphing_tooltip(),
                data=PriceChartState.price_chart_data,
                width="95%",
                height=500,
            ),
            width="100%",
        ),
        width="55%",  # ✅ Poloviční šířka
        max_width="55%",
    )

############################################################
#                     VYKRESLENÍ GRAFŮ                    #
############################################################

def reset_button():
    return card(
        rx.button(
            "🔄 Restart na dnešní datum",
            on_click=[EnergyChartState.set_today, PriceChartState.set_today],  # ✅ Správný způsob
            width="100%",
            size="3",  # ✅ Opravená velikost tlačítka
            color_scheme="blue",
        ),
        width="30%",
    )



@template(route="/dashboard", title="Dashboard")
def page() -> rx.Component:
    return rx.vstack(
        reset_button(),
        energy_chart(),
        rx.hstack(
            price_chart(),
            spacing="4",
            width="100%",
        ),
        spacing="8",
        width="100%",
    )
