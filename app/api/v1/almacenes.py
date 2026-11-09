from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.session import get_db
from app.core.seguridad import requiere_rol
from app.esquemas.almacenes import AlmacenOut, StockProductoOut
from app.modelo.almacenes import Almacen
from app.modelo.productos import Producto, StockPorAlmacen
from app.servicios.almacen_reglas import PREFIJO_SOCIO

router = APIRouter(tags=["almacenes"], dependencies=[Depends(requiere_rol("ADMIN"))])


@router.get("/almacenes", response_model=list[AlmacenOut])
async def listar_almacenes(db: AsyncSession = Depends(get_db)):
    """Almacenes con el stock de cada producto (lo que mantiene el trigger de movimientos)."""
    almacenes = (
        await db.execute(
            select(Almacen)
            .where(~func.upper(func.trim(Almacen.name)).like(PREFIJO_SOCIO + "%"))   # sin los socios comerciales
            .order_by(Almacen.id)
        )
    ).scalars().all()
    filas = (
        await db.execute(
            select(
                StockPorAlmacen.warehouse_id,
                StockPorAlmacen.product_id,
                StockPorAlmacen.stock,
                Producto.name,
                Producto.sku,
                Producto.unit_type,
            )
            .select_from(StockPorAlmacen)
            .outerjoin(Producto, Producto.id == StockPorAlmacen.product_id)
            .order_by(StockPorAlmacen.warehouse_id, StockPorAlmacen.product_id)
        )
    ).all()

    por_almacen: dict[int, list[StockProductoOut]] = defaultdict(list)
    for fila in filas:
        por_almacen[fila.warehouse_id].append(
            StockProductoOut(
                productId=fila.product_id,
                name=fila.name or f"Producto {fila.product_id}",
                sku=fila.sku or "",
                unitType=(fila.unit_type or "").strip().upper(),
                stock=float(fila.stock),
            )
        )

    return [
        AlmacenOut(
            id=a.id,
            name=a.name,
            country=a.country,
            isTemporary=a.is_temporary is True,
            createdAt=a.created_at,
            products=por_almacen.get(a.id, []),
        )
        for a in almacenes
    ]
