import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.tables import DataTable
from credito_app.ui.components.notifications import NotificationBar
from credito_app.modules.excepciones import CrediNodaError


class PagosView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        
        self.notification = NotificationBar(self)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        SectionHeader(self, title="Pagos", subtitle="Historial de pagos realizados").pack(fill="x", padx=20, pady=(0, 20))
        
        columns = [
            {"key": "fecha", "text": "Fecha", "width": 130, "weight": 0, "anchor": "center"},
            {"key": "cliente", "text": "Cliente", "width": 240, "weight": 3, "anchor": "w"},
            {"key": "credito", "text": "Crédito", "width": 100, "weight": 0, "anchor": "center"},
            {"key": "cuota", "text": "Cuota", "width": 90, "weight": 0, "anchor": "center"},
            {"key": "monto", "text": "Monto", "width": 150, "weight": 1, "anchor": "e"}
        ]
        
        self.table = DataTable(self, columns=columns, on_row_click=self._on_row_click, height=500)
        self.table.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _load_data(self):
        try:
            pagos_detalle = self.app.pago_service.listar_pagos_con_detalle()
            rows = []
            
            for pago in pagos_detalle:
                num_cuota = pago.get("numero_cuota")
                cuota_display = str(num_cuota) if num_cuota is not None else str(pago["cuota_id"])
                rows.append({
                    "id": pago["pago_id"],
                    "fecha": formato_fecha(pago["fecha_pago"]),
                    "cliente": pago["cliente_nombre"],
                    "credito": f"#{pago['credito_id']}",
                    "cuota": cuota_display,
                    "monto": formato_moneda(pago["monto"]),
                    "__credito_id": pago["credito_id"]
                })
                
            self.table.set_data(rows)
            
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")

    def _on_row_click(self, row_data):
        if row_data and "__credito_id" in row_data:
            self.app.navigate("credito_detail", credito_id=row_data["__credito_id"])
