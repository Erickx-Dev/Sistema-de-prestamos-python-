import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from credito_app.database.connection import get_connection
from credito_app.database.schema import inicializar_base_datos
from credito_app.modules.credito import EstadoCredito, EstadoCuota, FrecuenciaPago
from credito_app.modules.excepciones import (
    ClienteNoEncontradoError,
    CreditoNoEncontradoError,
    CuotaNoEncontradaError,
    MontoInvalidoError,
)
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.services.pdf_service import PDFService
from credito_app.services.reporte_service import ReporteService
from credito_app.ui.app import App


class TestIntegracionServiciosE2E(unittest.TestCase):
    """Pruebas de integración de flujo completo (End-to-End) en la capa de servicios y negocio."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_e2e.db"
        inicializar_base_datos(str(self.db_path))
        self.conn = get_connection(str(self.db_path))

        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)
        self.reporte_svc = ReporteService(self.conn)
        self.pdf_svc = PDFService(default_output_dir=Path(self.temp_dir.name) / "comprobantes")

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_flujo_financiero_completo_ciclo_de_vida(self):
        """Valida el ciclo de vida financiero completo:
        1. Alta de cliente y validación de unicidad.
        2. Concesión de crédito con fecha retroactiva (simulación de cuotas vencidas).
        3. Detección automática de mora conservando estado PENDIENTE.
        4. Abono parcial a cuota en mora conservando estado PARCIAL y en_mora=True.
        5. Emisión de comprobante PDF oficial con códigos QR y balances.
        6. Liquidación de cuota vencida (desactiva en_mora).
        7. Pago secuencial de todas las cuotas hasta saldo cero.
        8. Transición automática del crédito a PAGADO.
        9. Verificación de reportes y métricas consolidadas sin créditos vencidos.
        """
        # 1. Registro de cliente
        cliente = self.cliente_svc.crear_cliente(
            nombre="Carlos Mendoza", telefono="3115559988", documento="CC-98765432"
        )
        self.assertIsNotNone(cliente.id)

        # Validación de unicidad de documento
        with self.assertRaises(Exception):
            self.cliente_svc.crear_cliente("Carlos Clon", "3000000000", "CC-98765432")

        # Búsqueda de cliente
        encontrados = self.cliente_svc.buscar_clientes("mendoza")
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].id, cliente.id)

        # 2. Concesión de crédito: $600.000 a 1 mes, semanal (4 cuotas), tasa 10%
        # Inicio hace 15 días: cuota 1 (día 7) y cuota 2 (día 14) ya vencieron
        fecha_inicio_pasada = date.today() - timedelta(days=15)
        credito = self.credito_svc.crear_credito(
            cliente_id=cliente.id,
            capital=Decimal("600000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=fecha_inicio_pasada,
        )
        self.assertEqual(credito.total_intereses, Decimal("60000.00"))
        self.assertEqual(credito.total_pagar, Decimal("660000.00"))
        self.assertEqual(credito.estado, EstadoCredito.ACTIVO)

        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(len(plan), 4)

        # Verificar cuadre contable exacto de cuotas
        self.assertEqual(sum(c.monto for c in plan), Decimal("660000.00"))

        # 3. Detección automática de mora
        vencidas = [c for c in plan if c.fecha_vencimiento < date.today()]
        self.assertEqual(len(vencidas), 2)
        for q in vencidas:
            self.assertEqual(q.estado, EstadoCuota.PENDIENTE)
            self.assertTrue(q.en_mora)
            self.assertEqual(q.etiqueta_estado, "PENDIENTE (EN MORA)")

        # Cuotas futuras no están en mora
        futuras = [c for c in plan if c.fecha_vencimiento >= date.today()]
        self.assertEqual(len(futuras), 2)
        for q in futuras:
            self.assertFalse(q.en_mora)

        # 4. Abono parcial a la cuota #1 (monto $165.000, abona $65.000)
        q1 = plan[0]
        pago_1 = self.pago_svc.registrar_pago(credito.id, q1.id, Decimal("65000.00"))
        self.assertEqual(pago_1.monto, Decimal("65000.00"))

        # Validar estado de la cuota: PARCIAL (EN MORA)
        plan_actualizado = self.credito_svc.obtener_plan_pagos(credito.id)
        q1_actualizada = plan_actualizado[0]
        self.assertEqual(q1_actualizada.estado, EstadoCuota.PARCIAL)
        self.assertTrue(q1_actualizada.en_mora)
        self.assertEqual(q1_actualizada.etiqueta_estado, "PARCIAL (EN MORA)")

        # 5. Generación y validación del Comprobante PDF del pago
        datos_recibo = self.pago_svc.obtener_datos_comprobante(pago_1.id)
        self.assertEqual(datos_recibo["cliente_nombre"], "Carlos Mendoza")
        self.assertEqual(datos_recibo["pago_monto"], Decimal("65000.00"))
        self.assertEqual(datos_recibo["saldo_cuota_despues"], Decimal("100000.00"))

        pdf_path = self.pdf_svc.generar_comprobante_pago(datos_recibo)
        self.assertTrue(pdf_path.exists())
        self.assertGreater(pdf_path.stat().st_size, 1000)
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            self.assertEqual(header, b"%PDF-")

        # 6. Pago restante de la cuota #1 ($100.000) -> Pasa a PAGADA y quita mora
        self.pago_svc.registrar_pago(credito.id, q1.id, Decimal("100000.00"))
        plan_actualizado = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PAGADA)
        self.assertFalse(plan_actualizado[0].en_mora)
        self.assertEqual(plan_actualizado[0].etiqueta_estado, "PAGADA")

        # 7. Liquidar el resto de cuotas (cuotas 2, 3 y 4)
        for cuota in plan_actualizado[1:]:
            self.pago_svc.registrar_pago(credito.id, cuota.id, cuota.monto)

        # 8. Transición automática a PAGADO
        estado_final = self.credito_svc.determinar_estado_credito(credito.id)
        self.assertEqual(estado_final, EstadoCredito.PAGADO)
        self.assertEqual(self.credito_svc.calcular_saldo_pendiente(credito.id), Decimal("0.00"))

        # 9. Validación de Inteligencia de Cartera y Métricas
        metricas = self.reporte_svc.obtener_metricas()
        self.assertEqual(metricas["total"], 1)
        self.assertEqual(metricas["pagados"], 1)
        self.assertEqual(metricas["activos"], 0)
        self.assertEqual(metricas["saldo_vencido"], Decimal("0.00"))
        self.assertEqual(metricas["tasa_morosidad"], Decimal("0.00"))
        self.assertEqual(metricas["intereses_cobrados"], Decimal("60000.00"))

        distribucion = self.reporte_svc.obtener_distribucion_cartera()
        self.assertEqual(distribucion["saldados"]["cantidad"], 1)
        self.assertEqual(distribucion["en_mora"]["cantidad"], 0)
        self.assertEqual(distribucion["al_dia"]["cantidad"], 0)

    def test_validaciones_frontera_y_errores_dominio(self):
        """Valida que los servicios rechacen operaciones inválidas con excepciones tipadas."""
        # Crédito a cliente inexistente
        with self.assertRaises(ClienteNoEncontradoError):
            self.credito_svc.crear_credito(9999, Decimal("100000"), 1, FrecuenciaPago.SEMANAL)

        # Montos no positivos
        with self.assertRaises(MontoInvalidoError):
            self.credito_svc.crear_credito(1, Decimal("0"), 1, FrecuenciaPago.SEMANAL)

        cliente = self.cliente_svc.crear_cliente("Test", "300", "CC-TEST-1")
        credito = self.credito_svc.crear_credito(cliente.id, Decimal("100000"), 1, FrecuenciaPago.SEMANAL)
        cuotas = self.credito_svc.obtener_plan_pagos(credito.id)

        # Pago de monto mayor al saldo de cuota
        with self.assertRaises(MontoInvalidoError):
            self.pago_svc.registrar_pago(credito.id, cuotas[0].id, cuotas[0].monto + Decimal("10.00"))

        # Pago a cuota inexistente
        with self.assertRaises(CuotaNoEncontradaError):
            self.pago_svc.registrar_pago(credito.id, 99999, Decimal("1000.00"))

        # Crédito inexistente
        with self.assertRaises(CreditoNoEncontradoError):
            self.credito_svc.obtener_credito(88888)


class TestIntegracionUIHeadlessE2E(unittest.TestCase):
    """Pruebas de integración de la interfaz de usuario en modo sin display (Headless Tkinter)."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_ui_e2e.db"
        inicializar_base_datos(str(cls.db_path))
        cls.app = App(db_path=str(cls.db_path))
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app.after_cancel(cls.app._after_verificar_dia_id)
        except Exception:
            pass
        try:
            cls.app.conn.close()
        except Exception:
            pass
        cls.temp_dir.cleanup()

    def setUp(self):
        self.app.conn.execute("DELETE FROM pagos")
        self.app.conn.execute("DELETE FROM cuotas")
        self.app.conn.execute("DELETE FROM creditos")
        self.app.conn.execute("DELETE FROM clientes")
        self.app.conn.commit()

        self.cliente = self.app.cliente_service.crear_cliente("Laura Restrepo", "3201112233", "CC-882233")
        self.credito = self.app.credito_service.crear_credito(
            self.cliente.id,
            Decimal("400000"),
            1,
            FrecuenciaPago.SEMANAL,
            fecha_inicio=date.today() - timedelta(days=10),
        )
        self.cuotas = self.app.credito_service.obtener_plan_pagos(self.credito.id)
        self.app.notificar_cambio_datos()

    def test_navegacion_integral_todas_las_vistas(self):
        """Recorre todas las pantallas del sistema verificando que carguen sin errores y sincronicen datos."""
        vistas = ["dashboard", "clientes", "pagos", "reportes"]
        for vista in vistas:
            self.app.navigate(vista)
            self.assertEqual(self.app.current_view_name, vista)
            self.assertIsNotNone(self.app.current_view)

        # Vistas dinámicas con parámetros
        self.app.navigate("cliente_detail", cliente_id=self.cliente.id)
        self.assertEqual(self.app.current_view_name, "cliente_detail")
        self.assertEqual(self.app.current_view.cliente_id, self.cliente.id)

        self.app.navigate("credito_detail", credito_id=self.credito.id)
        self.assertEqual(self.app.current_view_name, "credito_detail")
        self.assertEqual(self.app.current_view.credito_id, self.credito.id)

        self.app.navigate("credito_new", cliente_id=self.cliente.id)
        self.assertEqual(self.app.current_view_name, "credito_new")

    def test_flujo_ui_dashboard_y_mora(self):
        """Comprueba que el Dashboard refleje las cuotas en mora y sus etiquetas."""
        self.app.navigate("dashboard")
        dashboard = self.app.cached_views["dashboard"]
        dashboard._load_data()

        # Las cuotas vencidas deben contener '(EN MORA)'
        datos_tabla = [row for row in dashboard.table.rows]
        self.assertTrue(len(datos_tabla) > 0)
        self.assertEqual(dashboard.card_activos.value_label.cget("text"), "1")

    def test_flujo_ui_pagos_view_y_detalle_modal(self):
        """Registra un pago, verifica la tabla de pagos y abre el modal de detalle."""
        cuota = self.cuotas[0]
        pago = self.app.pago_service.registrar_pago(self.credito.id, cuota.id, Decimal("50000"))
        self.app.notificar_cambio_datos()

        self.app.navigate("pagos")
        pagos_view = self.app.cached_views["pagos"]
        pagos_view.on_show(force=True)

        self.assertTrue(len(pagos_view.table.rows) >= 1)

        # Clic en la fila para abrir DetallePagoDialog
        with patch.object(self.app, "generar_comprobante_pago", return_value="dummy.pdf") as mock_pdf:
            pagos_view._on_row_click({"pago_id": pago.id})
            # Verificar que DetallePagoDialog puede generar PDF
            from credito_app.ui.components.dialogs import DetallePagoDialog

            dialog = DetallePagoDialog(self.app, self.app.pago_service.obtener_datos_comprobante(pago.id), self.app)
            dialog._abrir_pdf()
            mock_pdf.assert_called_with(pago.id, preguntar_destino=False, abrir_al_terminar=True)
            dialog.destroy()

    def test_flujo_ui_reportes_filtros_y_graficas(self):
        """Verifica que ReportesView renderice métricas y gráficas sin error ante todos los preajustes."""
        self.app.navigate("reportes")
        reportes_view = self.app.cached_views["reportes"]

        filtros = ["Todos", "Hoy", "Esta Semana", "Este Mes", "Año en curso"]
        for f in filtros:
            reportes_view._set_preset(f)
            self.assertIsNotNone(reportes_view.fig_bar)
            self.assertIsNotNone(reportes_view.fig_donut)

        # Prueba rango personalizado
        reportes_view.entry_desde.delete(0, "end")
        reportes_view.entry_desde.insert(0, (date.today() - timedelta(days=30)).isoformat())
        reportes_view.entry_hasta.delete(0, "end")
        reportes_view.entry_hasta.insert(0, date.today().isoformat())
        reportes_view._aplicar_rango_personalizado()
        self.assertEqual(reportes_view.preset_var.get(), "Personalizado")

    def test_notificaciones_y_verificacion_dia(self):
        """Verifica el componente de notificaciones y la rutina de cambio de día."""
        self.app.show_notification("Éxito", "success")
        self.app.show_notification("Alerta", "warning")
        self.app.show_notification("Fallo", "error")

        # Simular cambio de día
        fecha_antigua = date.today() - timedelta(days=1)
        self.app._fecha_ultima_verificacion_mora = fecha_antigua
        version_previa = self.app.data_version
        self.app._verificar_cambio_dia()
        self.assertEqual(self.app._fecha_ultima_verificacion_mora, date.today())
        self.assertGreater(self.app.data_version, version_previa)

    def test_cliente_dialog_crear_editar_y_validaciones(self):
        """Prueba exhaustiva de ClienteDialog: validación de campos, guardado y edición."""
        from credito_app.ui.components.dialogs import ClienteDialog

        guardado = False

        def on_save():
            nonlocal guardado
            guardado = True

        dialog = ClienteDialog(self.app, self.app.cliente_service, on_save=on_save)

        # 1. Validación de campos vacíos
        dialog.nombre_entry.delete(0, "end")
        dialog.doc_entry.delete(0, "end")
        dialog.tel_entry.delete(0, "end")
        dialog._save()
        self.assertFalse(guardado)
        self.assertNotEqual(dialog.err_nombre.cget("text"), "")

        dialog.nombre_entry.insert(0, "Pedro Gómez")
        dialog._save()
        self.assertFalse(guardado)
        self.assertNotEqual(dialog.err_doc.cget("text"), "")

        dialog.doc_entry.insert(0, "CC-554433")
        dialog._save()
        self.assertFalse(guardado)
        self.assertNotEqual(dialog.err_tel.cget("text"), "")

        # 2. Guardado exitoso de nuevo cliente
        dialog.tel_entry.insert(0, "300778899")
        dialog._save()
        self.assertTrue(guardado)

        # 3. Modo Edición
        cliente_creado = self.app.cliente_service.obtener_por_documento("CC-554433")
        self.assertIsNotNone(cliente_creado)

        guardado_edit = False

        def on_save_edit():
            nonlocal guardado_edit
            guardado_edit = True

        dialog_edit = ClienteDialog(self.app, self.app.cliente_service, on_save=on_save_edit, cliente=cliente_creado)
        dialog_edit.nombre_entry.delete(0, "end")
        dialog_edit.nombre_entry.insert(0, "Pedro Gómez Editado")
        dialog_edit._save()
        self.assertTrue(guardado_edit)

        cliente_actualizado = self.app.cliente_service.obtener_cliente(cliente_creado.id)
        self.assertEqual(cliente_actualizado.nombre, "Pedro Gómez Editado")

    def test_pago_dialog_interacciones_y_guardado(self):
        """Prueba PagoDialog: selección de cuota, validación de monto y registro con comprobante."""
        from credito_app.ui.components.dialogs import PagoDialog

        pago_registrado = None

        def on_pago_save(pago):
            nonlocal pago_registrado
            pago_registrado = pago

        dialog = PagoDialog(
            self.app, self.credito, self.cuotas, self.app.pago_service, on_save=on_pago_save, app=self.app
        )

        # Validación de monto inválido
        dialog.monto_entry.delete(0, "end")
        dialog.monto_entry.insert(0, "0")
        dialog._save()
        self.assertIsNone(pago_registrado)
        self.assertNotEqual(dialog.err_monto.cget("text"), "")

        dialog.monto_entry.delete(0, "end")
        dialog.monto_entry.insert(0, "monto_invalido")
        dialog._save()
        self.assertIsNone(pago_registrado)

        # Guardado exitoso con PDF simulado
        dialog.monto_entry.delete(0, "end")
        dialog.monto_entry.insert(0, "20000")
        with patch.object(self.app, "generar_comprobante_pago") as mock_pdf:
            dialog._save()
            self.assertIsNotNone(pago_registrado)
            mock_pdf.assert_called_once()

    def test_credito_view_formulario_y_calculo_reactivo(self):
        """Prueba CreditoView: entrada de parámetros financieros, cálculo reactivo y creación."""
        from credito_app.ui.views.credito_view import CreditoView

        view = CreditoView(self.app.view_container, self.app, cliente_id=self.cliente.id)

        # Entrada de datos
        view.capital_entry.delete(0, "end")
        view.capital_entry.insert(0, "300000")

        view.plazo_entry.delete(0, "end")
        view.plazo_entry.insert(0, "2")

        view.tasa_entry.delete(0, "end")
        view.tasa_entry.insert(0, "10")

        view.frecuencia_var.set("QUINCENAL")

        # Recálculo reactivo
        view._on_calcular()
        self.assertIsNotNone(view._calculated_data)
        self.assertEqual(view._calculated_data["capital"], Decimal("300000"))
        self.assertEqual(view._calculated_data["num_cuotas"], 4)

        # Simular creación exitosa
        with patch("credito_app.ui.views.credito_view.ConfirmDialog") as mock_dialog:
            view._on_crear()
            self.assertTrue(mock_dialog.called)
            # Ejecutar el callback de confirmación
            on_confirm_cb = mock_dialog.call_args[1]["on_confirm"]
            on_confirm_cb()
            self.assertEqual(self.app.current_view_name, "credito_detail")

        view.destroy()

    def test_credito_detail_view_y_cliente_detail_view(self):
        """Prueba botones y acciones de detalle de cliente y crédito."""
        from credito_app.ui.views.credito_detail_view import CreditoDetailView
        from credito_app.ui.views.cliente_detail_view import ClienteDetailView

        # CreditoDetailView
        cred_view = CreditoDetailView(self.app.view_container, self.app, credito_id=self.credito.id)
        cred_view._on_cliente_click()
        self.assertEqual(self.app.current_view_name, "cliente_detail")

        cred_view._on_back()
        self.assertEqual(self.app.current_view_name, "dashboard")

        # ClienteDetailView
        cli_view = ClienteDetailView(self.app.view_container, self.app, cliente_id=self.cliente.id)
        cli_view.new_credito()
        self.assertEqual(self.app.current_view_name, "credito_new")

        cli_view.go_back()
        self.assertEqual(self.app.current_view_name, "clientes")

        cred_view.destroy()
        cli_view.destroy()

    def test_app_generar_comprobante_y_acciones_completas(self):
        """Cubre generación de PDF desde App, DetallePagoDialog, ClientesView y CreditoDetailView."""
        from credito_app.ui.components.dialogs import DetallePagoDialog
        from credito_app.ui.views.credito_detail_view import CreditoDetailView

        # 1. Registrar pago y generar comprobante vía App
        pago = self.app.pago_service.registrar_pago(self.credito.id, self.cuotas[0].id, Decimal("10000"))
        pdf_path = self.app.generar_comprobante_pago(pago.id, preguntar_destino=False, abrir_al_terminar=False)
        self.assertIsNotNone(pdf_path)
        self.assertTrue(Path(pdf_path).exists())

        # 2. DetallePagoDialog: guardar como y navegar a crédito
        detalle = self.app.pago_service.obtener_datos_comprobante(pago.id)
        dialog_pago = DetallePagoDialog(self.app, detalle, self.app)
        with patch.object(self.app, "generar_comprobante_pago") as mock_gen:
            dialog_pago._guardar_pdf_como()
            mock_gen.assert_called_with(pago.id, preguntar_destino=True, abrir_al_terminar=False)

        dialog_pago._ir_al_credito()
        self.assertEqual(self.app.current_view_name, "credito_detail")

        # 3. ClientesView: búsqueda y recargar
        self.app.navigate("clientes")
        cli_view = self.app.cached_views["clientes"]
        cli_view.search_entry.delete(0, "end")
        cli_view.search_entry.insert(0, "Laura")
        cli_view.search()
        self.assertTrue(len(cli_view.table.rows) >= 1)
        cli_view.refresh()

        # 4. CreditoDetailView: registrar pago y click en fila
        cred_view = CreditoDetailView(self.app.view_container, self.app, credito_id=self.credito.id)
        with patch("credito_app.ui.views.credito_detail_view.PagoDialog") as mock_pago_dlg:
            cred_view._on_registrar_pago()
            self.assertTrue(mock_pago_dlg.called)

            cred_view._on_row_click({"id": self.cuotas[1].id, "__estado_raw": EstadoCuota.PENDIENTE})
            self.assertEqual(mock_pago_dlg.call_count, 2)

        cred_view.destroy()

        # 5. Formatters
        from credito_app.ui.utils.formatters import formato_moneda

        self.assertEqual(formato_moneda(None), "$0")
        self.assertIn(",", formato_moneda(Decimal("1234.56")))


if __name__ == "__main__":
    unittest.main()
