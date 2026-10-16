from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Pago:
    """Representa un pago realizado a una cuota de un crédito."""

    credito_id: int
    cuota_id: int
    monto: Decimal
    fecha_pago: date = field(default_factory=date.today)
    id: Optional[int] = None
