"""
Inventario - reglas puras para registrar entradas, compras y mermas (sin BD ni FastAPI).

Los errores se lanzan como ReglaInventario(codigo, mensaje); la ruta los convierte en
HTTPException con `detail` de texto, que es lo que el front muestra tal cual.
"""
import math
from decimal import ROUND_HALF_UP, Decimal

MAX_TEXTO = 150                       # varchar(150) en `reason`
MAX_CANTIDAD = 9_999_999.999
MAX_COSTO = 9_999_999.99

# Misma lista que frontend/src/features/mermas/constants.ts (MOTIVOS_MERMA).
MOTIVOS_MERMA = (
    "Rotura o daño durante pulido",
    "Error de producción",
    "Pérdida o extravío",
    "Defecto de calidad",
    "Otro",
)


class ReglaInventario(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _es_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def validar_cantidad(cantidad, *, nombre: str, unit_type: str) -> float:
    if not _es_numero(cantidad) or cantidad <= 0:
        raise ReglaInventario(422, "La cantidad debe ser mayor a 0")
    if abs(cantidad * 1000 - round(cantidad * 1000)) > 1e-6:
        raise ReglaInventario(422, "La cantidad admite hasta 3 decimales")
    if cantidad > MAX_CANTIDAD:
        raise ReglaInventario(422, "La cantidad es demasiado grande")
    if (unit_type or "").strip().upper() == "UNIDAD" and cantidad != int(cantidad):
        raise ReglaInventario(422, f"{nombre} se maneja por unidad: la cantidad debe ser un número entero")
    return round(float(cantidad), 3)


def validar_producto_activo(*, nombre: str, activo: bool) -> None:
    if not activo:
        raise ReglaInventario(409, f"El producto {nombre} está inactivo; actívalo antes de registrar ingresos")


def validar_texto_opcional(texto: str | None, etiqueta: str) -> str | None:
    limpio = " ".join((texto or "").split())
    if len(limpio) > MAX_TEXTO:
        raise ReglaInventario(422, f"{etiqueta} no puede superar los {MAX_TEXTO} caracteres")
    return limpio or None


def validar_motivo(motivo: str | None) -> str:
    if motivo not in MOTIVOS_MERMA:
        raise ReglaInventario(422, "El motivo de la merma no es válido")
    return motivo


def validar_costo(costo) -> float:
    if not _es_numero(costo) or costo < 0:
        raise ReglaInventario(422, "El costo unitario no puede ser negativo")
    if costo > MAX_COSTO:
        raise ReglaInventario(422, "El costo unitario es demasiado grande")
    return round(float(costo), 2)


def costo_promedio(*, stock_actual, costo_actual, cantidad, costo_compra) -> Decimal:
    """
    Costo promedio ponderado tras una compra:
        (stock * costo_actual + cantidad * costo_compra) / (stock + cantidad)
    Sin stock (o con stock negativo) o sin costo previo, el nuevo costo es el de la compra.
    """
    cero = Decimal(0)
    precio = Decimal(str(costo_compra))
    stock = max(Decimal(str(stock_actual)), cero)
    if costo_actual is None or stock == cero:
        resultado = precio
    else:
        cantidad_d = Decimal(str(cantidad))
        resultado = (stock * Decimal(str(costo_actual)) + cantidad_d * precio) / (stock + cantidad_d)
    return resultado.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)