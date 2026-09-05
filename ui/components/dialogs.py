import customtkinter as ctk
from decimal import Decimal
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha
from credito_app.ui.utils.validators import validar_texto_no_vacio, validar_monto, parsear_monto
from credito_app.modules.credito import EstadoCuota
from credito_app.modules.excepciones import CrediNodaError

class BaseDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width: int = 400, height: int = 500):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        self.container = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"])
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            self.container, text=title, font=FONTS["dialog_title"], text_color=COLORS["text_primary"]
        )
        title_label.pack(anchor="w", pady=(0, 15))


class ConfirmDialog(BaseDialog):
    def __init__(self, parent, title, message, on_confirm):
        super().__init__(parent, title=title, width=400, height=220)
        self.on_confirm = on_confirm
        
        msg_label = ctk.CTkLabel(
            self.container, text=message, font=FONTS["body"], text_color=COLORS["text_primary"],
            wraplength=350
        )
        msg_label.pack(pady=20)
        
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancelar", fg_color="transparent",
            border_width=1, border_color=COLORS["border"], text_color=COLORS["text_primary"],
            command=self.destroy
        )
        cancel_btn.pack(side="left", expand=True, padx=10)
        
        self.confirm_btn = ctk.CTkButton(
            btn_frame, text="Confirmar", fg_color=COLORS["primary"],
            command=self._confirm
        )
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
            btn_frame, text="Cancelar", fg_color="transparent",
            border_width=1, border_color=COLORS["border"], text_color=COLORS["text_primary"],
            command=self.destroy
        ).pack(side="left", expand=True, padx=10)
        
        ctk.CTkButton(
            btn_frame, text="Guardar", fg_color=COLORS["primary"],
            command=self._save
        ).pack(side="right", expand=True, padx=10)
        
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
                    cliente_id=self.cliente.id,
                    nombre=nombre,
                    telefono=tel,
                    documento=doc
                )
            else:
                self.cliente_service.crear_cliente(
                    nombre=nombre,
                    telefono=tel,
                    documento=doc
                )
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
    def __init__(self, parent, credito, cuotas, pago_service, on_save, selected_cuota_id=None):
        super().__init__(parent, title="Registrar Pago", width=480, height=640)
        self.credito = credito
        self.cuotas = [c for c in cuotas if c.estado in (EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL)]
        self.pago_service = pago_service
        self.on_save = on_save
        
        self.cuota_map = {f"Cuota #{c.numero_cuota} - {formato_moneda(c.monto)} - {c.estado.value}": c for c in self.cuotas}
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
            btn_frame, text="Cancelar", fg_color="transparent",
            border_width=1, border_color=COLORS["border"], text_color=COLORS["text_primary"],
            command=self.destroy, height=38
        ).pack(side="left", expand=True, padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame, text="Registrar Pago", fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"], font=FONTS["body_bold"],
            command=self._save, height=38
        ).pack(side="right", expand=True, padx=(10, 0))
        
        pagos = self.pago_service.obtener_historial_pagos(self.credito.id)
        total_pagado = sum((p.monto for p in pagos), start=Decimal("0"))
        saldo = self.credito.total_pagar - total_pagado
        info_text = f"Crédito #{self.credito.id}   •   Saldo: {formato_moneda(saldo)}"
        ctk.CTkLabel(self.container, text=info_text, font=FONTS["body_bold"], text_color=COLORS["primary"], justify="left").pack(anchor="w", pady=(0, 15))
        
        if not self.cuotas:
            ctk.CTkLabel(self.container, text="No hay cuotas pendientes.", text_color=COLORS["warning"]).pack(pady=20)
            return
            
        ctk.CTkLabel(self.container, text="Seleccionar Cuota", font=FONTS["label"]).pack(anchor="w")
        self.cuota_selector = ctk.CTkOptionMenu(
            self.container, values=list(self.cuota_map.keys()),
            command=self._on_cuota_selected, width=440, height=36
        )
        self.cuota_selector.pack(fill="x", pady=(5, 12))
        
        self.info_frame = ctk.CTkFrame(self.container, fg_color=COLORS["row_alt"], corner_radius=8)
        self.info_frame.pack(fill="x", pady=(0, 15))
        
        self.lbl_valor = ctk.CTkLabel(self.info_frame, text="Valor de cuota: $0", font=FONTS["body"])
        self.lbl_valor.pack(anchor="w", padx=12, pady=(10, 2))
        
        self.lbl_pagado = ctk.CTkLabel(self.info_frame, text="Pagado: $0", font=FONTS["body"], text_color=COLORS["success"])
        self.lbl_pagado.pack(anchor="w", padx=12, pady=2)
        
        self.lbl_pendiente = ctk.CTkLabel(self.info_frame, text="Pendiente: $0", font=FONTS["body_bold"], text_color=COLORS["error"])
        self.lbl_pendiente.pack(anchor="w", padx=12, pady=(2, 10))
        
        ctk.CTkLabel(self.container, text="Monto a Pagar", font=FONTS["label"]).pack(anchor="w", pady=(0, 5))
        self.monto_entry = ctk.CTkEntry(self.container, width=440, height=36, font=FONTS["input"])
        self.monto_entry.pack(fill="x", pady=(0, 5))
        self.err_monto = ctk.CTkLabel(self.container, text="", text_color=COLORS["error"], font=FONTS["small"])
        self.err_monto.pack(anchor="w", pady=(0, 5))
        
    def _on_cuota_selected(self, choice: str):
        self.selected_cuota = self.cuota_map.get(choice)
        if not self.selected_cuota:
            return
            
        pagos = self.pago_service.obtener_pagos_cuota(self.selected_cuota.id)
        pagado = sum((p.monto for p in pagos), start=Decimal("0"))
        pendiente = (self.selected_cuota.monto - pagado).quantize(Decimal('0.01'))
        
        self.lbl_valor.configure(text=f"Valor de cuota: {formato_moneda(self.selected_cuota.monto)}")
        self.lbl_pagado.configure(text=f"Pagado: {formato_moneda(pagado)}")
        self.lbl_pendiente.configure(text=f"Pendiente: {formato_moneda(pendiente)}")
        
        self.monto_entry.delete(0, 'end')
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
            self.pago_service.registrar_pago(
                credito_id=self.credito.id,
                cuota_id=self.selected_cuota.id,
                monto=monto
            )
            self.on_save()
            self.destroy()
        except CrediNodaError as e:
            self.err_monto.configure(text=str(e))
        except Exception as e:
            self.err_monto.configure(text=f"Error al registrar pago: {str(e)}")
