from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.esquemas.comun import CamelModel


class ItemVentaCrear(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"productId": 12, "quantity": 2}]}}

    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)

    @field_validator("quantity")
    @classmethod
    def cantidad_finita(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class VentaCrear(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"items": [{"productId": 12, "quantity": 2}], "tipoVenta": "tienda", "metodoPago": "efectivo", "pagoCon": 100.0}]}}

    items: list[ItemVentaCrear] = Field(min_length=1)
    tipo_venta: Literal["tienda", "feria", "digital", "otro"]
    metodo_pago: Literal["efectivo", "billetera-digital"]
    pago_con: Decimal | None = Field(default=None, ge=0)

    @field_validator("pago_con")
    @classmethod
    def pago_finito(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Ingresá un monto válido")
        return value


class VentaItemPublica(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"productId": 12, "name": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD", "unitPrice": 45.0, "quantity": 2.0}]}}

    product_id: int
    name: str
    sku: str
    unit_type: Literal["UNIDAD", "KILOGRAMO"]
    unit_price: float
    quantity: float


class VentaPublica(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 4, "folio": "BLT-0004", "items": [{"productId": 12, "name": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD", "unitPrice": 45.0, "quantity": 2.0}], "tipoVenta": "tienda", "metodoPago": "efectivo", "subtotal": 90.0, "total": 90.0, "pagoCon": 100.0, "vuelto": 10.0, "responsable": "Ana Torres", "createdAt": "2026-09-29T15:30:00Z"}]}}

    id: int
    folio: str
    items: list[VentaItemPublica]
    tipo_venta: str
    metodo_pago: str
    subtotal: float
    total: float
    pago_con: float | None = None
    vuelto: float | None = None
    responsable: str
    created_at: datetime