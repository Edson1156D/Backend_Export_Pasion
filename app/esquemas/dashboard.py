from typing import Literal

from pydantic import BaseModel


class ResumenVentas(BaseModel):
    totalVentas: float
    cantidadVentas: int
    promedioPorVenta: float
    piezasVendidas: float
    margenBruto: float


class SemanaVentas(BaseModel):
    semana: str            # ej. "2026-W42"
    desde: str             # ISO 8601, hora de Lima
    hasta: str
    etiqueta: str          # ej. "S42"
    totalVentas: float
    piezasVendidas: float
    margenBruto: float


class TopProducto(BaseModel):
    productId: int
    nombre: str
    sku: str
    totalVentas: float
    piezasVendidas: float
    margenBruto: float


class AlertaStock(BaseModel):
    productId: int
    nombre: str
    sku: str
    unitType: str          # UNIDAD | KILOGRAMO
    currentStock: float
    minStockAlert: float
    unidadesFaltantes: float
    estado: Literal["agotado", "bajo", "inactivo"]


class AlertasStock(BaseModel):
    total: int
    agotados: int
    stockBajo: int
    inactivos: int
    items: list[AlertaStock]


class DashboardResumenResponse(BaseModel):
    periodo: Literal["dia", "semana", "mes"]
    desde: str
    hasta: str
    resumenVentas: ResumenVentas
    serieSemanal: list[SemanaVentas]
    topProductos: list[TopProducto]
    alertasStock: AlertasStock