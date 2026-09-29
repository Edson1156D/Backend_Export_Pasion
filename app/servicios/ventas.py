from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errores import ErrorDeNegocio
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.modelo.ventas import DetalleVenta, Venta
from app.servicios.inventario import consumir_lotes, costo_consumo_total, round2, validar_cantidad_positiva


async def registrar_venta(
    db: AsyncSession,
    *,
    items: list[dict[str, Decimal | int]],
    tipo_venta: str,
    metodo_pago: str,
    pago_con: Decimal | None,
    responsable: Usuario,
) -> Venta:
    productos: dict[int, Producto] = {}
    for item in items:
        product_id = int(item["product_id"])
        producto = await db.scalar(select(Producto).where(Producto.id == product_id))
        if producto is None:
            raise ErrorDeNegocio("Producto no encontrado", 404)
        if not producto.is_active:
            raise ErrorDeNegocio("Producto no encontrado", 404)
        cantidad = validar_cantidad_positiva(item["quantity"])
        if producto.unit_type == "UNIDAD" and cantidad != cantidad.to_integral_value():
            raise ErrorDeNegocio("La cantidad debe ser un número entero para productos por unidad", 400)
        productos[product_id] = producto

    lineas_por_indice = {}
    for indice, item in sorted(enumerate(items), key=lambda entrada: int(entrada[1]["product_id"])):
        producto = await db.scalar(
            select(Producto).where(Producto.id == int(item["product_id"])).with_for_update()
        )
        if producto is None or not producto.is_active:
            raise ErrorDeNegocio("Producto no encontrado", 404)
        productos[producto.id] = producto
        cantidad = validar_cantidad_positiva(item["quantity"])
        detalle_fifo = await consumir_lotes(db, product_id=producto.id, cantidad=cantidad)
        costo_unitario = round2(costo_consumo_total(detalle_fifo) / cantidad)
        precio = round2(producto.sale_price)
        lineas_por_indice[indice] = (
            {
                "producto": producto,
                "cantidad": cantidad,
                "precio": precio,
                "costo": costo_unitario,
            }
        )

    lineas = [lineas_por_indice[indice] for indice in range(len(items))]

    subtotal = round2(sum((linea["precio"] * linea["cantidad"] for linea in lineas), Decimal("0")))
    total = subtotal
    vuelto: Decimal | None = None
    if metodo_pago == "efectivo":
        if pago_con is None or pago_con < total:
            raise ErrorDeNegocio("El monto recibido debe ser mayor o igual al total", 400)
        vuelto = round2(pago_con - total)
    else:
        pago_con = None

    venta = Venta(
        folio=f"BLT-PENDIENTE-{uuid4().hex}",
        sale_type=tipo_venta,
        payment_method=metodo_pago,
        subtotal=subtotal,
        total=total,
        paid_with=round2(pago_con) if pago_con is not None else None,
        change_amount=vuelto,
        responsable_id=responsable.id,
    )
    db.add(venta)
    await db.flush()
    venta.folio = f"BLT-{venta.id:04d}"

    for linea in lineas:
        producto = linea["producto"]
        cantidad = linea["cantidad"]
        db.add(
            DetalleVenta(
                sale_id=venta.id,
                product_id=producto.id,
                name=producto.name,
                sku=producto.sku,
                unit_type=producto.unit_type,
                unit_price=linea["precio"],
                quantity=cantidad,
            )
        )
        db.add(
            MovimientoInventario(
                product_id=producto.id,
                responsable_id=responsable.id,
                movement_type="venta",
                quantity=-cantidad,
                unit_sold_price=linea["precio"],
                unit_cost_price=linea["costo"],
                sale_group_id=venta.id,
                folio=venta.folio,
            )
        )
    await db.flush()
    return venta


async def listar_ventas(db: AsyncSession, responsable_id: int | None = None) -> list[Venta]:
    consulta = (
        select(Venta)
        .options(selectinload(Venta.items), selectinload(Venta.responsable))
        .order_by(Venta.created_at.desc(), Venta.id.desc())
    )
    if responsable_id is not None:
        consulta = consulta.where(Venta.responsable_id == responsable_id)
    return list((await db.scalars(consulta)).all())