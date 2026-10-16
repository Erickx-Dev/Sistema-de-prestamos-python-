import sqlite3
from datetime import date
from typing import Optional

from credito_app.modules.cliente import Cliente
from credito_app.modules.credito import Credito
from credito_app.modules.excepciones import ClienteNoEncontradoError, DatosInvalidosError
from credito_app.database.repositories.cliente_repository import ClienteRepository
from credito_app.database.repositories.credito_repository import CreditoRepository


class ClienteService:
    """Servicio para la gestión de clientes."""

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.conn = conn
        self.cliente_repo = ClienteRepository(conn)
        self.credito_repo = CreditoRepository(conn)

    def crear_cliente(self, nombre: str, telefono: str, documento: str) -> Cliente:
        """
        Crea un nuevo cliente.
        """
        nombre = nombre.strip() if nombre else ""
        telefono = telefono.strip() if telefono else ""
        documento = documento.strip() if documento else ""

        if not nombre:
            raise DatosInvalidosError("El nombre no puede estar vacío.")
        if not telefono:
            raise DatosInvalidosError("El teléfono no puede estar vacío.")
        if not documento:
            raise DatosInvalidosError("El documento no puede estar vacío.")

        if self.cliente_repo.obtener_por_documento(documento):
            raise DatosInvalidosError(f"Ya existe un cliente con el documento: {documento}")

        cliente = Cliente(nombre=nombre, telefono=telefono, documento=documento, fecha_registro=date.today())

        cliente_creado = self.cliente_repo.crear(cliente)
        self.conn.commit()
        return cliente_creado

    def obtener_cliente(self, cliente_id: int) -> Cliente:
        """
        Obtiene un cliente por su ID.
        """
        cliente = self.cliente_repo.obtener_por_id(cliente_id)
        if not cliente:
            raise ClienteNoEncontradoError(f"Cliente con ID {cliente_id} no encontrado.")
        return cliente

    def buscar_clientes(self, nombre: str) -> list[Cliente]:
        """
        Busca clientes por su nombre.
        """
        return self.cliente_repo.buscar_general(nombre)

    def obtener_por_documento(self, documento: str) -> Optional[Cliente]:
        """
        Obtiene un cliente por su documento de identidad.
        """
        return self.cliente_repo.obtener_por_documento(documento.strip())

    def actualizar_cliente(
        self,
        cliente_id: int,
        nombre: Optional[str] = None,
        telefono: Optional[str] = None,
        documento: Optional[str] = None,
    ) -> Cliente:
        """
        Actualiza los datos de un cliente existente.
        """
        cliente = self.obtener_cliente(cliente_id)

        if nombre is not None:
            nombre = nombre.strip()
            if not nombre:
                raise DatosInvalidosError("El nombre no puede estar vacío.")
            cliente.nombre = nombre

        if telefono is not None:
            telefono = telefono.strip()
            if not telefono:
                raise DatosInvalidosError("El teléfono no puede estar vacío.")
            cliente.telefono = telefono

        if documento is not None:
            documento = documento.strip()
            if not documento:
                raise DatosInvalidosError("El documento no puede estar vacío.")

            if documento != cliente.documento:
                if self.cliente_repo.obtener_por_documento(documento):
                    raise DatosInvalidosError(f"Ya existe un cliente con el documento: {documento}")
            cliente.documento = documento

        self.cliente_repo.actualizar(cliente)
        self.conn.commit()
        return cliente

    def obtener_creditos_cliente(self, cliente_id: int) -> list[Credito]:
        """
        Obtiene todos los créditos de un cliente específico.
        """
        self.obtener_cliente(cliente_id)  # Valida que el cliente exista
        return self.credito_repo.obtener_por_cliente(cliente_id)
