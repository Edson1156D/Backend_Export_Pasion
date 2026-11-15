"""
Movimientos - traducción de una fila de `inventory_movements` al formato del front
(`InventoryMovement` en frontend/src/features/movimientos/types.ts). Lógica pura:
no toca la base de datos ni FastAPI.

Reglas acordadas para el vocabulario de `movement_type` (texto libre en la BD):
- VENTA_MAYORISTA / VENTA_MINORISTA -> "venta"; si el destino no es Perú y la moneda
  es USD -> "exportacion".
- INGRESO -> "entrada"; si la moneda es USD -> "importacion".
- MERMA -> "merma".
- TRANSFERENCIA -> "transferencia" (el front aún no la conoce; ver INCLUIR_TRANSFERENCIAS).
- Cualquier otro tipo se envía en minúsculas tal cual, para que se vea y no desaparezca.

Supuesto: `exchange_rate` son soles por unidad de moneda extranjera.
"""
import unicodedata
from datetime import datetime

# Mientras el front no tenga el tipo "transferencia", se dejan fuera del listado:
# si no, su pantalla las contaría como "exportaciones". Pasar a True al adaptar el front.
INCLUIR_TRANSFERENCIAS = True

TIPO_TRANSFERENCIA = "TRANSFERENCIA"
PAIS_LOCAL = "PERU"
MONEDA_EXTRANJERA = "USD"

_TIPO_BASE = {
    "VENTA_MAYORISTA": "venta",
    "VENTA_MINORISTA": "venta",
    "MERMA": "merma",
    "INGRESO": "entrada",
    "TRANSFERENCIA": "transferencia",
}
_ETIQUETA_VENTA = {"VENTA_MAYORISTA": "Mayorista", "VENTA_MINORISTA": "Minorista"}


def _normalizar(texto: str | None) -> str:
    """Mayúsculas, sin espacios sobrantes ni tildes ("Perú " -> "PERU")."""
    sin_tildes = unicodedata.normalize("NFD", (texto or "").strip())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").upper()


def _numero(valor) -> float | None:
    return None if valor is None else float(valor)


def _texto(valor: str | None) -> str | None:
    limpio = (valor or "").strip()
    return limpio or None


def tipo_para_front(movement_type: str | None, destination_country: str | None, currency: str | None) -> str:
    tipo = _normalizar(movement_type)
    base = _TIPO_BASE.get(tipo)
    if base is None:
        return tipo.lower()            # desconocido: visible, no oculto
    en_dolares = _normalizar(currency) == MONEDA_EXTRANJERA
    if base == "venta":
        pais = _normalizar(destination_country)
        return "exportacion" if pais and pais != PAIS_LOCAL and en_dolares else "venta"
    if base == "entrada" and en_dolares:
        return "importacion"
    return base


def armar_movimiento(fila: dict) -> dict:
    """
    `fila` trae las columnas de inventory_movements más `responsable` (users.full_name),
    `producto`, `sku` y `unit_type` (products). Los campos sin dato se devuelven en None
    y la ruta los omite de la respuesta (el front espera `undefined`, no `null`).
    """
    tipo_bd = _normalizar(fila.get("movement_type"))
    tipo = tipo_para_front(fila.get("movement_type"), fila.get("destination_country"), fila.get("currency"))

    en_dolares = _normalizar(fila.get("currency")) == MONEDA_EXTRANJERA
    precio = _numero(fila.get("unit_sold_price"))
    tasa = _numero(fila.get("exchange_rate"))
    tiene_tasa = en_dolares and tasa is not None and tasa > 0

    # El front muestra el precio en soles; el original en dólares va aparte.
    precio_soles = precio * tasa if (precio is not None and tiene_tasa) else precio

    creado: datetime = fila["created_at"]
    return {
        "id": fila["id"],
        "productId": fila["product_id"],
        "responsable": _texto(fila.get("responsable")) or "Sistema",
        "movementType": tipo,
        "quantity": float(fila["quantity"]),
        "createdAt": creado.isoformat(),
        "productName": _texto(fila.get("producto")) or f"Producto {fila['product_id']}",
        "sku": _texto(fila.get("sku")) or "",
        "unitType": _normalizar(fila.get("unit_type")) or "UNIDAD",
        "reason": _texto(fila.get("reason")),
        "unitSoldPrice": None if precio_soles is None else round(precio_soles, 2),
        "unitCostPrice": _numero(fila.get("unit_cost_price")),
        "wasteType": _texto(fila.get("waste_type")),
        "folio": _texto(fila.get("sale_group_id")),
        "unitPriceUSD": precio if (en_dolares and precio is not None) else None,
        "tipoCambio": tasa if tiene_tasa else None,
        "tipoVenta": _ETIQUETA_VENTA.get(tipo_bd),
    }