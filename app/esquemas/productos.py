from datetime import datetime
from typing import Literal

from pydantic import BaseModel

class CategoriaOut(BaseModel):
    """Igual a `Category` en frontend/src/types/products.ts."""
    id: int
    parentId: int | None
    name: str
    description: str | None


class ProductoOut(BaseModel):
    """Igual a `Product` en frontend/src/types/products.ts."""
    id: int
    categoryId: int
    sku: str
    name: str
    unitType: str            # "UNIDAD" | "KILOGRAMO"
    salePrice: float
    costPrice: float         # el front exige número; si la BD tiene NULL se envía 0
    currentStock: float
    minStockAlert: float
    isActive: bool
    createdAt: datetime | None


def categoria_a_out(c) -> CategoriaOut:
    return CategoriaOut(id=c.id, parentId=c.parent_id, name=c.name, description=c.description)


def producto_a_out(p) -> ProductoOut:
    return ProductoOut(
        id=p.id,
        categoryId=p.category_id,
        sku=p.sku,
        name=p.name,
        unitType=(p.unit_type or "").strip().upper(),
        salePrice=float(p.sale_price),
        costPrice=float(p.cost_price) if p.cost_price is not None else 0.0,
        currentStock=float(p.current_stock),
        minStockAlert=float(p.min_stock_alert),
        isActive=p.is_active is not False,   # NULL se trata como activo
        createdAt=p.created_at,
    )

UnidadMedida = Literal["UNIDAD", "KILOGRAMO"]


class ProductoCrear(BaseModel):
    """Igual a `ProductCreateData` del front. Stock y costo NO se envían: los calcula el sistema."""
    categoryId: int
    sku: str
    name: str
    unitType: UnidadMedida
    salePrice: float
    minStockAlert: float
    isActive: bool = True


class ProductoActualizar(BaseModel):
    """Igual a `ProductUpdateData` del front: solo se cambian los campos que lleguen."""
    categoryId: int | None = None
    sku: str | None = None
    name: str | None = None
    unitType: UnidadMedida | None = None
    salePrice: float | None = None
    minStockAlert: float | None = None
    isActive: bool | None = None