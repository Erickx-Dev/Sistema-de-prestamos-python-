import customtkinter as ctk
from typing import Callable
from credito_app.ui.theme import COLORS, FONTS

class DataTable(ctk.CTkFrame):
    def __init__(self, parent, columns: list[dict], on_row_click: Callable[[dict], None] = None, height: int = 400):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=8)
        self.columns = columns
        self.on_row_click = on_row_click
        
        # Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.header_frame.pack(fill="x", padx=(6, 26), pady=(2, 0))
        self.header_frame.pack_propagate(False)
        
        # Configure columns grid for header
        for i, col in enumerate(self.columns):
            weight = col.get("weight", 1)
            self.header_frame.grid_columnconfigure(i, weight=weight, minsize=col.get("width", 100))
            lbl = ctk.CTkLabel(
                self.header_frame, text=col["text"],
                font=FONTS["table_header"], text_color=COLORS["text_primary"],
                anchor=col.get("anchor", "w")
            )
            lbl.grid(row=0, column=i, sticky="ew", padx=10, pady=10)
            
        # Bottom border for header
        border = ctk.CTkFrame(self, height=1, fg_color=COLORS["border"])
        border.pack(fill="x", padx=6)
        
        # Body Scrollable Frame
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent", height=height)
        self.body.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.rows = []
        
    def set_data(self, rows: list[dict]):
        self.clear()
        
        for i, row_data in enumerate(rows):
            bg_color = COLORS["bg_panel"] if i % 2 == 0 else COLORS["row_alt"]
            
            row_frame = ctk.CTkFrame(self.body, fg_color=bg_color, corner_radius=6, height=42)
            row_frame.pack(fill="x", pady=2, padx=4)
            row_frame.pack_propagate(False)
            
            # Hover effects
            row_frame.bind("<Enter>", lambda e, f=row_frame, c=COLORS["row_hover"]: f.configure(fg_color=c))
            row_frame.bind("<Leave>", lambda e, f=row_frame, c=bg_color: f.configure(fg_color=c))
            
            # Click event
            if self.on_row_click:
                row_frame.bind("<Button-1>", lambda e, data=row_data: self.on_row_click(data))
                
            for j, col in enumerate(self.columns):
                weight = col.get("weight", 1)
                row_frame.grid_columnconfigure(j, weight=weight, minsize=col.get("width", 100))
                
                cell_text = str(row_data.get(col["key"], ""))
                lbl = ctk.CTkLabel(
                    row_frame, text=cell_text,
                    font=FONTS["table_cell"], text_color=COLORS["text_primary"],
                    anchor=col.get("anchor", "w")
                )
                lbl.grid(row=0, column=j, sticky="ew", padx=10, pady=10)
                
                # Bind click to labels too
                if self.on_row_click:
                    lbl.bind("<Button-1>", lambda e, data=row_data: self.on_row_click(data))
                    lbl.bind("<Enter>", lambda e, f=row_frame, c=COLORS["row_hover"]: f.configure(fg_color=c))
                    lbl.bind("<Leave>", lambda e, f=row_frame, c=bg_color: f.configure(fg_color=c))
                    
            self.rows.append(row_frame)
            
    def clear(self):
        for row in self.rows:
            row.destroy()
        self.rows.clear()
