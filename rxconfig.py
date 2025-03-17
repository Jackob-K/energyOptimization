"""
Konfigurační soubor pro aplikaci Reflex.

Vstup: Nastavení jména aplikace.
Výstup: Konfigurace aplikace Reflex.
Spolupracuje s: Celou aplikací `frontend`.
"""

import reflex as rx

config = rx.Config(
    app_name="frontend",  # Název aplikace
)
