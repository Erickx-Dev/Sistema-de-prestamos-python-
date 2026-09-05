import customtkinter as ctk
from decimal import Decimal
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.cards import MetricCard
from credito_app.ui.components.notifications import NotificationBar
from credito_app.modules.credito import EstadoCredito
from credito_app.modules.excepciones import CrediNodaError


class ReportesView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        
        self.notification = NotificationBar(self)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        SectionHeader(self, title="Reportes", subtitle="Métricas del sistema").pack(fill="x", padx=20, pady=(0, 20))
        
        # Row 1
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=(0, 20))
        
        self.card_activos = MetricCard(row1, "Créditos Activos", "0", icon="📋", color=COLORS["primary"])
        self.card_activos.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_pagados = MetricCard(row1, "Créditos Pagados", "0", icon="✅", color=COLORS["success"])
        self.card_pagados.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_total = MetricCard(row1, "Total Créditos", "0", icon="📁")
        self.card_total.pack(side="left", expand=True, fill="both")
        
        # Row 2
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=(0, 20))
        
        self.card_capital = MetricCard(row2, "Capital Prestado", "$0", icon="💰", color=COLORS["primary"])
        self.card_capital.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_intereses = MetricCard(row2, "Intereses Generados", "$0", icon="📈", color=COLORS["warning"])
        self.card_intereses.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_recibido = MetricCard(row2, "Pagos Recibidos", "$0", icon="💵", color=COLORS["success"])
        self.card_recibido.pack(side="left", expand=True, fill="both")

    def _load_data(self):
        try:
            creditos = self.app.credito_service.listar_creditos()
            pagos = self.app.pago_service.listar_pagos()
            
            activos = sum(1 for c in creditos if c.estado == EstadoCredito.ACTIVO)
            pagados = sum(1 for c in creditos if c.estado == EstadoCredito.PAGADO)
            total = len(creditos)
            
            capital_prestado = sum(c.capital for c in creditos)
            intereses_generados = sum(c.total_intereses for c in creditos)
            pagos_recibidos = sum(p.monto for p in pagos)
            
            self.card_activos.update_value(str(activos))
            self.card_pagados.update_value(str(pagados))
            self.card_total.update_value(str(total))
            
            self.card_capital.update_value(formato_moneda(capital_prestado))
            self.card_intereses.update_value(formato_moneda(intereses_generados))
            self.card_recibido.update_value(formato_moneda(pagos_recibidos))
            
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")
