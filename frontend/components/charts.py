import reflex as rx
import sqlite3
from datetime import datetime, timedelta
from backend.database import get_db  # Funkce pro připojení k databázi

class ChartState(rx.State):
    """Správa stavu grafů – aktuální datum a interval."""
    current_date: str = datetime.today().strftime("%Y-%m-%d")
    chart_data: list = []  # Data pro graf výroby a spotřeby

    def fetch_energy_data(self):
        """Načítá data z databáze pro graf a ukládá je."""
        conn = get_db()
        cursor = conn.cursor()
        
        query = """
            SELECT date, fveProduction, consumption
            FROM energyData
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        start_date = (datetime.strptime(self.current_date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        cursor.execute(query, (start_date, self.current_date))
        data = cursor.fetchall()
        conn.close()

        self.chart_data = [{"timestamp": row[0], "production": row[1], "consumption": row[2]} for row in data]

    def shift_date(self, days: int):
        """Posune datum o zadaný počet dní a aktualizuje data."""
        date_obj = datetime.strptime(self.current_date, "%Y-%m-%d")
        date_obj += timedelta(days=days)
        self.current_date = date_obj.strftime("%Y-%m-%d")
        self.fetch_energy_data()

def energy_chart():
    """Komponenta zobrazující graf výroby a spotřeby elektřiny."""
    return rx.card(
        rx.vstack(
            rx.heading("Výroba vs. Spotřeba elektřiny", size="4"),
            rx.hstack(
                rx.button("⬅️", on_click=lambda: ChartState.shift_date(-30)),
                rx.text(ChartState.current_date),
                rx.button("➡️", on_click=lambda: ChartState.shift_date(30)),
                spacing="4",
            ),
            rx.recharts.area_chart(
                rx.recharts.area(
                    data_key="consumption",
                    type_="monotone",
                    stroke="red",
                    fill="rgba(255, 99, 132, 0.3)",
                    fill_opacity=0.3,
                    dot=False,
                ),
                rx.recharts.area(
                    data_key="production",
                    type_="monotone",
                    stroke="blue",
                    fill="rgba(54, 162, 235, 0.3)",
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
                data=ChartState.chart_data,
                width="100%",
                height=500,
            ),
            width="100%",
        ),
        width="100%",
    )
