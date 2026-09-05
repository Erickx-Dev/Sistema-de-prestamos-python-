from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

class FrecuenciaPago(Enum):
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"

class EstadoCredito(Enum):
    ACTIVO = "ACTIVO"
    PAGADO = "PAGADO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"

class EstadoCuota(Enum):
    PENDIENTE = "PENDIENTE"
    PAGADA = "PAGADA"
    PARCIAL = "PARCIAL"
    VENCIDA = "VENCIDA"

@dataclass
class Credito:
    """Representa un crédito en el sistema."""
    cliente_id: int
    capital: Decimal
    tasa_mensual: Decimal
    plazo_meses: int
    total_intereses: Decimal
    total_pagar: Decimal
    frecuencia_pago: FrecuenciaPago
    fecha_inicio: date = field(default_factory=date.today)
    estado: EstadoCredito = field(default=EstadoCredito.ACTIVO)
    id: Optional[int] = None

@dataclass
class Cuota:
    """Representa una cuota de un crédito."""
    credito_id: int
    numero_cuota: int
    fecha_vencimiento: date
    monto: Decimal
    estado: EstadoCuota = field(default=EstadoCuota.PENDIENTE)
    id: Optional[int] = None
