import reflex as rx

def page() -> rx.Component:
    return rx.container(
        rx.heading("DataFeed"),
        rx.text("Zde nastav MQTT."),
    )
