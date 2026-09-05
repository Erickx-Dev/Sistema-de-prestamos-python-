from datetime import date
from decimal import Decimal
import customtkinter as ctk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Patch
import matplotlib.ticker as ticker

from credito_app.ui.theme import COLORS, FONTS
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha
from credito_app.ui.components.header import SectionHeader
from credito_app.ui.components.cards import MetricCard
from credito_app.ui.components.notifications import NotificationBar
from credito_app.modules.excepciones import CrediNodaError, DatosInvalidosError


class ReportesView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS["bg_main"])
        self.app = app

        self.current_desde: date | None = None
        self.current_hasta: date | None = None

        self.notification = NotificationBar(self)
        self._build_ui()
        self._set_preset("Todos")

    def _build_ui(self):
        SectionHeader(self, title="Reportes", subtitle="Métricas y rendimiento financiero").pack(
            fill="x", padx=10, pady=(0, 15)
        )

        # -------------------------------------------------------------
        # 1. FILTROS TEMPORALES
        # -------------------------------------------------------------
        self.filter_card = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=10)
        self.filter_card.pack(fill="x", padx=10, pady=(0, 20))

        filter_inner = ctk.CTkFrame(self.filter_card, fg_color="transparent")
        filter_inner.pack(fill="x", padx=15, pady=12)

        # Fila 1: Botones de preajuste
        presets_row = ctk.CTkFrame(filter_inner, fg_color="transparent")
        presets_row.pack(fill="x", pady=(0, 10))

        lbl_filtro = ctk.CTkLabel(
            presets_row,
            text="📅 Filtro temporal:",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        )
        lbl_filtro.pack(side="left", padx=(0, 15))

        self.preset_var = ctk.StringVar(value="Todos")
        self.preset_segmented = ctk.CTkSegmentedButton(
            presets_row,
            values=["Todos", "Hoy", "Esta Semana", "Este Mes", "Año en curso", "Personalizado"],
            variable=self.preset_var,
            command=self._on_preset_change,
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            font=FONTS["small"],
        )
        self.preset_segmented.pack(side="left", fill="x", expand=True)

        # Fila 2: Rango personalizado e indicador de período activo
        custom_row = ctk.CTkFrame(filter_inner, fg_color="transparent")
        custom_row.pack(fill="x")

        self.custom_inputs_frame = ctk.CTkFrame(custom_row, fg_color="transparent")
        self.custom_inputs_frame.pack(side="left")

        lbl_desde = ctk.CTkLabel(
            self.custom_inputs_frame, text="Desde:", font=FONTS["small"], text_color=COLORS["text_secondary"]
        )
        lbl_desde.pack(side="left", padx=(0, 5))

        self.entry_desde = ctk.CTkEntry(
            self.custom_inputs_frame, placeholder_text="AAAA-MM-DD", width=110, font=FONTS["small"]
        )
        self.entry_desde.pack(side="left", padx=(0, 10))
        self.entry_desde.bind("<Return>", lambda e: self._aplicar_rango_personalizado())

        lbl_hasta = ctk.CTkLabel(
            self.custom_inputs_frame, text="Hasta:", font=FONTS["small"], text_color=COLORS["text_secondary"]
        )
        lbl_hasta.pack(side="left", padx=(0, 5))

        self.entry_hasta = ctk.CTkEntry(
            self.custom_inputs_frame, placeholder_text="AAAA-MM-DD", width=110, font=FONTS["small"]
        )
        self.entry_hasta.pack(side="left", padx=(0, 10))
        self.entry_hasta.bind("<Return>", lambda e: self._aplicar_rango_personalizado())

        self.btn_aplicar = ctk.CTkButton(
            self.custom_inputs_frame,
            text="Aplicar",
            width=80,
            command=self._aplicar_rango_personalizado,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["button"],
        )
        self.btn_aplicar.pack(side="left", padx=(0, 15))

        self.lbl_resumen_periodo = ctk.CTkLabel(
            custom_row,
            text="Período: Histórico completo",
            font=FONTS["body_bold"],
            text_color=COLORS["primary"],
        )
        self.lbl_resumen_periodo.pack(side="right")

        # -------------------------------------------------------------
        # 2. TARJETAS MÉTRICAS
        # -------------------------------------------------------------
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(0, 15))

        self.card_activos = MetricCard(row1, "Créditos Activos", "0", icon="📋", color=COLORS["primary"])
        self.card_activos.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_pagados = MetricCard(row1, "Créditos Pagados", "0", icon="✅", color=COLORS["success"])
        self.card_pagados.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_total = MetricCard(row1, "Total Créditos", "0", icon="📁")
        self.card_total.pack(side="left", expand=True, fill="both")

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 15))

        self.card_capital = MetricCard(row2, "Capital Prestado", "$0", icon="💰", color=COLORS["primary"])
        self.card_capital.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_intereses = MetricCard(row2, "Intereses Generados", "$0", icon="📈", color=COLORS["warning"])
        self.card_intereses.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_recibido = MetricCard(row2, "Pagos Recibidos", "$0", icon="💵", color=COLORS["success"])
        self.card_recibido.pack(side="left", expand=True, fill="both")

        # Fila 3: Métricas Financieras Avanzadas
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=(0, 20))

        self.card_morosidad = MetricCard(
            row3, "Tasa de Morosidad", "0.0%", icon="⚠️", color=COLORS["success"]
        )
        self.card_morosidad.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_ganancia = MetricCard(
            row3, "Ganancia Líquida", "$0", icon="💎", color=COLORS["success"]
        )
        self.card_ganancia.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_ticket = MetricCard(
            row3, "Ticket Promedio", "$0", icon="🎯", color=COLORS["primary"]
        )
        self.card_ticket.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.card_plazo = MetricCard(
            row3, "Plazo Promedio", "0 meses", icon="⏱️", color=COLORS["secondary"]
        )
        self.card_plazo.pack(side="left", expand=True, fill="both")

        # -------------------------------------------------------------
        # 3. SECCIÓN DE GRÁFICOS VISUALES
        # -------------------------------------------------------------
        lbl_graficos = ctk.CTkLabel(
            self,
            text="📊 Rendimiento y Estado de Cartera",
            font=FONTS["heading2"],
            text_color=COLORS["text_primary"],
        )
        lbl_graficos.pack(anchor="w", padx=10, pady=(0, 12))

        self.charts_row = ctk.CTkFrame(self, fg_color="transparent")
        self.charts_row.pack(fill="x", padx=10, pady=(0, 20))
        self.charts_row.grid_columnconfigure(0, weight=3)
        self.charts_row.grid_columnconfigure(1, weight=2)

        # Tarjeta Izquierda: Gráfico de Barras
        self.card_chart_bar = ctk.CTkFrame(self.charts_row, fg_color=COLORS["bg_panel"], corner_radius=12)
        self.card_chart_bar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        bar_header = ctk.CTkFrame(self.card_chart_bar, fg_color="transparent")
        bar_header.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(
            bar_header,
            text="Recaudos Cobrados vs. Proyección Esperada",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            bar_header,
            text="Comparativa semanal de ingresos reales frente a cuotas programadas",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        self.fig_bar = Figure(figsize=(5.5, 3.4), dpi=100, facecolor=COLORS["bg_panel"])
        self.ax_bar = self.fig_bar.add_subplot(111)
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=self.card_chart_bar)
        self.canvas_bar.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Tarjeta Derecha: Gráfico Donut
        self.card_chart_donut = ctk.CTkFrame(self.charts_row, fg_color=COLORS["bg_panel"], corner_radius=12)
        self.card_chart_donut.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        donut_header = ctk.CTkFrame(self.card_chart_donut, fg_color="transparent")
        donut_header.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(
            donut_header,
            text="Distribución del Estado de Cartera",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            donut_header,
            text="Proporción de créditos al día, en mora y saldados",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        self.fig_donut = Figure(figsize=(4.5, 3.4), dpi=100, facecolor=COLORS["bg_panel"])
        self.ax_donut = self.fig_donut.add_subplot(111)
        self.canvas_donut = FigureCanvasTkAgg(self.fig_donut, master=self.card_chart_donut)
        self.canvas_donut.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _notify(self, message: str, tipo: str = "error"):
        if hasattr(self.app, "show_notification"):
            self.app.show_notification(message, tipo)
        elif hasattr(self, "notification"):
            if tipo == "error":
                self.notification.show_error(message)
            elif tipo == "warning":
                self.notification.show_warning(message)
            else:
                self.notification.show_success(message)

    def _on_preset_change(self, selected_preset: str):
        self._set_preset(selected_preset)

    def _set_preset(self, preset: str):
        if preset == "Personalizado":
            self.entry_desde.configure(state="normal")
            self.entry_hasta.configure(state="normal")
            self.btn_aplicar.configure(state="normal")
            return

        try:
            fecha_desde, fecha_hasta = self.app.reporte_service.calcular_rango_fechas(preset)
            self._update_date_entries(fecha_desde, fecha_hasta)
            self._load_data(fecha_desde, fecha_hasta)
        except CrediNodaError as e:
            self._notify(str(e), "error")

    def _update_date_entries(self, fecha_desde: date | None, fecha_hasta: date | None):
        self.entry_desde.configure(state="normal")
        self.entry_hasta.configure(state="normal")
        self.entry_desde.delete(0, "end")
        self.entry_hasta.delete(0, "end")

        if fecha_desde:
            self.entry_desde.insert(0, fecha_desde.isoformat())
        if fecha_hasta:
            self.entry_hasta.insert(0, fecha_hasta.isoformat())

    def _aplicar_rango_personalizado(self):
        txt_desde = self.entry_desde.get().strip()
        txt_hasta = self.entry_hasta.get().strip()

        fecha_desde = None
        fecha_hasta = None

        if txt_desde:
            try:
                fecha_desde = date.fromisoformat(txt_desde)
            except ValueError:
                self._notify(
                    "Fecha inicial inválida. Use el formato AAAA-MM-DD (ej: 2026-09-01).", "error"
                )
                return

        if txt_hasta:
            try:
                fecha_hasta = date.fromisoformat(txt_hasta)
            except ValueError:
                self._notify(
                    "Fecha final inválida. Use el formato AAAA-MM-DD (ej: 2026-09-01).", "error"
                )
                return

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            self._notify(
                "La fecha inicial no puede ser posterior a la fecha final.", "error"
            )
            return

        self.preset_var.set("Personalizado")
        self.preset_segmented.set("Personalizado")
        self._load_data(fecha_desde, fecha_hasta)

    def _load_data(self, fecha_desde: date | None = None, fecha_hasta: date | None = None):
        try:
            self.current_desde = fecha_desde
            self.current_hasta = fecha_hasta

            # 1. Cargar métricas consolidadas
            metricas = self.app.reporte_service.obtener_metricas(fecha_desde, fecha_hasta)

            self.card_activos.update_value(str(metricas["activos"]))
            self.card_pagados.update_value(str(metricas["pagados"]))
            self.card_total.update_value(str(metricas["total"]))

            self.card_capital.update_value(formato_moneda(metricas["capital_prestado"]))
            self.card_intereses.update_value(formato_moneda(metricas["intereses_generados"]))
            self.card_recibido.update_value(formato_moneda(metricas["pagos_recibidos"]))

            # Fila 3: Métricas Financieras Avanzadas
            tasa_mora = metricas.get("tasa_morosidad", Decimal("0.00"))
            color_mora = COLORS["error"] if tasa_mora > Decimal("0") else COLORS["success"]
            self.card_morosidad.update_value(f"{tasa_mora}%", color=color_mora)

            intereses_cobrados = metricas.get("intereses_cobrados", Decimal("0"))
            self.card_ganancia.update_value(formato_moneda(intereses_cobrados))

            ticket_prom = metricas.get("ticket_promedio", Decimal("0"))
            self.card_ticket.update_value(formato_moneda(ticket_prom))

            plazo_prom = metricas.get("plazo_promedio", Decimal("0.0"))
            txt_plazo = f"{plazo_prom} mes" if plazo_prom == Decimal("1.0") else f"{plazo_prom} meses"
            self.card_plazo.update_value(txt_plazo)

            self._update_periodo_label(fecha_desde, fecha_hasta)

            # 2. Cargar y renderizar gráficos
            self._update_charts(fecha_desde, fecha_hasta)

        except CrediNodaError as e:
            self._notify(str(e), "error")
        except Exception:
            self._notify("Ocurrió un error inesperado al actualizar los reportes.", "error")

    def _update_periodo_label(self, fecha_desde: date | None, fecha_hasta: date | None):
        if not fecha_desde and not fecha_hasta:
            self.lbl_resumen_periodo.configure(text="Período: Histórico completo")
        elif fecha_desde and fecha_hasta:
            if fecha_desde == fecha_hasta:
                self.lbl_resumen_periodo.configure(text=f"Período: {formato_fecha(fecha_desde)}")
            else:
                self.lbl_resumen_periodo.configure(
                    text=f"Período: {formato_fecha(fecha_desde)} al {formato_fecha(fecha_hasta)}"
                )
        elif fecha_desde:
            self.lbl_resumen_periodo.configure(text=f"Período: Desde {formato_fecha(fecha_desde)}")
        elif fecha_hasta:
            self.lbl_resumen_periodo.configure(text=f"Período: Hasta {formato_fecha(fecha_hasta)}")

    def _update_charts(self, fecha_desde: date | None, fecha_hasta: date | None):
        distribucion = self.app.reporte_service.obtener_distribucion_cartera(fecha_desde, fecha_hasta)
        semanas = self.app.reporte_service.obtener_recaudo_vs_proyeccion_semanal(fecha_desde, fecha_hasta)

        # -------------------------------------------------------------
        # A. Actualizar Gráfico de Barras (Recaudos vs Proyección)
        # -------------------------------------------------------------
        self.ax_bar.clear()
        self.ax_bar.set_facecolor(COLORS["bg_panel"])

        if not semanas:
            self.ax_bar.text(
                0.5, 0.5, "Sin datos para graficar en este período",
                ha='center', va='center', transform=self.ax_bar.transAxes,
                color=COLORS["text_secondary"], fontfamily="Segoe UI", fontsize=11
            )
            self.ax_bar.set_xticks([])
            self.ax_bar.set_yticks([])
        else:
            etiquetas = [s["etiqueta"] for s in semanas]
            proyectados = [float(s["proyectado"]) for s in semanas]
            recaudados = [float(s["recaudado"]) for s in semanas]

            todos_cero = all(p == 0 for p in proyectados) and all(r == 0 for r in recaudados)
            if todos_cero:
                self.ax_bar.text(
                    0.5, 0.5, "Sin cuotas ni recaudos registrados en este período",
                    ha='center', va='center', transform=self.ax_bar.transAxes,
                    color=COLORS["text_secondary"], fontfamily="Segoe UI", fontsize=11
                )
                self.ax_bar.set_xticks([])
                self.ax_bar.set_yticks([])
            else:
                x = list(range(len(semanas)))
                width = 0.35

                self.ax_bar.bar(
                    [i - width / 2 for i in x],
                    proyectados,
                    width,
                    label="Proyectado",
                    color="#94A3B8",
                    edgecolor="none",
                )
                self.ax_bar.bar(
                    [i + width / 2 for i in x],
                    recaudados,
                    width,
                    label="Recaudado",
                    color=COLORS["primary"],
                    edgecolor="none",
                )

                self.ax_bar.set_xticks(x)
                self.ax_bar.set_xticklabels(
                    etiquetas, fontfamily="Segoe UI", fontsize=8, color=COLORS["text_secondary"]
                )

                def currency_formatter(val, pos):
                    if abs(val) >= 1_000_000:
                        return f"${val * 1e-6:.1f}M".replace(".0M", "M")
                    elif abs(val) >= 1_000:
                        return f"${val * 1e-3:.0f}k"
                    return f"${int(val)}"

                self.ax_bar.yaxis.set_major_formatter(ticker.FuncFormatter(currency_formatter))
                self.ax_bar.tick_params(axis='y', labelsize=8, colors=COLORS["text_secondary"])
                self.ax_bar.tick_params(axis='x', length=0)
                self.ax_bar.grid(axis='y', linestyle='--', alpha=0.35, color="#CBD5E1")
                self.ax_bar.legend(
                    loc="upper left", frameon=False, prop={'family': 'Segoe UI', 'size': 9}
                )

        for spine in ['top', 'right']:
            self.ax_bar.spines[spine].set_visible(False)
        self.ax_bar.spines['left'].set_color("#E2E8F0")
        self.ax_bar.spines['bottom'].set_color("#E2E8F0")

        self.fig_bar.tight_layout()
        self.canvas_bar.draw()

        # -------------------------------------------------------------
        # B. Actualizar Gráfico Donut (Distribución de Cartera)
        # -------------------------------------------------------------
        self.ax_donut.clear()
        self.ax_donut.set_facecolor(COLORS["bg_panel"])

        al_dia = distribucion["al_dia"]
        en_mora = distribucion["en_mora"]
        saldados = distribucion["saldados"]
        total_creditos = distribucion["total_creditos"]

        if total_creditos == 0:
            self.ax_donut.text(
                0.5, 0.5, "Sin créditos en este período",
                ha='center', va='center', transform=self.ax_donut.transAxes,
                color=COLORS["text_secondary"], fontfamily="Segoe UI", fontsize=11
            )
            self.ax_donut.set_xticks([])
            self.ax_donut.set_yticks([])
        else:
            categorias = [
                ("Al día", al_dia["cantidad"], COLORS["primary"]),
                ("En mora", en_mora["cantidad"], COLORS["error"]),
                ("Saldados", saldados["cantidad"], COLORS["success"]),
            ]
            wedges_data = [(cat, cant, col) for cat, cant, col in categorias if cant > 0]
            vals = [w[1] for w in wedges_data]
            cols = [w[2] for w in wedges_data]

            wedges, texts, autotexts = self.ax_donut.pie(
                vals,
                colors=cols,
                autopct='%1.0f%%',
                pctdistance=0.72,
                startangle=90,
                wedgeprops=dict(width=0.45, edgecolor=COLORS["bg_panel"], linewidth=2),
            )
            for t in autotexts:
                t.set_color("white")
                t.set_fontsize(9)
                t.set_fontweight("bold")
                t.set_family("Segoe UI")

            self.ax_donut.text(
                0, 0, f"{total_creditos}\nCréditos",
                ha='center', va='center',
                fontfamily='Segoe UI', fontsize=11, fontweight='bold',
                color=COLORS["text_primary"],
            )

            handles = [
                Patch(facecolor=COLORS["primary"], label=f"Al día ({al_dia['cantidad']})"),
                Patch(facecolor=COLORS["error"], label=f"En mora ({en_mora['cantidad']})"),
                Patch(facecolor=COLORS["success"], label=f"Saldados ({saldados['cantidad']})"),
            ]
            self.ax_donut.legend(
                handles=handles,
                loc="center",
                bbox_to_anchor=(0.5, -0.05),
                ncol=3,
                frameon=False,
                prop={'family': 'Segoe UI', 'size': 8.5},
            )

        self.fig_donut.tight_layout()
        self.canvas_donut.draw()

    def refresh(self):
        self._load_data(self.current_desde, self.current_hasta)

    def destroy(self):
        try:
            import matplotlib.pyplot as plt
            if hasattr(self, 'fig_bar'):
                plt.close(self.fig_bar)
            if hasattr(self, 'fig_donut'):
                plt.close(self.fig_donut)
        except Exception:
            pass
        super().destroy()
