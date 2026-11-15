from datetime import datetime

from pydantic import BaseModel


class MovimientoOut(BaseModel):
    """Igual a `InventoryMovement` en frontend/src/features/movimientos/types.ts."""
    id: int
    productId: int
    responsable: str
    movementType: str        # entrada | venta | merma | importacion | exportacion | transferencia
    quantity: float
    createdAt: datetime
    productName: str
    sku: str
    unitType: str            # UNIDAD | KILOGRAMO
    # Opcionales: la ruta usa response_model_exclude_none, así que no viajan en null.
    reason: str | None = None
    unitSoldPrice: float | None = None
    unitCostPrice: float | None = None
    wasteType: str | None = None
    folio: str | None = None
    unitPriceUSD: float | None = None
    tipoCambio: float | None = None
    tipoVenta: str | None = None