"""
Inventario - mermas y entradas a partir de los movimientos, al formato del front
(`Merma` y `StockEntry`). Lógica pura: sin BD ni FastAPI.

- Merma  = movimiento MERMA: el motivo es `waste_type` y el detalle es `reason`.
- Entrada = movimiento INGRESO en soles (en dólares sería una importación).
La BD no guarda proveedor, así que `proveedorId` no se envía.
"""
from app.servicios.movimientos_mapeo import armar_movimiento

MOTIVO_SIN_ESPECIFICAR = "Sin especificar"


def a_mermas(filas: list[dict]) -> list[dict]:
    mermas = []
    for fila in filas:
        mov = armar_movimiento(fila)
        if mov["movementType"] != "merma":
            continue
        mermas.append({
            "id": mov["id"],
            "productId": mov["productId"],
            "quantity": mov["quantity"],
            "motivo": mov["wasteType"] or MOTIVO_SIN_ESPECIFICAR,
            "detalle": mov["reason"],
            "responsable": mov["responsable"],
            "createdAt": mov["createdAt"],
        })
    return mermas


def a_entradas(filas: list[dict]) -> list[dict]:
    entradas = []
    for fila in filas:
        mov = armar_movimiento(fila)
        if mov["movementType"] != "entrada":
            continue
        entradas.append({
            "id": mov["id"],
            "productId": mov["productId"],
            "quantity": mov["quantity"],
            "createdAt": mov["createdAt"],
            "responsable": mov["responsable"],
        })
    return entradas