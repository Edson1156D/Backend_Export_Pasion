"""
Socios comerciales (clientes del exterior y proveedores), guardados como filas de la tabla
`warehouses` cuyo nombre empieza por "SOCIO:". No hace falta crear tablas: agregar un socio es
agregar una fila (por la API o con un INSERT). Todo el sistema ignora estas filas como almacén.

    INSERT INTO warehouses (name, country, is_temporary, created_at)
    VALUES ('SOCIO: Gem Traders LLC', 'United States', false, now());

El `id` del socio es el `id` de la fila. El historial guarda el NOMBRE del socio (no el id): si
renombras un socio, sus operaciones antiguas se siguen mostrando con el nombre que tenían.
Lógica pura: sin base de datos ni FastAPI.
"""
from app.servicios.almacen_reglas import PREFIJO_SOCIO, es_socio

MIN_NOMBRE = 3
MAX_NOMBRE = 100 - len(PREFIJO_SOCIO) - 1      # `name` es varchar(100): "SOCIO: " + nombre
MIN_PAIS = 2
MAX_PAIS = 50                                  # `country` es varchar(50)


class ReglaSocio(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def desde_almacen(fila: dict) -> dict | None:
    """Convierte una fila de `warehouses` en socio; None si es un almacén de verdad."""
    nombre = (fila.get("name") or "").strip()
    if not es_socio(nombre):
        return None
    return {
        "id": fila["id"],
        "nombre": " ".join(nombre[len(PREFIJO_SOCIO):].split()),
        "pais": (fila.get("country") or "").strip(),
    }


def listar(filas: list[dict]) -> list[dict]:
    socios = (desde_almacen(fila) for fila in filas)
    return sorted((s for s in socios if s), key=lambda s: s["id"])


def por_id(socio_id: int, socios: list[dict]) -> dict | None:
    return next((s for s in socios if s["id"] == socio_id), None)


def por_nombre(nombre: str | None, socios: list[dict]) -> dict | None:
    buscado = " ".join((nombre or "").split()).lower()
    return next((s for s in socios if " ".join(s["nombre"].split()).lower() == buscado), None)


def nombre_de_almacen(nombre: str) -> str:
    """El valor de `warehouses.name` para un socio."""
    return f"{PREFIJO_SOCIO} {nombre}"


def validar_nuevo(nombre: str | None, pais: str | None, existentes: list[dict]) -> tuple[str, str]:
    limpio = " ".join((nombre or "").split())
    pais_limpio = " ".join((pais or "").split())
    if len(limpio) < MIN_NOMBRE:
        raise ReglaSocio(422, f"El nombre debe tener al menos {MIN_NOMBRE} caracteres")
    if len(limpio) > MAX_NOMBRE:
        raise ReglaSocio(422, f"El nombre no puede superar los {MAX_NOMBRE} caracteres")
    if ";" in limpio:
        # ';' separa los datos que se guardan en `reason`: rompería el vínculo con el historial
        raise ReglaSocio(422, "El nombre no puede contener el signo ';'")
    if not (MIN_PAIS <= len(pais_limpio) <= MAX_PAIS):
        raise ReglaSocio(422, f"El país debe tener entre {MIN_PAIS} y {MAX_PAIS} caracteres")
    if por_nombre(limpio, existentes) is not None:
        raise ReglaSocio(409, "Ya existe un socio con ese nombre")
    return limpio, pais_limpio