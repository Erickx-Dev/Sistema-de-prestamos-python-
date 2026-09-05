import sqlite3
from datetime import date
from typing import Optional

from credito_app.modules.cliente import Cliente

class ClienteRepository:
    """
    Repositorio para gestionar las operaciones de base de datos de los clientes.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el repositorio con una conexión a la base de datos."""
        self.conn = conn

    def _row_to_cliente(self, row: sqlite3.Row) -> Cliente:
        """Convierte una fila de la base de datos en un objeto Cliente."""
        return Cliente(
            id=row["id"],
            nombre=row["nombre"],
            telefono=row["telefono"],
            documento=row["documento"],
            fecha_registro=date.fromisoformat(row["fecha_registro"])
        )

    def crear(self, cliente: Cliente) -> Cliente:
        """Crea un nuevo cliente en la base de datos."""
        cursor = self.conn.cursor()
        query = """
            INSERT INTO clientes (nombre, telefono, documento, fecha_registro)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(
            query,
            (
                cliente.nombre,
                cliente.telefono,
                cliente.documento,
                cliente.fecha_registro.isoformat()
            )
        )
        self.conn.commit()
        cliente.id = cursor.lastrowid
        return cliente

    def obtener_por_id(self, cliente_id: int) -> Optional[Cliente]:
        """Obtiene un cliente por su ID."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM clientes WHERE id = ?"
        cursor.execute(query, (cliente_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_cliente(row)
        return None

    def obtener_por_documento(self, documento: str) -> Optional[Cliente]:
        """Obtiene un cliente por su número de documento."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM clientes WHERE documento = ?"
        cursor.execute(query, (documento,))
        row = cursor.fetchone()
        if row:
            return self._row_to_cliente(row)
        return None

    def buscar_por_nombre(self, nombre: str) -> list[Cliente]:
        """Busca clientes cuyo nombre coincida parcialmente con el término de búsqueda."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM clientes WHERE nombre LIKE ?"
        cursor.execute(query, (f"%{nombre}%",))
        rows = cursor.fetchall()
        return [self._row_to_cliente(row) for row in rows]

    def actualizar(self, cliente: Cliente) -> None:
        """Actualiza la información de un cliente existente."""
        if not cliente.id:
            raise ValueError("El cliente debe tener un ID para ser actualizado.")
        cursor = self.conn.cursor()
        query = """
            UPDATE clientes
            SET nombre = ?, telefono = ?, documento = ?
            WHERE id = ?
        """
        cursor.execute(
            query,
            (cliente.nombre, cliente.telefono, cliente.documento, cliente.id)
        )
        self.conn.commit()

    def listar_todos(self) -> list[Cliente]:
        """Lista todos los clientes registrados."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM clientes"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [self._row_to_cliente(row) for row in rows]

    def buscar_general(self, termino: str) -> list[Cliente]:
        """Busca clientes por nombre o documento."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM clientes WHERE nombre LIKE ? OR documento LIKE ?"
        patron = f"%{termino}%"
        cursor.execute(query, (patron, patron))
        return [self._row_to_cliente(row) for row in cursor.fetchall()]
