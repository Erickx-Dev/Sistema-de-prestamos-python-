import sqlite3
import unittest

from credito_app.database.schema import crear_tablas
from credito_app.database.connection import get_connection
from credito_app.services.cliente_service import ClienteService
from credito_app.services.credito_service import CreditoService
from credito_app.modules.excepciones import ClienteNoEncontradoError, DatosInvalidosError


def get_test_connection() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    crear_tablas(conn)
    conn.commit()
    return conn


class TestClienteService(unittest.TestCase):
    def setUp(self):
        self.conn = get_test_connection()
        self.cliente_svc = ClienteService(self.conn)
        self.credito_svc = CreditoService(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_crear_cliente(self):
        cliente = self.cliente_svc.crear_cliente("Juan Perez", "123456789", "CC123")
        self.assertIsNotNone(cliente.id)
        self.assertEqual(cliente.nombre, "Juan Perez")
        self.assertEqual(cliente.telefono, "123456789")
        self.assertEqual(cliente.documento, "CC123")

    def test_crear_cliente_nombre_vacio(self):
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.crear_cliente("", "123456789", "CC124")

    def test_crear_cliente_documento_duplicado(self):
        self.cliente_svc.crear_cliente("Juan Perez", "123456789", "CC123")
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.crear_cliente("Maria Lopez", "987654321", "CC123")

    def test_obtener_cliente_existente(self):
        creado = self.cliente_svc.crear_cliente("Juan Perez", "123456789", "CC123")
        obtenido = self.cliente_svc.obtener_cliente(creado.id)
        self.assertEqual(creado.id, obtenido.id)
        self.assertEqual(creado.nombre, obtenido.nombre)

    def test_obtener_cliente_no_existente(self):
        with self.assertRaises(ClienteNoEncontradoError):
            self.cliente_svc.obtener_cliente(999)

    def test_buscar_clientes_por_nombre(self):
        self.cliente_svc.crear_cliente("Juan Perez", "111", "CC1")
        self.cliente_svc.crear_cliente("Juan Gonzalez", "222", "CC2")
        self.cliente_svc.crear_cliente("Maria Perez", "333", "CC3")

        resultados = self.cliente_svc.buscar_clientes("Juan")
        self.assertEqual(len(resultados), 2)

    def test_actualizar_cliente(self):
        cliente = self.cliente_svc.crear_cliente("Juan Perez", "111", "CC1")
        actualizado = self.cliente_svc.actualizar_cliente(cliente.id, nombre="Juan P.")
        self.assertEqual(actualizado.nombre, "Juan P.")
        self.assertEqual(actualizado.telefono, "111")

        db_cliente = self.cliente_svc.obtener_cliente(cliente.id)
        self.assertEqual(db_cliente.nombre, "Juan P.")

    def test_crear_cliente_telefono_y_documento_vacio(self):
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.crear_cliente("Juan", "", "CC123")
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.crear_cliente("Juan", "123", "")

    def test_actualizar_cliente_validaciones(self):
        c1 = self.cliente_svc.crear_cliente("Cliente Uno", "111", "DOC1")
        self.cliente_svc.crear_cliente("Cliente Dos", "222", "DOC2")

        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.actualizar_cliente(c1.id, nombre="  ")
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.actualizar_cliente(c1.id, telefono="  ")
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.actualizar_cliente(c1.id, documento="  ")
        with self.assertRaises(DatosInvalidosError):
            self.cliente_svc.actualizar_cliente(c1.id, documento="DOC2")

        # Actualización válida de teléfono y documento
        c1_up = self.cliente_svc.actualizar_cliente(c1.id, telefono="999", documento="DOC1_NUEVO")
        self.assertEqual(c1_up.telefono, "999")
        self.assertEqual(c1_up.documento, "DOC1_NUEVO")

        # Cliente no encontrado
        with self.assertRaises(ClienteNoEncontradoError):
            self.cliente_svc.actualizar_cliente(9999, nombre="Inexistente")
