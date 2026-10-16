import customtkinter as ctk
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.dialogs import ClienteDialog
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha, color_estado_credito
from credito_app.modules.excepciones import CrediNodaError


class ClienteDetailView(ctk.CTkFrame):
    def __init__(self, parent, app, cliente_id=None):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        self.cliente_id = cliente_id
        self.cliente = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        self.back_btn = ctk.CTkButton(
            self,
            text="← Volver a Clientes",
            fg_color="transparent",
            text_color=COLORS["primary"],
            hover_color=COLORS["border"],
            anchor="w",
            width=150,
            command=self.go_back,
        )
        self.back_btn.pack(anchor="w", pady=(0, 10))

        self.info_panel = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=8)
        self.info_panel.pack(fill="x", pady=(0, 20), padx=5, ipady=10)

        self.name_label = ctk.CTkLabel(self.info_panel, text="", font=FONTS["heading1"], text_color=COLORS["text"])
        self.name_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 5))

        self.doc_label = ctk.CTkLabel(self.info_panel, text="", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.doc_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 5))

        self.tel_label = ctk.CTkLabel(self.info_panel, text="", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.tel_label.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 5))

        self.fecha_label = ctk.CTkLabel(
            self.info_panel, text="", font=FONTS["body"], text_color=COLORS["text_secondary"]
        )
        self.fecha_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 15))

        self.edit_btn = ctk.CTkButton(
            self.info_panel, text="Editar", width=80, height=28, command=self.open_edit_dialog
        )
        self.edit_btn.grid(row=0, column=2, sticky="e", padx=20, pady=15)
        self.info_panel.grid_columnconfigure(1, weight=1)

        self.header_creditos = SectionHeader(
            self, title="Créditos del Cliente", button_text="+ Nuevo Crédito", button_command=self.new_credito
        )
        self.header_creditos.pack(fill="x", pady=(0, 15))

        self.creditos_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.creditos_container.pack(fill="both", expand=True)

    def _load_data(self):
        if not self.cliente_id:
            return

        try:
            self.cliente = self.app.cliente_service.obtener_cliente(self.cliente_id)
            if not self.cliente:
                self.app.show_notification("Cliente no encontrado", "error")
                self.go_back()
                return

            self.name_label.configure(text=self.cliente.nombre)
            self.doc_label.configure(text=f"Documento: {self.cliente.documento}")
            self.tel_label.configure(text=f"Teléfono: {self.cliente.telefono or 'N/A'}")
            fecha_reg = formato_fecha(self.cliente.fecha_registro) if self.cliente.fecha_registro else "N/A"
            self.fecha_label.configure(text=f"Registrado el: {fecha_reg}")

            for widget in self.creditos_container.winfo_children():
                widget.destroy()

            creditos = self.app.cliente_service.obtener_creditos_cliente(self.cliente_id)

            for credito in creditos:
                self.create_credito_card(credito)

        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")
        except Exception:
            self.app.show_notification("Ocurrió un error inesperado al cargar el cliente.", "error")

    def create_credito_card(self, credito):
        card = ctk.CTkFrame(self.creditos_container, fg_color=COLORS["bg_card"], corner_radius=8)
        card.pack(fill="x", pady=(0, 10), ipady=5)

        saldo = self.app.credito_service.calcular_saldo_pendiente(credito.id)
        pagado = credito.total_pagar - saldo

        top_frame = ctk.CTkFrame(card, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(10, 5))

        title = ctk.CTkLabel(
            top_frame, text=f"Crédito #{credito.id}", font=FONTS["heading2"], text_color=COLORS["text"]
        )
        title.pack(side="left")

        bg_color = color_estado_credito(credito.estado)
        estado_badge = ctk.CTkLabel(
            top_frame,
            text=credito.estado.value,
            font=FONTS["body"],
            fg_color=bg_color,
            text_color="#FFFFFF",
            corner_radius=4,
            padx=8,
        )
        estado_badge.pack(side="left", padx=10)

        view_btn = ctk.CTkButton(
            top_frame,
            text="Ver Detalles",
            width=100,
            height=28,
            fg_color=COLORS["secondary"],
            command=lambda c_id=credito.id: self.app.navigate("credito_detail", credito_id=c_id),
        )
        view_btn.pack(side="right")

        mid_frame = ctk.CTkFrame(card, fg_color="transparent")
        mid_frame.pack(fill="x", padx=15, pady=5)
        mid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        metrics = [
            ("Capital", formato_moneda(credito.capital)),
            ("Total", formato_moneda(credito.total_pagar)),
            ("Pagado", formato_moneda(pagado)),
            ("Pendiente", formato_moneda(saldo)),
        ]

        for i, (label, val) in enumerate(metrics):
            f = ctk.CTkFrame(mid_frame, fg_color="transparent")
            f.grid(row=0, column=i, sticky="w")
            ctk.CTkLabel(f, text=label, font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(anchor="w")
            ctk.CTkLabel(f, text=val, font=FONTS["body"], text_color=COLORS["text"]).pack(anchor="w")

        bot_frame = ctk.CTkFrame(card, fg_color="transparent")
        bot_frame.pack(fill="x", padx=15, pady=(5, 10))

        info_text = f"Frecuencia: {credito.frecuencia_pago.value} | Plazo: {credito.plazo_meses} meses | Inicio: {formato_fecha(credito.fecha_inicio)}"
        ctk.CTkLabel(bot_frame, text=info_text, font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(
            anchor="w"
        )

    def go_back(self):
        self.app.navigate("clientes")

    def new_credito(self):
        self.app.navigate("credito_new", cliente_id=self.cliente_id)

    def open_edit_dialog(self):
        if self.cliente:
            ClienteDialog(self, self.app.cliente_service, on_save=self.refresh, cliente=self.cliente)

    def refresh(self):
        self._load_data()
