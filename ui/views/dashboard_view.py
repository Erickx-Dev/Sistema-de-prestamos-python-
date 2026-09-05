from decimal import Decimal
import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.cards import MetricCard
from credito_app.ui.components.tables import DataTable
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha, color_estado_cuota
from credito_app.modules.excepciones import CrediNodaError
from credito_app.modules.credito import EstadoCredito

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        self.header = SectionHeader(self, title="Inicio", subtitle="Resumen del sistema")
        self.header.pack(fill="x", pady=(0, 20))
        
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="x", pady=(0, 30))
        self.cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.card_activos = MetricCard(self.cards_frame, title="Créditos Activos", value="0", icon="📋", color=COLORS["primary"])
        self.card_activos.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.card_capital = MetricCard(self.cards_frame, title="Capital Prestado", value="$0", icon="💰", color=COLORS["success"])
        self.card_capital.grid(row=0, column=1, padx=(10, 10), sticky="ew")
        
        self.card_saldo = MetricCard(self.cards_frame, title="Saldo Pendiente", value="$0", icon="📊", color=COLORS["warning"])
        self.card_saldo.grid(row=0, column=2, padx=(10, 0), sticky="ew")
        
        self.subheader = ctk.CTkLabel(self, text="Próximos Pagos", font=FONTS["heading2"], text_color=COLORS["text"])
        self.subheader.pack(anchor="w", pady=(0, 10))
        
        columns = [
            {"key": "cliente", "text": "Cliente", "width": 220, "weight": 3, "anchor": "w"},
            {"key": "cuota", "text": "Cuota", "width": 90, "weight": 0, "anchor": "center"},
            {"key": "monto", "text": "Monto", "width": 150, "weight": 1, "anchor": "e"},
            {"key": "vencimiento", "text": "Vencimiento", "width": 130, "weight": 1, "anchor": "center"},
            {"key": "estado", "text": "Estado", "width": 120, "weight": 1, "anchor": "center"}
        ]
        
        self.table = DataTable(self, columns=columns, on_row_click=self.on_row_click, height=400)
        self.table.pack(fill="both", expand=True)
        
    def _load_data(self):
        try:
            creditos = self.app.credito_service.listar_creditos()
            creditos_activos = [
                c for c in creditos 
                if c.estado in (EstadoCredito.ACTIVO, EstadoCredito.ACTIVO.value)
            ]
            
            num_activos = len(creditos_activos)
            capital_prestado = sum([c.capital for c in creditos_activos], Decimal("0"))
            saldo_pendiente = sum([self.app.credito_service.calcular_saldo_pendiente(c.id) for c in creditos_activos], Decimal("0"))
            
            self.card_activos.update_value(str(num_activos))
            self.card_capital.update_value(formato_moneda(capital_prestado))
            self.card_saldo.update_value(formato_moneda(saldo_pendiente))
            
            proximos_pagos = self.app.credito_service.obtener_proximos_pagos(limite=10)
            rows = []
            for pago in proximos_pagos:
                estado_display = pago["estado"].value if hasattr(pago["estado"], "value") else str(pago["estado"])
                rows.append({
                    "id": pago["credito_id"],
                    "cliente": pago["cliente_nombre"],
                    "cuota": f"{pago['numero_cuota']}",
                    "monto": formato_moneda(pago["monto"]),
                    "vencimiento": formato_fecha(pago["fecha_vencimiento"]),
                    "estado": estado_display
                })
            self.table.set_data(rows)
            
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")
        except Exception as e:
            self.app.show_notification("Ocurrió un error inesperado al cargar el dashboard.", "error")
            
    def on_row_click(self, row_data):
        if "id" in row_data:
            self.app.navigate("credito_detail", credito_id=row_data["id"])
            
    def refresh(self):
        self._load_data()
