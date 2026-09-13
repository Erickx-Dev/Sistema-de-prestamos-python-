import customtkinter as ctk
from decimal import Decimal
from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha, formato_porcentaje
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.notifications import NotificationBar
from credito_app.ui.components.dialogs import ConfirmDialog
from credito_app.modules.credito import FrecuenciaPago
from credito_app.modules.excepciones import CrediNodaError
from credito_app.config import DEFAULT_MONTHLY_RATE
from credito_app.ui.utils.validators import validar_monto, parsear_monto, validar_entero_positivo


class CreditoView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app, cliente_id=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app
        self.target_cliente_id = cliente_id
        self._calculated_data = None
        self._cliente_map = {}
        
        self.notification = NotificationBar(self)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # Header
        SectionHeader(self, title="Nuevo Crédito").pack(fill="x", pady=(0, 20))
        
        # Form Panel
        self.form_panel = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=12)
        self.form_panel.pack(fill="x", padx=20, pady=(0, 20))
        
        form_inner = ctk.CTkFrame(self.form_panel, fg_color="transparent")
        form_inner.pack(fill="x", padx=20, pady=20)
        
        # Cliente
        ctk.CTkLabel(form_inner, text="Cliente", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 5))
        self.cliente_var = ctk.StringVar(value="Seleccionar cliente...")
        self.cliente_combo = ctk.CTkOptionMenu(
            form_inner, 
            variable=self.cliente_var, 
            font=FONTS["body_bold"], 
            dropdown_font=FONTS["body"],
            fg_color="#FFFFFF",
            text_color=COLORS["text_primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            dropdown_fg_color=COLORS["bg_panel"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_hover_color=COLORS["row_hover"],
            dynamic_resizing=False,
            anchor="w",
            height=38,
        )
        self.cliente_combo.pack(fill="x", pady=(0, 15))
        
        # Capital
        ctk.CTkLabel(form_inner, text="Capital", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 5))
        self.capital_entry = ctk.CTkEntry(form_inner, placeholder_text="Ej: 1000000", font=FONTS["body"], fg_color=COLORS["input_bg"], border_color=COLORS["border"])
        self.capital_entry.pack(fill="x", pady=(0, 15))
        
        # Tasa mensual
        ctk.CTkLabel(form_inner, text="Tasa mensual (%)", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 5))
        self.tasa_entry = ctk.CTkEntry(form_inner, font=FONTS["body"], fg_color=COLORS["input_bg"], border_color=COLORS["border"])
        self.tasa_entry.insert(0, str(int(DEFAULT_MONTHLY_RATE * 100)))
        self.tasa_entry.pack(fill="x", pady=(0, 15))
        
        # Plazo
        ctk.CTkLabel(form_inner, text="Plazo (meses)", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 5))
        self.plazo_entry = ctk.CTkEntry(form_inner, placeholder_text="Ej: 3", font=FONTS["body"], fg_color=COLORS["input_bg"], border_color=COLORS["border"])
        self.plazo_entry.pack(fill="x", pady=(0, 15))
        
        # Frecuencia
        ctk.CTkLabel(form_inner, text="Frecuencia", font=FONTS["body_bold"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 5))
        freq_frame = ctk.CTkFrame(form_inner, fg_color="transparent")
        freq_frame.pack(fill="x", pady=(0, 15))
        self.frecuencia_var = ctk.StringVar(value=FrecuenciaPago.SEMANAL.value)
        
        ctk.CTkRadioButton(freq_frame, text="Semanal", variable=self.frecuencia_var, value=FrecuenciaPago.SEMANAL.value, font=FONTS["body"]).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(freq_frame, text="Quincenal", variable=self.frecuencia_var, value=FrecuenciaPago.QUINCENAL.value, font=FONTS["body"]).pack(side="left")
        
        # Error label
        self.error_label = ctk.CTkLabel(form_inner, text="", text_color=COLORS["error"], font=FONTS["body"])
        self.error_label.pack(fill="x", pady=(0, 15))
        
        # Calcular button
        ctk.CTkButton(form_inner, text="Calcular", command=self._on_calcular, font=FONTS["body_bold"], fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"]).pack(fill="x", pady=(10, 0))
        
        # Summary Panel (Initially hidden)
        self.summary_panel = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=12)
        
        sum_inner = ctk.CTkFrame(self.summary_panel, fg_color="transparent")
        sum_inner.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(sum_inner, text="Resumen del Crédito", font=FONTS["h2"], text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 15))
        
        self.lbl_sum_capital = ctk.CTkLabel(sum_inner, text="Capital: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_sum_capital.pack(anchor="w", pady=2)
        
        self.lbl_sum_intereses = ctk.CTkLabel(sum_inner, text="Intereses: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_sum_intereses.pack(anchor="w", pady=2)
        
        self.lbl_sum_total = ctk.CTkLabel(sum_inner, text="Total a pagar: -", font=FONTS["body_bold"], text_color=COLORS["text_main"])
        self.lbl_sum_total.pack(anchor="w", pady=2)
        
        self.lbl_sum_cuotas = ctk.CTkLabel(sum_inner, text="Número de cuotas: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_sum_cuotas.pack(anchor="w", pady=2)
        
        self.lbl_sum_vcuota = ctk.CTkLabel(sum_inner, text="Valor aproximado de cuota: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_sum_vcuota.pack(anchor="w", pady=2)
        
        self.lbl_sum_freq = ctk.CTkLabel(sum_inner, text="Frecuencia: -", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self.lbl_sum_freq.pack(anchor="w", pady=2)
        
        btn_frame = ctk.CTkFrame(sum_inner, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=self._on_cancelar, font=FONTS["body"], fg_color=COLORS["border"], hover_color="#cccccc", text_color=COLORS["text_main"]).pack(side="left", expand=True, padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Crear Crédito", command=self._on_crear, font=FONTS["body_bold"], fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"]).pack(side="left", expand=True, padx=(10, 0))

    def _load_data(self):
        try:
            clientes = self.app.cliente_service.buscar_clientes("")
            self._cliente_map = {f"{c.nombre} ({c.documento})": c.id for c in clientes}
            
            if self._cliente_map:
                options = list(self._cliente_map.keys())
                self.cliente_combo.configure(values=options)
                
                selected_option = options[0]
                if self.target_cliente_id:
                    for name, c_id in self._cliente_map.items():
                        if c_id == self.target_cliente_id:
                            selected_option = name
                            break
                self.cliente_var.set(selected_option)
            else:
                self.cliente_combo.configure(values=["No hay clientes registrados"])
                self.cliente_var.set("No hay clientes registrados")
        except CrediNodaError as e:
            self.app.show_notification(str(e), "error")

    def _on_calcular(self):
        self.error_label.configure(text="")
        
        cliente_str = self.cliente_var.get()
        if cliente_str not in self._cliente_map:
            self.error_label.configure(text="Seleccione un cliente válido")
            self.summary_panel.pack_forget()
            return
            
        cliente_id = self._cliente_map[cliente_str]
        
        capital_str = self.capital_entry.get().strip()
        valido_capital, err_capital = validar_monto(capital_str)
        if not valido_capital:
            self.error_label.configure(text=err_capital)
            self.summary_panel.pack_forget()
            return
        capital = parsear_monto(capital_str)
        if capital <= 0:
            self.error_label.configure(text="El capital debe ser mayor a 0")
            self.summary_panel.pack_forget()
            return
            
        tasa_str = self.tasa_entry.get().strip().replace(",", ".")
        try:
            tasa_pct = Decimal(tasa_str)
            if tasa_pct <= 0:
                self.error_label.configure(text="La tasa debe ser mayor a 0")
                self.summary_panel.pack_forget()
                return
            tasa = tasa_pct / 100
        except Exception:
            self.error_label.configure(text="Tasa de interés inválida")
            self.summary_panel.pack_forget()
            return
            
        plazo_str = self.plazo_entry.get().strip()
        valido_plazo, err_plazo = validar_entero_positivo(plazo_str, "Plazo")
        if not valido_plazo:
            self.error_label.configure(text=err_plazo)
            self.summary_panel.pack_forget()
            return
        plazo = int(plazo_str)
        
        frecuencia_str = self.frecuencia_var.get()
        try:
            frecuencia = FrecuenciaPago(frecuencia_str)
        except Exception:
            self.error_label.configure(text="Frecuencia de pago inválida")
            self.summary_panel.pack_forget()
            return
        
        try:
            intereses = self.app.credito_service.calcular_intereses(capital, tasa, plazo)
            total = self.app.credito_service.calcular_total(capital, intereses)
            num_cuotas = self.app.credito_service.calcular_numero_cuotas(plazo, frecuencia)
            
            cuota_aprox = total / num_cuotas if num_cuotas > 0 else Decimal('0')
            
            cliente_nombre = cliente_str.split(" (")[0] if " (" in cliente_str else cliente_str

            self._calculated_data = {
                "cliente_id": cliente_id,
                "cliente_nombre": cliente_nombre,
                "capital": capital,
                "tasa": tasa,
                "plazo": plazo,
                "frecuencia": frecuencia,
                "intereses": intereses,
                "total": total,
                "num_cuotas": num_cuotas,
                "cuota_aprox": cuota_aprox
            }
            
            self.lbl_sum_capital.configure(text=f"Capital: {formato_moneda(capital)}")
            self.lbl_sum_intereses.configure(text=f"Intereses: {formato_moneda(intereses)}")
            self.lbl_sum_total.configure(text=f"Total a pagar: {formato_moneda(total)}")
            self.lbl_sum_cuotas.configure(text=f"Número de cuotas: {num_cuotas}")
            self.lbl_sum_vcuota.configure(text=f"Valor aproximado de cuota: {formato_moneda(cuota_aprox)}")
            self.lbl_sum_freq.configure(text=f"Frecuencia: {frecuencia.value}")
            
            self.summary_panel.pack(fill="x", padx=20, pady=(0, 20))
            
        except CrediNodaError as e:
            self.error_label.configure(text=str(e))
            self.summary_panel.pack_forget()
        except Exception as e:
            self.error_label.configure(text=f"Error al calcular: {str(e)}")
            self.summary_panel.pack_forget()
            
    def _on_cancelar(self):
        self.app.navigate("dashboard")
        
    def _on_crear(self):
        if not self._calculated_data:
            return
            
        def do_create():
            try:
                credito = self.app.credito_service.crear_credito(
                    cliente_id=self._calculated_data["cliente_id"],
                    capital=self._calculated_data["capital"],
                    plazo_meses=self._calculated_data["plazo"],
                    frecuencia=self._calculated_data["frecuencia"],
                    tasa_mensual=self._calculated_data["tasa"]
                )
                if hasattr(self.app, "notificar_cambio_datos"):
                    self.app.notificar_cambio_datos()
                self.app.show_notification("Crédito creado exitosamente", "success")
                self.app.navigate("credito_detail", credito_id=credito.id)
            except CrediNodaError as e:
                self.app.show_notification(str(e), "error")
            except Exception as e:
                self.app.show_notification(f"Error al crear crédito: {str(e)}", "error")
                
        cliente_nombre = self._calculated_data.get("cliente_nombre", "el cliente")
        msg = (
            f"¿Confirma la creación de este crédito para {cliente_nombre} por "
            f"{formato_moneda(self._calculated_data['capital'])} a pagar en "
            f"{self._calculated_data['num_cuotas']} cuotas?"
        )
        ConfirmDialog(self, title="Crear Crédito", message=msg, on_confirm=do_create)
