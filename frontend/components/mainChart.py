"""
Modul pro vizualizaci výroby a spotřeby energie pomocí grafu.

Vstup: Data z databáze obsahující hodnoty spotřeby a výroby energie.
Výstup: Graf zobrazující aktuální i historická data, včetně predikovaných hodnot.
Spolupracuje s: backend.database (načítání dat), frontend.styles (styly), Reflex (UI komponenty).
"""

import reflex as rx
from datetime import datetime, timedelta
from backend.database import getDb
from ..components.card import card
from .. import styles

class MainChartState(rx.State):
    """MainChartState"""
    currentDate: str = datetime.today().strftime("%Y-%m-%d")
    selectedInterval: str = "month"
    chartData: list = []
    displayedInterval: str = ""

    def fetchData(self):
        """Načítá data z databáze pro hlavní graf podle vybraného intervalu."""
        conn = getDb()
        cursor = conn.cursor()
        endDate = datetime.strptime(self.currentDate, "%Y-%m-%d")

        if self.selectedInterval == "day":
            startDate = endDate.strftime("%Y-%m-%d")
            query = """
                SELECT date || ' ' || hour, fveProduction, fvePredicted, consumption, consumptionPredicted
                FROM energyData
                WHERE date = ? AND hour != 24
                ORDER BY date ASC, hour ASC
            """
            cursor.execute(query, (startDate,))

        elif self.selectedInterval == "week":
            startDate = (endDate - timedelta(days=endDate.weekday())).strftime("%Y-%m-%d")
            endDate = (datetime.strptime(startDate, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
            query = """
                SELECT date || ' ' || hour, fveProduction, fvePredicted, consumption, consumptionPredicted
                FROM energyData
                WHERE date BETWEEN ? AND ? AND hour != 24
                ORDER BY date ASC, hour ASC
            """
            cursor.execute(query, (startDate, endDate))

        elif self.selectedInterval == "month":
            startDate = endDate.replace(day=1).strftime("%Y-%m-%d")
            endDate = (datetime.strptime(startDate, "%Y-%m-%d") + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            endDate = endDate.strftime("%Y-%m-%d")
            query = """
                SELECT date, 
                    SUM(fveProduction), 
                    SUM(fvePredicted),
                    SUM(consumption), 
                    SUM(consumptionPredicted)
                FROM energyData
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date ASC
            """
            cursor.execute(query, (startDate, endDate))

        else:  # "year"
            startDate = endDate.replace(month=1, day=1).strftime("%Y-%m-%d")
            endDate = endDate.replace(month=12, day=31).strftime("%Y-%m-%d")
            query = """
                SELECT SUBSTR(date, 1, 7) AS month, SUM(fveProduction), SUM(fvePredicted), SUM(consumption), SUM(consumptionPredicted)
                FROM energyData
                WHERE date BETWEEN ? AND ? AND hour = 24
                GROUP BY month
                ORDER BY month ASC
            """
            cursor.execute(query, (startDate, endDate))

        self.updateDisplayedInterval()
        data = cursor.fetchall()
        conn.close()

        # ✅ Správně formátujeme hodnoty osy X pro všechny datové body
        processedData = []
        lastRealConsumption = None
        lastRealProduction = None
        lastRealTimestamp = None
        predictedStarted = False

        for row in data:
            timestamp, production, predictedProduction, realConsumption, predictedConsumption = row
            formatted_timestamp = self.formatXAxisTicks(timestamp)  # ✅ Formátování osy X pro všechny záznamy

            if realConsumption is not None:
                lastRealConsumption = realConsumption
                lastRealProduction = production
                lastRealTimestamp = timestamp
                processedData.append({
                    "timestamp": formatted_timestamp,  # ✅ Nyní platí pro všechny záznamy
                    "production": production,
                    "consumption": realConsumption,
                    "consumptionPredicted": None,
                    "fvePredicted": None,
                })
            else:
                if not predictedStarted and lastRealConsumption is not None:
                    predictedStarted = True
                    if lastRealTimestamp is not None:
                        try:
                            if self.selectedInterval == "year":
                                lastRealTimestamp_dt = datetime.strptime(lastRealTimestamp, "%Y-%m")  # ✅ Opraveno pro 'YYYY-MM'
                                timestamp_dt = datetime.strptime(timestamp, "%Y-%m")  # ✅ Opraveno pro 'YYYY-MM'
                            else:
                                lastRealTimestamp_dt = datetime.strptime(lastRealTimestamp.split(" ")[0], "%Y-%m-%d")
                                timestamp_dt = datetime.strptime(timestamp.split(" ")[0], "%Y-%m-%d")

                            daysGap = (timestamp_dt - lastRealTimestamp_dt).days
                            if daysGap <= 1:
                                processedData.append({
                                    "timestamp": formatted_timestamp,
                                    "production": lastRealProduction,
                                    "consumption": lastRealConsumption,
                                    "consumptionPredicted": lastRealConsumption,
                                    "fvePredicted": lastRealProduction,
                                })
                        except ValueError:
                            pass  # ✅ Pokud není formát správný, přeskočíme

                processedData.append({
                    "timestamp": formatted_timestamp,  # ✅ Formátované pro všechny záznamy
                    "production": None,
                    "consumption": None,
                    "consumptionPredicted": predictedConsumption,
                    "fvePredicted": predictedProduction,
                })

        self.chartData = processedData

    def shiftDate(self, direction: str):
        """shiftDate"""
        conn = getDb()
        cursor = conn.cursor()
        query = "SELECT MIN(SUBSTR(date, 1, 4)), MAX(SUBSTR(date, 1, 4)) FROM energyData"
        cursor.execute(query)
        minYear, maxYear = cursor.fetchone()
        conn.close()

        minYear = int(minYear) if minYear else None
        maxYear = int(maxYear) if maxYear else None

        if direction in ["prev_start", "next_end"]:
            if direction == "prev_start" and minYear:
                self.currentDate = f"{minYear}-01-01"
            elif direction == "next_end" and maxYear:
                self.currentDate = f"{maxYear}-01-01"

        else:
            dateObj = datetime.strptime(self.currentDate, "%Y-%m-%d")

            if self.selectedInterval == "year":
                newYear = dateObj.year - 1 if direction == "prev" else dateObj.year + 1
                if minYear <= newYear <= maxYear:
                    dateObj = dateObj.replace(year=newYear, month=1, day=1)
                else:
                    return

            elif self.selectedInterval == "month":
                month = dateObj.month - 1 if direction == "prev" else dateObj.month + 1
                year = dateObj.year
                if month == 0:
                    month = 12
                    year -= 1
                elif month == 13:
                    month = 1
                    year += 1

                if minYear <= year <= maxYear:
                    dateObj = dateObj.replace(year=year, month=month, day=1)
                else:
                    return

            elif self.selectedInterval == "week":
                delta = timedelta(weeks=1)
                dateObj -= delta if direction == "prev" else -delta
                dateObj -= timedelta(days=dateObj.weekday())

            elif self.selectedInterval == "day":
                delta = timedelta(days=1)
                dateObj -= delta if direction == "prev" else -delta

            self.currentDate = dateObj.strftime("%Y-%m-%d")

        self.fetchData()

    def formatXAxisTicks(self, value):
        """formatXAxisTicks"""
        try:
            if self.selectedInterval == "year":
                return str(int(value.split("-")[1]))

            elif self.selectedInterval == "month":
                return str(int(value.split("-")[-1]))

            elif self.selectedInterval == "week":
                days = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
                dayNumber = int(value.split("-")[-1].split(" ")[0])
                return days[dayNumber % 7]

            elif self.selectedInterval == "day":
                hour = value.split(" ")[-1]
                return f"{int(hour):02d}:00"

        except ValueError:
            return str(value)

        return str(value)

    def updateDisplayedInterval(self):
        """updateDisplayedInterval"""
        if self.selectedInterval == "year":
            self.displayedInterval = self.currentDate[:4]
        elif self.selectedInterval == "month":
            self.displayedInterval = f"{self.currentDate[:7]}-01 až {self.currentDate[:7]}-31"
        elif self.selectedInterval == "week":
            startDate = datetime.strptime(self.currentDate, "%Y-%m-%d")
            startWeek = startDate - timedelta(days=startDate.weekday())
            endWeek = startWeek + timedelta(days=6)
            self.displayedInterval = f"{startWeek.strftime('%Y-%m-%d')} až {endWeek.strftime('%Y-%m-%d')}"
        elif self.selectedInterval == "day":
            self.displayedInterval = self.currentDate

    def setSelectedInterval(self, interval: str):
        """Změní interval a načte nová data."""
        self.selectedInterval = interval
        self.fetchData()

    def setToday(self):
        """Nastaví datum na dnešní den."""
        self.currentDate = datetime.today().strftime("%Y-%m-%d")
        self.fetchData()

def mainChart():
    """mainChart"""
    return rx.box(
        rx.heading("Graf spotřeby a výroby", size="4", margin_bottom="1rem"),
        card(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.button(rx.icon("chevrons-left"), on_click=lambda: MainChartState.shiftDate("prev_start"), style=styles.buttonStyle),
                        rx.button(rx.icon("chevron-left"), on_click=lambda: MainChartState.shiftDate("prev"), style=styles.buttonStyle),
                        rx.text(MainChartState.displayedInterval),
                        rx.button(rx.icon("chevron-right"), on_click=lambda: MainChartState.shiftDate("next"), style=styles.buttonStyle),
                        rx.button(rx.icon("chevrons-right"), on_click=lambda: MainChartState.shiftDate("next_end"), style=styles.buttonStyle),
                        spacing="4",
                    ),
                    rx.spacer(),
                    rx.select(
                        ["day", "week", "month", "year"],
                        value=MainChartState.selectedInterval,
                        on_change=MainChartState.setSelectedInterval,
                    ),
                    width="100%",  
                    justify="between",
                ),
                rx.recharts.area_chart(
                    rx.recharts.area(
                        data_key="consumption",
                        stroke=styles.graphConsumptionColor,
                        stroke_width=2,
                        fill=styles.graphConsumptionFill,
                        fill_opacity=0.3,
                        dot=False,
                    ),
                    rx.recharts.area(
                        data_key="production",
                        stroke=styles.graphProductionColor,
                        stroke_width=2,
                        fill=styles.graphProductionFill,
                        fill_opacity=0.3,
                        dot=False,
                    ),
                    rx.recharts.area(
                        data_key="consumptionPredicted",
                        stroke=styles.graphConsumptionPredictedColor,
                        stroke_width=2,
                        stroke_dasharray="5 5",
                        fill=styles.graphConsumptionPredictedFill,
                        fill_opacity=0,
                        dot=False,
                    ),
                    rx.recharts.area(
                        data_key="fvePredicted",
                        stroke=styles.graphProductionPredictedColor,
                        stroke_width=2,
                        stroke_dasharray="5 5",
                        fill_opacity=0,
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
                    ),
                    rx.recharts.cartesian_grid(
                        stroke_dasharray="3 3",
                        vertical=False,
                    ),
                    rx.recharts.graphing_tooltip(),
                    rx.recharts.legend(),
                    data=MainChartState.chartData,
                    width="95%",
                    height=500,
                    flex_grow=1,
                ),
                width="100%",
                flex_grow=1,
            ),
            width="100%",
            max_width="none",
        ),
        width="calc(85vw - 1rem)",
    )
