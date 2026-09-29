from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.esquemas.comun import CamelModel


class ItemVentaCrear(CamelModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)

    @field_validator("quantity")
    @classmethod
    def cantidad_finita(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class VentaCrear(CamelModel):
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
    product_id: int
    name: str
    sku: str
    unit_type: Literal["UNIDAD", "KILOGRAMO"]
    unit_price: float
    quantity: float


class VentaPublica(CamelModel):
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