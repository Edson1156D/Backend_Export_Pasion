from datetime import datetime

from pydantic import BaseModel


class MermaOut(BaseModel):
    """Igual a `Merma` en frontend/src/features/mermas/types.ts."""
    id: int
    productId: int
    quantity: float
    motivo: str
    detalle: str | None = None      # opcional: la ruta usa response_model_exclude_none
    responsable: str
    createdAt: datetime


class EntradaOut(BaseModel):
    """Igual a `StockEntry` del front. La BD no guarda proveedor, así que proveedorId no existe."""
    id: int
    productId: int
    quantity: float
    createdAt: datetime
    responsable: str


class LoteOut(BaseModel):
    """Igual a `Lote` del front. La BD no tiene lotes: hoy siempre se devuelve una lista vacía."""
    id: int
    productId: int
    codigo: str | None = None
    origen: str
    cantidadInicial: float
    cantidadDisponible: float
    costoUnitarioSoles: float
    responsable: str
    fechaIngreso: datetime


class ProveedorOut(BaseModel):
    """Igual a `Proveedor` del front. La BD no tiene proveedores: hoy siempre es una lista vacía."""
    id: int
    name: str

class EntradaCrear(BaseModel):
    """Cuerpo de POST /entradas (producción del taller). Igual al que arma el front."""
    productId: int
    quantity: float
    notas: str | None = None


class CompraCrear(BaseModel):
    """Cuerpo de POST /compras. proveedorId se acepta pero no se guarda: la BD no tiene proveedores."""
    productId: int
    quantity: float
    proveedorId: int | None = None
    costoUnitarioSoles: float | None = None
    notas: str | None = None


class MermaCrear(BaseModel):
    """Cuerpo de POST /mermas."""
    productId: int
    quantity: float
    motivo: str
    detalle: str | None = None