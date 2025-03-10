import reflex as rx

def page() -> rx.Component:
    return rx.container(
        rx.heading("Dashboard"),
        rx.text("Here is the dashboard with data visualization."),
    )
