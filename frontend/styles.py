"""
Modul pro definici stylů pro frontend aplikace.

Vstup: Žádné explicitní vstupy, obsahuje pouze definici stylů.
Výstup: Stylová konfigurace aplikace (barvy, pozadí, tlačítka, odkazy, grafy atd.).
Spolupracuje s: Reflex (UI framework), frontend komponenty.
"""

import reflex as rx

# ✅ Hlavní barvy
borderRadius = "var(--radius-2)"
border = f"1px solid {rx.color('gray', 5)}"
textColor = "#333333"  # Tmavě šedý text
grayColor = rx.color("gray", 11)
grayBgColor = rx.color("gray", 3)
backgroundColor = "#F5F5F5"  # Světle šedé pozadí
cardBackground = "#FFFFFF"  # Bílé pozadí karet

# ✅ Barvy pro akcenty
accentTextColor = "#D32F2F"  # Červená (spotřeba)
accentColor = "#1E88E5"  # Modrá (výroba FVE)
accentBgColor = rx.color("accent", 3)
hoverAccentColor = {"_hover": {"color": accentTextColor}}
hoverAccentBg = {"_hover": {"background_color": accentColor}}

# ✅ Rozměry
contentWidthVw = "90vw"
sidebarWidth = "32em"
sidebarContentWidth = "16em"
maxWidth = "1480px"
colorBoxSize = ["2.25rem", "2.25rem", "2.5rem"]

# ✅ Barvy pro grafy
graphConsumptionColor = "#D32F2F"  # Červená (spotřeba)
graphConsumptionFill = "rgba(211, 47, 47, 0.3)"

graphProductionColor = "#1E88E5"  # Modrá (výroba FVE)
graphProductionFill = "rgba(30, 136, 229, 0.3)"

graphPriceColor = "#FF9800"  # Oranžová čára pro cenu elektřiny
graphPriceFill = "rgba(255, 152, 0, 0.3)"

graphQuantityColor = "#8E24AA"  # Fialová pro množství
graphQuantityFill = "rgba(142, 36, 170, 0.3)"

graphConsumptionPredictedColor = "#FFC107"  # Žlutá čára pro predikovanou spotřebu
graphConsumptionPredictedFill = "rgba(255, 193, 7, 0.3)"

graphProductionPredictedColor = "#E91E63"  # Růžová čára pro predikovanou výrobu
graphProductionPredictedFill = "rgba(233, 30, 99, 0.3)"

# ✅ Styl pro karty
cardStyle = {
    "background": cardBackground,     # Pokud máš vlastní proměnnou
    "border_radius": "12px",
    "padding": "16px",
    "border": "1px solid #ccc",       # ← jemné šedé ohraničení
}

# ✅ Styly pro šablony
templatePageStyle = {
    "padding_top": ["1em", "1em", "2em"],
    "padding_x": ["auto", "auto", "2em"],
}

templateContentStyle = {
    "padding": "1em",
    "margin_bottom": "2em",
    "min_height": "90vh",
}

# ✅ Styl pro odkazy
linkStyle = {
    "color": accentTextColor,
    "text_decoration": "none",
    **hoverAccentColor,
}

# ✅ Styl pro tlačítka
buttonStyle = {
    "background_color": "white",
    "border": "1px solid #ccc",
    "color": textColor,
    "padding": "0.5rem 1rem",
    "border_radius": "8px",
    "_hover": {"background_color": "#f0f0f0"},
}

# ✅ Styl pro markdown
markdownStyle = {
    "code": lambda text: rx.code(text, color_scheme="gray"),
    "codeblock": lambda text, **props: rx.code_block(text, **props, margin_y="1em"),
    "a": lambda text, **props: rx.link(
        text,
        **props,
        font_weight="bold",
        text_decoration="underline",
        text_decoration_color=accentTextColor,
    ),
}

# ✅ Styl pro box-shadow
boxShadowStyle = "0px 4px 10px rgba(0, 0, 0, 0.1)"

# ✅ Styl pro color picker
colorPickerStyle = {
    "border_radius": "max(var(--radius-3), var(--radius-full))",
    "box_shadow": boxShadowStyle,
    "cursor": "pointer",
    "display": "flex",
    "align_items": "center",
    "justify_content": "center",
    "transition": "transform 0.15s ease-in-out",
    "_active": {
        "transform": "translateY(2px) scale(0.95)",
    },
}

# ✅ Externí stylesheety
baseStylesheets = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
]

baseStyle = {
    "font_family": "Inter",
}


############################################################
#                  IKONY A POŘADÍ STRÁNEK                 #
############################################################

pageIcons = {
    "Dashboard": "layout-dashboard",
    "Settings": "settings",
    "Datafeed": "rss",
    # můžeš přidat další podle potřeby
}

# Fallback ikona, pokud není ve slovníku
defaultPageIcon = "layout-dashboard"

pageOrder = ["/dashboard", "/datafeed", "/settings"]