"""
Zona 1 (pronóstico de demanda) - paso 1: ¿hay datos suficientes para pronosticar?

Este módulo NO usa base de datos ni librerías externas: recibe filas ya agrupadas
por semana y decide qué tan confiable puede ser un pronóstico de cada producto.
Así se puede probar solo y cambiar las reglas en un único lugar.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# --- Reglas que se pueden ajustar --------------------------------------------

# Tipos de movimiento que cuentan como VENTA (= demanda). Hoy solo uno.
# Transferencias, entradas y mermas NO son demanda y no deben agregarse aquí.
TIPOS_VENTA = ("VENTA_MAYORISTA", "VENTA_MINORISTA")

# Zona horaria del negocio (Lima, UTC-5, sin horario de verano).
ZONA_HORARIA_SQL = "America/Lima"
_LIMA = ZoneInfo(ZONA_HORARIA_SQL)

# Semanas de historial (desde la primera venta hasta hoy) para cada nivel.
# Son reglas prácticas, no verdades absolutas.
MIN_SEMANAS_BASICO = 8        # promedio móvil / suavizado exponencial
MIN_SEMANAS_ESTACIONAL = 52             # alcanza para "misma semana del año pasado"
MIN_SEMANAS_ESTACIONAL_COMPLETO = 104   # recién aquí tiene sentido Holt-Winters

# Si menos de la mitad de las semanas tiene ventas, la demanda es "a golpes"
# (ferias, pedidos grandes) y un pronóstico semanal suave funciona mal.
UMBRAL_INTERMITENTE = 0.5

NIVEL_INSUFICIENTE = "insuficiente"
NIVEL_BASICO = "basico"
NIVEL_ESTACIONAL = "estacional"
_ORDEN_NIVEL = {NIVEL_INSUFICIENTE: 0, NIVEL_BASICO: 1, NIVEL_ESTACIONAL: 2}
MIN_SEMANAS_CON_VENTAS = 4    # con menos semanas con ventas no hay patrón que aprender

@dataclass(frozen=True)
class FilaSemanal:
    """Ventas de un producto en una semana (la semana empieza el lunes)."""
    product_id: int
    semana: date
    unidades: float
    lineas: int


@dataclass(frozen=True)
class Suficiencia:
    product_id: int
    unidades_totales: float
    semanas_con_ventas: int
    semanas_historial: int
    primera_semana: date
    ultima_semana: date
    nivel: str
    intermitente: bool


def hoy_lima() -> date:
    """Fecha de hoy en Lima."""
    return datetime.now(_LIMA).date()


def inicio_de_semana(dia: date) -> date:
    """Lunes de la semana a la que pertenece `dia`."""
    return dia - timedelta(days=dia.weekday())


def _nivel(semanas_historial: int, semanas_con_ventas: int, intermitente: bool) -> str:
    if semanas_con_ventas < MIN_SEMANAS_CON_VENTAS:
        return NIVEL_INSUFICIENTE
    # La estacionalidad anual no aplica a demanda intermitente.
    if semanas_historial >= MIN_SEMANAS_ESTACIONAL and not intermitente:
        return NIVEL_ESTACIONAL
    if semanas_historial >= MIN_SEMANAS_BASICO:
        return NIVEL_BASICO
    return NIVEL_INSUFICIENTE


def evaluar(filas: list[FilaSemanal], hoy: date) -> list[Suficiencia]:
    """Evalúa, por producto, cuántos datos hay. Solo aparecen productos con ventas."""
    por_producto: dict[int, list[FilaSemanal]] = {}
    for fila in filas:
        por_producto.setdefault(fila.product_id, []).append(fila)

    semana_actual = inicio_de_semana(hoy)
    resultado: list[Suficiencia] = []

    for product_id, semanas in sorted(por_producto.items()):
        primera = min(f.semana for f in semanas)
        ultima = max(f.semana for f in semanas)
        # Semanas contadas desde la primera venta hasta la semana actual (incluida),
        # tengan o no ventas: las semanas sin ventas también son información.
        historial = max(1, (semana_actual - primera).days // 7 + 1)
        con_ventas = len({f.semana for f in semanas})
        intermitente = (
            historial >= MIN_SEMANAS_BASICO
            and con_ventas / historial < UMBRAL_INTERMITENTE
        )
        resultado.append(
            Suficiencia(
                product_id=product_id,
                unidades_totales=sum(f.unidades for f in semanas),
                semanas_con_ventas=con_ventas,
                semanas_historial=historial,
                primera_semana=primera,
                ultima_semana=ultima,
                nivel=_nivel(historial, con_ventas, intermitente),
                intermitente=intermitente,
            )
        )
    return resultado


def listos_para_pronosticar(evaluaciones: list[Suficiencia]) -> list[Suficiencia]:
    """Productos con al menos el nivel básico."""
    return [e for e in evaluaciones if _ORDEN_NIVEL[e.nivel] >= _ORDEN_NIVEL[NIVEL_BASICO]]


def mensaje_resumen(evaluaciones: list[Suficiencia]) -> str:
    """Texto corto en español para mostrar en el dashboard o en consola."""
    tipos = ", ".join(TIPOS_VENTA)
    if not evaluaciones:
        return f"Aún no hay ventas registradas (tipos considerados: {tipos}). No se puede pronosticar."
    listos = len(listos_para_pronosticar(evaluaciones))
    if listos == 0:
        mejor = max(e.semanas_historial for e in evaluaciones)
        return (
            f"Hay ventas de {len(evaluaciones)} producto(s), pero el mayor historial es de "
            f"{mejor} semana(s) y se necesitan al menos {MIN_SEMANAS_BASICO}. Datos insuficientes."
        )
    return f"{listos} de {len(evaluaciones)} producto(s) con historial suficiente para un pronóstico básico."