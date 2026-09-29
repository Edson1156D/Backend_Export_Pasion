from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.esquemas.comun import CamelModel


class LineaOperacionCrear(CamelModel):
	producto_id: int = Field(gt=0)
	cantidad: Decimal = Field(gt=0)
	precio_usd: Decimal = Field(ge=0, alias="precioUSD")

	@field_validator("cantidad", "precio_usd")
	@classmethod
	def valores_finitos(cls, value: Decimal) -> Decimal:
		if not value.is_finite():
			raise ValueError("El valor debe ser un número finito")
		return value


class OperacionCrear(CamelModel):
	fecha: date
	tipo: Literal["importacion", "exportacion"]
	socio_comercial_id: int = Field(gt=0)
	incoterm: Literal["EXW", "FOB", "CIF", "DAP", "DDP"] | None = None
	medio_transporte: Literal["maritimo", "aereo", "terrestre"] | None = None
	tipo_cambio: Decimal = Field(gt=0)
	notas: str | None = None
	lineas: list[LineaOperacionCrear] = Field(min_length=1)

	@field_validator("tipo_cambio")
	@classmethod
	def tipo_cambio_finito(cls, value: Decimal) -> Decimal:
		if not value.is_finite():
			raise ValueError("El tipo de cambio debe ser mayor a 0")
		return value


class ProductoOperacionPublico(CamelModel):
	id: int
	name: str
	sku: str
	unit_type: Literal["UNIDAD", "KILOGRAMO"]


class LineaOperacionPublica(CamelModel):
	producto: ProductoOperacionPublico
	cantidad: float
	precio_usd: float = Field(alias="precioUSD")
	subtotal_usd: float = Field(alias="subtotalUSD")


class SocioOperacionPublico(CamelModel):
	id: int
	nombre: str
	pais: str


class OperacionPublica(CamelModel):
	id: int
	folio: str
	fecha: date
	tipo: Literal["importacion", "exportacion"]
	socio_comercial: SocioOperacionPublico
	incoterm: str | None = None
	medio_transporte: str | None = None
	tipo_cambio: float
	lineas: list[LineaOperacionPublica]
	subtotal_usd: float = Field(alias="subtotalUSD")
	total_usd: float = Field(alias="totalUSD")
	total_pen: float = Field(alias="totalPEN")
	responsable: str
	notas: str | None = None
	created_at: datetime