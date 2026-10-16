import customtkinter as ctk
from typing import Callable, Optional
from PIL import Image
from credito_app.config import ICON_PNG_PATH
from credito_app.ui.theme import COLORS, FONTS


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_navigate: Callable[[str], None],
        on_backup: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, width=220, fg_color=COLORS["sidebar_bg"], corner_radius=0)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.on_backup = on_backup
        self.buttons = {}
        self.logo_image = None

        self.title_label = None
        if ICON_PNG_PATH.exists():
            try:
                import tkinter as tk

                tk._default_root = self.winfo_toplevel()
                pil_img = Image.open(ICON_PNG_PATH)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                self.title_label = ctk.CTkLabel(
                    self,
                    text=" CrediNoda",
                    image=self.logo_image,
                    compound="left",
                    font=FONTS["sidebar_title"],
                    text_color="#FFFFFF",
                )
            except Exception:
                self.logo_image = None
                self.title_label = None

        if self.title_label is None:
            self.title_label = ctk.CTkLabel(
                self,
                text="💰 CrediNoda",
                font=FONTS["sidebar_title"],
                text_color="#FFFFFF",
            )
        self.title_label.pack(pady=(20, 10))


        # Separator
        separator = ctk.CTkFrame(self, height=2, fg_color=COLORS["text_secondary"])
        separator.pack(fill="x", padx=20, pady=(0, 20))

        # Menu items
        self.items = [
            ("dashboard", "🏠 Inicio"),
            ("clientes", "👥 Clientes"),
            ("credito_new", "💳 Nuevo Crédito"),
            ("pagos", "💵 Pagos"),
            ("reportes", "📊 Reportes"),
        ]

        for key, text in self.items:
            btn = ctk.CTkButton(
                self,
                text=text,
                font=FONTS["sidebar_item"],
                fg_color="transparent",
                text_color=COLORS["sidebar_text"],
                hover_color=COLORS["sidebar_active"],
                anchor="w",
                command=lambda k=key: self._on_button_click(k),
            )
            btn.pack(fill="x", padx=10, pady=5)
            self.buttons[key] = btn

        # Botón de Copia de Seguridad en la parte inferior
        self.backup_btn = ctk.CTkButton(
            self,
            text="💾 Copia de Seguridad",
            font=FONTS["sidebar_item"],
            fg_color="transparent",
            text_color=COLORS["sidebar_text"],
            hover_color=COLORS["sidebar_active"],
            anchor="w",
            command=self._on_backup_click,
        )
        self.backup_btn.pack(side="bottom", fill="x", padx=10, pady=(5, 20))

        bottom_sep = ctk.CTkFrame(self, height=1, fg_color=COLORS["text_secondary"])
        bottom_sep.pack(side="bottom", fill="x", padx=20, pady=(10, 5))

    def _on_button_click(self, key: str):
        self.set_active(key)
        self.on_navigate(key)

    def _on_backup_click(self):
        if self.on_backup:
            self.on_backup()

    def set_active(self, key: str):
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(fg_color=COLORS["sidebar_active"], text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["sidebar_text"])
