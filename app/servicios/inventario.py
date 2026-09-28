from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorDeNegocio
from app.modelo.lotes import Lote
from app.modelo.productos import Producto

CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class LoteDisponible:
    lote_id: int
    product_id: int
    cantidad_disponible: Decimal
    costo_unitario: Decimal
    fecha_ingreso: datetime


def _decimal(valor: Decimal | int | float | str) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def round2(valor: Decimal | int | float | str) -> Decimal:
    try:
        decimal = _decimal(valor)
        if not decimal.is_finite():
            raise ValueError("El valor debe ser un número finito")
        return decimal.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("El valor debe ser un número finito") from None


def validar_cantidad_positiva(cantidad: Decimal | int | float | str) -> Decimal:
    try:
        resultado = round2(cantidad)
    except (InvalidOperation, ValueError):
        raise ValueError("La cantidad debe ser mayor a 0") from None
    if resultado <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    return resultado


def validar_costo_no_negativo(costo: Decimal | int | float | str) -> Decimal:
    try:
        resultado = round2(costo)
    except (InvalidOperation, ValueError):
        raise ValueError("El costo no puede ser negativo") from None
    if resultado < 0:
        raise ValueError("El costo no puede ser negativo")
    return resultado


def sum_disponible(lotes: Iterable[LoteDisponible]) -> Decimal:
    return round2(sum((_decimal(lote.cantidad_disponible) for lote in lotes), Decimal("0")))


def costo_promedio_ponderado(lotes: Iterable[LoteDisponible]) -> Decimal:
    lotes = list(lotes)
    total = sum_disponible(lotes)
    if total <= 0:
        return Decimal("0.00")
    valor = sum(
        (_decimal(lote.cantidad_disponible) * _decimal(lote.costo_unitario) for lote in lotes),
        Decimal("0"),
    )
    return round2(valor / total)


def costo_consumo_total(detalles: Iterable[dict[str, Any]]) -> Decimal:
    valor = sum(
        (_decimal(detalle["cantidad"]) * _decimal(detalle["costo_unitario"])
         for detalle in detalles),
        Decimal("0"),
    )
    return round2(valor)


def _orden_fifo(lotes: Iterable[LoteDisponible]) -> list[LoteDisponible]:
    return sorted(
        (lote for lote in lotes if _decimal(lote.cantidad_disponible) > 0),
        key=lambda lote: (lote.fecha_ingreso, lote.lote_id),
    )


def asignar_consumo_fifo(
    lotes: Iterable[LoteDisponible], cantidad: Decimal | int | float | str
) -> list[dict[str, Decimal | int]]:
    cantidad_validada = validar_cantidad_positiva(cantidad)
    disponibles = _orden_fifo(lotes)
    disponible_total = sum_disponible(disponibles)
    if disponible_total < cantidad_validada:
        raise ValueError(
            f"Stock insuficiente: hay {disponible_total:.2f} y se requieren {cantidad_validada:.2f}"
        )

    restante = cantidad_validada
    detalle: list[dict[str, Decimal | int]] = []
    for lote in disponibles:
        if restante <= 0:
            break
        cargar = min(_decimal(lote.cantidad_disponible), restante)
        detalle.append(
            {
                "lote_id": lote.lote_id,
                "cantidad": round2(cargar),
                "costo_unitario": round2(lote.costo_unitario),
            }
        )
        restante = round2(restante - cargar)
    return detalle


def _a_lote_disponible(lote: Lote) -> LoteDisponible:
    received_at = lote.received_at or datetime.now(timezone.utc)
    return LoteDisponible(
        lote_id=lote.id,
        product_id=lote.product_id,
        cantidad_disponible=_decimal(lote.available_qty),
        costo_unitario=_decimal(lote.unit_cost_pen),
        fecha_ingreso=received_at,
    )


async def _bloquear_lotes_producto(db: AsyncSession, product_id: int) -> list[Lote]:
    resultado = await db.scalars(
        select(Lote)
        .where(Lote.product_id == product_id, Lote.available_qty > 0)
        .order_by(Lote.product_id, Lote.received_at, Lote.id)
        .with_for_update()
    )
    return list(resultado.all())


async def sincronizar_stock_producto(db: AsyncSession, product_id: int) -> Producto:
    producto = await db.scalar(select(Producto).where(Producto.id == product_id).with_for_update())
    if producto is None:
        raise ErrorDeNegocio("Producto no encontrado", 404)
    lotes = await _bloquear_lotes_producto(db, product_id)
    disponibles = [_a_lote_disponible(lote) for lote in lotes]
    producto.current_stock = sum_disponible(disponibles)
    if producto.current_stock > 0:
        producto.cost_price = costo_promedio_ponderado(disponibles)
    await db.flush()
    return producto


async def ingresar_lote(
    db: AsyncSession,
    *,
    product_id: int,
    cantidad: Decimal | int | float | str,
    origen: str,
    responsable_id: int,
    costo_unitario_soles: Decimal | int | float | str | None = None,
    supplier_id: int | None = None,
    foreign_partner_id: int | None = None,
    received_at: datetime | None = None,
) -> Lote:
    cantidad_validada = validar_cantidad_positiva(cantidad)
    producto = await db.scalar(select(Producto).where(Producto.id == product_id).with_for_update())
    if producto is None:
        raise ErrorDeNegocio("Producto no encontrado", 404)

    existentes = await _bloquear_lotes_producto(db, product_id)
    disponibles = [_a_lote_disponible(lote) for lote in existentes]
    if origen == "entrada":
        costo = costo_promedio_ponderado(disponibles) if disponibles else Decimal("0.00")
    elif costo_unitario_soles is None:
        costo = costo_promedio_ponderado(disponibles) if disponibles else round2(producto.cost_price)
    else:
        try:
            costo = validar_costo_no_negativo(costo_unitario_soles)
        except ValueError as error:
            raise ErrorDeNegocio(str(error), 400) from error

    lote = Lote(
        product_id=product_id,
        code=f"LOTE-PENDIENTE-{uuid4().hex}",
        origin=origen,
        initial_qty=cantidad_validada,
        available_qty=cantidad_validada,
        unit_cost_pen=costo,
        supplier_id=supplier_id,
        foreign_partner_id=foreign_partner_id,
        responsable_id=responsable_id,
        received_at=received_at or datetime.now(timezone.utc),
    )
    db.add(lote)
    await db.flush()
    lote.code = f"LOTE-{lote.id:04d}"
    await db.flush()
    await sincronizar_stock_producto(db, product_id)
    return lote


async def consumir_lotes(
    db: AsyncSession, *, product_id: int, cantidad: Decimal | int | float | str
) -> list[dict[str, Decimal | int]]:
    cantidad_validada = validar_cantidad_positiva(cantidad)
    lotes = await _bloquear_lotes_producto(db, product_id)
    disponibles = [_a_lote_disponible(lote) for lote in lotes]
    try:
        detalle = asignar_consumo_fifo(disponibles, cantidad_validada)
    except ValueError as error:
        if str(error).startswith("Stock insuficiente"):
            raise ErrorDeNegocio(str(error), 409) from error
        raise

    por_id = {lote.id: lote for lote in lotes}
    for linea in detalle:
        lote = por_id[int(linea["lote_id"])]
        lote.available_qty = round2(_decimal(lote.available_qty) - _decimal(linea["cantidad"]))
    await db.flush()
    await sincronizar_stock_producto(db, product_id)
    return detalle


async def verificar_consistencia_stock(db: AsyncSession) -> list[int]:
    productos = (await db.scalars(select(Producto).order_by(Producto.id))).all()
    inconsistentes: list[int] = []
    for producto in productos:
        lotes = (await db.scalars(select(Lote).where(Lote.product_id == producto.id))).all()
        stock_lotes = sum_disponible(
            LoteDisponible(lote.id, lote.product_id, _decimal(lote.available_qty), _decimal(lote.unit_cost_pen), lote.received_at)
            for lote in lotes
        )
        if round2(producto.current_stock) != stock_lotes:
            inconsistentes.append(producto.id)
    return inconsistentes
