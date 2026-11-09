from datetime import datetime

from pydantic import BaseModel


class StockProductoOut(BaseModel):
    productId: int
    name: str
    sku: str
    unitType: str
    stock: float


class AlmacenOut(BaseModel):
    id: int
    name: str
    country: str | None
    isTemporary: bool
    createdAt: datetime | None
    products: list[StockProductoOut]      # stock de cada producto en este almacén