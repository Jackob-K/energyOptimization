import httpx
import reflex as rx
import base64

class FileUploadState(rx.State):
    """Ukládá stav nahrávání souboru."""
    file_name: str = ""
    uploading: bool = False

    @rx.event(background=True)
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Pošle vybraný soubor na backend jako Base64 JSON."""
        async with self:
            if self.uploading:
                return

            self.uploading = True

        try:
            for file in files:
                # ✅ Reflex již posílá bytes, takže nepoužíváme file.read()
                file_data = file  # `file` už je bytes!

                # ✅ Zakódujeme soubor do Base64
                file_base64 = base64.b64encode(file_data).decode("utf-8")
                
                # ✅ Získáme název souboru správně
                file_name = getattr(file, "name", "uploaded_file.xlsx")

                # ✅ Pošleme JSON do backendu
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://127.0.0.1:8000/upload/",
                        json={"filename": file_name, "filedata": file_base64},
                    )

                async with self:
                    if response.status_code == 200:
                        self.file_name = file_name
                        print(f"✅ Soubor {file_name} úspěšně nahrán!")
                    else:
                        error_text = response.text
                        print(f"❌ Chyba při nahrávání: {error_text}")

        except Exception as e:
            print(f"❌ Chyba v handle_upload: {e}")

        async with self:
            self.uploading = False

def page():
    return rx.container(
        rx.text("📂 Nahraj soubor pro zpracování"),
        rx.upload(
            rx.vstack(
                rx.button("Vybrat soubor"),
                rx.text("Můžeš přetáhnout nebo kliknout pro výběr .csv / .xlsx"),
            ),
            id="upload_xlsx",
            multiple=False,
            accept={
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                "text/csv": [".csv"]
            },
            max_files=1,
            on_drop=FileUploadState.handle_upload,
        ),
        rx.cond(FileUploadState.file_name != "", rx.text(f"📄 {FileUploadState.file_name}"), rx.text("❌ Žádný soubor nenahrán")),
        rx.cond(FileUploadState.uploading, rx.text("⏳ Nahrávání..."), rx.text("✅ Hotovo!")),  
        padding="5em",
    )

app = rx.App()
app.add_page(page)
