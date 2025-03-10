import reflex as rx
from .pages import dashboard, settings

def navbar() -> rx.Component:
    return rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("Dashboard", value="dashboard"),
            rx.tabs.trigger("Settings", value="settings")
        ),
        rx.tabs.content(
            dashboard.page(),
            value="dashboard",
        ),
        rx.tabs.content(
            settings.page(),
            value="settings",
        ),
    )

def index() -> rx.Component:
    return rx.container(
        navbar(),
        rx.text("Welcome to the Solar Optimization App"),
    )

app = rx.App()
app.add_page(index, route="/")
app.add_page(dashboard.page, route="/dashboard")
app.add_page(settings.page, route="/settings")

if __name__ == "__main__":
    app.run()
