"""
Punto de venta - reglas puras para registrar una venta (sin BD ni FastAPI).

Los errores se lanzan como ReglaVenta(codigo, mensaje); la ruta los convierte en
HTTPException con `detail` de texto, que es lo que el front muestra tal cual.
"""
import math
import re
from datetime import datetime

CANALES = ("tienda", "feria", "digital", "otro")
METODOS_PAGO = ("efectivo", "billetera-digital")
TIPO_MOVIMIENTO_POS = "VENTA_MINORISTA"
MAX_LINEAS = 50
MAX_CANTIDAD = 9_999_999.999

# La BD no tiene columnas para canal y método de pago: se guardan en `reason`.
_REASON_RE = re.compile(r"^canal=([a-z]+);pago=([a-z-]+)(?:;con=(\d+(?:\.\d+)?))?$")


class ReglaVenta(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _cantidad_valida(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def validar_items(items: list[tuple[int, float]]) -> dict[int, float]:
    """Valida las líneas y junta las repetidas del mismo producto."""
    if not items:
        raise ReglaVenta(422, "La venta debe tener al menos un producto")
    if len(items) > MAX_LINEAS:
        raise ReglaVenta(422, f"Una venta no puede tener más de {MAX_LINEAS} productos")

    acumulado: dict[int, float] = {}
    for product_id, cantidad in items:
        if not _cantidad_valida(cantidad) or cantidad <= 0:
            raise ReglaVenta(422, "La cantidad debe ser mayor a 0")
        if abs(cantidad * 1000 - round(cantidad * 1000)) > 1e-6:
            raise ReglaVenta(422, "La cantidad admite hasta 3 decimales")
        acumulado[product_id] = round(acumulado.get(product_id, 0.0) + cantidad, 3)

    if any(c > MAX_CANTIDAD for c in acumulado.values()):
        raise ReglaVenta(422, "La cantidad es demasiado grande")
    return acumulado


def validar_producto(*, nombre: str, unit_type: str, activo: bool, cantidad: float) -> None:
    if not activo:
        raise ReglaVenta(409, f"El producto {nombre} está inactivo y no se puede vender")
    if (unit_type or "").strip().upper() == "UNIDAD" and cantidad != int(cantidad):
        raise ReglaVenta(422, f"{nombre} se vende por unidad: la cantidad debe ser un número entero")


def validar_pago(*, tipo_venta: str | None, metodo_pago: str | None, pago_con: float | None, total: float) -> dict:
    """Devuelve canal, método, pago_con y vuelto ya validados (pago_con/vuelto solo en efectivo)."""
    canal = (tipo_venta or "").strip().lower()
    metodo = (metodo_pago or "").strip().lower()
    if canal not in CANALES:
        raise ReglaVenta(422, "El tipo de venta no es válido")
    if metodo not in METODOS_PAGO:
        raise ReglaVenta(422, "El método de pago no es válido")
    if pago_con is not None and (not _cantidad_valida(pago_con) or pago_con < 0):
        raise ReglaVenta(422, "El monto recibido no es válido")

    if metodo != "efectivo" or pago_con is None:
        return {"canal": canal, "metodo": metodo, "pago_con": None, "vuelto": None}
    if round(pago_con, 2) < round(total, 2):
        raise ReglaVenta(422, "El monto recibido no cubre el total de la venta")
    return {"canal": canal, "metodo": metodo, "pago_con": round(pago_con, 2), "vuelto": round(pago_con - total, 2)}


def _formato(cantidad: float) -> str:
    return f"{cantidad:.3f}".rstrip("0").rstrip(".")


def validar_stock(solicitado: dict[int, float], disponible: dict[int, float], nombres: dict[int, str]) -> None:
    """409 si algún producto no alcanza en el almacén; lista todos los que faltan."""
    faltantes = []
    for product_id, cantidad in sorted(solicitado.items()):
        hay = disponible.get(product_id, 0.0)
        if round(cantidad, 3) > round(hay, 3):
            nombre = nombres.get(product_id, f"producto {product_id}")
            faltantes.append(f"{nombre}: disponible {_formato(hay)}, solicitado {_formato(cantidad)}")
    if faltantes:
        raise ReglaVenta(409, "Stock insuficiente de " + "; ".join(faltantes))


def generar_folio(ahora: datetime, sufijo: str) -> str:
    """Un identificador legible y único por venta; `ahora` debe venir en hora de Lima."""
    return f"V-{ahora:%Y%m%d%H%M%S}-{sufijo.upper()}"


def codificar_reason(canal: str, metodo: str, pago_con: float | None) -> str:
    texto = f"canal={canal};pago={metodo}"
    return texto if pago_con is None else f"{texto};con={pago_con:.2f}"


def decodificar_reason(reason: str | None) -> dict | None:
    """Inverso de codificar_reason. None si el texto no tiene ese formato (ventas anteriores)."""
    coincidencia = _REASON_RE.match((reason or "").strip())
    if not coincidencia:
        return None
    canal, pago, con = coincidencia.groups()
    return {"canal": canal, "pago": pago, "con": None if con is None else float(con)}