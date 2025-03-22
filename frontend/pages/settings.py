import reflex as rx
from frontend.templates import template
from frontend.components.fveField import FveFieldState, fveFieldsForm

@template(
    route="/settings",
    title="Settings",
    description="Manage your energy settings here."
)
def page() -> rx.Component:
    return rx.container(

        # Rozložení FVE formuláře a Ovládacího panelu vedle sebe
        rx.hstack(
            # Kontejner pro FVE formulář + tlačítka
            rx.vstack(
                rx.heading("Nastavení FVE", size="5"),
                # Tlačítka umístěná pouze nad fveFieldsForm()
                rx.hstack(
                    rx.button("Přidat další FVE", on_click=FveFieldState.add_field, size="3"),
                    rx.button("Uložit parametry", on_click=FveFieldState.submit_form, size="3", background="green", color="white"),
                    spacing="4",
                    justify="start",  # Zarovnání tlačítek doleva
                    width="100%",
                ),
                fveFieldsForm(),  # ✅ Formulář pro FVE pole
                spacing="4",
                width="65%",  # Nastavení šířky formuláře
            ),
            rx.vstack(
                rx.heading("Obecné", size="5"),
            ),
            rx.vstack(
                rx.heading("Globální úpravy", size="5"),
                
            )
        ),

        on_mount=FveFieldState.loadFveData  # ✅ Správná reference na metodu
    )