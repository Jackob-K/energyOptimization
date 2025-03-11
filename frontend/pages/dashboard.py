import reflex as rx
import requests

API_URL = "http://localhost:8000/energy-data"  # Odkaz na backend

# ✅ Funkce pro načtení dat z API
def fetch_energy_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            #print(f"✅ Data z API: {data}")  # Debugging
            return data
        print("❌ API nevrací správná data")
        return []
    except Exception as e:
        print(f"❌ Chyba při načítání dat: {e}")
        return []

def dashboard():
    data = fetch_energy_data()
    #print(f"✅ Data poslaná do grafu: {data}")  # Debugging

    return rx.vstack(
        rx.heading("Denní spotřeba vs. výroba elektřiny"),
        rx.recharts.line_chart(
            rx.recharts.line(
                data_key="consumption", 
                type_="monotone",  # Změněno na "monotone" pro hladkou čáru
                stroke="#ff7300",  # Změněná barva čáry
                stroke_width=4, 
                fill_opacity=0.3,  # Méně výrazná výplň
                fill="#ff7300"  # Stejná barva výplně jako čáry
            ),
            rx.recharts.line(
                data_key="production", 
                type_="monotone",  # Změněno na "monotone" pro hladkou čáru
                stroke="#8884d8",  # Změněná barva čáry
                stroke_width=4, 
                fill_opacity=0.3,  # Méně výrazná výplň
                fill="#8884d8"  # Stejná barva výplně jako čáry
            ),
            rx.recharts.x_axis(data_key="timestamp", angle=-45, dy=20, tick_size=10),
            rx.recharts.y_axis(),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.graphing_tooltip(),
            data=data,  # ✅ Data musí být zde!
            width="100%",
            height=500,
        )
    )

# ✅ Přidáme funkci `page()`, kterou očekává `frontend.py`
def page():
    return dashboard()
