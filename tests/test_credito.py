import sqlite3
import unittest
from datetime import date
from decimal import Decimal

from credito_app.database.schema import crear_tablas
from credito_app.database.connection import get_connection
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.modules.credito import FrecuenciaPago, EstadoCredito
from credito_app.modules.excepciones import ClienteNoEncontradoError, MontoInvalidoError


def get_test_connection() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    crear_tablas(conn)
    conn.commit()
    return conn


class TestCreditoService(unittest.TestCase):
    def setUp(self):
        self.conn = get_test_connection()
        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)

        self.cliente = self.cliente_svc.crear_cliente("Cliente Prueba", "0000", "DOC1")

    def tearDown(self):
        self.conn.close()

    # Interest calculation tests
    def test_interes_1M_12pct_1mes(self):
        intereses = self.credito_svc.calcular_intereses(Decimal("1000000"), Decimal("0.12"), 1)
        self.assertEqual(intereses, Decimal("120000"))

    def test_interes_1M_12pct_3meses(self):
        intereses = self.credito_svc.calcular_intereses(Decimal("1000000"), Decimal("0.12"), 3)
        self.assertEqual(intereses, Decimal("360000"))

    def test_interes_500k_12pct_6meses(self):
        intereses = self.credito_svc.calcular_intereses(Decimal("500000"), Decimal("0.12"), 6)
        self.assertEqual(intereses, Decimal("360000"))

    # Cuota calculation tests
    def test_cuotas_semanal_3meses(self):
        cuotas = self.credito_svc.calcular_numero_cuotas(3, FrecuenciaPago.SEMANAL)
        self.assertEqual(cuotas, 12)

    def test_cuotas_quincenal_3meses(self):
        cuotas = self.credito_svc.calcular_numero_cuotas(3, FrecuenciaPago.QUINCENAL)
        self.assertEqual(cuotas, 6)

    def test_cuotas_semanal_6meses(self):
        cuotas = self.credito_svc.calcular_numero_cuotas(6, FrecuenciaPago.SEMANAL)
        self.assertEqual(cuotas, 24)

    def test_cuotas_quincenal_1mes(self):
        cuotas = self.credito_svc.calcular_numero_cuotas(1, FrecuenciaPago.QUINCENAL)
        self.assertEqual(cuotas, 2)

    # Credit creation tests
    def test_crear_credito_semanal(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        self.assertEqual(credito.total_intereses, Decimal("360000"))
        self.assertEqual(credito.total_pagar, Decimal("1360000"))
        self.assertEqual(credito.estado, EstadoCredito.ACTIVO)

        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(len(plan), 12)

        suma_cuotas = sum(c.monto for c in plan)
        self.assertEqual(suma_cuotas, Decimal("1360000"))

    def test_crear_credito_quincenal(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.QUINCENAL)
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(len(plan), 6)

    def test_crear_credito_capital_invalido(self):
        with self.assertRaises(MontoInvalidoError):
            self.credito_svc.crear_credito(self.cliente.id, Decimal("0"), 3, FrecuenciaPago.SEMANAL)

    def test_crear_credito_cliente_inexistente(self):
        with self.assertRaises(ClienteNoEncontradoError):
            self.credito_svc.crear_credito(999, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)

    # Payment plan tests
    def test_fechas_vencimiento_semanal(self):
        credito = self.credito_svc.crear_credito(
            self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL, fecha_inicio=date(2023, 1, 1)
        )
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        delta = plan[1].fecha_vencimiento - plan[0].fecha_vencimiento
        self.assertEqual(delta.days, 7)

    def test_fechas_vencimiento_quincenal(self):
        credito = self.credito_svc.crear_credito(
            self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.QUINCENAL, fecha_inicio=date(2023, 1, 1)
        )
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        delta = plan[1].fecha_vencimiento - plan[0].fecha_vencimiento
        self.assertEqual(delta.days, 15)

    def test_suma_cuotas_igual_total(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(sum(c.monto for c in plan), credito.total_pagar)

    # Balance tests
    def test_saldo_sin_pagos(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        saldo = self.credito_svc.calcular_saldo_pendiente(credito.id)
        self.assertEqual(saldo, credito.total_pagar)

    def test_saldo_con_pagos(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        plan = self.credito_svc.obtener_plan_pagos(credito.id)

        self.pago_svc.registrar_pago(credito.id, plan[0].id, plan[0].monto)
        saldo = self.credito_svc.calcular_saldo_pendiente(credito.id)
        self.assertEqual(saldo, credito.total_pagar - plan[0].monto)

    # State tests
    def test_estado_activo(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        estado = self.credito_svc.determinar_estado_credito(credito.id)
        self.assertEqual(estado, EstadoCredito.ACTIVO)

    def test_estado_pagado(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        plan = self.credito_svc.obtener_plan_pagos(credito.id)
        for cuota in plan:
            self.pago_svc.registrar_pago(credito.id, cuota.id, cuota.monto)

        estado = self.credito_svc.determinar_estado_credito(credito.id)
        self.assertEqual(estado, EstadoCredito.PAGADO)

    def test_calcular_intereses_validaciones(self):
        with self.assertRaises(MontoInvalidoError):
            self.credito_svc.calcular_intereses(Decimal("0"), Decimal("0.10"), 1)
        with self.assertRaises(Exception):
            self.credito_svc.calcular_intereses(Decimal("100000"), Decimal("-0.01"), 1)
        with self.assertRaises(Exception):
            self.credito_svc.calcular_intereses(Decimal("100000"), Decimal("0.10"), 0)

    def test_crear_credito_plazo_invalido_y_frecuencia_desconocida(self):
        with self.assertRaises(Exception):
            self.credito_svc.crear_credito(self.cliente.id, Decimal("100000"), 0, FrecuenciaPago.SEMANAL)
        self.assertEqual(self.credito_svc.calcular_numero_cuotas(1, None), 0)

    def test_estado_cancelado_y_sin_cuotas(self):
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("100000"), 1, FrecuenciaPago.SEMANAL)
        self.credito_svc.credito_repo.actualizar_estado(credito.id, EstadoCredito.CANCELADO)
        self.assertEqual(self.credito_svc.determinar_estado_credito(credito.id), EstadoCredito.CANCELADO)
