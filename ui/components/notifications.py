import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS


class NotificationBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, height=40, corner_radius=0)
        self.label = ctk.CTkLabel(self, text="", font=FONTS["body_bold"], text_color="#FFFFFF")
        self.label.pack(pady=8)
        self._timer_id = None
        self._manager = None

    def _determine_manager(self) -> str:
        if self._manager:
            return self._manager
        parent = self.master
        pack_slaves = [s for s in parent.pack_slaves() if s != self] if hasattr(parent, "pack_slaves") else []
        grid_slaves = [s for s in parent.grid_slaves() if s != self] if hasattr(parent, "grid_slaves") else []
        if pack_slaves and not grid_slaves:
            self._manager = "pack"
        else:
            self._manager = "grid"
        return self._manager

    def _show(self, message: str, color: str, icon: str):
        if self._timer_id:
            self.after_cancel(self._timer_id)

        self.configure(fg_color=color)
        self.label.configure(text=f"{icon} {message}")

        mgr = self._determine_manager()
        if mgr == "pack":
            first_slave = None
            if hasattr(self.master, "pack_slaves"):
                slaves = self.master.pack_slaves()
                if slaves and slaves[0] != self:
                    first_slave = slaves[0]
            self.pack(fill="x", side="top", before=first_slave)
        else:
            self.grid(row=0, column=0, sticky="ew")

        self._timer_id = self.after(4000, self.hide)

    def show_success(self, message: str):
        self._show(message, COLORS["success"], "✓")

    def show_error(self, message: str):
        self._show(message, COLORS["error"], "✕")

    def show_warning(self, message: str):
        self._show(message, COLORS["warning"], "⚠")

    def hide(self):
        mgr = self._determine_manager()
        if mgr == "pack":
            self.pack_forget()
        else:
            self.grid_remove()
        self._timer_id = None
