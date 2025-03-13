import reflex as rx
from .pages import dashboard, settings, datafeed
from .components.navbar import navbar  # Import navbar z komponenty

# Funkce pro navbar s odkazy místo záložek
import reflex as rx

# Funkce pro navbar s odkazy místo záložek a s ikonami
def navbar() -> rx.Component:
    return rx.vstack(  # Používáme vstack pro vertikální uspořádání
        rx.hstack(  # Vodorovné uspořádání pro Dashboard s ikonou
            rx.icon("home", size=20),  # Ikona pro Dashboard (může být jakákoliv ikona)
            rx.link("Dashboard", href="/dashboard", style={"margin-left": "10px"}),  # Odkaz na Dashboard
        ),
        rx.hstack(  # Vodorovné uspořádání pro Settings s ikonou
            rx.icon("settings", size=20),  # Ikona pro Settings
            rx.link("Settings", href="/settings", style={"margin-left": "10px"}),    # Odkaz na Settings
        ),
        rx.hstack(  # Vodorovné uspořádání pro DataFeed s ikonou
            rx.icon("cloud-upload", size=20),  # Ikona pro DataFeed
            rx.link("DataFeed", href="/datafeed", style={"margin-left": "10px"}),    # Odkaz na DataFeed
        ),
    )


# Hlavní stránka, která zobrazuje navbar a text
def index() -> rx.Component:
    return rx.container(
        navbar(),  # Zobrazíme navbar (menu)
        rx.text("Welcome to the Solar Optimization App"),  # Hlavní text stránky
    )

# Aplikace a její stránky
app = rx.App()
app.add_page(index, route="/")
app.add_page(dashboard.page, route="/dashboard")
app.add_page(settings.page, route="/settings")
app.add_page(datafeed.page, route="/datafeed")

if __name__ == "__main__":
    app.run()
