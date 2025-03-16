import reflex as rx
from datetime import datetime, timedelta
from backend.database import get_db
from ..components.card import card
from .. import styles

class MainChartState(rx.State):
    """Správa stavu hlavního grafu (výroba/spotřeba)."""
    currentDate: str = datetime.today().strftime("%Y-%m-%d")
    selectedInterval: str = "month"
    chartData: list = []
    displayedInterval: str = ""

    def fetchData(self):
        """Načítá data z databáze pro hlavní graf podle vybraného intervalu."""
        conn = get_db()
        cursor = conn.cursor()
        endDate = datetime.strptime(self.currentDate, "%Y-%m-%d")

        if self.selectedInterval == "day":
            startDate = endDate.strftime("%Y-%m-%d")
            query = """
                SELECT date || ' ' || hour, fveProduction, consumption, consumptionPredicted
                FROM energyData
                WHERE date = ? AND hour != 24
                ORDER BY date ASC, hour ASC
            """
            cursor.execute(query, (startDate,))

        elif self.selectedInterval == "week":
            startDate = (endDate - timedelta(days=endDate.weekday())).strftime("%Y-%m-%d")
            endDate = (datetime.strptime(startDate, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
            query = """
                SELECT date || ' ' || hour, fveProduction, consumption, consumptionPredicted
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
                SELECT SUBSTR(date, 1, 7) AS month, SUM(fveProduction), SUM(consumption), SUM(consumptionPredicted)
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
            timestamp, production, realConsumption, predictedConsumption = row
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
                    "fvePredicted": None,
                })

        self.chartData = processedData  # ✅ Nyní obsahuje správné hodnoty osy X pro celý graf

    def shiftDate(self, direction: str):
        """Posune datum dopředu nebo dozadu podle intervalu, ale jen v rámci dostupných dat."""
        conn = get_db()
        cursor = conn.cursor()

        # ✅ Získání minimálního a maximálního roku s daty
        query = "SELECT MIN(SUBSTR(date, 1, 4)), MAX(SUBSTR(date, 1, 4)) FROM energyData"
        cursor.execute(query)
        minYear, maxYear = cursor.fetchone()
        conn.close()

        # Převod na celé číslo (někdy se mohou vrátit None, pokud není žádná data)
        minYear = int(minYear) if minYear else None
        maxYear = int(maxYear) if maxYear else None

        if direction in ["prev_start", "next_end"]:
            if direction == "prev_start" and minYear:
                self.currentDate = f"{minYear}-01-01"  # Přepnutí na první dostupný rok
            elif direction == "next_end" and maxYear:
                self.currentDate = f"{maxYear}-01-01"  # Přepnutí na poslední dostupný rok

        else:
            dateObj = datetime.strptime(self.currentDate, "%Y-%m-%d")

            if self.selectedInterval == "year":
                newYear = dateObj.year - 1 if direction == "prev" else dateObj.year + 1

                # ✅ Ověření, zda nový rok spadá do dostupného rozsahu
                if minYear <= newYear <= maxYear:
                    dateObj = dateObj.replace(year=newYear, month=1, day=1)
                else:
                    return  # ❌ Pokud je mimo rozsah, neposunujeme datum

            elif self.selectedInterval == "month":
                month = dateObj.month - 1 if direction == "prev" else dateObj.month + 1
                year = dateObj.year
                if month == 0:
                    month = 12
                    year -= 1
                elif month == 13:
                    month = 1
                    year += 1

                # ✅ Ověření, zda je rok v rozsahu dat
                if minYear <= year <= maxYear:
                    dateObj = dateObj.replace(year=year, month=month, day=1)
                else:
                    return  # ❌ Neposuneme se, pokud rok není v databázi

            elif self.selectedInterval == "week":
                delta = timedelta(weeks=1)
                if direction == "prev":
                    dateObj -= delta
                elif direction == "next":
                    dateObj += delta
                dateObj -= timedelta(days=dateObj.weekday())  # Pondělí daného týdne

            elif self.selectedInterval == "day":
                delta = timedelta(days=1)
                if direction == "prev":
                    dateObj -= delta
                elif direction == "next":
                    dateObj += delta

            self.currentDate = dateObj.strftime("%Y-%m-%d")

        self.fetchData()



    def formatXAxisTicks(self, value):
        """Formátování hodnot osy X podle vybraného intervalu ještě před zobrazením v grafu."""
        try:
            if self.selectedInterval == "year":
                return str(int(value.split("-")[1]))  # 1-12 (měsíce)

            elif self.selectedInterval == "month":
                return str(int(value.split("-")[-1]))  # Den v měsíci

            elif self.selectedInterval == "week":
                days = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
                day_number = int(value.split("-")[-1].split(" ")[0])  # Extrahuje číslo dne
                return days[day_number % 7]  # Vrátí název dne

            elif self.selectedInterval == "day":
                hour = value.split(" ")[-1]  # Extrahuje hodinu (např. "12")
                return f"{int(hour):02d}:00"  # Vrátí formát HH:00

        except ValueError:
            return str(value)  # Pokud dojde k chybě, vrátí nezměněnou hodnotu

        return str(value)


    
    def updateDisplayedInterval(self):
        """Změní zobrazované období mezi šipkami podle vybraného intervalu."""
        if self.selectedInterval == "year":
            self.displayedInterval = self.currentDate[:4]  # Jen rok
        elif self.selectedInterval == "month":
            self.displayedInterval = f"{self.currentDate[:7]}-01 až {self.currentDate[:7]}-31"
        elif self.selectedInterval == "week":
            startDate = datetime.strptime(self.currentDate, "%Y-%m-%d")
            startWeek = startDate - timedelta(days=startDate.weekday())
            endWeek = startWeek + timedelta(days=6)
            self.displayedInterval = f"{startWeek.strftime('%Y-%m-%d')} až {endWeek.strftime('%Y-%m-%d')}"
        elif self.selectedInterval == "day":
            self.displayedInterval = self.currentDate  # Jen datum


    def setSelectedInterval(self, interval: str):
        """Změní interval a načte nová data."""
        self.selectedInterval = interval
        self.fetchData()

    def setToday(self):
        """Nastaví datum na dnešní den."""
        self.currentDate = datetime.today().strftime("%Y-%m-%d")
        self.fetchData()

def mainChart():
    """Komponenta zobrazující hlavní graf výroby a spotřeby."""
    return rx.box(
        rx.heading("Graf spotřeby a výroby", size="4", margin_bottom="1rem"),
        card(
            rx.vstack(
                rx.hstack(
                    
                    # Tlačítka pro posun intervalu (zarovnaná doprava)
                    rx.hstack(
                        rx.button(rx.icon("chevrons-left"), on_click=lambda: MainChartState.shiftDate("prev_start"), style=styles.button_style),
                        rx.button(rx.icon("chevron-left"), on_click=lambda: MainChartState.shiftDate("prev"), style=styles.button_style),
                        rx.text(MainChartState.displayedInterval),  # ✅ Dynamické zobrazení období
                        rx.button(rx.icon("chevron-right"), on_click=lambda: MainChartState.shiftDate("next"), style=styles.button_style),
                        rx.button(rx.icon("chevrons-right"), on_click=lambda: MainChartState.shiftDate("next_end"), style=styles.button_style),
                        spacing="4",
                    ),

                    rx.spacer(),

                    # Výběr intervalu (zarovnaný doleva)
                    rx.select(
                        ["day", "week", "month", "year"],
                        value=MainChartState.selectedInterval,
                        on_change=MainChartState.setSelectedInterval,
                    ),
                    

                    width="100%",  
                    justify="between",  # ✅ Zarovnání prvků do krajů
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
