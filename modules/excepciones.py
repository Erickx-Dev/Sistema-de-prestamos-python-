class CrediNodaError(Exception):
    """Excepción base del sistema de créditos."""

    pass


class ClienteNoEncontradoError(CrediNodaError):
    """El cliente solicitado no existe."""

    pass


class CreditoNoEncontradoError(CrediNodaError):
    """El crédito solicitado no existe."""

    pass


class CuotaNoEncontradaError(CrediNodaError):
    """La cuota solicitada no existe."""

    pass


class PagoInvalidoError(CrediNodaError):
    """El pago no cumple las validaciones requeridas."""

    pass


class MontoInvalidoError(CrediNodaError):
    """El monto proporcionado no es válido."""

    pass


class DatosInvalidosError(CrediNodaError):
    """Los datos proporcionados no son válidos."""

    pass
