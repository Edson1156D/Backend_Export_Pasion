from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.esquemas.comun import CamelModel


class EntradaCrear(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"productId": 12, "quantity": 10, "notas": "Producción del taller"}]}}

    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    notas: str | None = None

    @field_validator("quantity")
    @classmethod
    def cantidad_finita(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class CompraCrear(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"productId": 12, "quantity": 20, "proveedorId": 4, "costoUnitarioSoles": 18.5, "notas": "Compra de cuarzo rosa"}]}}

    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    proveedor_id: int | None = Field(default=None, gt=0)
    costo_unitario_soles: Decimal | None = Field(default=None, ge=0)
    notas: str | None = None

    @field_validator("quantity")
    @classmethod
    def cantidad_finita(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class EntradaPublica(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 31, "productId": 12, "quantity": 20.0, "createdAt": "2026-09-29T15:30:00Z", "proveedorId": 4, "responsable": "Ana Torres"}]}}

    id: int
    product_id: int
    quantity: float
    created_at: datetime
    proveedor_id: int | None = None
    responsable: str | None = None