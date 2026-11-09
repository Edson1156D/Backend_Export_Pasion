"""Une consulta + series + pronóstico, sin bloquear la API y con caché en memoria."""
import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.consultas import ventas_semanales
from app.ml.pronostico import Pronostico, pronosticar_todos
from app.ml.series import series_por_producto
from app.ml.suficiencia import evaluar, hoy_lima, listos_para_pronosticar

TTL_SEGUNDOS = 6 * 3600  # los datos cambian poco; 6 horas bastan para empezar

_cache: dict = {"t": 0.0, "datos": None}
_lock = asyncio.Lock()  # evita calcular dos veces si llegan peticiones a la vez


async def obtener_pronosticos(db: AsyncSession, forzar: bool = False) -> list[Pronostico]:
    async with _lock:
        vigente = _cache["datos"] is not None and time.monotonic() - _cache["t"] < TTL_SEGUNDOS
        if vigente and not forzar:
            return _cache["datos"]

        filas = await ventas_semanales(db)
        hoy = hoy_lima()
        listos = {e.product_id for e in listos_para_pronosticar(evaluar(filas, hoy))}
        series = {
            pid: s for pid, s in series_por_producto(filas, hoy).items() if pid in listos
        }
        datos = await asyncio.to_thread(pronosticar_todos, series)

        _cache["datos"], _cache["t"] = datos, time.monotonic()
        return datos