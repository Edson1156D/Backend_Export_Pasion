from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.esquemas.comun import CamelModel

MotivoMerma = Literal[
    "Rotura o daño durante pulido",
    "Error de producción",
    "Pérdida o extravío",
    "Defecto de calidad",
    "Otro",
]


class MermaCrear(CamelModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    motivo: MotivoMerma
    detalle: str | None = None

    @field_validator("quantity")
    @classmethod
    def cantidad_finita(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class MermaPublica(CamelModel):
    id: int
    product_id: int
    quantity: float
    motivo: str
    detalle: str | None = None
    responsable: str
    created_at: datetime