from datetime import datetime

from app.esquemas.comun import CamelModel


class MovimientoPublico(CamelModel):
    id: int
    product_id: int
    responsable: str
    movement_type: str
    quantity: float
    created_at: datetime
    reason: str | None = None
    unit_sold_price: float | None = None
    unit_cost_price: float | None = None
    waste_type: str | None = None
    sale_group_id: int | None = None
    proveedor: str | None = None
    folio: str | None = None
    unit_price_usd: float | None = None
    tipo_cambio: float | None = None
    product_name: str
    sku: str
    unit_type: str
    tipo_venta: str | None = None