import sqlite3
import unittest
from datetime import date, timedelta
from decimal import Decimal

from credito_app.database.schema import crear_tablas
from credito_app.database.connection import get_connection
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.services.reporte_service import ReporteService
from credito_app.modules.credito import FrecuenciaPago, EstadoCredito
from credito_app.modules.excepciones import DatosInvalidosError


def get_test_connection() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    crear_tablas(conn)
    conn.commit()
    return conn


class TestReporteService(unittest.TestCase):
    def setUp(self):
        self.conn = get_test_connection()
        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)
        self.reporte_svc = ReporteService(self.conn)

        self.cliente = self.cliente_svc.crear_cliente("Juan Pérez", "3001234567", "12345678")

    def tearDown(self):
        self.conn.close()

    def test_calcular_rango_todos(self):
        desde, hasta = self.reporte_svc.calcular_rango_fechas("Todos")
        self.assertIsNone(desde)
        self.assertIsNone(hasta)

    def test_calcular_rango_hoy(self):
        ref = date(2026, 9, 5)
        desde, hasta = self.reporte_svc.calcular_rango_fechas("Hoy", fecha_referencia=ref)
        self.assertEqual(desde, ref)
        self.assertEqual(hasta, ref)

    def test_calcular_rango_esta_semana(self):
        # 2026-09-05 is a Saturday. Monday is 2026-08-31, Sunday is 2026-09-06
        ref = date(2026, 9, 5)
        desde, hasta = self.reporte_svc.calcular_rango_fechas("Esta Semana", fecha_referencia=ref)
        self.assertEqual(desde, date(2026, 8, 31))
        self.assertEqual(hasta, date(2026, 9, 6))

    def test_calcular_rango_este_mes(self):
        ref = date(2026, 2, 14)  # February 2026 has 28 days
        desde, hasta = self.reporte_svc.calcular_rango_fechas("Este Mes", fecha_referencia=ref)
        self.assertEqual(desde, date(2026, 2, 1))
        self.assertEqual(hasta, date(2026, 2, 28))

    def test_calcular_rango_este_anio(self):
        ref = date(2026, 5, 20)
        desde, hasta = self.reporte_svc.calcular_rango_fechas("Año en curso", fecha_referencia=ref)
        self.assertEqual(desde, date(2026, 1, 1))
        self.assertEqual(hasta, date(2026, 12, 31))

    def test_calcular_rango_invalido(self):
        with self.assertRaises(DatosInvalidosError):
            self.reporte_svc.calcular_rango_fechas("Filtro_Inexistente")

    def test_metricas_base_datos_vacia(self):
        metricas = self.reporte_svc.obtener_metricas()
        self.assertEqual(metricas["activos"], 0)
        self.assertEqual(metricas["pagados"], 0)
        self.assertEqual(metricas["total"], 0)
        self.assertEqual(metricas["capital_prestado"], Decimal("0"))
        self.assertEqual(metricas["intereses_generados"], Decimal("0"))
        self.assertEqual(metricas["pagos_recibidos"], Decimal("0"))

    def test_metricas_historico_con_datos(self):
        # Crédito 1: Creado en 2026-01-10
        c1 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("100000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 1, 10),
        )

        # Crédito 2: Creado en 2026-02-15
        c2 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("200000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 2, 15),
        )

        cuotas_c1 = self.credito_svc.obtener_plan_pagos(c1.id)
        # Pago 1 en 2026-01-15
        self.pago_svc.registrar_pago(
            credito_id=c1.id,
            cuota_id=cuotas_c1[0].id,
            monto=Decimal("15000"),
            fecha_pago=date(2026, 1, 15),
        )

        # Pago 2 en 2026-02-20
        self.pago_svc.registrar_pago(
            credito_id=c1.id,
            cuota_id=cuotas_c1[1].id,
            monto=Decimal("20000"),
            fecha_pago=date(2026, 2, 20),
        )

        # Sin filtro (histórico total)
        metricas = self.reporte_svc.obtener_metricas()
        self.assertEqual(metricas["total"], 2)
        self.assertEqual(metricas["activos"], 2)
        self.assertEqual(metricas["capital_prestado"], Decimal("300000"))
        self.assertEqual(metricas["intereses_generados"], Decimal("30000"))
        self.assertEqual(metricas["pagos_recibidos"], Decimal("35000"))

    def test_metricas_filtradas_por_rango(self):
        # Crédito en Enero
        c1 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("100000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 1, 10),
        )
        # Crédito en Febrero
        c2 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("200000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 2, 15),
        )

        cuotas_c1 = self.credito_svc.obtener_plan_pagos(c1.id)
        # Pago en Enero
        self.pago_svc.registrar_pago(
            credito_id=c1.id,
            cuota_id=cuotas_c1[0].id,
            monto=Decimal("27500"),
            fecha_pago=date(2026, 1, 20),
        )
        # Pago en Febrero
        self.pago_svc.registrar_pago(
            credito_id=c1.id,
            cuota_id=cuotas_c1[1].id,
            monto=Decimal("27500"),
            fecha_pago=date(2026, 2, 20),
        )

        # Filtrar solo Febrero (2026-02-01 al 2026-02-28)
        metricas_feb = self.reporte_svc.obtener_metricas(
            fecha_desde=date(2026, 2, 1),
            fecha_hasta=date(2026, 2, 28),
        )
        # En febrero solo se originó c2
        self.assertEqual(metricas_feb["total"], 1)
        self.assertEqual(metricas_feb["capital_prestado"], Decimal("200000"))
        self.assertEqual(metricas_feb["intereses_generados"], Decimal("20000"))
        # En febrero solo se realizó 1 pago
        self.assertEqual(metricas_feb["pagos_recibidos"], Decimal("27500"))

        # Filtrar solo Enero (2026-01-01 al 2026-01-31)
        metricas_ene = self.reporte_svc.obtener_metricas(
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
        )
        self.assertEqual(metricas_ene["total"], 1)
        self.assertEqual(metricas_ene["capital_prestado"], Decimal("100000"))
        self.assertEqual(metricas_ene["intereses_generados"], Decimal("10000"))
        self.assertEqual(metricas_ene["pagos_recibidos"], Decimal("27500"))

    def test_fechas_invalidas_lanza_error(self):
        with self.assertRaises(DatosInvalidosError):
            self.reporte_svc.obtener_metricas(
                fecha_desde=date(2026, 5, 10),
                fecha_hasta=date(2026, 5, 1),
            )

    def test_distribucion_cartera_clasificacion(self):
        # Crédito 1: Saldado (completamente pagado)
        c1 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("100000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 1, 1),
        )
        cuotas_c1 = self.credito_svc.obtener_plan_pagos(c1.id)
        for q in cuotas_c1:
            self.pago_svc.registrar_pago(c1.id, q.id, q.monto, fecha_pago=date(2026, 1, 15))
        self.credito_svc.determinar_estado_credito(c1.id)

        # Crédito 2: En mora (cuota vencida en el pasado no pagada)
        c2 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("200000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 1, 1),  # Cuotas vencieron en enero
        )

        # Crédito 3: Al día (crédito reciente con cuotas a futuro)
        c3 = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("300000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date.today(),  # Cuotas vencen en el futuro
        )

        distribucion = self.reporte_svc.obtener_distribucion_cartera()
        self.assertEqual(distribucion["saldados"]["cantidad"], 1)
        self.assertEqual(distribucion["saldados"]["capital"], Decimal("100000"))

        self.assertEqual(distribucion["en_mora"]["cantidad"], 1)
        self.assertEqual(distribucion["en_mora"]["capital"], Decimal("200000"))

        self.assertEqual(distribucion["al_dia"]["cantidad"], 1)
        self.assertEqual(distribucion["al_dia"]["capital"], Decimal("300000"))
        self.assertEqual(distribucion["total_creditos"], 3)

    def test_recaudo_vs_proyeccion_semanal(self):
        # Crédito con cuotas semanales a partir de hoy
        c = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("100000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date.today(),
        )
        cuotas = self.credito_svc.obtener_plan_pagos(c.id)
        # Registrar un pago en la fecha de la primera cuota
        q1 = cuotas[0]
        self.pago_svc.registrar_pago(c.id, q1.id, Decimal("10000"), fecha_pago=q1.fecha_vencimiento)

        semanas = self.reporte_svc.obtener_recaudo_vs_proyeccion_semanal(num_semanas=5)
        self.assertIsInstance(semanas, list)
        self.assertGreaterEqual(len(semanas), 1)
        # Cada semana debe tener keys requeridas
        for sem in semanas:
            self.assertIn("etiqueta", sem)
            self.assertIn("proyectado", sem)
            self.assertIn("recaudado", sem)
            self.assertIn("inicio", sem)
            self.assertIn("fin", sem)

    def test_fechas_invalidas_distribucion_y_proyeccion(self):
        with self.assertRaises(DatosInvalidosError):
            self.reporte_svc.obtener_distribucion_cartera(
                fecha_desde=date(2026, 8, 10), fecha_hasta=date(2026, 8, 1)
            )

        with self.assertRaises(DatosInvalidosError):
            self.reporte_svc.obtener_recaudo_vs_proyeccion_semanal(
                fecha_desde=date(2026, 8, 10), fecha_hasta=date(2026, 8, 1)
            )

    def test_metricas_avanzadas_morosidad(self):
        # Crédito otorgado en el pasado cuyas cuotas ya vencieron
        c = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("100000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date(2026, 1, 1),
        )
        metricas = self.reporte_svc.obtener_metricas()
        self.assertGreater(metricas["saldo_vencido"], Decimal("0"))
        self.assertGreater(metricas["tasa_morosidad"], Decimal("0"))
        # El total a pagar es 110.000 sobre 100.000 de capital -> 110% de morosidad
        self.assertEqual(metricas["tasa_morosidad"], Decimal("110.00"))

    def test_metricas_avanzadas_intereses_cobrados(self):
        # Crédito: 1.000.000 capital, 10% mensual x 1 mes = 100.000 interés, 1.100.000 total (4 cuotas de 275.000)
        c = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("1000000"),
            plazo_meses=1,
            frecuencia=FrecuenciaPago.SEMANAL,
            tasa_mensual=Decimal("0.10"),
            fecha_inicio=date.today(),
        )
        cuotas = self.credito_svc.obtener_plan_pagos(c.id)
        # Pagar 1 cuota de 275.000 -> la porción de interés es 275.000 * (100.000 / 1.100.000) = 25.000
        self.pago_svc.registrar_pago(c.id, cuotas[0].id, Decimal("275000"), fecha_pago=date.today())

        metricas = self.reporte_svc.obtener_metricas()
        self.assertEqual(metricas["intereses_cobrados"], Decimal("25000.00"))
        self.assertEqual(metricas["pagos_recibidos"], Decimal("275000.00"))
        # Margen: 25.000 / 275.000 = 9.09%
        self.assertEqual(metricas["margen_ganancia"], Decimal("9.09"))

    def test_metricas_avanzadas_ticket_y_plazo_promedio(self):
        # Crédito 1: 1.000.000 a 2 meses
        self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("1000000"),
            plazo_meses=2,
            frecuencia=FrecuenciaPago.SEMANAL,
            fecha_inicio=date.today(),
        )
        # Crédito 2: 2.000.000 a 4 meses
        self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("2000000"),
            plazo_meses=4,
            frecuencia=FrecuenciaPago.SEMANAL,
            fecha_inicio=date.today(),
        )

        metricas = self.reporte_svc.obtener_metricas()
        # Ticket: (1.000.000 + 2.000.000) / 2 = 1.500.000
        self.assertEqual(metricas["ticket_promedio"], Decimal("1500000.00"))
        # Plazo: (2 + 4) / 2 = 3.0 meses
        self.assertEqual(metricas["plazo_promedio"], Decimal("3.0"))


if __name__ == "__main__":
    unittest.main()
