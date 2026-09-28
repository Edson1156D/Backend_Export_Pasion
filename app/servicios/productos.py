from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelo.comercio_exterior import LineaComercioExterior
from app.modelo.lotes import Lote
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.ventas import DetalleVenta


async def sku_en_uso(db: AsyncSession, sku: str, excluir_id: int | None = None) -> bool:
    consulta = select(Producto.id).where(func.lower(Producto.sku) == sku.lower())
    if excluir_id is not None:
        consulta = consulta.where(Producto.id != excluir_id)
    return await db.scalar(consulta) is not None


async def producto_tiene_historial(db: AsyncSession, producto_id: int) -> bool:
    relaciones = (
        (Lote, Lote.product_id),
        (MovimientoInventario, MovimientoInventario.product_id),
        (DetalleVenta, DetalleVenta.product_id),
        (LineaComercioExterior, LineaComercioExterior.product_id),
    )
    for modelo, columna in relaciones:
        if await db.scalar(select(modelo.id).where(columna == producto_id).limit(1)) is not None:
            return True
    return False