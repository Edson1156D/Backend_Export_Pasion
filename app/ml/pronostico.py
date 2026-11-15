"""
Zona 1 - paso 2: pronóstico semanal de demanda.

Para cada producto se prueban varios métodos con un backtest de origen móvil
y se usa el de menor WAPE. El promedio móvil siempre compite como línea base,
así que ningún modelo "complicado" se usa si no la supera.
"""
import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.ml.suficiencia import MIN_SEMANAS_ESTACIONAL, MIN_SEMANAS_ESTACIONAL_COMPLETO

# --- Reglas que se pueden ajustar --------------------------------------------
HORIZONTE = 4            # semanas a pronosticar
VENTANA_MA = 4           # semanas del promedio móvil
ALFA_CROSTON = 0.1
ORIGENES_BACKTEST = 8    # cuántas veces se simula "pronosticar desde aquí"
MIN_ORIGENES = 4         # menos orígenes que esto no valida nada: se descarta el método más exigente
PASO_BACKTEST = 1        # semanas entre un origen y el siguiente
MARGEN_VS_BASE = 0.10    # un método complejo debe mejorar al promedio móvil en 10 %
PERIODO_ANUAL = 52

METODO_MA = "promedio_movil"
METODO_CROSTON = "croston_sba"
METODO_ETS = "suavizado_exponencial"
METODO_ESTACIONAL = "estacional_ingenuo"
METODO_HW = "holt_winters"

UMBRAL_CONFIABLE = 0.5     # WAPE máximo para marcar el pronóstico como confiable
CV_MAX_INTERVALO = 0.25    # qué tan irregular puede ser el ritmo de pedidos
MIN_EVENTOS_CICLO = 4
METODO_CICLO = "ciclo_regular"
METODO_HOLT = "holt_amortiguado"

@dataclass(frozen=True)
class Pronostico:
    product_id: int
    metodo: str
    wape: float | None
    semanas_historial: int
    semanas: list[tuple[date, float]]
    confiable: bool


# --- Métodos: cada uno recibe (y: ndarray, h: int) y devuelve ndarray de h ----

def _promedio_movil(y: np.ndarray, h: int) -> np.ndarray:
    return np.full(h, y[-VENTANA_MA:].mean())


def _croston_sba(y: np.ndarray, h: int) -> np.ndarray:
    """Croston con corrección de sesgo (Syntetos-Boylan)."""
    pos = np.flatnonzero(y > 0)
    if pos.size == 0:
        return np.zeros(h)
    z = y[pos[0]]          # tamaño medio de la demanda
    p = pos[0] + 1         # intervalo medio entre demandas
    q = 0
    for t in range(pos[0] + 1, len(y)):
        q += 1
        if y[t] > 0:
            z += ALFA_CROSTON * (y[t] - z)
            p += ALFA_CROSTON * (q - p)
            q = 0
    return np.full(h, (1 - ALFA_CROSTON / 2) * z / p)


def _suavizado_exponencial(y: np.ndarray, h: int) -> np.ndarray:
    if y.sum() == 0:
        return np.zeros(h)
    modelo = ExponentialSmoothing(y, initialization_method="estimated").fit()
    return np.clip(modelo.forecast(h), 0, None)


def _estacional_ingenuo(y: np.ndarray, h: int) -> np.ndarray:
    """Misma semana del año pasado, promediada con la anterior y la siguiente."""
    n = len(y)
    salida = np.empty(h)
    for k in range(h):
        t = n + k - PERIODO_ANUAL
        salida[k] = y[max(0, t - 1): t + 2].mean()
    return salida


def _holt_winters(y: np.ndarray, h: int) -> np.ndarray:
    if y.sum() == 0:
        return np.zeros(h)
    modelo = ExponentialSmoothing(
        y, seasonal="add", seasonal_periods=PERIODO_ANUAL, initialization_method="estimated"
    ).fit()
    return np.clip(modelo.forecast(h), 0, None)
def _ciclo_regular(y: np.ndarray, h: int) -> np.ndarray:
    """Demanda a golpes con ritmo regular: repite el pedido típico en la semana que toca."""
    pos = np.flatnonzero(y > 0)
    if pos.size < MIN_EVENTOS_CICLO:
        raise ValueError("pocos pedidos")
    intervalos = np.diff(pos)
    intervalo = int(round(np.median(intervalos)))
    if intervalo < 2 or intervalos.std() / intervalos.mean() > CV_MAX_INTERVALO:
        raise ValueError("sin ritmo regular")
    toca = pos[-1] + intervalo - len(y)    # semanas hasta el próximo pedido (0 = ya toca)
    if toca < -intervalo:
        raise ValueError("pedido muy atrasado")
    toca = max(toca, 0)
    salida = np.zeros(h)
    for k in range(toca, h, intervalo):
        salida[k] = y[pos[-3:]].mean()
    return salida

def _holt_amortiguado(y: np.ndarray, h: int) -> np.ndarray:
    if y.sum() == 0:
        return np.zeros(h)
    modelo = ExponentialSmoothing(
        y, trend="add", damped_trend=True, initialization_method="estimated"
    ).fit()
    return np.clip(modelo.forecast(h), 0, None)

# método -> (función, mínimo de semanas de historial para usarlo)
_METODOS = {
    METODO_MA: (_promedio_movil, VENTANA_MA),
    METODO_CROSTON: (_croston_sba, 8),
    METODO_ETS: (_suavizado_exponencial, 8),
    METODO_ESTACIONAL: (_estacional_ingenuo, MIN_SEMANAS_ESTACIONAL + 1),
    METODO_HW: (_holt_winters, MIN_SEMANAS_ESTACIONAL_COMPLETO),
    METODO_CICLO: (_ciclo_regular, 8),    
    METODO_HOLT: (_holt_amortiguado, 12),
}

# --- Backtest ---------------------------------------------------------------

def _wape(y: np.ndarray, funcion, cortes: list[int], h: int) -> float | None:
    """Error del método en los orígenes dados. None si no se pudo medir."""
    error_total = 0.0
    real_total = 0.0
    for corte in cortes:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pred = funcion(y[:corte], h)
        except Exception:
            return None
        real = y[corte:corte + h]
        error_total += float(np.abs(real - pred).sum())
        real_total += float(real.sum())
    if not cortes or real_total == 0:
        return None
    return error_total / real_total

# --- API del módulo ---------------------------------------------------------

def pronosticar_producto(product_id: int, serie: pd.Series, h: int = HORIZONTE) -> Pronostico:
    y = serie.to_numpy(dtype=float)
    n = len(y)

    # Métodos con historial suficiente. Si no hay orígenes comunes donde medirlos
    # a todos, se descarta el más exigente: un método que no se puede validar no se usa.
    elegibles = {k: v for k, v in _METODOS.items() if n >= v[1]}
    elegibles.setdefault(METODO_MA, _METODOS[METODO_MA])
    while True:
        minimo_comun = max(m for _, m in elegibles.values())
        cortes = [
            c for c in (n - h - i * PASO_BACKTEST for i in range(ORIGENES_BACKTEST))
            if c >= minimo_comun
        ]
        if len(cortes) >= MIN_ORIGENES or len(elegibles) == 1:
            break
        del elegibles[max(elegibles, key=lambda k: elegibles[k][1])]

    resultados = {k: _wape(y, f, cortes, h) for k, (f, _) in elegibles.items()}
    resultados = {k: w for k, w in resultados.items() if w is not None}

    base = resultados.get(METODO_MA)
    mejor_metodo, mejor_wape = METODO_MA, base
    otros = {k: w for k, w in resultados.items() if k != METODO_MA}
    if otros:
        k, w = min(otros.items(), key=lambda kv: kv[1])
        if base is None or w < base * (1 - MARGEN_VS_BASE):
            mejor_metodo, mejor_wape = k, w

    funcion = _METODOS[mejor_metodo][0]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pred = funcion(y, h)
    except Exception:
                mejor_metodo, mejor_wape, pred = METODO_MA, base, _promedio_movil(y, h)

    pred = np.clip(pred, 0, None)
    fechas = [(serie.index[-1] + pd.Timedelta(weeks=k + 1)).date() for k in range(h)]
    return Pronostico(
        product_id=product_id,
        metodo=mejor_metodo,
        wape=None if mejor_wape is None else round(mejor_wape, 4),
        semanas_historial=n,
        semanas=[(f, round(float(v), 3)) for f, v in zip(fechas, pred)],
        confiable=mejor_wape is not None and mejor_wape <= UMBRAL_CONFIABLE,
    )

def pronosticar_todos(series: dict[int, pd.Series]) -> list[Pronostico]:
    """Función síncrona y pesada: llamarla desde asyncio.to_thread."""
    return [pronosticar_producto(pid, s) for pid, s in sorted(series.items())]

