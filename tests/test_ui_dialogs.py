import unittest
import customtkinter as ctk
from unittest.mock import MagicMock
from credito_app.ui.components.dialogs import ConfirmDialog
from credito_app.ui.components.notifications import NotificationBar


class TestUIDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_confirm_dialog_disables_button_and_destroys(self):
        called = False

        def on_confirm_callback():
            nonlocal called
            called = True

        dialog = ConfirmDialog(self.root, title="Test", message="Test message", on_confirm=on_confirm_callback)

        # Verify confirm button exists and is normal
        self.assertEqual(dialog.confirm_btn.cget("state"), "normal")

        # Trigger confirm
        dialog._confirm()

        # Verify callback was executed
        self.assertTrue(called)

        # Verify dialog window is destroyed / not viewable
        self.assertFalse(dialog.winfo_exists())

    def test_notification_bar_pack_and_grid(self):
        # Test in pack container
        pack_frame = ctk.CTkFrame(self.root)
        pack_frame.pack()
        child = ctk.CTkLabel(pack_frame, text="Hello")
        child.pack()

        notif_pack = NotificationBar(pack_frame)
        notif_pack.show_success("Operación exitosa en pack")
        self.assertEqual(notif_pack._determine_manager(), "pack")
        notif_pack.hide()

        # Test in grid container
        grid_frame = ctk.CTkFrame(self.root)
        grid_frame.pack()
        child_grid = ctk.CTkLabel(grid_frame, text="Hello Grid")
        child_grid.grid(row=1, column=0)

        notif_grid = NotificationBar(grid_frame)
        notif_grid.show_error("Error en grid")
        self.assertEqual(notif_grid._determine_manager(), "grid")
        notif_grid.hide()

    def test_credito_view_confirm_flow(self):
        from decimal import Decimal
        from credito_app.modules.credito import FrecuenciaPago, Credito, EstadoCredito
        from datetime import date
        from credito_app.ui.views.credito_view import CreditoView

        mock_app = MagicMock()
        mock_app.cliente_service.buscar_clientes.return_value = []

        dummy_credito = Credito(
            id=42,
            cliente_id=1,
            capital=Decimal("1000000"),
            tasa_mensual=Decimal("0.12"),
            plazo_meses=3,
            total_intereses=Decimal("360000"),
            total_pagar=Decimal("1360000"),
            frecuencia_pago=FrecuenciaPago.QUINCENAL,
            fecha_inicio=date.today(),
            estado=EstadoCredito.ACTIVO,
        )
        mock_app.credito_service.crear_credito.return_value = dummy_credito

        view = CreditoView(self.root, mock_app)
        view._calculated_data = {
            "cliente_id": 1,
            "capital": Decimal("1000000"),
            "plazo": 3,
            "frecuencia": FrecuenciaPago.QUINCENAL,
            "tasa": Decimal("0.12"),
            "num_cuotas": 6,
        }

        # Mock ConfirmDialog to verify on_confirm execution
        captured_on_confirm = None

        def mock_confirm_dialog(parent, title, message, on_confirm):
            nonlocal captured_on_confirm
            captured_on_confirm = on_confirm

        import credito_app.ui.views.credito_view as cv_mod

        orig_dialog = cv_mod.ConfirmDialog
        cv_mod.ConfirmDialog = mock_confirm_dialog
        try:
            view._on_crear()
            self.assertIsNotNone(captured_on_confirm)
            # Execute the confirm action
            captured_on_confirm()

            # Verify credito_service.crear_credito was called
            mock_app.credito_service.crear_credito.assert_called_once()
            # Verify success notification was shown
            mock_app.show_notification.assert_called_with("Crédito creado exitosamente", "success")
            # Verify navigation to credito_detail with ID 42
            mock_app.navigate.assert_called_with("credito_detail", credito_id=42)
        finally:
            cv_mod.ConfirmDialog = orig_dialog
            view.destroy()

    def test_dashboard_view_metrics(self):
        from decimal import Decimal
        from datetime import date
        from credito_app.modules.credito import FrecuenciaPago, Credito, EstadoCredito, EstadoCuota
        from credito_app.ui.views.dashboard_view import DashboardView

        mock_app = MagicMock()
        credito_activo = Credito(
            id=1,
            cliente_id=1,
            capital=Decimal("1000000"),
            tasa_mensual=Decimal("0.12"),
            plazo_meses=3,
            total_intereses=Decimal("360000"),
            total_pagar=Decimal("1360000"),
            frecuencia_pago=FrecuenciaPago.QUINCENAL,
            fecha_inicio=date.today(),
            estado=EstadoCredito.ACTIVO,
        )
        credito_pagado = Credito(
            id=2,
            cliente_id=1,
            capital=Decimal("500000"),
            tasa_mensual=Decimal("0.12"),
            plazo_meses=2,
            total_intereses=Decimal("120000"),
            total_pagar=Decimal("620000"),
            frecuencia_pago=FrecuenciaPago.QUINCENAL,
            fecha_inicio=date.today(),
            estado=EstadoCredito.PAGADO,
        )

        mock_app.credito_service.listar_creditos.return_value = [credito_activo, credito_pagado]
        mock_app.credito_service.calcular_saldo_pendiente.return_value = Decimal("800000")
        mock_app.credito_service.obtener_proximos_pagos.return_value = [
            {
                "credito_id": 1,
                "cliente_nombre": "Test Cliente",
                "numero_cuota": 1,
                "monto": Decimal("226666.67"),
                "fecha_vencimiento": date.today(),
                "estado": EstadoCuota.PENDIENTE,
            }
        ]

        view = DashboardView(self.root, mock_app)
        try:
            self.assertEqual(view.card_activos.value_label.cget("text"), "1")
            self.assertEqual(view.card_capital.value_label.cget("text"), "$1.000.000")
            self.assertEqual(view.card_saldo.value_label.cget("text"), "$800.000")
        finally:
            view.destroy()

    def test_data_table_alternating_colors_and_weights(self):
        from credito_app.ui.components.tables import DataTable
        from credito_app.ui.theme import COLORS

        cols = [
            {"key": "col1", "text": "Columna 1", "width": 200, "weight": 2, "anchor": "w"},
            {"key": "cuota", "text": "Cuota", "width": 80, "weight": 0, "anchor": "center"},
        ]
        table = DataTable(self.root, columns=cols)
        try:
            rows = [
                {"col1": "Registro 1", "cuota": "1"},
                {"col1": "Registro 2", "cuota": "2"},
                {"col1": "Registro 3", "cuota": "3"},
            ]
            table.set_data(rows)
            self.assertEqual(len(table.rows), 3)
            # Verify alternating background colors
            self.assertEqual(table.rows[0].cget("fg_color"), COLORS["bg_panel"])
            self.assertEqual(table.rows[1].cget("fg_color"), COLORS["row_alt"])
            self.assertEqual(table.rows[2].cget("fg_color"), COLORS["bg_panel"])
            # Verify row corner radius for visual styling
            self.assertEqual(table.rows[0].cget("corner_radius"), 6)
        finally:
            table.destroy()

    def test_pagos_view_load_data(self):
        from decimal import Decimal
        from datetime import date
        from credito_app.ui.views.pagos_view import PagosView

        mock_app = MagicMock()
        mock_app.pago_service.listar_pagos_con_detalle.return_value = [
            {
                "pago_id": 10,
                "credito_id": 1,
                "cuota_id": 7,
                "numero_cuota": 1,
                "fecha_pago": date(2026, 9, 5),
                "monto": Decimal("150000"),
                "cliente_nombre": "Erickson",
                "cliente_id": 1,
            }
        ]

        view = PagosView(self.root, mock_app)
        try:
            self.assertEqual(len(view.table.rows), 1)
            # Verify cuota displays numero_cuota
            labels = [w for w in view.table.rows[0].winfo_children() if hasattr(w, "cget") and hasattr(w, "_text")]
            cell_texts = [w.cget("text") for w in labels]
            self.assertIn("1", cell_texts)
            self.assertIn("#1", cell_texts)
            self.assertIn("$150.000", cell_texts)
        finally:
            view.destroy()

    def test_pagos_view_busqueda_manual_y_limpiar(self):
        from decimal import Decimal
        from datetime import date
        from credito_app.ui.views.pagos_view import PagosView

        mock_app = MagicMock()
        mock_app.pago_service.listar_pagos_con_detalle.return_value = [
            {
                "pago_id": 14,
                "credito_id": 1,
                "cuota_id": 7,
                "numero_cuota": 2,
                "fecha_pago": date(2026, 9, 11),
                "monto": Decimal("92500"),
                "cliente_nombre": "Erickson Jhair",
                "cliente_id": 1,
            },
            {
                "pago_id": 15,
                "credito_id": 4,
                "cuota_id": 12,
                "numero_cuota": 1,
                "fecha_pago": date(2026, 9, 11),
                "monto": Decimal("92500"),
                "cliente_nombre": "Erickson Jhair",
                "cliente_id": 1,
            },
        ]

        view = PagosView(self.root, mock_app)
        try:
            # Inicialmente ambos pagos están presentes
            self.assertEqual(len(view.table.rows), 2)

            # Escribir '4' y ejecutar búsqueda
            view.search_entry.delete(0, "end")
            view.search_entry.insert(0, "4")
            view._on_search()

            # Solo debe mostrar el pago del crédito #4, NO el pago #14 que pertenece al crédito #1
            self.assertEqual(len(view.table.rows), 1)
            labels = [w for w in view.table.rows[0].winfo_children() if hasattr(w, "cget") and hasattr(w, "_text")]
            cell_texts = [w.cget("text") for w in labels]
            self.assertIn("#4", cell_texts)
            self.assertNotIn("#1", cell_texts)

            # Probar búsqueda con '#4'
            view.search_entry.delete(0, "end")
            view.search_entry.insert(0, "#4")
            view._on_search()
            self.assertEqual(len(view.table.rows), 1)

            # Probar botón limpiar
            view._on_limpiar()
            self.assertEqual(len(view.table.rows), 2)
            self.assertEqual(view.search_entry.get(), "")
        finally:
            view.destroy()

    def test_navigation_caching_and_pack_forget(self):
        from unittest.mock import MagicMock, patch
        from credito_app.ui.views.dashboard_view import DashboardView
        from credito_app.ui.views.clientes_view import ClientesView

        mock_app = MagicMock()
        mock_app.data_version = 1
        mock_app.credito_service.listar_creditos.return_value = []
        mock_app.credito_service.obtener_proximos_pagos.return_value = []
        mock_app.cliente_service.buscar_clientes.return_value = []

        container = ctk.CTkFrame(self.root)
        container.pack()

        try:
            dashboard = DashboardView(container, mock_app)
            dashboard.pack(fill="both", expand=True)

            cached_views = {"dashboard": dashboard}

            # Simular ocultar dashboard con pack_forget
            dashboard.pack_forget()

            # Crear y mostrar clientes
            clientes = ClientesView(container, mock_app)
            clientes.pack(fill="both", expand=True)
            cached_views["clientes"] = clientes

            # Volver a mostrar dashboard desde caché reutilizando la misma instancia
            clientes.pack_forget()
            cached_dashboard = cached_views["dashboard"]
            cached_dashboard.pack(fill="both", expand=True)
            self.assertIs(cached_dashboard, dashboard)

            # Probar sincronización por versión de datos en on_show
            mock_app.data_version = 2
            with patch.object(cached_dashboard, "_load_data") as mock_load:
                cached_dashboard.on_show()
                mock_load.assert_called_once()
                self.assertEqual(cached_dashboard.last_data_version, 2)

                # Segunda llamada sin cambio de versión no debe recargar datos
                mock_load.reset_mock()
                cached_dashboard.on_show()
                mock_load.assert_not_called()
        finally:
            container.destroy()
