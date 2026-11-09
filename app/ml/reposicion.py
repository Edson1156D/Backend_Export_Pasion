"""
Zona 2 - reposición: ¿alcanza el stock para lo que se va a vender?

Módulo puro (sin base de datos ni librerías externas). Recibe el stock actual y
el pronóstico semanal de un producto y devuelve cuánto dura el stock, cuándo
conviene pedir y cuánto. Las reglas se ajustan en un único lugar.
"""
import math
from dataclasses import dataclass
from datetime import date, timedelta

from app.ml.suficiencia import inicio_de_semana

# --- Reglas que se pueden ajustar --------------------------------------------

# Semanas que tarda en llegar un pedido. VALOR PROVISIONAL: nadie lo ha medido.
PLAZO_REPOSICION_SEMANAS = 2

# Excepciones por tipo de unidad, p. ej. {"KILOGRAMO": 4} si la materia prima tarda más.
PLAZO_POR_UNIDAD: dict[str, int] = {}

ESTADO_PEDIR_YA = "pedir_ya"
ESTADO_PEDIR_PRONTO = "pedir_pronto"
ESTADO_SUFICIENTE = "suficiente"
ESTADO_SIN_DEMANDA = "sin_demanda"


@dataclass(frozen=True)
class Reposicion:
    product_id: int
    stock_actual: float
    stock_minimo: float
    demanda_horizonte: float            # unidades esperadas en todo el pronóstico
    horizonte_semanas: int
    semanas_cobertura: float | None     # None = el stock dura más que el pronóstico
    semana_agotamiento: date | None     # None = no se agota dentro del pronóstico
    cantidad_sugerida: float
    fecha_limite_pedido: date | None    # si ya pasó, se muestra la semana actual
    plazo_semanas: int
    estado: str
    confiable: bool


def plazo_para(unit_type: str) -> int:
    return PLAZO_POR_UNIDAD.get(unit_type, PLAZO_REPOSICION_SEMANAS)


def _cantidad(necesaria: float, unit_type: str) -> float:
    if necesaria <= 1e-9:
        return 0.0
    if unit_type == "UNIDAD":
        return float(math.ceil(necesaria - 1e-9))   # no se piden medias piezas
    return round(necesaria, 3)


def recomendar(
    *,
    product_id: int,
    unit_type: str,
    stock: float,
    stock_minimo: float,
    semanas: list[tuple[date, float]],
    confiable: bool,
    hoy: date,
    plazo: int | None = None,
) -> Reposicion:
    """
    - Agotamiento: primera semana en que la demanda acumulada supera el stock.
    - Cantidad sugerida: demanda del pronóstico + stock mínimo - stock actual.
    - Fecha límite: semana de agotamiento menos el plazo de reposición.
    Simplificación: el stock actual se compara con la demanda desde el inicio de la
    semana en curso (no descuenta lo ya vendido esta semana).
    """
    if not semanas:
        raise ValueError("Se necesita al menos una semana de pronóstico")
    plazo = plazo_para(unit_type) if plazo is None else plazo
    semana_actual = inicio_de_semana(hoy)
    demanda = sum(u for _, u in semanas)

    cobertura: float | None = None
    agotamiento: date | None = None
    if demanda > 0:
        if stock <= 0:
            cobertura, agotamiento = 0.0, semanas[0][0]
        else:
            acumulada = 0.0
            for k, (fecha, unidades) in enumerate(semanas):
                if acumulada + unidades > stock:
                    cobertura = round(k + (stock - acumulada) / unidades, 2)
                    agotamiento = fecha
                    break
                acumulada += unidades

    if demanda <= 0:
        cantidad, limite, estado = 0.0, None, ESTADO_SIN_DEMANDA
    else:
        cantidad = _cantidad(demanda + stock_minimo - stock, unit_type)
        if agotamiento is not None:
            limite = max(agotamiento - timedelta(weeks=plazo), semana_actual)
            estado = ESTADO_PEDIR_YA if limite <= semana_actual else ESTADO_PEDIR_PRONTO
        else:
            limite = None
            estado = ESTADO_PEDIR_PRONTO if cantidad > 0 else ESTADO_SUFICIENTE

    return Reposicion(
        product_id=product_id,
        stock_actual=stock,
        stock_minimo=stock_minimo,
        demanda_horizonte=round(demanda, 3),
        horizonte_semanas=len(semanas),
        semanas_cobertura=cobertura,
        semana_agotamiento=agotamiento,
        cantidad_sugerida=cantidad,
        fecha_limite_pedido=limite,
        plazo_semanas=plazo,
        estado=estado,
        confiable=confiable,
    )

_ORDEN_ESTADO = {
    ESTADO_PEDIR_YA: 0,
    ESTADO_PEDIR_PRONTO: 1,
    ESTADO_SUFICIENTE: 2,
    ESTADO_SIN_DEMANDA: 3,
}


def ordenar_por_urgencia(items: list[Reposicion]) -> list[Reposicion]:
    """Lo más urgente primero; dentro de cada estado, el que antes se agota."""
    return sorted(
        items,
        key=lambda r: (
            _ORDEN_ESTADO[r.estado],
            r.semanas_cobertura if r.semanas_cobertura is not None else float("inf"),
            r.product_id,
        ),
    )