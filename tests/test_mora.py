import unittest
from datetime import date, timedelta
from decimal import Decimal

from credito_app.modules.credito import FrecuenciaPago, EstadoCredito, EstadoCuota
from credito_app.database.schema import crear_tablas
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.tests.test_credito import get_test_connection


class TestMoraCuotas(unittest.TestCase):
    def setUp(self):
        self.conn = get_test_connection()
        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)
        self.cliente = self.cliente_svc.crear_cliente("Cliente Mora", "0000", "DOCM")

    def tearDown(self):
        self.conn.close()

    def _credito_pasado(self):
        # Inicio hace 60 días: las primeras cuotas semanales ya vencieron, las últimas no necesariamente
        credito = self.credito_svc.crear_credito(
            self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL,
            fecha_inicio=date.today() - timedelta(days=60),
        )
        return credito, self.credito_svc.obtener_plan_pagos(credito.id)

    def test_cuota_vencida_conserva_estado_pendiente_y_marca_mora(self):
        _, plan = self._credito_pasado()
        vencidas = [c for c in plan if c.fecha_vencimiento < date.today()]
        self.assertTrue(vencidas)
        for c in vencidas:
            self.assertEqual(c.estado, EstadoCuota.PENDIENTE)
            self.assertTrue(c.en_mora)
            self.assertEqual(c.etiqueta_estado, "PENDIENTE (EN MORA)")

    def test_cuota_futura_no_esta_en_mora(self):
        credito = self.credito_svc.crear_credito(
            self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL
        )
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertTrue(all(not c.en_mora for c in plan))

    def test_actualizar_cuotas_en_mora_detecta_y_es_idempotente(self):
        credito, plan = self._credito_pasado()
        # Simular estado previo sin mora (p. ej. base de datos migrada)
        self.conn.execute("UPDATE cuotas SET en_mora = 0")
        self.conn.commit()

        cambiadas = self.credito_svc.actualizar_cuotas_en_mora()
        esperadas = sum(1 for c in plan if c.fecha_vencimiento < date.today())
        self.assertEqual(cambiadas, esperadas)
        self.assertEqual(self.credito_svc.actualizar_cuotas_en_mora(), 0)

    def test_pago_parcial_conserva_parcial_y_mora(self):
        credito, plan = self._credito_pasado()
        cuota = plan[0]
        self.pago_svc.registrar_pago(credito.id, cuota.id, Decimal("1000"))
        actual = self.credito_svc.obtener_plan_pagos(credito.id)[0]
        self.assertEqual(actual.estado, EstadoCuota.PARCIAL)
        self.assertTrue(actual.en_mora)
        self.assertEqual(actual.etiqueta_estado, "PARCIAL (EN MORA)")

    def test_pago_total_quita_mora(self):
        credito, plan = self._credito_pasado()
        cuota = plan[0]
        self.pago_svc.registrar_pago(credito.id, cuota.id, cuota.monto)
        actual = self.credito_svc.obtener_plan_pagos(credito.id)[0]
        self.assertEqual(actual.estado, EstadoCuota.PAGADA)
        self.assertFalse(actual.en_mora)

    def test_credito_con_mora_sigue_activo_y_pasa_a_pagado(self):
        credito, plan = self._credito_pasado()
        self.credito_svc.actualizar_cuotas_en_mora()
        self.assertEqual(self.credito_svc.determinar_estado_credito(credito.id), EstadoCredito.ACTIVO)
        for c in plan:
            self.pago_svc.registrar_pago(credito.id, c.id, c.monto)
        self.assertEqual(self.credito_svc.determinar_estado_credito(credito.id), EstadoCredito.PAGADO)

    def test_fecha_referencia_futura_marca_mora(self):
        credito = self.credito_svc.crear_credito(
            self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL
        )
        self.credito_svc.actualizar_cuotas_en_mora(date.today() + timedelta(days=365))
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertTrue(all(c.en_mora for c in plan))

    def test_migracion_agrega_columna_en_mora(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE cuotas (id INTEGER PRIMARY KEY, credito_id INTEGER, numero_cuota INTEGER, "
                     "fecha_vencimiento TEXT, monto TEXT, estado TEXT DEFAULT 'PENDIENTE')")
        crear_tablas(conn)
        columnas = [r[1] for r in conn.execute("PRAGMA table_info(cuotas)").fetchall()]
        self.assertIn("en_mora", columnas)
        conn.close()


if __name__ == "__main__":
    unittest.main()
