"""
Modul pro komponentu navigačního panelu (Navbar).

Vstup: Žádné explicitní vstupy, komponenty generují navigační položky dynamicky.
Výstup: Navigační panel s položkami menu, tlačítkem pro menu a odkazem na dokumentaci.
Spolupracuje s: Reflex (UI framework), frontend.styles (styly), backend (stránky aplikace).
"""

import reflex as rx
from .. import styles
from reflex.page import get_decorated_pages

def menuItemIcon(text: str) -> rx.Component:
    icon_name = styles.pageIcons.get(text, styles.defaultPageIcon)
    return rx.icon(icon_name, size=18)

def getOrderedPages():
    pages = get_decorated_pages()
    return sorted(
        pages,
        key=lambda page: (
            styles.pageOrder.index(page["route"])
            if page["route"] in styles.pageOrder
            else len(styles.pageOrder)
        ),
    )

def getPageIcon(route: str) -> str:
    return styles.pageIcons.get(route, styles.defaultPageIcon)

def menuItem(text: str, url: str) -> rx.Component:
    """menuItem"""
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & text == "Overview"
    )

    return rx.link(
        rx.hstack(
            rx.icon(getPageIcon(url), size=20),
            rx.text(text, size="4", weight="regular"),
            color=rx.cond(active, styles.accentTextColor, styles.textColor),
            style={
                "_hover": {
                    "background_color": rx.cond(active, styles.accentBgColor, styles.grayBgColor),
                    "color": rx.cond(active, styles.accentTextColor, styles.textColor),
                    "opacity": "1",
                },
                "opacity": rx.cond(active, "1", "0.95"),
            },
            align="center",
            border_radius=styles.borderRadius,
            width="100%",
            spacing="2",
            padding="0.35em",
        ),
        underline="none",
        href=url,
        width="100%",
    )

def navbarFooter() -> rx.Component:
    """navbarFooter"""
    return rx.spacer()

def menuButton() -> rx.Component:
    """menuButton"""

    orderedPages = getOrderedPages()

    return rx.drawer.root(
        rx.drawer.trigger(rx.icon("align-justify")),
        rx.drawer.overlay(z_index="5"),
        rx.drawer.portal(
            rx.drawer.content(
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.drawer.close(rx.icon(tag="x")),
                        justify="end",
                        width="100%",
                    ),
                    rx.divider(),
                    *[
                        menuItem(
                            text=page.get("title", page["route"].strip("/").capitalize()),
                            url=page["route"],
                        )
                        for page in orderedPages
                    ],
                    rx.spacer(),
                    navbarFooter(),
                    spacing="4",
                    width="100%",
                ),
                top="auto",
                left="auto",
                height="100%",
                width="20em",
                padding="1em",
                bg=rx.color("gray", 1),
            ),
            width="100%",
        ),
        direction="right",
    )
def navbar() -> rx.Component:
    """navbar"""
    return rx.el.nav(
        rx.hstack(
            rx.spacer(),
            menuButton(),
            align="center",
            width="100%",
            padding_y="0.75em",
            padding_x="1em",
            background_color=styles.grayBgColor,
        ),
        display=["block", "block", "block", "block", "block", "none"],
        position="sticky",
        top="0px",
        z_index="5",
        border_bottom=styles.border,
    )
