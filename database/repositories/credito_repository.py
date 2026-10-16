import sqlite3
from decimal import Decimal
from datetime import date
from typing import Optional

from credito_app.modules.credito import Credito, Cuota, FrecuenciaPago, EstadoCredito, EstadoCuota

class CreditoRepository:
    """
    Repositorio para gestionar las operaciones de base de datos de los créditos y cuotas.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el repositorio con una conexión a la base de datos."""
        self.conn = conn

    def _row_to_credito(self, row: sqlite3.Row) -> Credito:
        """Convierte una fila de la base de datos en un objeto Credito."""
        return Credito(
            id=row["id"],
            cliente_id=row["cliente_id"],
            capital=Decimal(row["capital"]),
            tasa_mensual=Decimal(row["tasa_mensual"]),
            plazo_meses=row["plazo_meses"],
            total_intereses=Decimal(row["total_intereses"]),
            total_pagar=Decimal(row["total_pagar"]),
            frecuencia_pago=FrecuenciaPago(row["frecuencia_pago"]),
            fecha_inicio=date.fromisoformat(row["fecha_inicio"]),
            estado=EstadoCredito(row["estado"])
        )

    def _row_to_cuota(self, row: sqlite3.Row) -> Cuota:
        """Convierte una fila de la base de datos en un objeto Cuota."""
        return Cuota(
            id=row["id"],
            credito_id=row["credito_id"],
            numero_cuota=row["numero_cuota"],
            fecha_vencimiento=date.fromisoformat(row["fecha_vencimiento"]),
            monto=Decimal(row["monto"]),
            estado=EstadoCuota(row["estado"]),
            en_mora=bool(row["en_mora"])
        )

    def crear(self, credito: Credito) -> Credito:
        """Crea un nuevo crédito en la base de datos."""
        cursor = self.conn.cursor()
        query = """
            INSERT INTO creditos (
                cliente_id, capital, tasa_mensual, plazo_meses,
                total_intereses, total_pagar, frecuencia_pago,
                fecha_inicio, estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(
            query,
            (
                credito.cliente_id,
                str(credito.capital),
                str(credito.tasa_mensual),
                credito.plazo_meses,
                str(credito.total_intereses),
                str(credito.total_pagar),
                credito.frecuencia_pago.value,
                credito.fecha_inicio.isoformat(),
                credito.estado.value
            )
        )
        self.conn.commit()
        credito.id = cursor.lastrowid
        return credito

    def obtener_por_id(self, credito_id: int) -> Optional[Credito]:
        """Obtiene un crédito por su ID."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM creditos WHERE id = ?"
        cursor.execute(query, (credito_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_credito(row)
        return None

    def obtener_por_cliente(self, cliente_id: int) -> list[Credito]:
        """Obtiene todos los créditos asociados a un cliente."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM creditos WHERE cliente_id = ?"
        cursor.execute(query, (cliente_id,))
        rows = cursor.fetchall()
        return [self._row_to_credito(row) for row in rows]

    def actualizar_estado(self, credito_id: int, estado: EstadoCredito) -> None:
        """Actualiza el estado de un crédito."""
        cursor = self.conn.cursor()
        query = "UPDATE creditos SET estado = ? WHERE id = ?"
        cursor.execute(query, (estado.value, credito_id))
        self.conn.commit()

    def crear_cuota(self, cuota: Cuota) -> Cuota:
        """Crea una nueva cuota en la base de datos."""
        cursor = self.conn.cursor()
        query = """
            INSERT INTO cuotas (credito_id, numero_cuota, fecha_vencimiento, monto, estado, en_mora)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(
            query,
            (
                cuota.credito_id,
                cuota.numero_cuota,
                cuota.fecha_vencimiento.isoformat(),
                str(cuota.monto),
                cuota.estado.value,
                1 if cuota.en_mora else 0
            )
        )
        self.conn.commit()
        cuota.id = cursor.lastrowid
        return cuota

    def obtener_cuotas_por_credito(self, credito_id: int) -> list[Cuota]:
        """Obtiene todas las cuotas de un crédito, ordenadas por número de cuota."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM cuotas WHERE credito_id = ? ORDER BY numero_cuota ASC"
        cursor.execute(query, (credito_id,))
        rows = cursor.fetchall()
        return [self._row_to_cuota(row) for row in rows]

    def obtener_cuota_por_id(self, cuota_id: int) -> Optional[Cuota]:
        """Obtiene una cuota por su ID."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM cuotas WHERE id = ?"
        cursor.execute(query, (cuota_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_cuota(row)
        return None

    def actualizar_estado_cuota(self, cuota_id: int, estado: EstadoCuota) -> None:
        """Actualiza el estado de una cuota. Si queda PAGADA, deja de estar en mora."""
        cursor = self.conn.cursor()
        query = """
            UPDATE cuotas
            SET estado = ?,
                en_mora = CASE WHEN ? = 'PAGADA' THEN 0 ELSE en_mora END
            WHERE id = ?
        """
        cursor.execute(query, (estado.value, estado.value, cuota_id))
        self.conn.commit()

    def actualizar_mora_cuotas(self, fecha_referencia: date) -> int:
        """Sincroniza el indicador en_mora de todas las cuotas.

        Marca en_mora = 1 en cuotas PENDIENTE o PARCIAL con fecha_vencimiento anterior a
        fecha_referencia (conservando su estado), y en_mora = 0 en el resto.
        Retorna la cantidad de cuotas cuyo indicador cambió.
        """
        cursor = self.conn.cursor()
        fecha_str = fecha_referencia.isoformat()
        cursor.execute(
            """
            UPDATE cuotas
            SET en_mora = CASE
                WHEN estado IN ('PENDIENTE', 'PARCIAL') AND fecha_vencimiento < ? THEN 1
                ELSE 0
            END
            WHERE en_mora != CASE
                WHEN estado IN ('PENDIENTE', 'PARCIAL') AND fecha_vencimiento < ? THEN 1
                ELSE 0
            END
            """,
            (fecha_str, fecha_str)
        )
        afectadas = cursor.rowcount
        self.conn.commit()
        return afectadas

    def listar_todos(self) -> list[Credito]:
        """Obtiene todos los créditos del sistema."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM creditos")
        return [self._row_to_credito(row) for row in cursor.fetchall()]

    def listar_todas_las_cuotas(self) -> list[Cuota]:
        """Obtiene todas las cuotas de todos los créditos ordenadas por vencimiento."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cuotas ORDER BY fecha_vencimiento ASC, numero_cuota ASC")
        return [self._row_to_cuota(row) for row in cursor.fetchall()]

    def obtener_cuotas_pendientes(self, limite: int = 10) -> list[dict]:
        """Obtiene las próximas cuotas pendientes de todos los créditos con info del cliente.
        Returns list of dicts with keys: cuota_id, credito_id, numero_cuota, fecha_vencimiento, monto, estado, cliente_nombre, cliente_id
        """
        cursor = self.conn.cursor()
        query = """
            SELECT c.id as cuota_id, c.credito_id, c.numero_cuota, c.fecha_vencimiento,
                   c.monto, c.estado, c.en_mora, cl.nombre as cliente_nombre, cl.id as cliente_id
            FROM cuotas c
            JOIN creditos cr ON c.credito_id = cr.id
            JOIN clientes cl ON cr.cliente_id = cl.id
            WHERE c.estado IN ('PENDIENTE', 'PARCIAL')
            ORDER BY c.fecha_vencimiento ASC
            LIMIT ?
        """
        cursor.execute(query, (limite,))
        results = []
        for row in cursor.fetchall():
            results.append({
                "cuota_id": row["cuota_id"],
                "credito_id": row["credito_id"],
                "numero_cuota": row["numero_cuota"],
                "fecha_vencimiento": date.fromisoformat(row["fecha_vencimiento"]),
                "monto": Decimal(row["monto"]),
                "estado": EstadoCuota(row["estado"]),
                "en_mora": bool(row["en_mora"]),
                "cliente_nombre": row["cliente_nombre"],
                "cliente_id": row["cliente_id"],
            })
        return results
