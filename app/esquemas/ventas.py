from datetime import datetime

from pydantic import BaseModel


class VentaItemOut(BaseModel):
    """Igual a `VentaItem` en frontend/src/features/ventas/types.ts."""
    productId: int
    name: str
    sku: str
    unitType: str
    unitPrice: float
    quantity: float


class VentaOut(BaseModel):
    """Igual a `Venta` del front. pagoCon y vuelto solo existen si se registraron en efectivo."""
    id: int
    items: list[VentaItemOut]
    tipoVenta: str
    metodoPago: str
    subtotal: float
    total: float
    folio: str
    responsable: str
    createdAt: datetime
    pagoCon: float | None = None
    vuelto: float | None = None


class VentaItemCrear(BaseModel):
    productId: int
    quantity: float


class VentaCrear(BaseModel):
    """Cuerpo del punto de venta. Los precios NO se envían: los pone el servidor."""
    items: list[VentaItemCrear]
    tipoVenta: str
    metodoPago: str
    pagoCon: float | None = None