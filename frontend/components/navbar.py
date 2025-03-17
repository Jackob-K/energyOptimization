"""
Modul pro komponentu navigačního panelu (Navbar).

Vstup: Žádné explicitní vstupy, komponenty generují navigační položky dynamicky.
Výstup: Navigační panel s položkami menu, tlačítkem pro menu a odkazem na dokumentaci.
Spolupracuje s: Reflex (UI framework), frontend.styles (styly), backend (stránky aplikace).
"""

import reflex as rx
from .. import styles

def menuItemIcon(icon: str) -> rx.Component:
    """menuItemIcon"""
    return rx.icon(icon, size=20)

def menuItem(text: str, url: str) -> rx.Component:
    """menuItem"""
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & text == "Overview"
    )

    return rx.link(
        rx.hstack(
            rx.match(
                text,
                ("Dashboard", menuItemIcon("layout-dashboard")),
                ("About", menuItemIcon("book-open")),
                ("Settings", menuItemIcon("settings")),
                menuItemIcon("layout-dashboard"),
            ),
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

def menuButton() -> rx.Component:
    """menuButton"""
    from reflex.page import get_decorated_pages

    orderedPageRoutes = ["/", "/about", "/settings"]
    pages = get_decorated_pages()

    orderedPages = sorted(
        pages,
        key=lambda page: (
            orderedPageRoutes.index(page["route"])
            if page["route"] in orderedPageRoutes
            else len(orderedPageRoutes)
        ),
    )

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
            rx.color_mode_cond(
                rx.image(src="/reflex_black.svg", height="1em"),
                rx.image(src="/reflex_white.svg", height="1em"),
            ),
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
