from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.esquemas.comun import CamelModel

TipoUnidad = Literal["UNIDAD", "KILOGRAMO"]


class ProductoPublico(CamelModel):
    id: int
    category_id: int
    sku: str
    name: str
    unit_type: TipoUnidad
    sale_price: float
    cost_price: float
    current_stock: float
    min_stock_alert: float
    is_active: bool
    created_at: datetime


class ProductoCrear(CamelModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=3, max_length=150)
    category_id: int = Field(gt=0)
    unit_type: TipoUnidad
    sale_price: float = Field(ge=0)
    min_stock_alert: float = Field(ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validar_activacion(self) -> "ProductoCrear":
        if self.is_active and self.sale_price <= 0:
            raise ValueError("Para activar el producto, el precio de venta debe ser mayor a 0")
        return self


class ProductoActualizar(CamelModel):
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=3, max_length=150)
    category_id: int | None = Field(default=None, gt=0)
    unit_type: TipoUnidad | None = None
    sale_price: float | None = Field(default=None, ge=0)
    min_stock_alert: float | None = Field(default=None, ge=0)
    is_active: bool | None = None
