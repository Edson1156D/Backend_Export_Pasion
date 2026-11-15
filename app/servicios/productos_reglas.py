"""
Productos - reglas de negocio puras (sin base de datos ni FastAPI).

Los errores se lanzan como ReglaProducto(codigo, mensaje); la ruta los convierte en
HTTPException con `detail` de texto, que es lo que el front muestra tal cual.
Las reglas de formato repiten las del formulario del front (features/products/schemas.ts).
"""
import math

UNIDADES = ("UNIDAD", "KILOGRAMO")

MIN_NOMBRE = 3
MAX_NOMBRE = 150
MAX_SKU = 50
MAX_PRECIO = 9_999_999.99
MAX_STOCK_MINIMO = 9_999_999.999     # igual que el máximo de `quantity` en los movimientos


class ReglaProducto(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def validar_sku(sku: str | None) -> str:
    limpio = (sku or "").strip()
    if not limpio:
        raise ReglaProducto(422, "El SKU es obligatorio")
    if len(limpio) > MAX_SKU:
        raise ReglaProducto(422, f"El SKU no puede superar los {MAX_SKU} caracteres")
    return limpio


def validar_nombre(nombre: str | None) -> str:
    limpio = " ".join((nombre or "").split())
    if len(limpio) < MIN_NOMBRE:
        raise ReglaProducto(422, f"El nombre debe tener al menos {MIN_NOMBRE} caracteres")
    if len(limpio) > MAX_NOMBRE:
        raise ReglaProducto(422, f"El nombre no puede superar los {MAX_NOMBRE} caracteres")
    return limpio


def _numero_valido(valor: float | None, etiqueta: str, maximo: float) -> float:
    if valor is None or isinstance(valor, bool) or not math.isfinite(valor):
        raise ReglaProducto(422, f"{etiqueta} no es un número válido")
    if valor < 0:
        raise ReglaProducto(422, f"{etiqueta} no puede ser negativo")
    if valor > maximo:
        raise ReglaProducto(422, f"{etiqueta} es demasiado grande")
    return float(valor)


def validar_precio(valor: float | None) -> float:
    return round(_numero_valido(valor, "El precio de venta", MAX_PRECIO), 2)


def validar_stock_minimo(valor: float | None) -> float:
    return round(_numero_valido(valor, "El stock mínimo", MAX_STOCK_MINIMO), 3)


def validar_unidad(unidad: str | None) -> str:
    if unidad not in UNIDADES:
        raise ReglaProducto(422, "Seleccioná una unidad de medida válida")
    return unidad


def validar_activacion(*, activo: bool, precio: float) -> None:
    if activo and precio <= 0:
        raise ReglaProducto(422, "Para activar el producto, el precio de venta debe ser mayor a 0")


def validar_cambio_unidad(*, unidad_actual: str, unidad_nueva: str, movimientos: int) -> None:
    """Cambiar de unidad a un producto con historia cambiaría el significado de sus cantidades."""
    if unidad_nueva != unidad_actual and movimientos > 0:
        raise ReglaProducto(
            409,
            "No se puede cambiar la unidad de medida: el producto ya tiene movimientos registrados",
        )


def validar_eliminacion(*, movimientos: int, hay_stock: bool) -> None:
    if movimientos > 0:
        plural = "s" if movimientos != 1 else ""
        raise ReglaProducto(
            409,
            f"Este producto tiene {movimientos} movimiento{plural} registrado{plural} y no se puede "
            "eliminar; desactívalo en su lugar",
        )
    if hay_stock:
        raise ReglaProducto(409, "Este producto aún tiene stock y no se puede eliminar; desactívalo en su lugar")