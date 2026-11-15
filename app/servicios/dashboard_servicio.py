"""Une las consultas y los cálculos del dashboard."""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.servicios.dashboard_calculos import ZONA, armar_resumen, rango_consulta
from app.servicios.dashboard_consultas import leer_lineas_venta, leer_productos_stock


async def obtener_resumen(db: AsyncSession, periodo: str) -> dict:
    ahora = datetime.now(ZONA)
    desde, hasta = rango_consulta(periodo, ahora)
    lineas = await leer_lineas_venta(db, desde, hasta)
    productos = await leer_productos_stock(db)
    return armar_resumen(periodo, ahora, lineas, productos)