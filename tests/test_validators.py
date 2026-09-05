import unittest
from decimal import Decimal
from credito_app.ui.utils.validators import (
    validar_monto,
    parsear_monto,
    validar_texto_no_vacio,
    validar_entero_positivo
)

class TestValidators(unittest.TestCase):
    def test_parsear_monto_formatos_validos(self):
        casos = [
            ("11333.33", Decimal("11333.33")),
            ("11333,33", Decimal("11333.33")),
            ("11.333,33", Decimal("11333.33")),
            ("11,333.33", Decimal("11333.33")),
            ("11.333.33", Decimal("11333.33")),
            ("11,333,33", Decimal("11333.33")),
            ("$11.333,33", Decimal("11333.33")),
            ("$ 11333.33", Decimal("11333.33")),
            ("11333", Decimal("11333")),
            ("500", Decimal("500")),
            ("500.00", Decimal("500.00")),
            ("500,00", Decimal("500.00")),
            ("500.50", Decimal("500.50")),
            ("500,50", Decimal("500.50")),
            ("500.5", Decimal("500.5")),
            ("500,5", Decimal("500.5")),
            ("1.000.000", Decimal("1000000")),
            ("1,000,000", Decimal("1000000")),
            ("1.000.000,50", Decimal("1000000.50")),
            ("1,000,000.50", Decimal("1000000.50")),
            ("10.000", Decimal("10000")),
            ("10,000", Decimal("10000")),
            ("100.000", Decimal("100000")),
            ("1.000", Decimal("1000")),
            ("1,000", Decimal("1000")),
            ("1.500", Decimal("1500")),
            ("1.50", Decimal("1.50")),
            ("1.5", Decimal("1.5")),
            (".50", Decimal("0.50")),
            (",50", Decimal("0.50")),
            ("0.5", Decimal("0.5")),
            ("0,5", Decimal("0.5")),
            ("11333.330", Decimal("11333.330")),
        ]
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                resultado = parsear_monto(texto)
                self.assertEqual(resultado, esperado)
                es_valido, msg = validar_monto(texto)
                self.assertTrue(es_valido, f"Error validando '{texto}': {msg}")

    def test_validar_monto_invalidos(self):
        casos_invalidos = [
            ("", "Ingresa un monto."),
            ("   ", "Ingresa un monto."),
            ("0", "El monto debe ser mayor a cero."),
            ("0.00", "El monto debe ser mayor a cero."),
            ("-100", "El monto debe ser mayor a cero."),
            ("-500.25", "El monto debe ser mayor a cero."),
            ("abc", "Ingresa un monto numérico válido."),
            ("$", "Ingresa un monto numérico válido."),
            ("12.34.56.78", "Ingresa un monto numérico válido."),
            ("12..34", "Ingresa un monto numérico válido."),
            ("1.23.456", "Ingresa un monto numérico válido."),
        ]
        for texto, msg_esperado in casos_invalidos:
            with self.subTest(texto=texto):
                es_valido, msg = validar_monto(texto)
                self.assertFalse(es_valido, f"Se esperaba inválido para '{texto}'")
                self.assertEqual(msg, msg_esperado)

    def test_validar_texto_no_vacio(self):
        valido, _ = validar_texto_no_vacio("Juan", "Nombre")
        self.assertTrue(valido)
        invalido, msg = validar_texto_no_vacio("   ", "Nombre")
        self.assertFalse(invalido)
        self.assertIn("obligatorio", msg)

    def test_validar_entero_positivo(self):
        valido, _ = validar_entero_positivo("5", "Plazo")
        self.assertTrue(valido)
        invalido, msg = validar_entero_positivo("0", "Plazo")
        self.assertFalse(invalido)
        invalido2, msg2 = validar_entero_positivo("abc", "Plazo")
        self.assertFalse(invalido2)
