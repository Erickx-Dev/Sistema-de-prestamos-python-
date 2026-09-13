import customtkinter as ctk
from decimal import Decimal
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha, formato_porcentaje, color_estado_credito, color_estado_cuota
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.tables import DataTable
from credito_app.ui.components.cards import MetricCard
from credito_app.ui.components.notifications import NotificationBar
from credito_app.ui.components.dialogs import PagoDialog
from credito_app.modules.credito import EstadoCredito, EstadoCuota
from credito_app.modules.excepciones import CrediNodaError


class CreditoDetailView(ctk.CTkFrame):
    def __init__(self, parent, app, credito_id):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        self.credito_id = credito_id
        
        self.credito = None
        self.cliente = None
        self.cuotas = []
        
        self.notification = NotificationBar(self)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # Back button
        btn_back = ctk.CTkButton(self, text="← Volver", command=self._on_back, font=FONTS["body"], fg_color="transparent", text_color=COLORS["primary"], hover_color=COLORS["border"], width=80)
        btn_back.pack(anchor="w", padx=20, pady=(10, 10))
        
        # Header Panel
        self.header_panel = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=12)
        self.header_panel.pack(fill="x", padx=20, pady=(0, 20))
        
        header_inner = ctk.CTkFrame(self.header_panel, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=20)
        
        title_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 10))
        
        self.lbl_title = ctk.CTkLabel(title_row, text=f"Crédito #{self.credito_id}", font=FONTS["h1"], text_color=COLORS["text_main"])
        self.lbl_title.pack(side="left")
        
        self.lbl_estado = ctk.CTkLabel(title_row, text="", font=FONTS["body_bold"], text_color="white", corner_radius=6)
        self.lbl_estado.pack(side="left", padx=(10, 0))
        
        self.btn_cliente = ctk.CTkButton(header_inner, text="Cliente: -", command=self._on_cliente_click, font=FONTS["body"], fg_color="transparent", text_color=COLORS["primary"], hover_color=COLORS["input_bg"], anchor="w")
        self.btn_cliente.pack(fill="x", pady=(0, 10))
        
        # Details row
        self.details_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        self.details_frame.pack(fill="x")
        
        self.lbl_tasa = ctk.CTkLabel(self.details_frame, text="Tasa: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_tasa.pack(side="left", padx=(0, 15))
        
        self.lbl_plazo = ctk.CTkLabel(self.details_frame, text="Plazo: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_plazo.pack(side="left", padx=(0, 15))
        
        self.lbl_frec = ctk.CTkLabel(self.details_frame, text="Frecuencia: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_frec.pack(side="left", padx=(0, 15))
        
        self.lbl_inicio = ctk.CTkLabel(self.details_frame, text="Inicio: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_inicio.pack(side="left")
        
        # Financial summary (MetricCards)
        summary_container = ctk.CTkFrame(self, fg_color="transparent")
        summary_container.pack(fill="x", padx=20, pady=(0, 20))
        
        self.card_capital = MetricCard(summary_container, "Capital", "$0", icon="💰", color=COLORS["primary"])
        self.card_capital.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_total = MetricCard(summary_container, "Total", "$0", icon="📝")
        self.card_total.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_pagado = MetricCard(summary_container, "Pagado", "$0", icon="✅", color=COLORS["success"])
        self.card_pagado.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_saldo = MetricCard(summary_container, "Saldo Pendiente", "$0", icon="⏳", color=COLORS["warning"])
        self.card_saldo.pack(side="left", expand=True, fill="both")
        
        # Payment Plan Section
        SectionHeader(self, title="Plan de Pagos", button_text="Registrar Pago", button_command=self._on_registrar_pago).pack(fill="x", padx=20, pady=(0, 10))
        
        columns = [
            {"key": "numero", "text": "#", "width": 60, "weight": 0, "anchor": "center"},
            {"key": "vencimiento", "text": "Vencimiento", "width": 130, "weight": 1, "anchor": "center"},
            {"key": "monto", "text": "Cuota", "width": 140, "weight": 1, "anchor": "e"},
            {"key": "pagado", "text": "Pagado", "width": 140, "weight": 1, "anchor": "e"},
            {"key": "pendiente", "text": "Pendiente", "width": 140, "weight": 1, "anchor": "e"},
            {"key": "estado", "text": "Estado", "width": 110, "weight": 0, "anchor": "center"}
        ]
        
        self.table = DataTable(self, columns=columns, on_row_click=self._on_row_click, height=300)
        self.table.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _load_data(self):
        try:
            self.credito = self.app.credito_service.obtener_credito(self.credito_id)
            self.cliente = self.app.cliente_service.obtener_cliente(self.credito.cliente_id)
            self.cuotas = self.app.credito_service.obtener_plan_pagos(self.credito_id)
            
            saldo = self.app.credito_service.calcular_saldo_pendiente(self.credito_id)
            total_pagado = self.credito.total_pagar - saldo
            estado_credito = self.app.credito_service.determinar_estado_credito(self.credito_id)
            
            # Update header info
            self.lbl_title.configure(text=f"Crédito #{self.credito_id}")
            self.lbl_estado.configure(text=f" {estado_credito.value} ", fg_color=color_estado_credito(estado_credito))
            self.btn_cliente.configure(text=f"Cliente: {self.cliente.nombre} ({self.cliente.documento})")
            
            self.lbl_tasa.configure(text=f"Tasa: {formato_porcentaje(self.credito.tasa_mensual)}")
            self.lbl_plazo.configure(text=f"Plazo: {self.credito.plazo_meses} meses")
            self.lbl_frec.configure(text=f"Frecuencia: {self.credito.frecuencia_pago.value}")
            self.lbl_inicio.configure(text=f"Inicio: {formato_fecha(self.credito.fecha_inicio)}")
            
            # Update metric cards
            self.card_capital.update_value(formato_moneda(self.credito.capital))
            self.card_total.update_value(formato_moneda(self.credito.total_pagar))
            self.card_pagado.update_value(formato_moneda(total_pagado))
            self.card_saldo.update_value(formato_moneda(saldo))
            
            # Update table
            rows = []
            for cuota in self.cuotas:
                pagos = self.app.pago_service.obtener_pagos_cuota(cuota.id)
                pagado = sum(p.monto for p in pagos)
                pendiente = cuota.monto - pagado
                
                rows.append({
                    "id": cuota.id,
                    "numero": str(cuota.numero_cuota),
                    "vencimiento": formato_fecha(cuota.fecha_vencimiento),
                    "monto": formato_moneda(cuota.monto),
                    "pagado": formato_moneda(pagado),
                    "pendiente": formato_moneda(pendiente),
                    "estado": cuota.estado.value,
                    "__estado_raw": cuota.estado,
                    "__bg_color": color_estado_cuota(cuota.estado)
                })
                
            self.table.set_data(rows)
            
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")

    def _on_back(self):
        self.app.navigate("dashboard")

    def _on_cliente_click(self):
        if self.cliente:
            self.app.navigate("cliente_detail", cliente_id=self.cliente.id)

    def _on_registrar_pago(self):
        if not self.credito or not self.cuotas:
            return
            
        cuotas_pendientes = [c for c in self.cuotas if c.estado in (EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL)]
        if not cuotas_pendientes:
            self.app.show_notification("No hay cuotas pendientes para este crédito.", "warning")
            return
            
        PagoDialog(self, self.credito, cuotas_pendientes, self.app.pago_service, self._on_pago_saved)

    def _on_row_click(self, row_data):
        if not row_data or not self.credito or not self.cuotas:
            return
            
        cuota_id = row_data["id"]
        estado = row_data["__estado_raw"]
        
        if estado in (EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL):
            cuotas_pendientes = [c for c in self.cuotas if c.estado in (EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL)]
            PagoDialog(self, self.credito, cuotas_pendientes, self.app.pago_service, self._on_pago_saved, selected_cuota_id=cuota_id)

    def _on_pago_saved(self, pago=None):
        if hasattr(self.app, "notificar_cambio_datos"):
            self.app.notificar_cambio_datos()
        self.app.show_notification("Pago registrado exitosamente", "success")
        self._load_data()

