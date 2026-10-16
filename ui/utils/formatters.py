from decimal import Decimal
from datetime import date
from credito_app.modules.credito import EstadoCredito, EstadoCuota
from credito_app.ui.theme import COLORS


def formato_moneda(valor: Decimal | int | float) -> str:
    """Formatea un valor numérico o Decimal como moneda: $1.000.000 o $113.333,33"""
    if valor is None:
        return "$0"
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    if valor == valor.to_integral_value():
        texto = f"{int(valor):,}".replace(",", ".")
    else:
        parts = f"{valor:,.2f}".split(".")
        integer_part = parts[0].replace(",", ".")
        texto = f"{integer_part},{parts[1]}"
    return f"${texto}"


def formato_fecha(fecha: date) -> str:
    """Formatea una fecha como dd/mm/aaaa."""
    return fecha.strftime("%d/%m/%Y")


def formato_porcentaje(valor: Decimal) -> str:
    """Formatea un Decimal como porcentaje: 0.12 -> 12%"""
    return f"{int(valor * 100)}%"


def color_estado_credito(estado: EstadoCredito) -> str:
    """Retorna el color hexadecimal correspondiente al estado del crédito."""
    mapa = {
        EstadoCredito.ACTIVO: COLORS["primary"],
        EstadoCredito.PAGADO: COLORS["success"],
        EstadoCredito.VENCIDO: COLORS["error"],
        EstadoCredito.CANCELADO: COLORS["text_secondary"],
    }
    return mapa.get(estado, COLORS["text_secondary"])


def color_estado_cuota(estado: EstadoCuota) -> str:
    """Retorna el color hexadecimal correspondiente al estado de la cuota."""
    mapa = {
        EstadoCuota.PENDIENTE: COLORS["text_secondary"],
        EstadoCuota.PAGADA: COLORS["success"],
        EstadoCuota.PARCIAL: COLORS["warning"],
        EstadoCuota.VENCIDA: COLORS["error"],
    }
    return mapa.get(estado, COLORS["text_secondary"])
