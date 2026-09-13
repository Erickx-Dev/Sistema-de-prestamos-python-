import unittest
import tempfile
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import date

from credito_app.database.schema import crear_tablas
from credito_app.database.connection import get_connection
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.services.pago_service import PagoService
from credito_app.services.pdf_service import PDFService, PDFServiceError
from credito_app.modules.credito import FrecuenciaPago
from credito_app.modules.excepciones import PagoInvalidoError


class TestPDFService(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        crear_tablas(self.conn)
        self.conn.commit()

        self.temp_dir = tempfile.mkdtemp()
        self.pdf_service = PDFService(default_output_dir=Path(self.temp_dir))

        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)
        self.pago_svc = PagoService(self.conn)

        self.cliente = self.cliente_svc.crear_cliente(
            nombre="Carlos Andrés Mendoza",
            telefono="3119876543",
            documento="CC-1098765432"
        )
        self.credito = self.credito_svc.crear_credito(
            cliente_id=self.cliente.id,
            capital=Decimal("500000"),
            plazo_meses=2,
            frecuencia=FrecuenciaPago.QUINCENAL
        )

        self.cuotas = self.credito_svc.obtener_plan_pagos(self.credito.id)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_obtener_datos_comprobante_exitoso(self):
        cuota = self.cuotas[0]
        monto_pago = Decimal("100000")
        pago = self.pago_svc.registrar_pago(self.credito.id, cuota.id, monto_pago)

        datos = self.pago_svc.obtener_datos_comprobante(pago.id)

        self.assertEqual(datos["pago_id"], pago.id)
        self.assertEqual(datos["numero_recibo"], f"REC-{pago.id:05d}")
        self.assertEqual(datos["cliente_nombre"], "Carlos Andrés Mendoza")
        self.assertEqual(datos["cliente_documento"], "CC-1098765432")
        self.assertEqual(datos["pago_monto"], monto_pago)
        self.assertEqual(datos["credito_id"], self.credito.id)
        self.assertEqual(datos["numero_cuota"], 1)
        self.assertEqual(datos["cuotas_total"], len(self.cuotas))
        self.assertIn("saldo_cuota_despues", datos)
        self.assertIn("saldo_credito_restante", datos)
        self.assertIn("porcentaje_pagado_credito", datos)

    def test_obtener_datos_comprobante_inexistente(self):
        with self.assertRaises(PagoInvalidoError):
            self.pago_svc.obtener_datos_comprobante(999999)

    def test_obtener_pago_por_id(self):
        cuota = self.cuotas[0]
        pago = self.pago_svc.registrar_pago(self.credito.id, cuota.id, Decimal("50000"))
        pago_obtenido = self.pago_svc.obtener_pago(pago.id)

        self.assertIsNotNone(pago_obtenido)
        self.assertEqual(pago_obtenido.id, pago.id)
        self.assertEqual(pago_obtenido.monto, Decimal("50000"))

        pago_inexistente = self.pago_svc.obtener_pago(999999)
        self.assertIsNone(pago_inexistente)

    def test_generar_pdf_comprobante_archivo_valido(self):
        cuota = self.cuotas[0]
        pago = self.pago_svc.registrar_pago(self.credito.id, cuota.id, cuota.monto)
        datos = self.pago_svc.obtener_datos_comprobante(pago.id)

        archivo_destino = Path(self.temp_dir) / "comprobante_prueba.pdf"
        ruta_resultado = self.pdf_service.generar_comprobante_pago(datos, output_path=archivo_destino)

        self.assertTrue(ruta_resultado.exists())
        self.assertTrue(ruta_resultado.is_file())
        self.assertGreater(ruta_resultado.stat().st_size, 1000)

        # Verificar cabecera mágica de PDF
        with open(ruta_resultado, "rb") as f:
            cabecera = f.read(5)
            self.assertEqual(cabecera, b"%PDF-")

    def test_generar_pdf_sin_ruta_destino_usa_directorio_por_defecto(self):
        cuota = self.cuotas[1]
        pago = self.pago_svc.registrar_pago(self.credito.id, cuota.id, Decimal("80000"))
        datos = self.pago_svc.obtener_datos_comprobante(pago.id)

        ruta_resultado = self.pdf_service.generar_comprobante_pago(datos)

        self.assertTrue(ruta_resultado.exists())
        self.assertEqual(ruta_resultado.parent, Path(self.temp_dir))
        self.assertTrue(ruta_resultado.name.startswith("Recibo_REC-"))

    def test_sanitizar_nombre_archivo(self):
        sucio = 'Cliente: "Juan / Pedro" * <VIP>?|'
        limpio = self.pdf_service._sanitizar_nombre_archivo(sucio)
        self.assertNotIn(":", limpio)
        self.assertNotIn("/", limpio)
        self.assertNotIn('"', limpio)
        self.assertNotIn("<", limpio)
        self.assertNotIn(">", limpio)
        self.assertNotIn("?", limpio)
        self.assertNotIn("|", limpio)
        self.assertNotIn("*", limpio)

    def test_abrir_documento_inexistente_retorna_false(self):
        ruta_falsa = Path(self.temp_dir) / "no_existe.pdf"
        resultado = self.pdf_service.abrir_documento(ruta_falsa)
        self.assertFalse(resultado)

    def test_generar_pdf_con_pago_parcial(self):
        cuota = self.cuotas[0]
        # Pago menor al total de la cuota
        abono = Decimal("30000")
        pago = self.pago_svc.registrar_pago(self.credito.id, cuota.id, abono)
        datos = self.pago_svc.obtener_datos_comprobante(pago.id)

        self.assertEqual(datos["saldo_cuota_despues"], cuota.monto - abono)
        archivo_salida = Path(self.temp_dir) / "recibo_parcial.pdf"
        ruta = self.pdf_service.generar_comprobante_pago(datos, output_path=archivo_salida)
        self.assertTrue(ruta.exists())
        self.assertGreater(ruta.stat().st_size, 1000)

    def test_generar_pdf_liquidacion_total_credito(self):
        # Pagar todas las cuotas
        for cuota in self.cuotas:
            self.pago_svc.registrar_pago(self.credito.id, cuota.id, cuota.monto)

        ultimo_pago = self.pago_svc.listar_pagos()[-1]
        datos = self.pago_svc.obtener_datos_comprobante(ultimo_pago.id)

        self.assertEqual(datos["saldo_credito_restante"], Decimal("0.00"))
        self.assertEqual(datos["porcentaje_pagado_credito"], Decimal("100.0"))

        archivo_salida = Path(self.temp_dir) / "recibo_final.pdf"
        ruta = self.pdf_service.generar_comprobante_pago(datos, output_path=archivo_salida)
        self.assertTrue(ruta.exists())
        self.assertGreater(ruta.stat().st_size, 1000)

    def test_generar_pdf_con_datos_invalidos_lanza_excepcion(self):
        with self.assertRaises(PDFServiceError):
            self.pdf_service.generar_comprobante_pago({})

    def test_generar_pdf_sin_qrcode(self):
        import credito_app.services.pdf_service as pdf_mod
        original_val = pdf_mod.QRCODE_AVAILABLE
        try:
            pdf_mod.QRCODE_AVAILABLE = False
            cuota = self.cuotas[0]
            pago = self.pago_svc.registrar_pago(self.credito.id, cuota.id, Decimal("40000"))
            datos = self.pago_svc.obtener_datos_comprobante(pago.id)

            archivo_salida = Path(self.temp_dir) / "recibo_sin_qr.pdf"
            ruta = self.pdf_service.generar_comprobante_pago(datos, output_path=archivo_salida)
            self.assertTrue(ruta.exists())
            self.assertGreater(ruta.stat().st_size, 1000)
        finally:
            pdf_mod.QRCODE_AVAILABLE = original_val


if __name__ == "__main__":
    unittest.main()

