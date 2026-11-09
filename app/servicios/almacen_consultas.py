"""Consultas de almacén y stock para registrar movimientos (usa la BD)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelo.almacenes import Almacen
from app.modelo.productos import StockPorAlmacen
from app.servicios.almacen_reglas import elegir_principal


async def almacen_principal_id(db: AsyncSession) -> int:
    filas = (
        await db.execute(select(Almacen.id, Almacen.name, Almacen.country, Almacen.is_temporary).order_by(Almacen.id))
    ).all()
    return elegir_principal(
        [{"id": f.id, "name": f.name, "country": f.country, "is_temporary": f.is_temporary} for f in filas]
    )

async def stock_disponible(db: AsyncSession, almacen_id: int, product_ids: list[int]) -> dict[int, float]:
    """
    Stock de cada producto en el almacén. Las filas se BLOQUEAN hasta el commit (FOR UPDATE),
    así dos ventas simultáneas no pueden gastar el mismo stock: la base no valida stock sola.
    Un producto sin fila de stock en ese almacén no aparece (= 0).
    """
    consulta = (
        select(StockPorAlmacen.product_id, StockPorAlmacen.stock)
        .where(StockPorAlmacen.warehouse_id == almacen_id, StockPorAlmacen.product_id.in_(product_ids))
        .order_by(StockPorAlmacen.product_id)       # mismo orden siempre: evita bloqueos cruzados
        .with_for_update()
    )
    return {fila.product_id: float(fila.stock) for fila in (await db.execute(consulta)).all()}