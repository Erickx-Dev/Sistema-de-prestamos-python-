import sqlite3
from decimal import Decimal
from datetime import date
from typing import Optional

from credito_app.modules.pago import Pago


class PagoRepository:
    """
    Repositorio para gestionar las operaciones de base de datos de los pagos.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el repositorio con una conexión a la base de datos."""
        self.conn = conn

    def _row_to_pago(self, row: sqlite3.Row) -> Pago:
        """Convierte una fila de la base de datos en un objeto Pago."""
        return Pago(
            id=row["id"],
            credito_id=row["credito_id"],
            cuota_id=row["cuota_id"],
            monto=Decimal(row["monto"]),
            fecha_pago=date.fromisoformat(row["fecha_pago"]),
        )

    def crear(self, pago: Pago) -> Pago:
        """Registra un nuevo pago en la base de datos."""
        cursor = self.conn.cursor()
        query = """
            INSERT INTO pagos (credito_id, cuota_id, monto, fecha_pago)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(query, (pago.credito_id, pago.cuota_id, str(pago.monto), pago.fecha_pago.isoformat()))
        self.conn.commit()
        pago.id = cursor.lastrowid
        return pago

    def obtener_por_credito(self, credito_id: int) -> list[Pago]:
        """Obtiene todos los pagos realizados para un crédito específico."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM pagos WHERE credito_id = ?"
        cursor.execute(query, (credito_id,))
        rows = cursor.fetchall()
        return [self._row_to_pago(row) for row in rows]

    def obtener_por_cuota(self, cuota_id: int) -> list[Pago]:
        """Obtiene todos los pagos realizados para una cuota específica."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM pagos WHERE cuota_id = ?"
        cursor.execute(query, (cuota_id,))
        rows = cursor.fetchall()
        return [self._row_to_pago(row) for row in rows]

    def obtener_total_pagado_cuota(self, cuota_id: int) -> Decimal:
        """Calcula el monto total pagado para una cuota específica."""
        pagos = self.obtener_por_cuota(cuota_id)
        if not pagos:
            return Decimal("0")
        return sum((pago.monto for pago in pagos), start=Decimal("0"))

    def obtener_total_pagado_credito(self, credito_id: int) -> Decimal:
        """Calcula el monto total pagado para un crédito específico."""
        pagos = self.obtener_por_credito(credito_id)
        if not pagos:
            return Decimal("0")
        return sum((pago.monto for pago in pagos), start=Decimal("0"))

    def listar_todos(self) -> list[Pago]:
        """Obtiene todos los pagos del sistema."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pagos ORDER BY fecha_pago DESC")
        return [self._row_to_pago(row) for row in cursor.fetchall()]

    def listar_todos_con_detalle(self) -> list[dict]:
        """Obtiene todos los pagos con información del cliente y crédito.
        Returns list of dicts with keys: pago_id, credito_id, cuota_id, numero_cuota, fecha_pago, monto, cliente_nombre, cliente_id
        """
        cursor = self.conn.cursor()
        query = """
            SELECT p.id as pago_id, p.credito_id, p.cuota_id, cu.numero_cuota, p.fecha_pago, p.monto,
                   cl.nombre as cliente_nombre, cl.id as cliente_id
            FROM pagos p
            JOIN creditos cr ON p.credito_id = cr.id
            JOIN cuotas cu ON p.cuota_id = cu.id
            JOIN clientes cl ON cr.cliente_id = cl.id
            ORDER BY p.fecha_pago DESC, p.id DESC
        """
        cursor.execute(query)
        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "pago_id": row["pago_id"],
                    "credito_id": row["credito_id"],
                    "cuota_id": row["cuota_id"],
                    "numero_cuota": row["numero_cuota"],
                    "fecha_pago": date.fromisoformat(row["fecha_pago"]),
                    "monto": Decimal(row["monto"]),
                    "cliente_nombre": row["cliente_nombre"],
                    "cliente_id": row["cliente_id"],
                }
            )
        return results

    def obtener_por_id(self, pago_id: int) -> Optional[Pago]:
        """Obtiene un pago por su ID."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM pagos WHERE id = ?"
        cursor.execute(query, (pago_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_pago(row)

    def obtener_detalle_pago(self, pago_id: int) -> Optional[dict]:
        """Obtiene la información detallada de un pago con datos del cliente, crédito y cuota para el comprobante."""
        cursor = self.conn.cursor()
        query = """
            SELECT p.id as pago_id, p.credito_id, p.cuota_id, p.monto as pago_monto, p.fecha_pago,
                   cu.numero_cuota, cu.monto as cuota_monto, cu.fecha_vencimiento as cuota_fecha_vencimiento, cu.estado as cuota_estado,
                   cr.capital as credito_capital, cr.total_pagar as credito_total_pagar, cr.tasa_mensual,
                   cr.plazo_meses, cr.frecuencia_pago, cr.fecha_inicio as credito_fecha_inicio, cr.estado as credito_estado,
                   (SELECT COUNT(*) FROM cuotas WHERE credito_id = cr.id) as cuotas_total,
                   cl.id as cliente_id, cl.nombre as cliente_nombre, cl.documento as cliente_documento, cl.telefono as cliente_telefono
            FROM pagos p
            JOIN creditos cr ON p.credito_id = cr.id
            JOIN cuotas cu ON p.cuota_id = cu.id
            JOIN clientes cl ON cr.cliente_id = cl.id
            WHERE p.id = ?
        """
        cursor.execute(query, (pago_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "pago_id": row["pago_id"],
            "credito_id": row["credito_id"],
            "cuota_id": row["cuota_id"],
            "pago_monto": Decimal(row["pago_monto"]),
            "fecha_pago": date.fromisoformat(row["fecha_pago"]),
            "numero_cuota": row["numero_cuota"],
            "cuota_monto": Decimal(row["cuota_monto"]),
            "cuota_fecha_vencimiento": date.fromisoformat(row["cuota_fecha_vencimiento"]),
            "cuota_estado": row["cuota_estado"],
            "credito_capital": Decimal(row["credito_capital"]),
            "credito_total_pagar": Decimal(row["credito_total_pagar"]),
            "tasa_mensual": Decimal(row["tasa_mensual"]),
            "plazo_meses": row["plazo_meses"],
            "frecuencia_pago": row["frecuencia_pago"],
            "credito_fecha_inicio": date.fromisoformat(row["credito_fecha_inicio"]),
            "credito_estado": row["credito_estado"],
            "cuotas_total": row["cuotas_total"],
            "cliente_id": row["cliente_id"],
            "cliente_nombre": row["cliente_nombre"],
            "cliente_documento": row["cliente_documento"],
            "cliente_telefono": row["cliente_telefono"],
        }
