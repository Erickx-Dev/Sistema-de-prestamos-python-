import customtkinter as ctk
from typing import Callable
from credito_app.ui.theme import COLORS, FONTS

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate: Callable[[str], None]):
        super().__init__(parent, width=220, fg_color=COLORS["sidebar_bg"], corner_radius=0)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.buttons = {}
        
        # Logo/Title
        self.title_label = ctk.CTkLabel(
            self, text="💰 CrediNoda", 
            font=FONTS["sidebar_title"], text_color="#FFFFFF"
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
            ("reportes", "📊 Reportes")
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
                command=lambda k=key: self._on_button_click(k)
            )
            btn.pack(fill="x", padx=10, pady=5)
            self.buttons[key] = btn
            
    def _on_button_click(self, key: str):
        self.set_active(key)
        self.on_navigate(key)
        
    def set_active(self, key: str):
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(fg_color=COLORS["sidebar_active"], text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["sidebar_text"])
