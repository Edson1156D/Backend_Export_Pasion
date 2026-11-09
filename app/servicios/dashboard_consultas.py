"""Consultas a la base de datos para el dashboard. Solo lectura."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.suficiencia import TIPOS_VENTA
from app.modelo.movimientos import MovimientoInventario as Mov
from app.modelo.productos import Producto
from app.servicios.dashboard_calculos import LineaVenta, ProductoStock, crear_linea


def _num(valor) -> float | None:
    """Numeric de la BD llega como Decimal; se pasa a float conservando el None."""
    return None if valor is None else float(valor)


async def leer_lineas_venta(db: AsyncSession, desde: datetime, hasta: datetime) -> list[LineaVenta]:
    """Ventas con created_at en [desde, hasta), cada una con su producto."""
    consulta = (
        select(
            Mov.id,
            Mov.sale_group_id,
            Mov.product_id,
            Producto.name,
            Producto.sku,
            Mov.created_at,
            Mov.quantity,
            Mov.unit_sold_price,
            Mov.unit_cost_price,
            Mov.exchange_rate,
            Producto.sale_price,
            Producto.cost_price,
        )
        .join(Producto, Producto.id == Mov.product_id)
        # movement_type es texto libre: mismo criterio que en ml/consultas.py
        .where(func.upper(func.trim(Mov.movement_type)).in_(TIPOS_VENTA))
        .where(Mov.created_at >= desde, Mov.created_at < hasta)
        .order_by(Mov.created_at, Mov.id)
    )
    filas = (await db.execute(consulta)).all()
    return [
        crear_linea(
            mov_id=f.id,
            sale_group_id=f.sale_group_id,
            product_id=f.product_id,
            nombre=f.name,
            sku=f.sku,
            fecha=f.created_at,
            cantidad=float(f.quantity),
            precio_unit=_num(f.unit_sold_price),
            costo_unit=_num(f.unit_cost_price),
            tasa=_num(f.exchange_rate),
            precio_lista=_num(f.sale_price),
            costo_lista=_num(f.cost_price),
        )
        for f in filas
    ]


async def leer_productos_stock(db: AsyncSession) -> list[ProductoStock]:
    """Todos los productos con su stock actual, para las alertas."""
    consulta = select(
        Producto.id,
        Producto.name,
        Producto.sku,
        Producto.unit_type,
        Producto.current_stock,
        Producto.min_stock_alert,
        Producto.is_active,
    ).order_by(Producto.id)
    filas = (await db.execute(consulta)).all()
    return [
        ProductoStock(
            product_id=f.id,
            nombre=f.name,
            sku=f.sku,
            unit_type=f.unit_type,
            current_stock=float(f.current_stock),
            min_stock_alert=float(f.min_stock_alert),
            is_active=f.is_active is not False,   # NULL cuenta como activo (igual que en el login)
        )
        for f in filas
    ]