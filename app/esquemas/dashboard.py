from datetime import date, datetime

from app.esquemas.comun import CamelModel


class ResumenVentas(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"totalVentas": 1250.0, "cantidadVentas": 18, "promedioPorVenta": 69.44, "piezasVendidas": 42.0, "margenBruto": 520.0}]}}

    total_ventas: float
    cantidad_ventas: int
    promedio_por_venta: float
    piezas_vendidas: float
    margen_bruto: float


class SerieSemanal(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"semana": "2026-W39", "desde": "2026-09-21", "hasta": "2026-09-27", "etiqueta": "21-27 Sep", "totalVentas": 1250.0, "piezasVendidas": 42.0, "margenBruto": 520.0}]}}

    semana: str
    desde: date
    hasta: date
    etiqueta: str
    total_ventas: float
    piezas_vendidas: float
    margen_bruto: float


class ProductoTop(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"productId": 12, "nombre": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "totalVentas": 450.0, "piezasVendidas": 10.0, "margenBruto": 180.0}]}}

    product_id: int
    nombre: str
    sku: str
    total_ventas: float
    piezas_vendidas: float
    margen_bruto: float


class AlertaStockItem(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"productId": 12, "nombre": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD", "currentStock": 2.0, "minStockAlert": 5.0, "unidadesFaltantes": 3.0, "estado": "stock_bajo"}]}}

    product_id: int
    nombre: str
    sku: str
    unit_type: str
    current_stock: float
    min_stock_alert: float
    unidades_faltantes: float
    estado: str


class AlertasStock(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"total": 3, "agotados": 1, "stockBajo": 2, "inactivos": 0, "items": [{"productId": 12, "nombre": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD", "currentStock": 2.0, "minStockAlert": 5.0, "unidadesFaltantes": 3.0, "estado": "stock_bajo"}]}]}}

    total: int
    agotados: int
    stock_bajo: int
    inactivos: int
    items: list[AlertaStockItem]


class DashboardResumen(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"periodo": "mes", "desde": "2026-09-01T05:00:00Z", "hasta": "2026-10-01T04:59:59Z", "resumenVentas": {"totalVentas": 1250.0, "cantidadVentas": 18, "promedioPorVenta": 69.44, "piezasVendidas": 42.0, "margenBruto": 520.0}, "serieSemanal": [], "topProductos": [], "alertasStock": {"total": 0, "agotados": 0, "stockBajo": 0, "inactivos": 0, "items": []}}]}}

    periodo: str
    desde: datetime
    hasta: datetime
    resumen_ventas: ResumenVentas
    serie_semanal: list[SerieSemanal]
    top_productos: list[ProductoTop]
    alertas_stock: AlertasStock