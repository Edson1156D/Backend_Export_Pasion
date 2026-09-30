from typing import Optional

from app.esquemas.comun import CamelModel


class CategoriaPublica(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 1, "parentId": None, "name": "Minerales", "description": "Piedras semipreciosas"}]}}

    id: int
    parent_id: Optional[int]
    name: str
    description: Optional[str]


class ProveedorPublico(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 4, "name": "Proveedor Andino SAC"}]}}

    id: int
    name: str


class SocioComercialPublico(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 2, "nombre": "Gemstones Trading LLC", "pais": "Estados Unidos"}]}}

    id: int
    nombre: str
    pais: str