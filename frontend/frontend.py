import reflex as rx
from .pages import dashboard, settings, datafeed

def navbar() -> rx.Component:
    return rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("Dashboard", value="dashboard"),
            rx.tabs.trigger("Settings", value="settings"),
            rx.tabs.trigger("DataFeed", value="datafeed")
        ),
        rx.tabs.content(
            dashboard.page(),
            value="dashboard",
        ),
        rx.tabs.content(
            settings.page(),
            value="settings",
        ),
        rx.tabs.content(
            datafeed.page(),
            value="datafeed",
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
app.add_page(datafeed.page, route="/datafeed")

if __name__ == "__main__":
    app.run()
