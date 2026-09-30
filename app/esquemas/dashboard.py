from datetime import date, datetime

from app.esquemas.comun import CamelModel


class ResumenVentas(CamelModel):
    total_ventas: float
    cantidad_ventas: int
    promedio_por_venta: float
    piezas_vendidas: float
    margen_bruto: float


class SerieSemanal(CamelModel):
    semana: str
    desde: date
    hasta: date
    etiqueta: str
    total_ventas: float
    piezas_vendidas: float
    margen_bruto: float


class ProductoTop(CamelModel):
    product_id: int
    nombre: str
    sku: str
    total_ventas: float
    piezas_vendidas: float
    margen_bruto: float


class AlertaStockItem(CamelModel):
    product_id: int
    nombre: str
    sku: str
    unit_type: str
    current_stock: float
    min_stock_alert: float
    unidades_faltantes: float
    estado: str


class AlertasStock(CamelModel):
    total: int
    agotados: int
    stock_bajo: int
    inactivos: int
    items: list[AlertaStockItem]


class DashboardResumen(CamelModel):
    periodo: str
    desde: datetime
    hasta: datetime
    resumen_ventas: ResumenVentas
    serie_semanal: list[SerieSemanal]
    top_productos: list[ProductoTop]
    alertas_stock: AlertasStock