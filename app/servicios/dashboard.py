from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.esquemas.dashboard import (
    AlertaStockItem,
    AlertasStock,
    DashboardResumen,
    ProductoTop,
    ResumenVentas,
    SerieSemanal,
)
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.ventas import Venta

_LIMA = timezone(timedelta(hours=-5), "America/Lima")
_PERIODOS = {"dia", "semana", "mes"}
_SEMANAS_SERIE = 8


def _inicio_periodo(fecha: date, periodo: str) -> date:
    if periodo == "dia":
        return fecha
    if periodo == "semana":
        return fecha - timedelta(days=fecha.weekday())
    return fecha.replace(day=1)


def _siguiente_mes(fecha: date) -> date:
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 1)
    return date(fecha.year, fecha.month + 1, 1)


def _limites_periodo(periodo: str, ahora: datetime) -> tuple[datetime, datetime]:
    fecha_local = ahora.astimezone(_LIMA).date()
    inicio = _inicio_periodo(fecha_local, periodo)
    if periodo == "dia":
        fin = inicio + timedelta(days=1)
    elif periodo == "semana":
        fin = inicio + timedelta(days=7)
    else:
        fin = _siguiente_mes(inicio)
    return (
        datetime.combine(inicio, time.min, tzinfo=_LIMA).astimezone(timezone.utc),
        datetime.combine(fin, time.min, tzinfo=_LIMA).astimezone(timezone.utc),
    )


def _fin_exclusivo_a_local(fecha: datetime) -> date:
    return fecha.astimezone(_LIMA).date()


def _numero(valor: Decimal | int | float | None) -> float:
    return float(valor or 0)


def _margen(movimiento: MovimientoInventario) -> Decimal:
    cantidad = abs(movimiento.quantity or Decimal("0"))
    return cantidad * (
        (movimiento.unit_sold_price or Decimal("0"))
        - (movimiento.unit_cost_price or Decimal("0"))
    )


async def obtener_resumen_dashboard(
    db: AsyncSession,
    periodo: str,
    ahora: datetime | None = None,
) -> DashboardResumen:
    if periodo not in _PERIODOS:
        raise ValueError("El periodo debe ser dia, semana o mes")

    ahora = ahora or datetime.now(timezone.utc)
    desde, hasta = _limites_periodo(periodo, ahora)
    ventas = list(
        (
            await db.scalars(
                select(Venta)
                .where(Venta.created_at >= desde, Venta.created_at < hasta)
            )
        ).all()
    )
    movimientos = list(
        (
            await db.scalars(
                select(MovimientoInventario)
                .where(
                    MovimientoInventario.movement_type == "venta",
                    MovimientoInventario.created_at >= desde,
                    MovimientoInventario.created_at < hasta,
                )
            )
        ).all()
    )
    productos = list((await db.scalars(select(Producto))).all())
    productos_por_id = {producto.id: producto for producto in productos}

    total_ventas = sum((venta.total for venta in ventas), Decimal("0"))
    piezas = sum((abs(movimiento.quantity) for movimiento in movimientos), Decimal("0"))
    margen = sum((_margen(movimiento) for movimiento in movimientos), Decimal("0"))

    por_producto: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: {"ventas": Decimal("0"), "piezas": Decimal("0"), "margen": Decimal("0")}
    )
    por_semana: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"ventas": Decimal("0"), "piezas": Decimal("0"), "margen": Decimal("0")}
    )
    for movimiento in movimientos:
        cantidad = abs(movimiento.quantity or Decimal("0"))
        importe = cantidad * (movimiento.unit_sold_price or Decimal("0"))
        costo = _margen(movimiento)
        por_producto[movimiento.product_id]["ventas"] += importe
        por_producto[movimiento.product_id]["piezas"] += cantidad
        por_producto[movimiento.product_id]["margen"] += costo
        fecha_local = movimiento.created_at.astimezone(_LIMA).date()
        semana = fecha_local - timedelta(days=fecha_local.weekday())
        por_semana[semana]["ventas"] += importe
        por_semana[semana]["piezas"] += cantidad
        por_semana[semana]["margen"] += costo

    fecha_fin_local = _fin_exclusivo_a_local(hasta)
    primera_semana = fecha_fin_local - timedelta(days=fecha_fin_local.weekday() + 7 * _SEMANAS_SERIE)
    serie = []
    for indice in range(_SEMANAS_SERIE):
        semana = primera_semana + timedelta(days=indice * 7)
        siguiente = semana + timedelta(days=7)
        valores = por_semana[semana]
        iso = semana.isocalendar()
        serie.append(
            SerieSemanal(
                semana=f"{iso.year}-W{iso.week:02d}",
                desde=semana,
                hasta=siguiente - timedelta(days=1),
                etiqueta=f"S{iso.week}",
                total_ventas=_numero(valores["ventas"]),
                piezas_vendidas=_numero(valores["piezas"]),
                margen_bruto=_numero(valores["margen"]),
            )
        )

    top = []
    for product_id, valores in sorted(
        por_producto.items(),
        key=lambda item: (-item[1]["ventas"], -item[1]["piezas"], item[0]),
    )[:5]:
        producto = productos_por_id.get(product_id)
        if producto is not None:
            top.append(
                ProductoTop(
                    product_id=producto.id,
                    nombre=producto.name,
                    sku=producto.sku,
                    total_ventas=_numero(valores["ventas"]),
                    piezas_vendidas=_numero(valores["piezas"]),
                    margen_bruto=_numero(valores["margen"]),
                )
            )

    alertas = []
    agotados = stock_bajo = inactivos = 0
    for producto in sorted(productos, key=lambda item: item.name.lower()):
        stock = _numero(producto.current_stock)
        minimo = _numero(producto.min_stock_alert)
        estado = None
        if stock == 0:
            agotados += 1
            estado = "agotado"
        elif stock <= minimo:
            stock_bajo += 1
            estado = "bajo"
        if not producto.is_active:
            inactivos += 1
            estado = estado or "inactivo"
        if estado:
            alertas.append(
                AlertaStockItem(
                    product_id=producto.id,
                    nombre=producto.name,
                    sku=producto.sku,
                    unit_type=producto.unit_type,
                    current_stock=stock,
                    min_stock_alert=minimo,
                    unidades_faltantes=max(0, minimo - stock),
                    estado=estado,
                )
            )

    return DashboardResumen(
        periodo=periodo,
        desde=desde,
        hasta=hasta,
        resumen_ventas=ResumenVentas(
            total_ventas=_numero(total_ventas),
            cantidad_ventas=len(ventas),
            promedio_por_venta=_numero(total_ventas / len(ventas)) if ventas else 0,
            piezas_vendidas=_numero(piezas),
            margen_bruto=_numero(margen),
        ),
        serie_semanal=serie,
        top_productos=top,
        alertas_stock=AlertasStock(
            total=len(alertas),
            agotados=agotados,
            stock_bajo=stock_bajo,
            inactivos=inactivos,
            items=alertas,
        ),
    )