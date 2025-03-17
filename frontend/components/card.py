"""
Modul pro vytvoření stylizované karty pomocí Reflex.

Vstup: Dětské komponenty a vlastnosti.
Výstup: Box se stylizovanou kartou.
Spolupracuje s: frontend.styles.

Změny názvů funkcí a proměnných:
- card → createCard
"""

# Externí knihovny
import reflex as rx

# Lokální importy
from frontend import styles

def card(*children, **props):
    """createCard"""
    return rx.box(  
        *children,
        **styles.cardStyle,  
        **props,  
    )
