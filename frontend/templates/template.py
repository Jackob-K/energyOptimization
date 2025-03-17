"""
Modul pro šablony společné pro stránky aplikace.

Vstup: Konfigurace šablon stránek (route, title, meta, script tags).
Výstup: Stylizovaná stránka s navigací, postranním panelem a obsahem.
Spolupracuje s: Reflex (UI framework), frontend.styles (styly), navbar, sidebar.
"""

from __future__ import annotations
from typing import Callable
import reflex as rx
from .. import styles
from ..components.navbar import navbar
from ..components.sidebar import sidebar

# ✅ Meta tagy pro aplikaci
defaultMeta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]

def menuItemLink(text, href):
    """menuItemLink"""
    return rx.menu.item(
        rx.link(
            text,
            href=href,
            width="100%",
            color="inherit",
        ),
        _hover={
            "color": styles.accentColor,
            "background_color": styles.accentTextColor,
        },
    )

class ThemeState(rx.State):
    """ThemeState"""
    accentColor: str = "blue"
    grayColor: str = "gray"
    radius: str = "large"
    scaling: str = "100%"

def template(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    meta: str | None = None,
    scriptTags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """template"""

    def decorator(pageContent: Callable[[], rx.Component]) -> rx.Component:
        """decorator"""
        allMeta = [*defaultMeta, *(meta or [])]

        def templatedPage():
            return rx.flex(
                navbar(),
                sidebar(),
                rx.flex(
                    rx.vstack(
                        pageContent(),
                        width="100%",
                        **styles.templateContentStyle,
                    ),
                    width="100%",
                    **styles.templatePageStyle,
                    max_width=[
                        "100%",
                        "100%",
                        "100%",
                        "100%",
                        "100%",
                        styles.maxWidth,
                    ],
                ),
                flex_direction=[
                    "column",
                    "column",
                    "column",
                    "column",
                    "column",
                    "row",
                ],
                width="100%",
                margin="auto",
                position="relative",
            )

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=allMeta,
            script_tags=scriptTags,
            on_load=on_load,
        )
        def themeWrap():
            return rx.theme(
                templatedPage(),
                has_background=True,
                accent_color=ThemeState.accentColor,
                gray_color=ThemeState.grayColor,
                radius=ThemeState.radius,
                scaling=ThemeState.scaling,
            )

        return themeWrap

    return decorator
