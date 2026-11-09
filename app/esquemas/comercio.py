from datetime import datetime

from pydantic import BaseModel


class SocioOut(BaseModel):
    """Igual a `SocioComercial` en frontend/src/features/comercio-exterior/types.ts."""
    id: int
    nombre: str
    pais: str


class ProductoLineaOut(BaseModel):
    id: int
    name: str
    sku: str
    unitType: str


class LineaOut(BaseModel):
    producto: ProductoLineaOut
    cantidad: float
    precioUSD: float
    subtotalUSD: float


class OperacionOut(BaseModel):
    """Igual a `OperacionComercioExterior` del front; los opcionales se omiten si no hay dato."""
    id: int
    folio: str
    fecha: str
    tipo: str
    socioComercial: SocioOut
    incoterm: str | None = None
    medioTransporte: str | None = None
    tipoCambio: float
    lineas: list[LineaOut]
    subtotalUSD: float
    totalUSD: float
    totalPEN: float
    responsable: str
    notas: str | None = None
    createdAt: datetime


class LineaCrear(BaseModel):
    productoId: int
    cantidad: float
    precioUSD: float


class OperacionCrear(BaseModel):
    """Cuerpo de POST /comercio-exterior/operaciones. El responsable NO se toma del cliente: es el usuario del token."""
    fecha: str
    tipo: str
    socioComercialId: int
    tipoCambio: float
    incoterm: str | None = None
    medioTransporte: str | None = None
    notas: str | None = None
    lineas: list[LineaCrear]

class SocioCrear(BaseModel):
    """Cuerpo de POST /comercio-exterior/socios-comerciales."""
    nombre: str
    pais: str