"""
Revisión rápida desde consola. Ejecutar desde backend/:

    python -m app.ml.revision

Muestra cuántos datos de venta hay por producto y si alcanzan para pronosticar.
"""
import asyncio

from app.bd.session import AsyncSessionLocal, engine
from app.ml.consultas import ventas_semanales
from app.ml.suficiencia import evaluar, hoy_lima, mensaje_resumen, TIPOS_VENTA


async def main() -> None:
    try:
        async with AsyncSessionLocal() as db:
            filas = await ventas_semanales(db)
    finally:
        await engine.dispose()

    evaluaciones = evaluar(filas, hoy_lima())
    print(f"\nTipos contados como venta: {', '.join(TIPOS_VENTA)}")
    print(mensaje_resumen(evaluaciones) + "\n")

    if evaluaciones:
        print(f"{'prod':<6}{'unidades':>10}{'sem. c/ventas':>15}{'historial':>11}  {'nivel':<13}intermitente")
        for e in evaluaciones:
            print(
                f"{e.product_id:<6}{e.unidades_totales:>10.3f}{e.semanas_con_ventas:>15}"
                f"{e.semanas_historial:>11}  {e.nivel:<13}{'sí' if e.intermitente else 'no'}"
            )


if __name__ == "__main__":
    asyncio.run(main())