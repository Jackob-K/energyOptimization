# frontend/styles.py

import reflex as rx

# Definice stylů
border_radius = "var(--radius-2)"
border = f"1px solid {rx.color('gray', 5)}"
text_color = rx.color("gray", 11)
gray_color = rx.color("gray", 11)
gray_bg_color = rx.color("gray", 3)
accent_text_color = rx.color("accent", 10)
accent_color = rx.color("accent", 1)
accent_bg_color = rx.color("accent", 3)
hover_accent_color = {"_hover": {"color": accent_text_color}}
hover_accent_bg = {"_hover": {"background_color": accent_color}}
content_width_vw = "90vw"
sidebar_width = "32em"
sidebar_content_width = "16em"
max_width = "1480px"
color_box_size = ["2.25rem", "2.25rem", "2.5rem"]
accent_color = "#1E88E5"  # Modrá (výroba FVE)
accent_text_color = "#D32F2F"  # Červená (spotřeba)

# ✅ Hlavní barvy pro grafy
graph_consumption_color = "#D32F2F"  # Červená (spotřeba)
graph_consumption_fill = "rgba(211, 47, 47, 0.3)"  # Červená výplň

graph_production_color = "#1E88E5"  # Modrá (výroba FVE)
graph_production_fill = "rgba(30, 136, 229, 0.3)"  # Modrá výplň

# ✅ Další globální barvy
accent_color = graph_production_color  # Může se použít i jinde
accent_text_color = graph_consumption_color  # Může se použít i jinde

background_color = "#F5F5F5"  # Světle šedé pozadí
card_background = "#FFFFFF"  # Bílé pozadí karet
text_color = "#333333"  # Tmavě šedý text

# ✅ Barvy pro graf ceny elektřiny
graph_price_color = "#FF9800"  # Oranžová čára pro cenu elektřiny
graph_price_fill = "rgba(255, 152, 0, 0.3)"  # Oranžová výplň pro čáru

graph_quantity_color = "#4CAF50"  # Zelená pro sloupce (množství)
graph_quantity_fill = "rgba(76, 175, 80, 0.3)"  # Zelená výplň pro sloupce


# Styl pro karty - přidat do styles.py
card_style = {
    "background": "white",  # 🔹 Barva pozadí karty (můžete změnit)
    "border_radius": "12px",
    "padding": "16px",
    "box_shadow": "0 4px 10px rgba(0, 0, 0, 0.1)",  # 🔹 Jemný stín pro vizuální efekt
}

# Styly pro šablony
template_page_style = {
    "padding_top": ["1em", "1em", "2em"],
    "padding_x": ["auto", "auto", "2em"],
}

template_content_style = {
    "padding": "1em",
    "margin_bottom": "2em",
    "min_height": "90vh",
}

# Styl pro odkazy
link_style = {
    "color": accent_text_color,
    "text_decoration": "none",
    **hover_accent_color,
}

# Styl pro tlačítka
overlapping_button_style = {
    "background_color": "white",
    "border_radius": border_radius,
}

# Styl pro markdown
markdown_style = {
    "code": lambda text: rx.code(text, color_scheme="gray"),
    "codeblock": lambda text, **props: rx.code_block(text, **props, margin_y="1em"),
    "a": lambda text, **props: rx.link(
        text,
        **props,
        font_weight="bold",
        text_decoration="underline",
        text_decoration_color=accent_text_color,
    ),
}

# Styl pro box-shadow
box_shadow_style = "0px 4px 10px rgba(0, 0, 0, 0.1)"  # Jemný stín pro karty

# Styl pro color picker
color_picker_style = {
    "border_radius": "max(var(--radius-3), var(--radius-full))",
    "box_shadow": box_shadow_style,
    "cursor": "pointer",
    "display": "flex",
    "align_items": "center",
    "justify_content": "center",
    "transition": "transform 0.15s ease-in-out",
    "_active": {
        "transform": "translateY(2px) scale(0.95)",
    },
}

# Základní externí stylesheety
base_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
]

base_style = {
    "font_family": "Inter",
}

