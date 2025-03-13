import reflex as rx
from frontend import styles

def card(*children, **props):
    return rx.box(  # Použijeme `rx.box` místo `rx.card`, aby nedocházelo ke konfliktům
        *children,
        **styles.card_style,  # ✅ Použijeme předdefinovaný styl karty
        **props,  # ✅ Umožní přidání dalších atributů (např. vlastní šířky, barvy)
    )
