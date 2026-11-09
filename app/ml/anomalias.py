"""
Zona 3 - detección de anomalías en ventas, mermas y stock.

Módulo puro (sin base de datos ni librerías externas). Usa estadística robusta
(mediana y MAD) para que los propios valores raros no distorsionen la referencia.
Todas las reglas se ajustan aquí.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median

from app.ml.suficiencia import TIPOS_VENTA, UMBRAL_INTERMITENTE, FilaSemanal, inicio_de_semana
from app.servicios.dashboard_calculos import ProductoStock

# --- Reglas que se pueden ajustar --------------------------------------------

VENTANA_BASE = 12            # semanas anteriores que sirven de referencia
ULTIMAS_SEMANAS = 8          # cuántas semanas recientes se revisan
HISTORIAL_MOVIMIENTOS_SEMANAS = 26   # cuánto historial de movimientos se lee como referencia
MIN_MOVIMIENTOS = 8          # movimientos mínimos de un producto y tipo para juzgar uno
UMBRAL_Z = 4.5               # desviaciones robustas para considerar algo anómalo
UMBRAL_Z_ALTA = 6.0          # a partir de aquí la severidad es alta
ESCALA_MAD = 1.4826          # convierte el MAD en una desviación estándar equivalente
ESCALA_DESV_MEDIA = 1.253314  # ídem para la desviación media (se usa si el MAD es 0)

# Tipos de movimiento cuya cantidad se compara con el historial del producto.
# Las transferencias no entran: su tamaño es una decisión logística, no un patrón.
TIPOS_ANALIZADOS = (*TIPOS_VENTA, "MERMA")

TIPO_SEMANA = "semana_atipica"
TIPO_MOVIMIENTO = "movimiento_atipico"
TIPO_STOCK = "stock_negativo"
SEVERIDAD_ALTA = "alta"
SEVERIDAD_MEDIA = "media"
_ORDEN_SEVERIDAD = {SEVERIDAD_ALTA: 0, SEVERIDAD_MEDIA: 1}


@dataclass(frozen=True)
class Movimiento:
    mov_id: int
    product_id: int
    tipo: str
    fecha: datetime
    cantidad: float


@dataclass(frozen=True)
class Anomalia:
    tipo: str
    severidad: str
    product_id: int
    fecha: date | None
    valor: float | None
    esperado: float | None
    puntaje: float | None        # desviaciones robustas; None si no aplica
    mensaje: str


def _n(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def _severidad(z: float) -> str:
    return SEVERIDAD_ALTA if abs(z) >= UMBRAL_Z_ALTA else SEVERIDAD_MEDIA


def _referencia(valores: list[float]) -> tuple[float, float | None]:
    """
    (mediana, escala) de una lista de valores. La escala es el MAD; si vale 0 (muchos
    valores iguales, típico de las mermas) se usa la desviación media. Si tampoco hay
    variación, la escala es None y no se puede juzgar nada.
    """
    med = median(valores)
    desvios = [abs(v - med) for v in valores]
    mad = median(desvios)
    if mad > 0:
        return med, ESCALA_MAD * mad
    media = sum(desvios) / len(desvios)
    return med, (ESCALA_DESV_MEDIA * media if media > 0 else None)


# --- Detectores ---------------------------------------------------------------

def semanas_atipicas(
    filas: list[FilaSemanal], hoy: date, ultimas_semanas: int = ULTIMAS_SEMANAS
) -> list[Anomalia]:
    """
    Semanas recientes cuyas ventas se alejan de las 12 semanas anteriores, y semanas
    sin ventas en un producto que vendía casi todas las semanas.
    No se juzgan: la semana en curso (incompleta), los productos con demanda a golpes
    (muchas semanas en cero) ni las referencias sin variación (no hay escala).
    """
    ultima_completa = inicio_de_semana(hoy) - timedelta(weeks=1)
    ventas: dict[int, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    for f in filas:
        if f.semana <= ultima_completa:
            ventas[f.product_id][f.semana] += f.unidades

    resultado: list[Anomalia] = []
    for pid, por_semana in sorted(ventas.items()):
        primera = min(por_semana)
        n = (ultima_completa - primera).days // 7 + 1
        if n <= VENTANA_BASE:
            continue
        serie = [por_semana.get(primera + timedelta(weeks=i), 0.0) for i in range(n)]
        for t in range(max(VENTANA_BASE, n - ultimas_semanas), n):
            base = serie[t - VENTANA_BASE:t]
            ceros_base = sum(1 for b in base if b == 0)
            if ceros_base / len(base) >= UMBRAL_INTERMITENTE:
                continue
            med, escala = _referencia(base)
            if serie[t] == 0 and ceros_base <= 1:
                resultado.append(Anomalia(
                    tipo=TIPO_SEMANA, severidad=SEVERIDAD_ALTA, product_id=pid,
                    fecha=primera + timedelta(weeks=t), valor=0.0, esperado=med, puntaje=None,
                    mensaje=f"Sin ventas esta semana (lo habitual: ~{_n(med)}).",
                ))
                continue
            if escala is None:
                continue
            z = (serie[t] - med) / escala
            if abs(z) < UMBRAL_Z:
                continue
            semana = primera + timedelta(weeks=t)
            sentido = "más" if z > 0 else "menos"
            resultado.append(Anomalia(
                tipo=TIPO_SEMANA, severidad=_severidad(z), product_id=pid, fecha=semana,
                valor=serie[t], esperado=med, puntaje=round(z, 1),
                mensaje=f"Ventas de la semana: {_n(serie[t])} ({sentido} de lo habitual, ~{_n(med)}).",
            ))
    return resultado


def movimientos_atipicos(
    movimientos: list[Movimiento], desde: datetime | None = None
) -> list[Anomalia]:
    """
    Movimientos de venta o merma cuya cantidad se aleja de lo habitual para ese
    producto y tipo. `desde` limita qué movimientos se reportan (la referencia se
    calcula con todo el historial recibido).
    """
    grupos: dict[tuple[int, str], list[Movimiento]] = defaultdict(list)
    for m in movimientos:
        tipo = m.tipo.strip().upper()
        if tipo in TIPOS_ANALIZADOS:
            grupos[(m.product_id, tipo)].append(m)

    resultado: list[Anomalia] = []
    for (pid, tipo), movs in sorted(grupos.items()):
        if len(movs) < MIN_MOVIMIENTOS:
            continue
        med, escala = _referencia([m.cantidad for m in movs])
        if escala is None:
            continue
        for m in movs:
            if desde is not None and m.fecha < desde:
                continue
            z = (m.cantidad - med) / escala
            if abs(z) < UMBRAL_Z:
                continue
            sentido = "más" if z > 0 else "menos"
            resultado.append(Anomalia(
                tipo=TIPO_MOVIMIENTO, severidad=_severidad(z), product_id=pid,
                fecha=m.fecha.date(), valor=m.cantidad, esperado=med, puntaje=round(z, 1),
                mensaje=f"{tipo} de {_n(m.cantidad)} ({sentido} de lo habitual, ~{_n(med)}).",
            ))
    return resultado


def stocks_negativos(productos: list[ProductoStock]) -> list[Anomalia]:
    """El trigger de la base no valida stock: un negativo indica un error de registro."""
    return [
        Anomalia(
            tipo=TIPO_STOCK, severidad=SEVERIDAD_ALTA, product_id=p.product_id, fecha=None,
            valor=p.current_stock, esperado=None, puntaje=None,
            mensaje=f"Stock negativo ({_n(p.current_stock)}): revisar los movimientos del producto.",
        )
        for p in productos
        if p.current_stock < 0
    ]


def detectar(
    filas: list[FilaSemanal],
    movimientos: list[Movimiento],
    productos: list[ProductoStock],
    hoy: date,
    desde: datetime | None = None,
) -> list[Anomalia]:
    """Todas las anomalías: primero las de severidad alta y, dentro, las más recientes."""
    todas = [
        *stocks_negativos(productos),
        *semanas_atipicas(filas, hoy),
        *movimientos_atipicos(movimientos, desde),
    ]
    return sorted(
        todas,
        key=lambda a: (
            _ORDEN_SEVERIDAD[a.severidad],
            a.fecha is not None,                       # sin fecha (stock) primero
            -(a.fecha.toordinal() if a.fecha else 0),  # luego lo más reciente
            a.product_id,
        ),
    )