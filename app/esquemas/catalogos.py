from typing import Optional

from app.esquemas.comun import CamelModel


class CategoriaPublica(CamelModel):
    id: int
    parent_id: Optional[int]
    name: str
    description: Optional[str]


class ProveedorPublico(CamelModel):
    id: int
    name: str


class SocioComercialPublico(CamelModel):
    id: int
    nombre: str
    pais: str