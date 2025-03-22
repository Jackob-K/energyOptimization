"""
Hlavní soubor aplikace pro správu solární optimalizace.

Vstup: Uživatel vybírá mezi stránkami Dashboard, Settings a DataFeed.
Výstup: Dynamické načítání obsahu na základě uživatelské volby.
Spolupracuje s: Moduly `dashboard`, `settings`, `datafeed` a komponentou `navbar`.
"""

import reflex as rx
from .pages import dashboard, settings, datafeed

def navbarMenu() -> rx.Component:
    """Vytváří navigační menu s odkazy a ikonami."""
    return rx.vstack(  
        rx.hstack(  
            rx.icon("home", size=20),  
            rx.link("Dashboard", href="/dashboard", style={"margin-left": "10px"}),  
        ),
        rx.hstack(  
            rx.icon("settings", size=20),  
            rx.link("Settings", href="/settings", style={"margin-left": "10px"}),    
        ),
        rx.hstack(  
            rx.icon("home", size=20),  
            rx.link("DataFeed", href="/datafeed", style={"margin-left": "10px"}),    
        ),
    )

def index() -> rx.Component:
    """Hlavní stránka aplikace."""
    return rx.container(
        navbarMenu(),  
        rx.text("Welcome to the Solar Optimization App"),  
    )

# Aplikace a její stránky
app = rx.App()
app.add_page(index, route="/")
app.add_page(dashboard.page, route="/dashboard")
app.add_page(settings.page, route="/settings")
app.add_page(datafeed.page, route="/datafeed")

if __name__ == "__main__":
    app.run()
