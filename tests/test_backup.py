import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from credito_app.database.connection import get_connection
from credito_app.database.schema import inicializar_base_datos
from credito_app.modules.credito import FrecuenciaPago
from credito_app.services.backup_service import BackupError, BackupService
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.ui.app import App
from credito_app.ui.components.dialogs import BackupDialog


class TestBackupService(unittest.TestCase):
    """Pruebas unitarias y de integración del servicio de Backup y Restauración."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.db_path = self.base_path / "creditos_test.db"
        self.backups_dir = self.base_path / "backups"

        inicializar_base_datos(str(self.db_path))
        self.conn = get_connection(str(self.db_path))

        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)
        self.backup_svc = BackupService(self.conn, backups_dir=self.backups_dir)

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_crear_backup_por_defecto_y_listar(self):
        """Verifica que crear_backup genere un archivo .db válido y listar_backups lo encuentre."""
        self.assertEqual(len(self.backup_svc.listar_backups()), 0)

        cliente = self.cliente_svc.crear_cliente("Carlos Ruiz", "3109998877", "CC-700100")
        self.assertIsNotNone(cliente.id)

        ruta_backup = self.backup_svc.crear_backup()
        self.assertTrue(ruta_backup.exists())
        self.assertEqual(ruta_backup.suffix, ".db")
        self.assertTrue(self.backup_svc.validar_archivo_backup(ruta_backup))

        lista = self.backup_svc.listar_backups()
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["nombre"], ruta_backup.name)
        self.assertGreater(lista[0]["tamano_kb"], 0)

    def test_crear_backup_ruta_personalizada_sin_extension(self):
        """Si el usuario indica una ruta sin extensión .db, se añade automáticamente."""
        destino_custom = self.base_path / "exportados" / "mi_respaldo_manual"
        ruta_final = self.backup_svc.crear_backup(destino=destino_custom)
        self.assertEqual(ruta_final.suffix, ".db")
        self.assertTrue(ruta_final.exists())
        self.assertTrue(self.backup_svc.validar_archivo_backup(ruta_final))

    def test_validacion_archivos_invalidos(self):
        """Comprueba que validar_archivo_backup rechace archivos inexistentes, corruptos o ajenos."""
        # 1. Archivo inexistente
        with self.assertRaises(BackupError):
            self.backup_svc.validar_archivo_backup(self.base_path / "no_existe.db")

        # 2. Archivo vacío
        archivo_vacio = self.base_path / "vacio.db"
        archivo_vacio.write_bytes(b"")
        with self.assertRaises(BackupError):
            self.backup_svc.validar_archivo_backup(archivo_vacio)

        # 3. Archivo de texto que no es SQLite
        archivo_texto = self.base_path / "falso.db"
        archivo_texto.write_text("Esto no es una base de datos SQLite válida", encoding="utf-8")
        with self.assertRaises(BackupError):
            self.backup_svc.validar_archivo_backup(archivo_texto)

        # 4. Base de datos SQLite válida pero sin las tablas de CrediNoda
        otra_db = self.base_path / "otra_app.db"
        conn_otra = sqlite3.connect(str(otra_db))
        conn_otra.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT)")
        conn_otra.commit()
        conn_otra.close()

        with self.assertRaises(BackupError) as ctx:
            self.backup_svc.validar_archivo_backup(otra_db)
        self.assertIn("faltan tablas", str(ctx.exception))

    def test_ciclo_completo_backup_borrado_y_restauracion_en_caliente(self):
        """
        Ciclo E2E: Crea cliente, crédito y pago -> Crea backup -> Borra toda la BD ->
        Restaura backup -> Verifica que todos los datos e importes regresaron intactos.
        """
        cliente = self.cliente_svc.crear_cliente("Elena Noda", "3150001122", "CC-900500")
        credito = self.credito_svc.crear_credito(
            cliente.id,
            Decimal("500000"),
            1,
            FrecuenciaPago.SEMANAL,
            fecha_inicio=date.today() - timedelta(days=10),
        )
        cuotas = self.credito_svc.obtener_plan_pagos(credito.id)
        pago = self.pago_svc.registrar_pago(credito.id, cuotas[0].id, Decimal("60000"))

        # 1. Crear copia de seguridad
        ruta_respaldo = self.backup_svc.crear_backup()

        # 2. Destruir todos los datos actuales en la BD activa
        self.conn.execute("DELETE FROM pagos")
        self.conn.execute("DELETE FROM cuotas")
        self.conn.execute("DELETE FROM creditos")
        self.conn.execute("DELETE FROM clientes")
        self.conn.commit()

        self.assertEqual(len(self.cliente_svc.buscar_clientes("")), 0)
        self.assertEqual(len(self.credito_svc.listar_creditos()), 0)

        # 3. Restaurar desde el backup
        ruta_preventiva = self.backup_svc.restaurar_backup(ruta_respaldo)
        self.assertTrue(ruta_preventiva.exists())
        self.assertIn("pre_restauracion", ruta_preventiva.name)

        # 4. Verificar que los datos restaurados estén íntegros
        clientes_restaurados = self.cliente_svc.buscar_clientes("")
        self.assertEqual(len(clientes_restaurados), 1)
        self.assertEqual(clientes_restaurados[0].nombre, "Elena Noda")

        credito_restaurado = self.credito_svc.obtener_credito(credito.id)
        self.assertEqual(credito_restaurado.capital, Decimal("500000"))

        pago_restaurado = self.pago_svc.obtener_pago(pago.id)
        self.assertIsNotNone(pago_restaurado)
        self.assertEqual(pago_restaurado.monto, Decimal("60000"))


class TestBackupUIHeadless(unittest.TestCase):
    """Pruebas de interfaz sin display para BackupDialog y botón de Sidebar."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.base_path = Path(cls.temp_dir.name)
        cls.db_path = cls.base_path / "ui_backup_test.db"
        inicializar_base_datos(str(cls.db_path))
        cls.app = App(db_path=str(cls.db_path))
        cls.app.withdraw()
        cls.app.backup_service.backups_dir = cls.base_path / "backups"
        cls.app.backup_service.backups_dir.mkdir(parents=True, exist_ok=True)

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

    def test_abrir_dialogo_y_acciones_backup_restauracion(self):
        """Verifica Respaldo Rápido, Guardar Como y Restauración desde BackupDialog."""
        # Crear un cliente antes del respaldo
        self.app.cliente_service.crear_cliente("Cliente Respaldo UI", "3001234567", "CC-UI-999")

        # Abrir diálogo desde el método de App / Sidebar
        dialog: BackupDialog = self.app.abrir_dialogo_backup()
        self.assertIsNotNone(dialog)

        # 1. Respaldo rápido
        ruta_rapida = dialog._crear_respaldo_rapido()
        self.assertIsNotNone(ruta_rapida)
        self.assertTrue(ruta_rapida.exists())
        self.assertIn("Último respaldo local:", dialog.lbl_ultimo_backup.cget("text"))

        # 2. Guardar copia como (simulando filedialog)
        destino_custom = self.base_path / "copia_dialog.db"
        with patch("tkinter.filedialog.asksaveasfilename", return_value=str(destino_custom)):
            ruta_guardada = dialog._guardar_copia_como()
            self.assertEqual(ruta_guardada, destino_custom)
            self.assertTrue(destino_custom.exists())

        # 2b. Cancelar guardar copia como
        with patch("tkinter.filedialog.asksaveasfilename", return_value=""):
            self.assertIsNone(dialog._guardar_copia_como())

        # 3. Seleccionar y restaurar vía ConfirmDialog + Restaurar archivo válido
        self.app.conn.execute("DELETE FROM clientes")
        self.app.conn.commit()
        self.assertEqual(len(self.app.cliente_service.buscar_clientes("")), 0)

        with patch("tkinter.filedialog.askopenfilename", return_value=""):
            dialog._seleccionar_y_restaurar()

        with (
            patch("tkinter.filedialog.askopenfilename", return_value=str(ruta_rapida)),
            patch("credito_app.ui.components.dialogs.ConfirmDialog") as mock_confirm,
        ):
            dialog._seleccionar_y_restaurar()
            self.assertTrue(mock_confirm.called)
            on_confirm_cb = mock_confirm.call_args.kwargs["on_confirm"]

        version_previa = self.app.data_version
        on_confirm_cb()
        self.assertGreater(self.app.data_version, version_previa)
        self.assertEqual(len(self.app.cliente_service.buscar_clientes("")), 1)

        # 4. Intentar restaurar un archivo inválido desde el diálogo y probar botón de Sidebar
        with patch.object(self.app.sidebar, "on_backup") as mock_abrir:
            self.app.sidebar._on_backup_click()
            mock_abrir.assert_called_once()
        self.app.sidebar._on_button_click("dashboard")


        dialog2: BackupDialog = self.app.abrir_dialogo_backup()
        exito_invalido = dialog2._ejecutar_restauracion(str(self.base_path / "inexistente.db"))
        self.assertFalse(exito_invalido)

        with patch.object(self.app.backup_service, "crear_backup", side_effect=BackupError("Error simulado")):
            self.assertIsNone(dialog2._crear_respaldo_rapido())
            with patch("tkinter.filedialog.asksaveasfilename", return_value=str(destino_custom)):
                self.assertIsNone(dialog2._guardar_copia_como())

        dialog2.destroy()


if __name__ == "__main__":
    unittest.main()

