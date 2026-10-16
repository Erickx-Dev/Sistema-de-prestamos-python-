import sqlite3
import unittest
from decimal import Decimal

from credito_app.database.schema import crear_tablas
from credito_app.database.connection import get_connection
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.modules.credito import FrecuenciaPago, EstadoCredito, EstadoCuota
from credito_app.modules.excepciones import CuotaNoEncontradaError, MontoInvalidoError, PagoInvalidoError


def get_test_connection() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    crear_tablas(conn)
    conn.commit()
    return conn


class TestPagoService(unittest.TestCase):
    def setUp(self):
        self.conn = get_test_connection()
        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)

        self.cliente = self.cliente_svc.crear_cliente("Cliente Prueba", "0000", "DOC1")
        self.credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("1000000"), 3, FrecuenciaPago.SEMANAL)
        self.plan = self.credito_svc.obtener_plan_pagos(self.credito.id)

    def tearDown(self):
        self.conn.close()

    def test_pago_completo(self):
        cuota = self.plan[0]
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, cuota.monto)

        plan_actualizado = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PAGADA)
        pagos = self.pago_svc.obtener_pagos_cuota(cuota.id)
        total_pagado = sum(p.monto for p in pagos)
        self.assertEqual(total_pagado, cuota.monto)

    def test_pago_parcial(self):
        cuota = self.plan[0]
        monto_pago = Decimal("50000")
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, monto_pago)

        plan_actualizado = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PARCIAL)
        pagos = self.pago_svc.obtener_pagos_cuota(cuota.id)
        total_pagado = sum(p.monto for p in pagos)
        self.assertEqual(total_pagado, monto_pago)

    def test_segundo_pago_parcial(self):
        cuota = self.plan[0]
        monto_pago = cuota.monto / 2
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, monto_pago)
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, monto_pago)

        plan_actualizado = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PAGADA)
        pagos = self.pago_svc.obtener_pagos_cuota(cuota.id)
        total_pagado = sum(p.monto for p in pagos)
        self.assertEqual(total_pagado, cuota.monto)

    def test_pago_que_completa_cuota(self):
        cuota = self.plan[0]
        monto_pago_1 = Decimal("10000")
        monto_pago_2 = cuota.monto - monto_pago_1
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, monto_pago_1)
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, monto_pago_2)

        plan_actualizado = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PAGADA)

    def test_multiples_cuotas_pagadas(self):
        self.pago_svc.registrar_pago(self.credito.id, self.plan[0].id, self.plan[0].monto)
        self.pago_svc.registrar_pago(self.credito.id, self.plan[1].id, self.plan[1].monto)
        self.pago_svc.registrar_pago(self.credito.id, self.plan[2].id, self.plan[2].monto)

        plan = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan[0].estado, EstadoCuota.PAGADA)
        self.assertEqual(plan[1].estado, EstadoCuota.PAGADA)
        self.assertEqual(plan[2].estado, EstadoCuota.PAGADA)
        self.assertEqual(plan[3].estado, EstadoCuota.PENDIENTE)

    def test_pago_cuota_inexistente(self):
        with self.assertRaises(CuotaNoEncontradaError):
            self.pago_svc.registrar_pago(self.credito.id, 999, Decimal("1000"))

    def test_pago_monto_invalido(self):
        with self.assertRaises(MontoInvalidoError):
            self.pago_svc.registrar_pago(self.credito.id, self.plan[0].id, Decimal("0"))

    def test_pago_excede_saldo_cuota(self):
        with self.assertRaises(MontoInvalidoError):
            self.pago_svc.registrar_pago(self.credito.id, self.plan[0].id, self.plan[0].monto + Decimal("1"))

    def test_pago_cuota_ya_pagada(self):
        self.pago_svc.registrar_pago(self.credito.id, self.plan[0].id, self.plan[0].monto)
        with self.assertRaises(PagoInvalidoError):
            self.pago_svc.registrar_pago(self.credito.id, self.plan[0].id, Decimal("1000"))

    def test_pago_cuota_no_pertenece_credito(self):
        credito_2 = self.credito_svc.crear_credito(self.cliente.id, Decimal("500000"), 1, FrecuenciaPago.QUINCENAL)
        with self.assertRaises(PagoInvalidoError):
            self.pago_svc.registrar_pago(credito_2.id, self.plan[0].id, Decimal("1000"))

    def test_historial_pagos(self):
        self.pago_svc.registrar_pago(self.credito.id, self.plan[0].id, self.plan[0].monto)
        self.pago_svc.registrar_pago(self.credito.id, self.plan[1].id, Decimal("50000"))

        pagos = self.pago_svc.obtener_historial_pagos(self.credito.id)
        self.assertEqual(len(pagos), 2)

    def test_transicion_pendiente_parcial_pagada(self):
        cuota = self.plan[0]
        # PENDIENTE
        self.assertEqual(cuota.estado, EstadoCuota.PENDIENTE)

        # PARCIAL
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, Decimal("10000"))
        plan = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan[0].estado, EstadoCuota.PARCIAL)

        # PAGADA
        restante = cuota.monto - Decimal("10000")
        self.pago_svc.registrar_pago(self.credito.id, cuota.id, restante)
        plan = self.credito_svc.obtener_plan_pagos(self.credito.id)
        self.assertEqual(plan[0].estado, EstadoCuota.PAGADA)

    def test_credito_pasa_a_pagado(self):
        for cuota in self.plan:
            self.pago_svc.registrar_pago(self.credito.id, cuota.id, cuota.monto)

        estado = self.credito_svc.determinar_estado_credito(self.credito.id)
        self.assertEqual(estado, EstadoCredito.PAGADO)

    def test_pago_cuota_con_decimales_exacto(self):
        from credito_app.ui.utils.validators import parsear_monto

        # Simular exactamente el caso del usuario: capital 100000, 3 meses, semanal (12 cuotas -> 11333.33)
        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("100000"), 3, FrecuenciaPago.SEMANAL)
        cuotas = self.credito_svc.obtener_plan_pagos(credito.id)
        cuota1 = cuotas[0]
        self.assertEqual(cuota1.monto, Decimal("11333.33"))

        # El usuario ingresa exactamente "11333.33"
        monto_ingresado = parsear_monto("11333.33")
        self.assertEqual(monto_ingresado, Decimal("11333.33"))

        # Debe permitir pagar exactamente ese monto sin lanzar MontoInvalidoError
        pago = self.pago_svc.registrar_pago(credito.id, cuota1.id, monto_ingresado)
        self.assertEqual(pago.monto, Decimal("11333.33"))

        # La cuota debe quedar pagada
        plan_actualizado = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PAGADA)

    def test_pago_parcial_inferior_con_decimales(self):
        from credito_app.ui.utils.validators import parsear_monto

        credito = self.credito_svc.crear_credito(self.cliente.id, Decimal("100000"), 3, FrecuenciaPago.SEMANAL)
        cuotas = self.credito_svc.obtener_plan_pagos(credito.id)
        cuota1 = cuotas[0]

        # El usuario ingresa un número muy inferior a la cuota, por ejemplo 500.00 o 500.50
        monto_500 = parsear_monto("500.00")
        self.assertEqual(monto_500, Decimal("500.00"))
        self.pago_svc.registrar_pago(credito.id, cuota1.id, monto_500)

        plan_actualizado = self.credito_svc.obtener_plan_pagos(credito.id)
        self.assertEqual(plan_actualizado[0].estado, EstadoCuota.PARCIAL)

        # Segundo pago parcial con coma o formato moneda
        monto_parcial_2 = parsear_monto("$ 1.000,50")
        self.assertEqual(monto_parcial_2, Decimal("1000.50"))
        self.pago_svc.registrar_pago(credito.id, cuota1.id, monto_parcial_2)

        pagos = self.pago_svc.obtener_pagos_cuota(cuota1.id)
        total_pagado = sum(p.monto for p in pagos)
        self.assertEqual(total_pagado, Decimal("1500.50"))

    def test_listar_pagos_con_detalle(self):
        cliente = self.cliente_svc.crear_cliente("María Gómez", "3009998877", "CC-778899")
        credito = self.credito_svc.crear_credito(cliente.id, Decimal("500000"), 1, FrecuenciaPago.QUINCENAL)
        plan = self.credito_svc.obtener_plan_pagos(credito.id)

        pago = self.pago_svc.registrar_pago(credito.id, plan[0].id, Decimal("100000"))
        detalles = self.pago_svc.listar_pagos_con_detalle()
        self.assertTrue(len(detalles) >= 1)

        pago_detalle = next(d for d in detalles if d["pago_id"] == pago.id)
        self.assertEqual(pago_detalle["cliente_nombre"], "María Gómez")
        self.assertEqual(pago_detalle["credito_id"], credito.id)
        self.assertEqual(pago_detalle["cuota_id"], plan[0].id)
        self.assertEqual(pago_detalle["numero_cuota"], 1)
        self.assertEqual(pago_detalle["monto"], Decimal("100000"))
