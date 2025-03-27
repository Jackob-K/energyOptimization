"""
Modul pro komponentu postranního panelu (Sidebar).

Vstup: Dynamicky generované navigační položky.
Výstup: Sidebar s navigačními položkami, logem, odkazy na dokumentaci a možností změny režimu barev.
Spolupracuje s: Reflex (UI framework), frontend.styles (styly), backend (stránky aplikace).
"""

import reflex as rx
from .. import styles
from reflex.page import get_decorated_pages

def sidebarHeader() -> rx.Component:
    """sidebarHeader"""
    return rx.hstack(
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )

def sidebarFooter() -> rx.Component:
    return rx.spacer()

def sidebarItemIcon(text: str) -> rx.Component:
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

def sidebarItem(text: str, url: str) -> rx.Component:
    """sidebarItem"""
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & text == "Overview"
    )

    rx.icon(getPageIcon(url), size=18)

    return rx.link(
        rx.hstack(
            sidebarItemIcon(text),
            rx.text(text, size="3", weight="regular"),
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

def sidebar() -> rx.Component:
    """sidebar"""
    orderedPages = getOrderedPages()

    return rx.flex(
        rx.vstack(
            sidebarHeader(),
            rx.vstack(
                *[
                    sidebarItem(
                        text=page.get("title", page["route"].strip("/").capitalize()),
                        url=page["route"],
                    )
                    for page in orderedPages
                ],
                spacing="1",
                width="100%",
            ),
            rx.spacer(),
            sidebarFooter(),
            justify="start",
            align="start",
            width=styles.sidebarContentWidth,
            height="100dvh",
            padding="1em",
        ),
        display=["none", "none", "none", "none", "none", "flex"],
        max_width="15em",
        width="auto",
        height="100%",
        position="sticky",
        justify="start",
        top="0px",
        left="0px",
        flex="1",
        bg=rx.color("gray", 2),
    )
