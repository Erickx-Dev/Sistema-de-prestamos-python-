import customtkinter as ctk
from decimal import Decimal
from datetime import date, datetime
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha
from credito_app.ui.utils.validators import validar_texto_no_vacio, validar_monto, parsear_monto
from credito_app.modules.credito import EstadoCuota
from credito_app.modules.excepciones import CrediNodaError


class BaseDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width: int = 400, height: int = 500):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.withdraw()  # Ocultar temporalmente para posicionar sin parpadeos

        self.transient(parent)
        self.grab_set()

        # Center the dialog relative to the application main window
        self.update_idletasks()
        try:
            root = parent.winfo_toplevel()
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            if rw > 100 and rh > 100:
                x = rx + (rw // 2) - (width // 2)
                y = ry + (rh // 2) - (height // 2)
            else:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = (sw // 2) - (width // 2)
                y = (sh // 2) - (height // 2)
        except Exception:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw // 2) - (width // 2)
            y = (sh // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        self.deiconify()  # Mostrar centrada

        self.container = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"])
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            self.container, text=title, font=FONTS["dialog_title"], text_color=COLORS["text_primary"]
        )
        title_label.pack(anchor="w", pady=(0, 15))


class ConfirmDialog(BaseDialog):
    def __init__(self, parent, title, message, on_confirm):
        super().__init__(parent, title=title, width=460, height=230)
        self.on_confirm = on_confirm

        msg_label = ctk.CTkLabel(
            self.container,
            text=message,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            wraplength=410,
            justify="center",
        )
        msg_label.pack(expand=True, pady=(10, 20))

        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self.destroy,
        )
        cancel_btn.pack(side="left", expand=True, padx=10)

        self.confirm_btn = ctk.CTkButton(btn_frame, text="Confirmar", fg_color=COLORS["primary"], command=self._confirm)
        self.confirm_btn.pack(side="right", expand=True, padx=10)

    def _confirm(self):
        self.confirm_btn.configure(state="disabled")
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_confirm:
            self.on_confirm()


class ClienteDialog(BaseDialog):
    def __init__(self, parent, cliente_service, on_save, cliente=None):
        title = "Editar Cliente" if cliente else "Nuevo Cliente"
        super().__init__(parent, title=title, width=450)
        self.cliente_service = cliente_service
        self.on_save = on_save
        self.cliente = cliente

        self._build_form()

    def _build_form(self):
        # Nombre
        ctk.CTkLabel(self.container, text="Nombre Completo", font=FONTS["label"]).pack(anchor="w")
        self.nombre_entry = ctk.CTkEntry(self.container, width=400, font=FONTS["input"])
        self.nombre_entry.pack(pady=(5, 0))
        self.err_nombre = ctk.CTkLabel(self.container, text="", text_color=COLORS["error"], font=FONTS["small"])
        self.err_nombre.pack(anchor="w", pady=(0, 10))

        # Documento
        ctk.CTkLabel(self.container, text="Documento de Identidad", font=FONTS["label"]).pack(anchor="w")
        self.doc_entry = ctk.CTkEntry(self.container, width=400, font=FONTS["input"])
        self.doc_entry.pack(pady=(5, 0))
        self.err_doc = ctk.CTkLabel(self.container, text="", text_color=COLORS["error"], font=FONTS["small"])
        self.err_doc.pack(anchor="w", pady=(0, 10))

        # Teléfono
        ctk.CTkLabel(self.container, text="Teléfono", font=FONTS["label"]).pack(anchor="w")
        self.tel_entry = ctk.CTkEntry(self.container, width=400, font=FONTS["input"])
        self.tel_entry.pack(pady=(5, 0))
        self.err_tel = ctk.CTkLabel(self.container, text="", text_color=COLORS["error"], font=FONTS["small"])
        self.err_tel.pack(anchor="w", pady=(0, 10))

        if self.cliente:
            self.nombre_entry.insert(0, self.cliente.nombre)
            self.doc_entry.insert(0, self.cliente.documento)
            if self.cliente.telefono:
                self.tel_entry.insert(0, self.cliente.telefono)

        # Buttons
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self.destroy,
        ).pack(side="left", expand=True, padx=10)

        ctk.CTkButton(btn_frame, text="Guardar", fg_color=COLORS["primary"], command=self._save).pack(
            side="right", expand=True, padx=10
        )

    def _save(self):
        self.err_nombre.configure(text="")
        self.err_doc.configure(text="")
        self.err_tel.configure(text="")

        nombre = self.nombre_entry.get().strip()
        doc = self.doc_entry.get().strip()
        tel = self.tel_entry.get().strip()

        valid_nom, msg_nom = validar_texto_no_vacio(nombre, "Nombre")
        if not valid_nom:
            self.err_nombre.configure(text=msg_nom)
            return

        valid_doc, msg_doc = validar_texto_no_vacio(doc, "Documento")
        if not valid_doc:
            self.err_doc.configure(text=msg_doc)
            return

        valid_tel, msg_tel = validar_texto_no_vacio(tel, "Teléfono")
        if not valid_tel:
            self.err_tel.configure(text=msg_tel)
            return

        try:
            if self.cliente:
                self.cliente_service.actualizar_cliente(
                    cliente_id=self.cliente.id, nombre=nombre, telefono=tel, documento=doc
                )
            else:
                self.cliente_service.crear_cliente(nombre=nombre, telefono=tel, documento=doc)
            self.on_save()
            self.destroy()
        except CrediNodaError as e:
            msg = str(e)
            if "documento" in msg.lower():
                self.err_doc.configure(text=msg)
            elif "teléfono" in msg.lower() or "telefono" in msg.lower():
                self.err_tel.configure(text=msg)
            else:
                self.err_nombre.configure(text=msg)
        except Exception as e:
            self.err_nombre.configure(text=str(e))


class PagoDialog(BaseDialog):
    def __init__(self, parent, credito, cuotas, pago_service, on_save, selected_cuota_id=None, app=None):
        super().__init__(parent, title="Registrar Pago", width=480, height=670)
        self.app = app or getattr(parent, "app", None)
        self.credito = credito
        self.cuotas = [c for c in cuotas if c.estado in (EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL)]
        self.pago_service = pago_service
        self.on_save = on_save

        self.cuota_map = {
            f"Cuota #{c.numero_cuota} - {formato_moneda(c.monto)} - {c.etiqueta_estado}": c for c in self.cuotas
        }
        self.selected_cuota = None

        self._build_form()

        if selected_cuota_id:
            for name, c in self.cuota_map.items():
                if c.id == selected_cuota_id:
                    self.cuota_selector.set(name)
                    self._on_cuota_selected(name)
                    break
        elif self.cuotas:
            first_name = list(self.cuota_map.keys())[0]
            self.cuota_selector.set(first_name)
            self._on_cuota_selected(first_name)

    def _build_form(self):
        # Botones anclados en la parte inferior para que nunca queden ocultos
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=(15, 0))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self.destroy,
            height=38,
        ).pack(side="left", expand=True, padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="Registrar Pago",
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
            command=self._save,
            height=38,
        ).pack(side="right", expand=True, padx=(10, 0))

        pagos = self.pago_service.obtener_historial_pagos(self.credito.id)
        total_pagado = sum((p.monto for p in pagos), start=Decimal("0"))
        saldo = self.credito.total_pagar - total_pagado
        info_text = f"Crédito #{self.credito.id}   •   Saldo: {formato_moneda(saldo)}"
        ctk.CTkLabel(
            self.container, text=info_text, font=FONTS["body_bold"], text_color=COLORS["primary"], justify="left"
        ).pack(anchor="w", pady=(0, 12))

        if not self.cuotas:
            ctk.CTkLabel(self.container, text="No hay cuotas pendientes.", text_color=COLORS["warning"]).pack(pady=20)
            return

        ctk.CTkLabel(self.container, text="Seleccionar Cuota", font=FONTS["label"]).pack(anchor="w")
        self.cuota_selector = ctk.CTkOptionMenu(
            self.container, values=list(self.cuota_map.keys()), command=self._on_cuota_selected, width=440, height=36
        )
        self.cuota_selector.pack(fill="x", pady=(4, 10))

        self.info_frame = ctk.CTkFrame(self.container, fg_color=COLORS["row_alt"], corner_radius=8)
        self.info_frame.pack(fill="x", pady=(0, 12))

        self.lbl_valor = ctk.CTkLabel(self.info_frame, text="Valor de cuota: $0", font=FONTS["body"])
        self.lbl_valor.pack(anchor="w", padx=12, pady=(8, 2))

        self.lbl_pagado = ctk.CTkLabel(
            self.info_frame, text="Pagado: $0", font=FONTS["body"], text_color=COLORS["success"]
        )
        self.lbl_pagado.pack(anchor="w", padx=12, pady=2)

        self.lbl_pendiente = ctk.CTkLabel(
            self.info_frame, text="Pendiente: $0", font=FONTS["body_bold"], text_color=COLORS["error"]
        )
        self.lbl_pendiente.pack(anchor="w", padx=12, pady=(2, 8))

        ctk.CTkLabel(self.container, text="Monto a Pagar", font=FONTS["label"]).pack(anchor="w", pady=(0, 4))
        self.monto_entry = ctk.CTkEntry(self.container, width=440, height=36, font=FONTS["input"])
        self.monto_entry.pack(fill="x", pady=(0, 4))
        self.err_monto = ctk.CTkLabel(self.container, text="", text_color=COLORS["error"], font=FONTS["small"])
        self.err_monto.pack(anchor="w", pady=(0, 4))

        # Checkbox para comprobante en PDF
        self.var_generar_pdf = ctk.BooleanVar(value=True)
        self.chk_pdf = ctk.CTkCheckBox(
            self.container,
            text="Generar y abrir comprobante en PDF",
            variable=self.var_generar_pdf,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
        )
        self.chk_pdf.pack(anchor="w", pady=(4, 0))

    def _on_cuota_selected(self, choice: str):
        self.selected_cuota = self.cuota_map.get(choice)
        if not self.selected_cuota:
            return

        pagos = self.pago_service.obtener_pagos_cuota(self.selected_cuota.id)
        pagado = sum((p.monto for p in pagos), start=Decimal("0"))
        pendiente = (self.selected_cuota.monto - pagado).quantize(Decimal("0.01"))

        self.lbl_valor.configure(text=f"Valor de cuota: {formato_moneda(self.selected_cuota.monto)}")
        self.lbl_pagado.configure(text=f"Pagado: {formato_moneda(pagado)}")
        self.lbl_pendiente.configure(text=f"Pendiente: {formato_moneda(pendiente)}")

        self.monto_entry.delete(0, "end")
        if pendiente == pendiente.to_integral_value():
            self.monto_entry.insert(0, str(int(pendiente)))
        else:
            self.monto_entry.insert(0, f"{pendiente:.2f}")

    def _save(self):
        if not self.selected_cuota:
            return

        self.err_monto.configure(text="")

        texto = self.monto_entry.get()
        valid, msg = validar_monto(texto)
        if not valid:
            self.err_monto.configure(text=msg)
            return

        monto = parsear_monto(texto)
        try:
            pago = self.pago_service.registrar_pago(
                credito_id=self.credito.id, cuota_id=self.selected_cuota.id, monto=monto
            )

            # Generar comprobante si la opción está activada
            if self.var_generar_pdf.get() and self.app and hasattr(self.app, "generar_comprobante_pago"):
                try:
                    self.app.generar_comprobante_pago(pago.id, preguntar_destino=False, abrir_al_terminar=True)
                except Exception as pdf_err:
                    print(f"Error generando PDF automático: {pdf_err}")

            if self.app and hasattr(self.app, "notificar_cambio_datos"):
                self.app.notificar_cambio_datos()

            if callable(self.on_save):
                try:
                    self.on_save(pago)
                except TypeError:
                    self.on_save()

            self.destroy()
        except CrediNodaError as e:
            self.err_monto.configure(text=str(e))
        except Exception as e:
            self.err_monto.configure(text=f"Error al registrar pago: {str(e)}")


class DetallePagoDialog(BaseDialog):
    """Diálogo modal para visualizar el detalle de un pago y generar/exportar su comprobante PDF."""

    def __init__(self, parent, pago_detalle: dict, app):
        super().__init__(parent, title=f"Pago #{pago_detalle.get('pago_id', '')}", width=480, height=450)
        self.pago_detalle = pago_detalle
        self.app = app
        self._build_ui()

    def _build_ui(self):
        pago_id = self.pago_detalle.get("pago_id")
        cliente_nombre = self.pago_detalle.get("cliente_nombre", "-")
        credito_id = self.pago_detalle.get("credito_id", "-")
        cuota_num = self.pago_detalle.get("numero_cuota", "-")
        fecha_pago = self.pago_detalle.get("fecha_pago")
        fecha_str = formato_fecha(fecha_pago) if isinstance(fecha_pago, (date, datetime)) else str(fecha_pago)
        monto_str = formato_moneda(self.pago_detalle.get("monto", Decimal("0")))

        # Tarjeta informativa
        info_card = ctk.CTkFrame(self.container, fg_color=COLORS["row_alt"], corner_radius=8)
        info_card.pack(fill="x", pady=(0, 15), padx=5)

        ctk.CTkLabel(
            info_card, text=f"Recibo: REC-{pago_id:05d}", font=FONTS["body_bold"], text_color=COLORS["primary"]
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            info_card, text=f"Cliente: {cliente_nombre}", font=FONTS["body"], text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(
            info_card,
            text=f"Crédito: #{credito_id}   •   Cuota: #{cuota_num}",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(
            info_card, text=f"Fecha del Pago: {fecha_str}", font=FONTS["body"], text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(
            info_card, text=f"Monto Abonado: {monto_str}", font=FONTS["body_bold"], text_color=COLORS["success"]
        ).pack(anchor="w", padx=15, pady=(4, 12))

        # Botones de acción principales
        ctk.CTkButton(
            self.container,
            text="📄  Ver / Imprimir Comprobante PDF",
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
            height=40,
            command=self._abrir_pdf,
        ).pack(fill="x", pady=(5, 8), padx=5)

        ctk.CTkButton(
            self.container,
            text="💾  Guardar Comprobante Como...",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["primary"],
            text_color=COLORS["primary"],
            font=FONTS["body"],
            height=38,
            command=self._guardar_pdf_como,
        ).pack(fill="x", pady=(0, 8), padx=5)

        ctk.CTkButton(
            self.container,
            text="🔍  Ir al Detalle del Crédito",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
            height=38,
            command=self._ir_al_credito,
        ).pack(fill="x", pady=(0, 12), padx=5)

        # Botón Cerrar
        ctk.CTkButton(
            self.container,
            text="Cerrar",
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            command=self.destroy,
            height=32,
        ).pack(fill="x", padx=5)

    def _abrir_pdf(self):
        pago_id = self.pago_detalle.get("pago_id")
        if self.app and hasattr(self.app, "generar_comprobante_pago"):
            self.app.generar_comprobante_pago(pago_id, preguntar_destino=False, abrir_al_terminar=True)

    def _guardar_pdf_como(self):
        pago_id = self.pago_detalle.get("pago_id")
        if self.app and hasattr(self.app, "generar_comprobante_pago"):
            self.app.generar_comprobante_pago(pago_id, preguntar_destino=True, abrir_al_terminar=False)

    def _ir_al_credito(self):
        credito_id = self.pago_detalle.get("credito_id")
        self.destroy()
        if self.app and credito_id:
            self.app.navigate("credito_detail", credito_id=credito_id)
