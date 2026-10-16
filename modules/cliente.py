from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Cliente:
    """Representa un cliente del sistema de créditos."""

    nombre: str
    telefono: str
    documento: str
    id: Optional[int] = None
    fecha_registro: date = field(default_factory=date.today)
