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
        rx.color_mode_cond(
            rx.image(src="/reflex_black.svg", height="1.5em"),
            rx.image(src="/reflex_white.svg", height="1.5em"),
        ),
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )

def sidebarFooter() -> rx.Component:
    """sidebarFooter"""
    return rx.hstack(
        rx.link(
            rx.text("Docs", size="3"),
            href="https://reflex.dev/docs/getting-started/introduction/",
            color_scheme="gray",
            underline="none",
        ),
        rx.link(
            rx.text("Blog", size="3"),
            href="https://reflex.dev/blog/",
            color_scheme="gray",
            underline="none",
        ),
        rx.spacer(),
        rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
        justify="start",
        align="center",
        width="100%",
        padding="0.35em",
    )

def sidebarItemIcon(icon: str) -> rx.Component:
    """sidebarItemIcon"""
    return rx.icon(icon, size=18)

def sidebarItem(text: str, url: str) -> rx.Component:
    """sidebarItem"""
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & text == "Overview"
    )

    return rx.link(
        rx.hstack(
            rx.match(
                text,
                ("Dashboard", sidebarItemIcon("layout-dashboard")),
                ("About", sidebarItemIcon("book-open")),
                ("Settings", sidebarItemIcon("settings")),
                sidebarItemIcon("layout-dashboard"),
            ),
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
    pages = get_decorated_pages()

    orderedPageRoutes = [
        "/",
        "/about",
        "/settings",
    ]

    orderedPages = sorted(
        pages,
        key=lambda page: (
            orderedPageRoutes.index(page["route"])
            if page["route"] in orderedPageRoutes
            else len(orderedPageRoutes)
        ),
    )

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
