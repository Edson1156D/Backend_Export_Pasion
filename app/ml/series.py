"""Convierte filas semanales en series completas (con ceros) listas para modelar."""
from collections import defaultdict
from datetime import date

import pandas as pd

from app.ml.suficiencia import FilaSemanal, inicio_de_semana


def series_por_producto(filas: list[FilaSemanal], hoy: date) -> dict[int, pd.Series]:
    """
    Una serie por producto: índice = lunes de cada semana, valor = unidades.
    - Las semanas sin ventas se rellenan con 0.
    - La semana actual se excluye (está incompleta y sesgaría el modelo a la baja).
    """
    ultima_completa = pd.Timestamp(inicio_de_semana(hoy)) - pd.Timedelta(weeks=1)
    por_producto: dict[int, list[FilaSemanal]] = defaultdict(list)
    for f in filas:
        por_producto[f.product_id].append(f)

    resultado: dict[int, pd.Series] = {}
    for pid, fs in por_producto.items():
        s = pd.Series({pd.Timestamp(f.semana): f.unidades for f in fs}).sort_index()
        s = s[s.index <= ultima_completa]
        if s.empty:
            continue
        idx = pd.date_range(s.index.min(), ultima_completa, freq="7D")
        resultado[pid] = s.reindex(idx, fill_value=0.0)
    return resultado