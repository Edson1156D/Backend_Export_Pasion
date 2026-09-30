from datetime import datetime

from app.esquemas.comun import CamelModel


class MovimientoPublico(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 55, "productId": 12, "responsable": "Ana Torres", "movementType": "venta", "quantity": -2.0, "createdAt": "2026-09-29T15:30:00Z", "reason": "Venta POS", "unitSoldPrice": 45.0, "unitCostPrice": 18.0, "folio": "BLT-0001", "productName": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD", "tipoVenta": "Tienda"}]}}

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