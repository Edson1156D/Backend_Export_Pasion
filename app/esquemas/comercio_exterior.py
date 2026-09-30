from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.esquemas.comun import CamelModel


class LineaOperacionCrear(CamelModel):
	model_config = {"json_schema_extra": {"examples": [{"productoId": 12, "cantidad": 10, "precioUSD": 12.5}]}}

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
	model_config = {"json_schema_extra": {"examples": [{"fecha": "2026-09-29", "tipo": "importacion", "socioComercialId": 2, "incoterm": "FOB", "medioTransporte": "maritimo", "tipoCambio": 3.75, "notas": "Importación de piedras", "lineas": [{"productoId": 12, "cantidad": 10, "precioUSD": 12.5}]}]}}

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
	model_config = {"json_schema_extra": {"examples": [{"id": 12, "name": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD"}]}}

	id: int
	name: str
	sku: str
	unit_type: Literal["UNIDAD", "KILOGRAMO"]


class LineaOperacionPublica(CamelModel):
	model_config = {"json_schema_extra": {"examples": [{"producto": {"id": 12, "name": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD"}, "cantidad": 10.0, "precioUSD": 12.5, "subtotalUSD": 125.0}]}}

	producto: ProductoOperacionPublico
	cantidad: float
	precio_usd: float = Field(alias="precioUSD")
	subtotal_usd: float = Field(alias="subtotalUSD")


class SocioOperacionPublico(CamelModel):
	model_config = {"json_schema_extra": {"examples": [{"id": 2, "nombre": "Gemstones Trading LLC", "pais": "Estados Unidos"}]}}

	id: int
	nombre: str
	pais: str


class OperacionPublica(CamelModel):
	model_config = {"json_schema_extra": {"examples": [{"id": 3, "folio": "IMP-0002", "fecha": "2026-09-29", "tipo": "importacion", "socioComercial": {"id": 2, "nombre": "Gemstones Trading LLC", "pais": "Estados Unidos"}, "incoterm": "FOB", "medioTransporte": "maritimo", "tipoCambio": 3.75, "lineas": [{"producto": {"id": 12, "name": "Cuarzo rosa pulido", "sku": "CUARZO-ROSA-001", "unitType": "UNIDAD"}, "cantidad": 10.0, "precioUSD": 12.5, "subtotalUSD": 125.0}], "subtotalUSD": 125.0, "totalUSD": 125.0, "totalPEN": 468.75, "responsable": "Ana Torres", "notas": "Importación de piedras", "createdAt": "2026-09-29T15:30:00Z"}]}}

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