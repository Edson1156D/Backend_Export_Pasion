from datetime import datetime

from pydantic import BaseModel

from app.esquemas.comun import CamelModel


class ProveedorLote(CamelModel):
    id: int
    name: str


class LotePublico(CamelModel):
    id: int
    product_id: int
    codigo: str
    origen: str
    cantidad_inicial: float
    cantidad_disponible: float
    costo_unitario_soles: float
    proveedor: ProveedorLote | None = None
    responsable: str
    fecha_ingreso: datetime
