"""
Almacenes - reglas puras (sin base de datos ni FastAPI).

Las operaciones del taller y del punto de venta salen/entran por el ALMACÉN PRINCIPAL:
el permanente (no temporal) ubicado en Perú. Los temporales (ferias) y el de tránsito
no se eligen solos.
"""
import unicodedata

PAIS_PRINCIPAL = "PERU"
PREFIJO_SOCIO = "SOCIO:"      # filas de `warehouses` con este prefijo son socios comerciales, no almacenes


class ReglaAlmacen(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _normalizar(texto: str | None) -> str:
    sin_tildes = unicodedata.normalize("NFD", (texto or "").strip())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").upper()


def es_socio(nombre: str | None) -> bool:
    """Una fila de `warehouses` cuyo nombre empieza por "SOCIO:" es un socio comercial, no un almacén."""
    return _normalizar(nombre).startswith(PREFIJO_SOCIO)


def elegir_principal(almacenes: list[dict]) -> int:
    """`almacenes`: dicts con id, name, country, is_temporary. Devuelve el id del principal."""
    candidatos = sorted(
        a["id"]
        for a in almacenes
        if not es_socio(a.get("name"))
        and a.get("is_temporary") is not True
        and _normalizar(a.get("country")) == PAIS_PRINCIPAL
    )
    if not candidatos:
        raise ReglaAlmacen(409, "No hay un almacén principal configurado (permanente y en Perú)")
    return candidatos[0]