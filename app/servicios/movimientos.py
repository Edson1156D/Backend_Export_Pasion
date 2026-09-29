from collections.abc import Sequence

from sqlalchemy import outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.esquemas.movimientos import MovimientoPublico
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.modelo.ventas import Venta

_TIPOS_VENTA = {
    "tienda": "Tienda",
    "feria": "Feria",
    "digital": "Digital",
    "otro": "Otro",
}


def _float_or_none(value: object) -> float | None:
    return float(value) if value is not None else None


async def listar_movimientos(db: AsyncSession) -> Sequence[MovimientoPublico]:
    producto_join = outerjoin(MovimientoInventario, Producto, MovimientoInventario.product_id == Producto.id)
    venta_join = outerjoin(producto_join, Venta, MovimientoInventario.sale_group_id == Venta.id)
    consulta = (
        select(MovimientoInventario, Producto, Usuario, Venta)
        .select_from(venta_join)
        .join(Usuario, MovimientoInventario.responsable_id == Usuario.id)
        .order_by(MovimientoInventario.created_at.desc(), MovimientoInventario.id.desc())
    )
    filas = (await db.execute(consulta)).all()

    return [
        MovimientoPublico(
            id=movimiento.id,
            product_id=movimiento.product_id,
            responsable=responsable.full_name,
            movement_type=movimiento.movement_type,
            quantity=float(movimiento.quantity),
            created_at=movimiento.created_at,
            reason=movimiento.reason,
            unit_sold_price=_float_or_none(movimiento.unit_sold_price),
            unit_cost_price=_float_or_none(movimiento.unit_cost_price),
            waste_type=movimiento.waste_type,
            sale_group_id=movimiento.sale_group_id,
            proveedor=movimiento.supplier_name,
            folio=movimiento.folio or (venta.folio if venta is not None else None),
            unit_price_usd=_float_or_none(movimiento.unit_price_usd),
            tipo_cambio=_float_or_none(movimiento.exchange_rate),
            product_name=producto.name if producto is not None else "Producto no disponible",
            sku=producto.sku if producto is not None else "—",
            unit_type=producto.unit_type if producto is not None else "UNIDAD",
            tipo_venta=_TIPOS_VENTA.get(venta.sale_type) if venta is not None else None,
        )
        for movimiento, producto, responsable, venta in filas
    ]