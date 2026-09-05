import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Optional

from credito_app.modules.credito import Credito, Cuota, FrecuenciaPago, EstadoCredito, EstadoCuota
from credito_app.modules.excepciones import (
    ClienteNoEncontradoError,
    CreditoNoEncontradoError,
    MontoInvalidoError,
    DatosInvalidosError
)
from credito_app.database.repositories.credito_repository import CreditoRepository
from credito_app.database.repositories.pago_repository import PagoRepository
from credito_app.database.repositories.cliente_repository import ClienteRepository
from credito_app.config import DEFAULT_MONTHLY_RATE, WEEKS_PER_MONTH, FORTNIGHTS_PER_MONTH


class CreditoService:
    """Servicio para la gestión de créditos y cuotas."""

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.conn = conn
        self.credito_repo = CreditoRepository(conn)
        self.pago_repo = PagoRepository(conn)
        self.cliente_repo = ClienteRepository(conn)

    def calcular_intereses(self, capital: Decimal, tasa_mensual: Decimal, plazo_meses: int) -> Decimal:
        """Calcula los intereses de un crédito usando interés simple."""
        if capital <= 0:
            raise MontoInvalidoError("El capital debe ser mayor a 0.")
        if tasa_mensual < 0:
            raise DatosInvalidosError("La tasa mensual no puede ser negativa.")
        if plazo_meses <= 0:
            raise DatosInvalidosError("El plazo en meses debe ser mayor a 0.")

        intereses = capital * tasa_mensual * plazo_meses
        return intereses.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def calcular_total(self, capital: Decimal, intereses: Decimal) -> Decimal:
        """Calcula el total a pagar sumando capital e intereses."""
        return capital + intereses

    def calcular_numero_cuotas(self, plazo_meses: int, frecuencia: FrecuenciaPago) -> int:
        """Calcula el número total de cuotas según la frecuencia de pago."""
        if frecuencia == FrecuenciaPago.SEMANAL:
            return plazo_meses * WEEKS_PER_MONTH
        elif frecuencia == FrecuenciaPago.QUINCENAL:
            return plazo_meses * FORTNIGHTS_PER_MONTH
        return 0

    def crear_credito(
        self,
        cliente_id: int,
        capital: Decimal,
        plazo_meses: int,
        frecuencia: FrecuenciaPago,
        tasa_mensual: Optional[Decimal] = None,
        fecha_inicio: Optional[date] = None
    ) -> Credito:
        """Crea un nuevo crédito para un cliente y genera su plan de pagos."""
        if capital <= 0:
            raise MontoInvalidoError("El capital debe ser mayor a 0.")
        if plazo_meses <= 0:
            raise DatosInvalidosError("El plazo en meses debe ser mayor a 0.")

        if not self.cliente_repo.obtener_por_id(cliente_id):
            raise ClienteNoEncontradoError(f"Cliente con ID {cliente_id} no encontrado.")

        tasa_mensual = tasa_mensual if tasa_mensual is not None else DEFAULT_MONTHLY_RATE
        fecha_inicio = fecha_inicio if fecha_inicio is not None else date.today()

        intereses = self.calcular_intereses(capital, tasa_mensual, plazo_meses)
        total_pagar = self.calcular_total(capital, intereses)

        credito = Credito(
            cliente_id=cliente_id,
            capital=capital,
            tasa_mensual=tasa_mensual,
            plazo_meses=plazo_meses,
            total_intereses=intereses,
            total_pagar=total_pagar,
            frecuencia_pago=frecuencia,
            fecha_inicio=fecha_inicio,
            estado=EstadoCredito.ACTIVO
        )

        credito_creado = self.credito_repo.crear(credito)
        cuotas = self.generar_plan_pagos(credito_creado)

        for cuota in cuotas:
            self.credito_repo.crear_cuota(cuota)

        self.conn.commit()
        return credito_creado

    def generar_plan_pagos(self, credito: Credito) -> list[Cuota]:
        """Genera el plan de pagos (cuotas) para un crédito."""
        numero_cuotas = self.calcular_numero_cuotas(credito.plazo_meses, credito.frecuencia_pago)
        if numero_cuotas <= 0:
            return []

        monto_cuota_base = (credito.total_pagar / Decimal(numero_cuotas)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        ajuste = credito.total_pagar - (monto_cuota_base * numero_cuotas)

        cuotas = []
        for i in range(1, numero_cuotas + 1):
            monto = monto_cuota_base
            if i == numero_cuotas:
                monto += ajuste

            if credito.frecuencia_pago == FrecuenciaPago.SEMANAL:
                fecha_vencimiento = credito.fecha_inicio + timedelta(days=7 * i)
            elif credito.frecuencia_pago == FrecuenciaPago.QUINCENAL:
                fecha_vencimiento = credito.fecha_inicio + timedelta(days=15 * i)
            else:
                fecha_vencimiento = credito.fecha_inicio

            cuota = Cuota(
                credito_id=credito.id,  # type: ignore
                numero_cuota=i,
                fecha_vencimiento=fecha_vencimiento,
                monto=monto,
                estado=EstadoCuota.PENDIENTE
            )
            cuotas.append(cuota)

        return cuotas

    def obtener_credito(self, credito_id: int) -> Credito:
        """Obtiene un crédito por su ID."""
        credito = self.credito_repo.obtener_por_id(credito_id)
        if not credito:
            raise CreditoNoEncontradoError(f"Crédito con ID {credito_id} no encontrado.")
        return credito

    def obtener_plan_pagos(self, credito_id: int) -> list[Cuota]:
        """Obtiene las cuotas de un crédito."""
        self.obtener_credito(credito_id)  # Validate existence
        return self.credito_repo.obtener_cuotas_por_credito(credito_id)

    def calcular_saldo_pendiente(self, credito_id: int) -> Decimal:
        """Calcula el saldo pendiente de un crédito."""
        credito = self.obtener_credito(credito_id)
        total_pagado = self.pago_repo.obtener_total_pagado_credito(credito_id)
        return credito.total_pagar - total_pagado

    def determinar_estado_credito(self, credito_id: int) -> EstadoCredito:
        """Determina y actualiza el estado de un crédito según sus cuotas."""
        credito = self.obtener_credito(credito_id)
        
        if credito.estado == EstadoCredito.CANCELADO:
            return EstadoCredito.CANCELADO

        cuotas = self.credito_repo.obtener_cuotas_por_credito(credito_id)
        if not cuotas:
            nuevo_estado = EstadoCredito.ACTIVO
        elif all(cuota.estado == EstadoCuota.PAGADA for cuota in cuotas):
            nuevo_estado = EstadoCredito.PAGADO
        else:
            nuevo_estado = EstadoCredito.ACTIVO

        if credito.estado != nuevo_estado:
            self.credito_repo.actualizar_estado(credito_id, nuevo_estado)
            self.conn.commit()

        return nuevo_estado

    def listar_creditos(self) -> list[Credito]:
        """Obtiene todos los créditos del sistema."""
        return self.credito_repo.listar_todos()

    def obtener_proximos_pagos(self, limite: int = 10) -> list[dict]:
        """Obtiene las próximas cuotas pendientes con información del cliente."""
        return self.credito_repo.obtener_cuotas_pendientes(limite)
