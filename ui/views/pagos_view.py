import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.tables import DataTable
from credito_app.ui.components.notifications import NotificationBar
from credito_app.ui.components.dialogs import DetallePagoDialog
from credito_app.modules.excepciones import CrediNodaError


class PagosView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        self.pagos_detalle = []
        self.mapa_pagos = {}
        
        self.notification = NotificationBar(self)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        SectionHeader(
            self,
            title="Pagos",
            subtitle="Historial de recaudos y emisión de comprobantes"
        ).pack(fill="x", padx=20, pady=(0, 12))

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(0, 12))

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Buscar por cliente o # crédito...",
            width=280,
            height=36,
            font=FONTS["input"]
        )
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<Return>", self._on_search)

        self.btn_buscar = ctk.CTkButton(
            filter_frame,
            text="Buscar",
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            width=90,
            height=36,
            command=self._on_search
        )
        self.btn_buscar.pack(side="left", padx=(0, 8))

        self.btn_limpiar = ctk.CTkButton(
            filter_frame,
            text="Limpiar",
            font=FONTS["body"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["row_hover"],
            width=80,
            height=36,
            command=self._on_limpiar
        )
        self.btn_limpiar.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(
            filter_frame,
            text="💡 Presiona Enter o Buscar para filtrar",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        ).pack(side="left")
        
        columns = [
            {"key": "fecha", "text": "Fecha", "width": 120, "weight": 0, "anchor": "center"},
            {"key": "cliente", "text": "Cliente", "width": 240, "weight": 3, "anchor": "w"},
            {"key": "credito", "text": "Crédito", "width": 100, "weight": 0, "anchor": "center"},
            {"key": "cuota", "text": "Cuota", "width": 90, "weight": 0, "anchor": "center"},
            {"key": "monto", "text": "Monto Abonado", "width": 140, "weight": 1, "anchor": "e"}
        ]
        
        self.table = DataTable(self, columns=columns, on_row_click=self._on_row_click, height=500)
        self.table.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _load_data(self):
        try:
            self.pagos_detalle = self.app.pago_service.listar_pagos_con_detalle()
            self.mapa_pagos = {p["pago_id"]: p for p in self.pagos_detalle}
            self._render_rows(self.pagos_detalle)
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")

    def _render_rows(self, lista_pagos: list[dict]):
        rows = []
        for pago in lista_pagos:
            num_cuota = pago.get("numero_cuota")
            cuota_display = str(num_cuota) if num_cuota is not None else str(pago["cuota_id"])
            rows.append({
                "id": pago["pago_id"],
                "fecha": formato_fecha(pago["fecha_pago"]),
                "cliente": pago["cliente_nombre"],
                "credito": f"#{pago['credito_id']}",
                "cuota": cuota_display,
                "monto": formato_moneda(pago["monto"]),
                "__pago_id": pago["pago_id"],
                "__credito_id": pago["credito_id"]
            })

        self.table.set_data(rows)

    def _on_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self._render_rows(self.pagos_detalle)
            return

        query_num = query.lstrip("#").strip()
        es_numero = query_num.isdigit()

        filtrados = []
        for p in self.pagos_detalle:
            nombre_cliente = p.get("cliente_nombre", "").lower()
            credito_id_str = str(p.get("credito_id", ""))
            pago_id_str = str(p.get("pago_id", ""))
            recibo_str = f"rec-{p.get('pago_id', 0):05d}".lower()

            if es_numero:
                if credito_id_str == query_num or pago_id_str == query_num or query in nombre_cliente:
                    filtrados.append(p)
            else:
                if query in nombre_cliente or query == f"#{credito_id_str}" or query in recibo_str:
                    filtrados.append(p)

        self._render_rows(filtrados)

    def _on_limpiar(self):
        self.search_entry.delete(0, "end")
        self._render_rows(self.pagos_detalle)



    def _on_row_click(self, row_data):
        if not row_data:
            return
        pago_id = row_data.get("id") or row_data.get("__pago_id")
        pago_info = self.mapa_pagos.get(pago_id)
        if pago_info:
            DetallePagoDialog(self, pago_info, self.app)

