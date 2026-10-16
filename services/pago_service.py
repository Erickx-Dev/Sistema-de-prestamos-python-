import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional

from credito_app.modules.pago import Pago
from credito_app.modules.credito import EstadoCuota
from credito_app.modules.excepciones import (
    CreditoNoEncontradoError,
    CuotaNoEncontradaError,
    MontoInvalidoError,
    PagoInvalidoError,
)
from credito_app.database.repositories.pago_repository import PagoRepository
from credito_app.database.repositories.credito_repository import CreditoRepository


class PagoService:
    """Servicio para la gestión de pagos."""

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.conn = conn
        self.pago_repo = PagoRepository(conn)
        self.credito_repo = CreditoRepository(conn)

    def registrar_pago(self, credito_id: int, cuota_id: int, monto: Decimal, fecha_pago: Optional[date] = None) -> Pago:
        """Registra un pago para una cuota específica."""
        if monto <= 0:
            raise MontoInvalidoError("El monto del pago debe ser mayor a 0.")

        credito = self.credito_repo.obtener_por_id(credito_id)
        if not credito:
            raise CreditoNoEncontradoError(f"Crédito con ID {credito_id} no encontrado.")

        cuota = self.credito_repo.obtener_cuota_por_id(cuota_id)
        if not cuota:
            raise CuotaNoEncontradaError(f"Cuota con ID {cuota_id} no encontrada.")

        if cuota.credito_id != credito_id:
            raise PagoInvalidoError("La cuota no pertenece al crédito especificado.")

        if cuota.estado == EstadoCuota.PAGADA:
            raise PagoInvalidoError("La cuota ya está pagada.")

        total_pagado_cuota = self.pago_repo.obtener_total_pagado_cuota(cuota_id)
        saldo_cuota = cuota.monto - total_pagado_cuota

        if monto > saldo_cuota:
            raise MontoInvalidoError("El monto excede el saldo pendiente de la cuota.")

        fecha_pago = fecha_pago if fecha_pago is not None else date.today()

        pago = Pago(credito_id=credito_id, cuota_id=cuota_id, monto=monto, fecha_pago=fecha_pago)

        pago_creado = self.pago_repo.crear(pago)

        nuevo_total_pagado = total_pagado_cuota + monto
        if nuevo_total_pagado >= cuota.monto:
            nuevo_estado = EstadoCuota.PAGADA
        else:
            nuevo_estado = EstadoCuota.PARCIAL

        self.credito_repo.actualizar_estado_cuota(cuota_id, nuevo_estado)
        self.conn.commit()

        return pago_creado

    def obtener_historial_pagos(self, credito_id: int) -> list[Pago]:
        """Obtiene el historial de pagos de un crédito."""
        return self.pago_repo.obtener_por_credito(credito_id)

    def obtener_pagos_cuota(self, cuota_id: int) -> list[Pago]:
        """Obtiene los pagos asociados a una cuota específica."""
        return self.pago_repo.obtener_por_cuota(cuota_id)

    def listar_pagos(self) -> list[Pago]:
        """Obtiene todos los pagos del sistema."""
        return self.pago_repo.listar_todos()

    def listar_pagos_con_detalle(self) -> list[dict]:
        """Obtiene todos los pagos con información del cliente y crédito."""
        return self.pago_repo.listar_todos_con_detalle()

    def obtener_pago(self, pago_id: int) -> Optional[Pago]:
        """Obtiene un pago por su ID."""
        return self.pago_repo.obtener_por_id(pago_id)

    def obtener_datos_comprobante(self, pago_id: int) -> dict:
        """Compila y calcula la información financiera completa para el comprobante de pago."""
        detalle = self.pago_repo.obtener_detalle_pago(pago_id)
        if not detalle:
            raise PagoInvalidoError(f"Pago con ID {pago_id} no encontrado.")

        # Cálculos de cuota
        total_pagado_cuota = self.pago_repo.obtener_total_pagado_cuota(detalle["cuota_id"])
        cuota_monto = detalle["cuota_monto"]
        saldo_cuota_despues = max(Decimal("0.00"), cuota_monto - total_pagado_cuota)
        saldo_cuota_antes = saldo_cuota_despues + detalle["pago_monto"]

        # Cálculos de crédito global
        total_pagado_credito = self.pago_repo.obtener_total_pagado_credito(detalle["credito_id"])
        total_pagar_credito = detalle["credito_total_pagar"]
        saldo_credito_restante = max(Decimal("0.00"), total_pagar_credito - total_pagado_credito)
        porcentaje_pagado = (
            (total_pagado_credito / total_pagar_credito * Decimal("100")).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
            if total_pagar_credito > 0
            else Decimal("0.0")
        )

        return {
            **detalle,
            "numero_recibo": f"REC-{pago_id:05d}",
            "total_pagado_cuota": total_pagado_cuota,
            "saldo_cuota_antes": saldo_cuota_antes,
            "saldo_cuota_despues": saldo_cuota_despues,
            "total_pagado_credito": total_pagado_credito,
            "saldo_credito_restante": saldo_credito_restante,
            "porcentaje_pagado_credito": porcentaje_pagado,
        }
