"""
Revisión rápida del dashboard desde consola. Ejecutar desde backend/:

    python -m app.servicios.dashboard_revision
"""
import asyncio
import json
from datetime import datetime

from app.bd.session import AsyncSessionLocal, engine
from app.servicios.dashboard_calculos import ZONA, armar_resumen, rango_consulta
from app.servicios.dashboard_consultas import leer_lineas_venta, leer_productos_stock

PERIODO = "mes"


async def main() -> None:
    ahora = datetime.now(ZONA)
    desde, hasta = rango_consulta(PERIODO, ahora)
    try:
        async with AsyncSessionLocal() as db:
            lineas = await leer_lineas_venta(db, desde, hasta)
            productos = await leer_productos_stock(db)
    finally:
        await engine.dispose()

    print(f"\nVentana leída: {desde.date()} -> {hasta.date()}")
    print(f"Líneas de venta: {len(lineas)} | Productos: {len(productos)}\n")
    resumen = armar_resumen(PERIODO, ahora, lineas, productos)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())