import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS

class SectionHeader(ctk.CTkFrame):
    def __init__(self, parent, title, subtitle="", button_text=None, button_command=None):
        super().__init__(parent, fg_color="transparent")
        
        # Left side: Title and Subtitle
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        
        title_label = ctk.CTkLabel(
            text_frame, text=title,
            font=FONTS["heading"], text_color=COLORS["text_primary"]
        )
        title_label.pack(anchor="w")
        
        if subtitle:
            subtitle_label = ctk.CTkLabel(
                text_frame, text=subtitle,
                font=FONTS["body"], text_color=COLORS["text_secondary"]
            )
            subtitle_label.pack(anchor="w", pady=(2, 0))
            
        # Right side: Action Button
        if button_text and button_command:
            action_btn = ctk.CTkButton(
                self, text=button_text,
                font=FONTS["button"],
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                command=button_command
            )
            action_btn.pack(side="right", anchor="center")
