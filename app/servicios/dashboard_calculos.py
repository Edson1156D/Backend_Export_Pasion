"""
Dashboard - cálculos puros (sin base de datos ni FastAPI).

Reciben las líneas de venta ya leídas y devuelven los bloques del contrato
`GET /dashboard/resumen` (frontend/src/features/dashboard/types.ts), con las
llaves ya en camelCase.

Supuestos (ajustables aquí):
- Venta = movimiento cuyo tipo está en TIPOS_VENTA (hoy solo VENTA_MAYORISTA).
- El precio de venta se convierte a soles multiplicando por `exchange_rate`.
  El costo unitario ya está en soles y no se convierte.
- Una venta (operación) es un `sale_group_id`; sin grupo, cada fila es una venta.
- Periodos calendario, hora de Lima: día = hoy, semana = lunes a domingo en curso,
  mes = mes en curso.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Lima")
SEMANAS_SERIE = 8
TOP_PRODUCTOS = 5
PERIODOS = ("dia", "semana", "mes")


@dataclass(frozen=True)
class LineaVenta:
    """Una fila de venta ya convertida a soles."""
    venta_id: str
    product_id: int
    nombre: str
    sku: str
    fecha: datetime        # con zona horaria
    cantidad: float
    total: float           # cantidad * precio unitario * tipo de cambio
    costo: float           # cantidad * costo unitario


@dataclass(frozen=True)
class ProductoStock:
    product_id: int
    nombre: str
    sku: str
    unit_type: str
    current_stock: float
    min_stock_alert: float
    is_active: bool


# --- Construcción de líneas --------------------------------------------------

def crear_linea(
    *,
    mov_id: int,
    sale_group_id: str | None,
    product_id: int,
    nombre: str,
    sku: str,
    fecha: datetime,
    cantidad: float,
    precio_unit: float | None,
    costo_unit: float | None,
    tasa: float | None,
    precio_lista: float | None,
    costo_lista: float | None,
) -> LineaVenta:
    """Aplica los respaldos: si el movimiento no trae precio/costo, se usa el del producto."""
    precio = precio_unit if precio_unit is not None else (precio_lista or 0.0)
    costo = costo_unit if costo_unit is not None else (costo_lista or 0.0)
    tipo_cambio = tasa if tasa and tasa > 0 else 1.0
    grupo = (sale_group_id or "").strip()
    return LineaVenta(
        venta_id=grupo or f"mov-{mov_id}",
        product_id=product_id,
        nombre=nombre,
        sku=sku,
        fecha=fecha.astimezone(ZONA),
        cantidad=float(cantidad),
        total=float(cantidad) * float(precio) * float(tipo_cambio),
        costo=float(cantidad) * float(costo),
    )


# --- Rangos de fechas --------------------------------------------------------

def _medianoche(dia: date) -> datetime:
    return datetime(dia.year, dia.month, dia.day, tzinfo=ZONA)


def _lunes(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


def rango_periodo(periodo: str, ahora: datetime) -> tuple[datetime, datetime]:
    """Devuelve (desde, hasta) del periodo; `hasta` es exclusivo."""
    hoy = ahora.astimezone(ZONA).date()
    if periodo == "dia":
        desde, hasta = hoy, hoy + timedelta(days=1)
    elif periodo == "semana":
        desde = _lunes(hoy)
        hasta = desde + timedelta(days=7)
    elif periodo == "mes":
        desde = hoy.replace(day=1)
        hasta = date(desde.year + 1, 1, 1) if desde.month == 12 else date(desde.year, desde.month + 1, 1)
    else:
        raise ValueError(f"Periodo no válido: {periodo!r} (use {', '.join(PERIODOS)})")
    return _medianoche(desde), _medianoche(hasta)


def rango_serie(ahora: datetime) -> tuple[datetime, datetime]:
    """Las últimas SEMANAS_SERIE semanas, terminando con la semana en curso."""
    lunes_actual = _lunes(ahora.astimezone(ZONA).date())
    inicio = lunes_actual - timedelta(weeks=SEMANAS_SERIE - 1)
    return _medianoche(inicio), _medianoche(lunes_actual + timedelta(days=7))


def rango_consulta(periodo: str, ahora: datetime) -> tuple[datetime, datetime]:
    """Ventana que cubre el periodo Y la serie, para leer de la BD una sola vez."""
    desde_p, hasta_p = rango_periodo(periodo, ahora)
    desde_s, hasta_s = rango_serie(ahora)
    return min(desde_p, desde_s), max(hasta_p, hasta_s)


# --- Bloques del resumen -----------------------------------------------------

def _en_rango(lineas: list[LineaVenta], desde: datetime, hasta: datetime) -> list[LineaVenta]:
    return [l for l in lineas if desde <= l.fecha < hasta]


def _totales(lineas: list[LineaVenta]) -> tuple[float, float, float]:
    total = sum(l.total for l in lineas)
    piezas = sum(l.cantidad for l in lineas)
    margen = total - sum(l.costo for l in lineas)
    return round(total, 2), round(piezas, 3), round(margen, 2)


def construir_resumen(lineas: list[LineaVenta], desde: datetime, hasta: datetime) -> dict:
    sel = _en_rango(lineas, desde, hasta)
    total, piezas, margen = _totales(sel)
    ventas = len({l.venta_id for l in sel})
    return {
        "totalVentas": total,
        "cantidadVentas": ventas,
        "promedioPorVenta": round(total / ventas, 2) if ventas else 0.0,
        "piezasVendidas": piezas,
        "margenBruto": margen,
    }


def construir_serie(lineas: list[LineaVenta], ahora: datetime) -> list[dict]:
    """Una entrada por semana, también las que no tuvieron ventas (con ceros)."""
    inicio, _ = rango_serie(ahora)
    primer_lunes = inicio.date()
    serie = []
    for i in range(SEMANAS_SERIE):
        lunes = primer_lunes + timedelta(weeks=i)
        desde, hasta = _medianoche(lunes), _medianoche(lunes + timedelta(days=7))
        total, piezas, margen = _totales(_en_rango(lineas, desde, hasta))
        iso = lunes.isocalendar()
        serie.append({
            "semana": f"{iso.year}-W{iso.week:02d}",
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "etiqueta": f"S{iso.week}",
            "totalVentas": total,
            "piezasVendidas": piezas,
            "margenBruto": margen,
        })
    return serie


def construir_top(
    lineas: list[LineaVenta], desde: datetime, hasta: datetime, n: int = TOP_PRODUCTOS
) -> list[dict]:
    """Los n productos con mayor facturación del periodo."""
    por_producto: dict[int, dict] = {}
    for l in _en_rango(lineas, desde, hasta):
        acc = por_producto.setdefault(
            l.product_id,
            {"nombre": l.nombre, "sku": l.sku, "total": 0.0, "piezas": 0.0, "costo": 0.0},
        )
        acc["total"] += l.total
        acc["piezas"] += l.cantidad
        acc["costo"] += l.costo

    ordenados = sorted(por_producto.items(), key=lambda kv: (-kv[1]["total"], kv[0]))[:n]
    return [
        {
            "productId": pid,
            "nombre": a["nombre"],
            "sku": a["sku"],
            "totalVentas": round(a["total"], 2),
            "piezasVendidas": round(a["piezas"], 3),
            "margenBruto": round(a["total"] - a["costo"], 2),
        }
        for pid, a in ordenados
    ]


def construir_alertas(productos: list[ProductoStock]) -> dict:
    """
    Alertas de stock (no dependen del periodo):
    - inactivo: producto desactivado.
    - agotado:  activo y stock <= 0.
    - bajo:     activo y 0 < stock <= mínimo de alerta.
    """
    items = []
    for p in productos:
        if not p.is_active:
            estado, faltantes = "inactivo", 0.0
        elif p.current_stock <= 0:
            estado, faltantes = "agotado", max(p.min_stock_alert - p.current_stock, 0.0)
        elif p.current_stock <= p.min_stock_alert:
            estado, faltantes = "bajo", p.min_stock_alert - p.current_stock
        else:
            continue
        items.append({
            "productId": p.product_id,
            "nombre": p.nombre,
            "sku": p.sku,
            "unitType": p.unit_type,
            "currentStock": p.current_stock,
            "minStockAlert": p.min_stock_alert,
            "unidadesFaltantes": round(faltantes, 3),
            "estado": estado,
        })
    return {
        "total": len(items),
        "agotados": sum(1 for i in items if i["estado"] == "agotado"),
        "stockBajo": sum(1 for i in items if i["estado"] == "bajo"),
        "inactivos": sum(1 for i in items if i["estado"] == "inactivo"),
        "items": items,
    }


def armar_resumen(
    periodo: str,
    ahora: datetime,
    lineas: list[LineaVenta],
    productos: list[ProductoStock],
) -> dict:
    """Respuesta completa de GET /dashboard/resumen."""
    desde, hasta = rango_periodo(periodo, ahora)
    return {
        "periodo": periodo,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "resumenVentas": construir_resumen(lineas, desde, hasta),
        "serieSemanal": construir_serie(lineas, ahora),
        "topProductos": construir_top(lineas, desde, hasta),
        "alertasStock": construir_alertas(productos),
    }