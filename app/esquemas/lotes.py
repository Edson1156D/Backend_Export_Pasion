from datetime import datetime

from app.esquemas.comun import CamelModel


class ProveedorLote(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 4, "name": "Proveedor Andino SAC"}]}}

    id: int
    name: str


class LotePublico(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": 22, "productId": 12, "codigo": "LOTE-0022", "origen": "compra", "cantidadInicial": 20.0, "cantidadDisponible": 18.0, "costoUnitarioSoles": 18.5, "proveedor": {"id": 4, "name": "Proveedor Andino SAC"}, "responsable": "Ana Torres", "fechaIngreso": "2026-09-29T15:30:00Z"}]}}

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
