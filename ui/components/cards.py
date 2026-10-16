import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS


class MetricCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, icon="", color=None):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=12, height=120)
        self.pack_propagate(False)
        self.grid_propagate(False)

        accent_color = color if color else COLORS["primary"]

        # Accent bar
        self.bar = ctk.CTkFrame(self, height=3, fg_color=accent_color, corner_radius=12)
        self.bar.place(relx=0, rely=0, relwidth=1.0)

        # Internal padding frame
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=15)

        # Layout: Icon and Title on top, Value below
        header_frame = ctk.CTkFrame(inner, fg_color="transparent")
        header_frame.pack(fill="x", anchor="w")

        if icon:
            icon_label = ctk.CTkLabel(header_frame, text=icon, font=FONTS["body"], text_color=COLORS["text_secondary"])
            icon_label.pack(side="left", padx=(0, 5))

        title_label = ctk.CTkLabel(
            header_frame, text=title, font=FONTS["metric_label"], text_color=COLORS["text_secondary"]
        )
        title_label.pack(side="left")

        self.value_label = ctk.CTkLabel(
            inner, text=value, font=FONTS["metric_value"], text_color=COLORS["text_primary"]
        )
        self.value_label.pack(anchor="w", pady=(10, 0))

    def update_value(self, value, color=None):
        self.value_label.configure(text=str(value))
        if color:
            self.bar.configure(fg_color=color)
