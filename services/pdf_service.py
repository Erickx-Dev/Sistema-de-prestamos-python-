import os
import io
import re
import platform
import subprocess
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether
)

from credito_app.config import BASE_DIR
from credito_app.ui.utils.formatters import formato_moneda, formato_fecha, formato_porcentaje
from credito_app.modules.excepciones import CrediNodaError

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class PDFServiceError(CrediNodaError):
    """Excepción para errores ocurridos durante la generación o manipulación de PDFs."""
    pass


class PDFService:
    """
    Servicio para la generación y apertura de documentos PDF del sistema CrediNoda.
    Maneja el diseño de comprobantes de pago, tablas de amortización y documentos contractuales.
    """

    def __init__(self, default_output_dir: Optional[Path] = None):
        self.output_dir = default_output_dir or (BASE_DIR / "comprobantes")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitizar_nombre_archivo(nombre: str) -> str:
        """Elimina caracteres inválidos para nombres de archivo en Windows y Unix."""
        limpio = re.sub(r'[\\/*?:"<>|]', "", nombre)
        return re.sub(r"\s+", "_", limpio.strip())

    def generar_comprobante_pago(self, datos: dict, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Genera un comprobante de pago / recibo de caja en formato PDF a partir de los datos consolidados.

        Args:
            datos: Diccionario con la información del pago, crédito, cuota y cliente.
            output_path: Ruta destino opcional donde guardar el archivo PDF.

        Returns:
            Path al archivo PDF generado.
        """
        try:
            pago_id = datos["pago_id"]
            numero_recibo = datos.get("numero_recibo", f"REC-{pago_id:05d}")
            cliente_nombre = datos.get("cliente_nombre", "Cliente")
            fecha_pago = datos.get("fecha_pago", date.today())
            fecha_str = fecha_pago.strftime("%Y%m%d") if isinstance(fecha_pago, (date, datetime)) else str(fecha_pago)

            if output_path is None:
                cliente_slug = self._sanitizar_nombre_archivo(cliente_nombre)
                nombre_archivo = f"Recibo_{numero_recibo}_{cliente_slug}_{fecha_str}.pdf"
                destino = self.output_dir / nombre_archivo
            else:
                destino = Path(output_path)
                destino.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                str(destino),
                pagesize=letter,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36
            )

            elementos = self._construir_elementos_comprobante(datos)
            doc.build(elementos)

            return destino

        except Exception as e:
            raise PDFServiceError(f"Error al generar el comprobante PDF: {str(e)}") from e

    def _construir_elementos_comprobante(self, datos: dict) -> list:
        """Construye los elementos Platypus (Flowables) para maquetar el comprobante."""
        styles = getSampleStyleSheet()

        # Estilos tipográficos personalizados
        style_header_title = ParagraphStyle(
            "HeaderTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A")
        )

        style_header_subtitle = ParagraphStyle(
            "HeaderSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569")
        )

        style_badge_num = ParagraphStyle(
            "BadgeNum",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=2,  # Right
            textColor=colors.HexColor("#1E3A8A")
        )

        style_badge_meta = ParagraphStyle(
            "BadgeMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            alignment=2,  # Right
            textColor=colors.HexColor("#64748B")
        )

        style_sec_title = ParagraphStyle(
            "SecTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1E293B")
        )

        style_cell_lbl = ParagraphStyle(
            "CellLbl",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155")
        )

        style_cell_val = ParagraphStyle(
            "CellVal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0F172A")
        )

        style_th = ParagraphStyle(
            "TableHead",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )

        style_td = ParagraphStyle(
            "TableData",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1E293B")
        )

        style_td_bold = ParagraphStyle(
            "TableDataBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A")
        )

        style_legal = ParagraphStyle(
            "LegalText",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            alignment=1  # Center
        )

        elementos = []

        # -------------------------------------------------------------
        # 1. ENCABEZADO DEL DOCUMENTO
        # -------------------------------------------------------------
        numero_recibo = datos.get("numero_recibo", f"REC-{datos['pago_id']:05d}")
        fecha_pago = datos.get("fecha_pago", date.today())
        fecha_pago_fmt = formato_fecha(fecha_pago) if isinstance(fecha_pago, date) else str(fecha_pago)
        emision_ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

        header_left = [
            Paragraph("CREDINODA", style_header_title),
            Paragraph("Sistema de Administración y Cobranza de Créditos", style_header_subtitle),
            Paragraph("Soporte Oficial de Recaudo y Amortización", style_header_subtitle)
        ]

        header_right = [
            Paragraph("COMPROBANTE DE PAGO", style_badge_num),
            Paragraph(f"N°: <b>{numero_recibo}</b>", style_badge_num),
            Paragraph(f"Fecha del Pago: <b>{fecha_pago_fmt}</b>", style_badge_meta),
            Paragraph(f"Generado: {emision_ahora}", style_badge_meta)
        ]

        header_table = Table([[header_left, header_right]], colWidths=[330, 210])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 1.5, colors.HexColor("#2563EB")),
        ]))
        elementos.append(header_table)
        elementos.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 2. SECCIONES EN PARALELO: CLIENTE & CRÉDITO
        # -------------------------------------------------------------
        # Bloque Cliente
        cliente_content = [
            [Paragraph("DATOS DEL TITULAR / CLIENTE", style_sec_title), ""],
            [Paragraph("Nombre:", style_cell_lbl), Paragraph(str(datos.get("cliente_nombre", "-")), style_cell_val)],
            [Paragraph("Documento / C.C.:", style_cell_lbl), Paragraph(str(datos.get("cliente_documento", "-")), style_cell_val)],
            [Paragraph("Teléfono:", style_cell_lbl), Paragraph(str(datos.get("cliente_telefono", "-")), style_cell_val)],
        ]
        tabla_cliente = Table(cliente_content, colWidths=[100, 160])
        tabla_cliente.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (1, 0), 1, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#F8FAFC")),
        ]))

        # Bloque Crédito
        credito_id = datos.get("credito_id", "-")
        capital_str = formato_moneda(datos.get("credito_capital", 0))
        frecuencia_str = str(datos.get("frecuencia_pago", "-")).title()
        plazo_str = f"{datos.get('plazo_meses', '-')} meses"
        tasa_str = formato_porcentaje(datos.get("tasa_mensual", Decimal("0")))

        credito_content = [
            [Paragraph("DATOS DEL CRÉDITO", style_sec_title), ""],
            [Paragraph("Crédito N°:", style_cell_lbl), Paragraph(f"#{credito_id}", style_cell_val)],
            [Paragraph("Capital Inicial:", style_cell_lbl), Paragraph(capital_str, style_cell_val)],
            [Paragraph("Frecuencia / Plazo:", style_cell_lbl), Paragraph(f"{frecuencia_str} ({plazo_str})", style_cell_val)],
            [Paragraph("Tasa Pactada:", style_cell_lbl), Paragraph(tasa_str, style_cell_val)],
        ]
        tabla_credito = Table(credito_content, colWidths=[100, 160])
        tabla_credito.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (1, 0), 1, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#F8FAFC")),
        ]))

        info_general = Table([[tabla_cliente, tabla_credito]], colWidths=[270, 270])
        info_general.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor("#E2E8F0")),
            ("BOX", (1, 0), (1, 0), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
        ]))
        elementos.append(info_general)
        elementos.append(Spacer(1, 14))

        # -------------------------------------------------------------
        # 3. DETALLE DE LA CUOTA Y ABONO REALIZADO
        # -------------------------------------------------------------
        num_cuota = datos.get("numero_cuota", 1)
        tot_cuotas = datos.get("cuotas_total", "")
        cuota_desc = f"Cuota #{num_cuota}" + (f" de {tot_cuotas}" if tot_cuotas else "")
        vencimiento_fmt = formato_fecha(datos["cuota_fecha_vencimiento"]) if "cuota_fecha_vencimiento" in datos else "-"
        monto_cuota_str = formato_moneda(datos.get("cuota_monto", 0))
        monto_abono_str = formato_moneda(datos.get("pago_monto", 0))
        saldo_cuota_despues_str = formato_moneda(datos.get("saldo_cuota_despues", 0))
        estado_cuota = str(datos.get("cuota_estado", "PENDIENTE")).upper()
        estado_cuota_badge = "SALDADA (PAGADA)" if estado_cuota == "PAGADA" else f"PARCIAL (Saldo: {saldo_cuota_despues_str})"

        tabla_detalle_data = [
            [
                Paragraph("Concepto de Cobro", style_th),
                Paragraph("Fecha Venc.", style_th),
                Paragraph("Valor Cuota", style_th),
                Paragraph("Monto Abonado", style_th),
                Paragraph("Estado Cuota", style_th),
            ],
            [
                Paragraph(cuota_desc, style_td_bold),
                Paragraph(vencimiento_fmt, style_td),
                Paragraph(monto_cuota_str, style_td),
                Paragraph(f"<b>{monto_abono_str}</b>", style_td_bold),
                Paragraph(estado_cuota_badge, style_td),
            ]
        ]

        tabla_detalle = Table(tabla_detalle_data, colWidths=[130, 90, 100, 110, 110])
        tabla_detalle.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (3, 1), (3, 1), colors.HexColor("#EFF6FF")),  # Resaltar abono
        ]))
        elementos.append(tabla_detalle)
        elementos.append(Spacer(1, 14))

        # -------------------------------------------------------------
        # 4. BALANCE FINANCIERO DE LA OBLIGACIÓN POST-PAGO
        # -------------------------------------------------------------
        saldo_credito_restante = datos.get("saldo_credito_restante", Decimal("0"))
        total_pagado_credito = datos.get("total_pagado_credito", Decimal("0"))
        credito_total_pagar = datos.get("credito_total_pagar", Decimal("0"))
        porcentaje_pagado = datos.get("porcentaje_pagado_credito", Decimal("0"))

        balance_data = [
            [
                Paragraph("<b>Total Acordado a Pagar:</b>", style_cell_lbl),
                Paragraph(formato_moneda(credito_total_pagar), style_cell_val),
                Paragraph("<b>Total Recaudado Acumulado:</b>", style_cell_lbl),
                Paragraph(formato_moneda(total_pagado_credito), style_cell_val),
            ],
            [
                Paragraph("<b>Saldo Pendiente Total:</b>", style_cell_lbl),
                Paragraph(f"<font color='#B91C1C'><b>{formato_moneda(saldo_credito_restante)}</b></font>", style_cell_val),
                Paragraph("<b>Avance de Amortización:</b>", style_cell_lbl),
                Paragraph(f"<b>{porcentaje_pagado}%</b>", style_cell_val),
            ]
        ]
        tabla_balance = Table(balance_data, colWidths=[140, 130, 140, 130])
        tabla_balance.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        elementos.append(tabla_balance)
        elementos.append(Spacer(1, 18))

        # -------------------------------------------------------------
        # 5. CÓDIGO QR Y FIRMAS DE VALIDACIÓN
        # -------------------------------------------------------------
        qr_flowable = None
        if QRCODE_AVAILABLE:
            try:
                qr_text = (
                    f"CREDINODA | {numero_recibo}\n"
                    f"Cliente: {datos.get('cliente_nombre')}\n"
                    f"Doc: {datos.get('cliente_documento')}\n"
                    f"Credito: #{credito_id} | Cuota: {num_cuota}\n"
                    f"Abono: {formato_moneda(datos.get('pago_monto', 0))}\n"
                    f"Saldo Pend: {formato_moneda(saldo_credito_restante)}\n"
                    f"Fecha: {fecha_pago_fmt}"
                )
                qr_img = qrcode.make(qr_text, box_size=3, border=1)
                img_buffer = io.BytesIO()
                qr_img.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                qr_flowable = Image(img_buffer, width=65, height=65)
            except Exception:
                qr_flowable = None

        firma_cliente = [
            Spacer(1, 35),
            Paragraph("___________________________________", style_cell_lbl),
            Paragraph("<b>Firma del Prestatario / Cliente</b>", style_cell_val),
            Paragraph(f"C.C. {datos.get('cliente_documento', '__________')}", style_cell_val)
        ]

        firma_cobrador = [
            Spacer(1, 35),
            Paragraph("___________________________________", style_cell_lbl),
            Paragraph("<b>Recibido Conforme / Sello</b>", style_cell_val),
            Paragraph("CrediNoda Cobranza", style_cell_val)
        ]

        if qr_flowable:
            qr_col = [
                qr_flowable,
                Paragraph("<font size='6'>Validación Digital</font>", style_legal)
            ]
            firmas_data = [[firma_cliente, firma_cobrador, qr_col]]
            firmas_table = Table(firmas_data, colWidths=[220, 220, 100])
        else:
            firmas_data = [[firma_cliente, firma_cobrador]]
            firmas_table = Table(firmas_data, colWidths=[270, 270])

        firmas_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        bloque_inferior = KeepTogether([
            firmas_table,
            Spacer(1, 14),
            Paragraph(
                "Este recibo es el soporte oficial de descargo y amortización del crédito individual otorgado. "
                "Consérvelo para cualquier aclaración de saldo o paz y salvo.",
                style_legal
            )
        ])
        elementos.append(bloque_inferior)

        return elementos

    def abrir_documento(self, ruta_archivo: Union[str, Path]) -> bool:
        """
        Abre el archivo PDF generado en la aplicación predeterminada del sistema operativo.
        Soporta Windows, macOS y entornos Linux.

        Returns:
            True si se abrió exitosamente, False en caso contrario.
        """
        ruta = Path(ruta_archivo).resolve()
        if not ruta.exists():
            return False

        sistema = platform.system()
        try:
            if sistema == "Windows":
                os.startfile(str(ruta))
                return True
            elif sistema == "Darwin":
                subprocess.Popen(["open", str(ruta)])
                return True
            else:
                subprocess.Popen(["xdg-open", str(ruta)])
                return True
        except Exception:
            return False
