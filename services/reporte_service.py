import calendar
import sqlite3
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from credito_app.modules.credito import EstadoCredito, EstadoCuota
from credito_app.modules.excepciones import DatosInvalidosError
from credito_app.database.repositories.credito_repository import CreditoRepository
from credito_app.database.repositories.pago_repository import PagoRepository


class ReporteService:
    """Servicio para generación y filtrado de reportes y métricas."""

    def __init__(self, conn: sqlite3.Connection):
        """Inicializa el servicio con una conexión a la base de datos."""
        self.conn = conn
        self.credito_repo = CreditoRepository(conn)
        self.pago_repo = PagoRepository(conn)

    def calcular_rango_fechas(
        self, tipo: str, fecha_referencia: Optional[date] = None
    ) -> tuple[Optional[date], Optional[date]]:
        """
        Calcula el rango (fecha_desde, fecha_hasta) según un filtro temporal predefinido.
        Tipos soportados:
        - "TODOS" / "Todos"
        - "HOY" / "Hoy"
        - "ESTA_SEMANA" / "Esta Semana"
        - "ESTE_MES" / "Este Mes"
        - "ANIO_EN_CURSO" / "Año en curso" / "Año en Curso"
        - "PERSONALIZADO" / "Personalizado"
        """
        ref = fecha_referencia if fecha_referencia is not None else date.today()
        clave = (
            tipo.strip()
            .upper()
            .replace("Á", "A")
            .replace("É", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ú", "U")
            .replace(" ", "_")
        )

        if clave in ("TODOS", "HISTORICO", "HISTORICO_COMPLETO"):
            return None, None

        if clave == "HOY":
            return ref, ref

        if clave in ("ESTA_SEMANA", "SEMANA"):
            lunes = ref - timedelta(days=ref.weekday())
            domingo = lunes + timedelta(days=6)
            return lunes, domingo

        if clave in ("ESTE_MES", "MES"):
            primer_dia = date(ref.year, ref.month, 1)
            _, ultimo_dia_num = calendar.monthrange(ref.year, ref.month)
            ultimo_dia = date(ref.year, ref.month, ultimo_dia_num)
            return primer_dia, ultimo_dia

        if clave in ("ANIO_EN_CURSO", "ESTE_ANIO", "AÑO_EN_CURSO", "ESTE_AÑO", "ANIO", "AÑO"):
            primer_dia = date(ref.year, 1, 1)
            ultimo_dia = date(ref.year, 12, 31)
            return primer_dia, ultimo_dia

        if clave == "PERSONALIZADO":
            return None, None

        raise DatosInvalidosError(f"Tipo de filtro temporal no reconocido: {tipo}")

    def obtener_metricas(
        self, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None
    ) -> dict:
        """
        Calcula las métricas consolidadas del sistema dentro del rango de fechas especificado.
        - Créditos: filtrados por fecha_inicio
        - Pagos: filtrados por fecha_pago
        """
        if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
            raise DatosInvalidosError("La fecha inicial no puede ser posterior a la fecha final.")

        creditos = self.credito_repo.listar_todos()
        if fecha_desde is not None:
            creditos = [c for c in creditos if c.fecha_inicio >= fecha_desde]
        if fecha_hasta is not None:
            creditos = [c for c in creditos if c.fecha_inicio <= fecha_hasta]

        pagos = self.pago_repo.listar_todos()
        if fecha_desde is not None:
            pagos = [p for p in pagos if p.fecha_pago >= fecha_desde]
        if fecha_hasta is not None:
            pagos = [p for p in pagos if p.fecha_pago <= fecha_hasta]

        activos = sum(1 for c in creditos if c.estado in (EstadoCredito.ACTIVO, EstadoCredito.ACTIVO.value))
        pagados = sum(1 for c in creditos if c.estado in (EstadoCredito.PAGADO, EstadoCredito.PAGADO.value))
        total = len(creditos)

        capital_prestado = sum((c.capital for c in creditos), Decimal("0"))
        intereses_generados = sum((c.total_intereses for c in creditos), Decimal("0"))
        pagos_recibidos = sum((p.monto for p in pagos), Decimal("0"))

        today = date.today()

        # 1. Saldo vencido y Tasa de morosidad
        saldo_vencido = Decimal("0")
        for c in creditos:
            cuotas_c = self.credito_repo.obtener_cuotas_por_credito(c.id)
            for q in cuotas_c:
                if q.fecha_vencimiento < today and q.estado not in (EstadoCuota.PAGADA, EstadoCuota.PAGADA.value):
                    pagado_q = self.pago_repo.obtener_total_pagado_cuota(q.id)
                    pend_q = max(Decimal("0"), q.monto - pagado_q)
                    saldo_vencido += pend_q

        if capital_prestado > Decimal("0"):
            tasa_morosidad = ((saldo_vencido / capital_prestado) * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            tasa_morosidad = Decimal("0.00")

        # 2. Intereses efectivamente cobrados (Ganancia líquida)
        todos_creditos_map = {c.id: c for c in self.credito_repo.listar_todos()}
        intereses_cobrados = Decimal("0")
        for p in pagos:
            cred = todos_creditos_map.get(p.credito_id)
            if cred and cred.total_pagar > Decimal("0"):
                factor_interes = cred.total_intereses / cred.total_pagar
                intereses_cobrados += p.monto * factor_interes
        intereses_cobrados = intereses_cobrados.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if pagos_recibidos > Decimal("0"):
            margen_ganancia = ((intereses_cobrados / pagos_recibidos) * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            margen_ganancia = Decimal("0.00")

        # 3. Ticket promedio de desembolso y Plazo promedio
        if total > 0:
            ticket_promedio = (capital_prestado / Decimal(total)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            plazo_promedio = (
                Decimal(sum(c.plazo_meses for c in creditos)) / Decimal(total)
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        else:
            ticket_promedio = Decimal("0")
            plazo_promedio = Decimal("0.0")

        return {
            "activos": activos,
            "pagados": pagados,
            "total": total,
            "capital_prestado": capital_prestado,
            "intereses_generados": intereses_generados,
            "pagos_recibidos": pagos_recibidos,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "saldo_vencido": saldo_vencido,
            "tasa_morosidad": tasa_morosidad,
            "intereses_cobrados": intereses_cobrados,
            "margen_ganancia": margen_ganancia,
            "ticket_promedio": ticket_promedio,
            "plazo_promedio": plazo_promedio,
        }

    def obtener_distribucion_cartera(
        self, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None
    ) -> dict:
        """
        Calcula la distribución de la cartera en tres categorías:
        - 'al_dia': Créditos activos con todas sus cuotas al corriente
        - 'en_mora': Créditos con cuotas vencidas no liquidadas o en estado VENCIDO
        - 'saldados': Créditos totalmente pagados
        """
        if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
            raise DatosInvalidosError("La fecha inicial no puede ser posterior a la fecha final.")

        creditos = self.credito_repo.listar_todos()
        if fecha_desde is not None:
            creditos = [c for c in creditos if c.fecha_inicio >= fecha_desde]
        if fecha_hasta is not None:
            creditos = [c for c in creditos if c.fecha_inicio <= fecha_hasta]

        today = date.today()
        al_dia_count = 0
        al_dia_capital = Decimal("0")
        al_dia_saldo = Decimal("0")

        en_mora_count = 0
        en_mora_capital = Decimal("0")
        en_mora_saldo = Decimal("0")

        saldados_count = 0
        saldados_capital = Decimal("0")

        for c in creditos:
            pagado = self.pago_repo.obtener_total_pagado_credito(c.id)
            saldo = c.total_pagar - pagado

            if c.estado in (EstadoCredito.PAGADO, EstadoCredito.PAGADO.value) or saldo <= Decimal("0"):
                saldados_count += 1
                saldados_capital += c.capital
            else:
                cuotas = self.credito_repo.obtener_cuotas_por_credito(c.id)
                cuotas_en_mora = [
                    q for q in cuotas
                    if q.estado not in (EstadoCuota.PAGADA, EstadoCuota.PAGADA.value)
                    and q.fecha_vencimiento < today
                ]
                if cuotas_en_mora or c.estado in (EstadoCredito.VENCIDO, EstadoCredito.VENCIDO.value):
                    en_mora_count += 1
                    en_mora_capital += c.capital
                    en_mora_saldo += saldo
                else:
                    al_dia_count += 1
                    al_dia_capital += c.capital
                    al_dia_saldo += saldo

        return {
            "al_dia": {
                "cantidad": al_dia_count,
                "capital": al_dia_capital,
                "saldo": al_dia_saldo,
            },
            "en_mora": {
                "cantidad": en_mora_count,
                "capital": en_mora_capital,
                "saldo": en_mora_saldo,
            },
            "saldados": {
                "cantidad": saldados_count,
                "capital": saldados_capital,
                "saldo": Decimal("0"),
            },
            "total_creditos": len(creditos),
            "total_capital": sum((c.capital for c in creditos), Decimal("0")),
        }

    def obtener_recaudo_vs_proyeccion_semanal(
        self,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        num_semanas: int = 5,
    ) -> list[dict]:
        """
        Calcula la proyección de cobros esperados vs los recaudos reales cobrados, agrupados por semanas.
        Retorna una lista de diccionarios:
        [{"etiqueta": str, "inicio": date, "fin": date, "proyectado": Decimal, "recaudado": Decimal}, ...]
        """
        if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
            raise DatosInvalidosError("La fecha inicial no puede ser posterior a la fecha final.")

        today = date.today()

        if fecha_desde is not None and fecha_hasta is not None and (fecha_hasta - fecha_desde).days >= 7:
            semanas = []
            cursor_inicio = fecha_desde
            while cursor_inicio <= fecha_hasta:
                cursor_fin = min(cursor_inicio + timedelta(days=6), fecha_hasta)
                etiqueta = f"{cursor_inicio.strftime('%d/%m')} - {cursor_fin.strftime('%d/%m')}"
                semanas.append({"inicio": cursor_inicio, "fin": cursor_fin, "etiqueta": etiqueta})
                cursor_inicio = cursor_fin + timedelta(days=1)
                if len(semanas) >= 8:
                    break
        else:
            lunes_actual = today - timedelta(days=today.weekday())
            semanas = []
            for i in range(num_semanas - 1, -1, -1):
                lunes = lunes_actual - timedelta(weeks=i)
                domingo = lunes + timedelta(days=6)
                etiqueta = f"{lunes.strftime('%d/%m')} - {domingo.strftime('%d/%m')}"
                semanas.append({"inicio": lunes, "fin": domingo, "etiqueta": etiqueta})

        cuotas = self.credito_repo.listar_todas_las_cuotas()
        pagos = self.pago_repo.listar_todos()

        resultado = []
        for sem in semanas:
            ini = sem["inicio"]
            fin = sem["fin"]

            proyectado = sum(
                (q.monto for q in cuotas if ini <= q.fecha_vencimiento <= fin),
                Decimal("0"),
            )
            recaudado = sum(
                (p.monto for p in pagos if ini <= p.fecha_pago <= fin),
                Decimal("0"),
            )
            resultado.append({
                "etiqueta": sem["etiqueta"],
                "inicio": ini,
                "fin": fin,
                "proyectado": proyectado,
                "recaudado": recaudado,
            })

        return resultado
