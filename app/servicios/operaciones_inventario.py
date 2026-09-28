from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorDeNegocio
from app.modelo.entradas import EntradaStock
from app.modelo.lotes import Lote
from app.modelo.mermas import Merma
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.proveedores import Proveedor
from app.modelo.usuarios import Usuario
from app.servicios.inventario import consumir_lotes, costo_consumo_total, ingresar_lote, round2


async def _producto(db: AsyncSession, product_id: int) -> Producto:
    producto = await db.get(Producto, product_id)
    if producto is None:
        raise ErrorDeNegocio("Producto no encontrado", 404)
    return producto


async def _proveedor(db: AsyncSession, supplier_id: int | None) -> Proveedor | None:
    if supplier_id is None:
        return None
    proveedor = await db.get(Proveedor, supplier_id)
    if proveedor is None:
        raise ErrorDeNegocio("Proveedor no encontrado", 404)
    return proveedor


async def _registrar_entrada(
    db: AsyncSession,
    *,
    producto: Producto,
    cantidad: Decimal,
    responsable: Usuario,
    origen: str,
    proveedor: Proveedor | None = None,
    costo_unitario: Decimal | None = None,
    notas: str | None = None,
) -> EntradaStock:
    lote = await ingresar_lote(
        db,
        product_id=producto.id,
        cantidad=cantidad,
        origen=origen,
        responsable_id=responsable.id,
        costo_unitario_soles=costo_unitario,
        supplier_id=proveedor.id if proveedor else None,
    )
    entrada = EntradaStock(
        product_id=producto.id,
        quantity=cantidad,
        supplier_id=proveedor.id if proveedor else None,
        responsable_id=responsable.id,
        notes=notas,
    )
    db.add(entrada)
    db.add(
        MovimientoInventario(
            product_id=producto.id,
            responsable_id=responsable.id,
            movement_type="entrada",
            quantity=cantidad,
            reason=notas,
            unit_sold_price=round2(producto.sale_price),
            unit_cost_price=round2(lote.unit_cost_pen),
            supplier_name=proveedor.name if proveedor else None,
        )
    )
    await db.flush()
    return entrada


async def registrar_entrada_produccion(
    db: AsyncSession, *, product_id: int, cantidad: Decimal, responsable: Usuario, notas: str | None
) -> EntradaStock:
    producto = await _producto(db, product_id)
    return await _registrar_entrada(
        db,
        producto=producto,
        cantidad=cantidad,
        responsable=responsable,
        origen="entrada",
        notas=notas or "Producción del taller",
    )


async def registrar_compra(
    db: AsyncSession,
    *,
    product_id: int,
    cantidad: Decimal,
    proveedor_id: int | None,
    costo_unitario: Decimal | None,
    responsable: Usuario,
    notas: str | None,
) -> EntradaStock:
    producto = await _producto(db, product_id)
    proveedor = await _proveedor(db, proveedor_id)
    if costo_unitario is None:
        tiene_lotes = await db.scalar(select(exists().where(Lote.product_id == product_id)))
        if not tiene_lotes:
            raise ErrorDeNegocio(
                "El costo de compra es obligatorio cuando el producto aún no tiene stock", 400
            )
    return await _registrar_entrada(
        db,
        producto=producto,
        cantidad=cantidad,
        responsable=responsable,
        origen="compra",
        proveedor=proveedor,
        costo_unitario=costo_unitario,
        notas=notas or "Compra a proveedor",
    )


async def registrar_merma(
    db: AsyncSession,
    *,
    product_id: int,
    cantidad: Decimal,
    motivo: str,
    detalle: str | None,
    responsable: Usuario,
) -> Merma:
    producto = await _producto(db, product_id)
    lotes = await consumir_lotes(db, product_id=product_id, cantidad=cantidad)
    costo_unitario = round2(costo_consumo_total(lotes) / cantidad)
    merma = Merma(
        product_id=product_id,
        quantity=cantidad,
        reason_code=motivo,
        detail=detalle,
        responsable_id=responsable.id,
    )
    db.add(merma)
    db.add(
        MovimientoInventario(
            product_id=product_id,
            responsable_id=responsable.id,
            movement_type="merma",
            quantity=-cantidad,
            reason=detalle,
            unit_sold_price=round2(producto.sale_price),
            unit_cost_price=costo_unitario,
            waste_type=motivo,
        )
    )
    await db.flush()
    return merma