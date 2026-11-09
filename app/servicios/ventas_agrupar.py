"""
Ventas - agrupa las líneas de `inventory_movements` en ventas, al formato del front
(`Venta` en frontend/src/features/ventas/types.ts). Lógica pura: sin BD ni FastAPI.

Una venta es el conjunto de líneas con el mismo `sale_group_id`; una línea sin grupo
es una venta por sí sola. Solo cuentan los movimientos que el listado de movimientos
clasifica como "venta": las exportaciones pertenecen a Comercio exterior.

Lo que la BD no guarda (método de pago, pago con, vuelto) NO se inventa: el método sale
como "sin registrar" y pagoCon/vuelto se omiten (la boleta ya sabe ocultar el vuelto).
Sin descuentos ni impuestos en la BD, subtotal y total son iguales.
"""
from app.servicios.movimientos_mapeo import armar_movimiento, tipo_para_front
from app.servicios.ventas_reglas import decodificar_reason

METODO_PAGO_SIN_DATO = "sin registrar"


def _clave_grupo(fila: dict) -> str:
    return (fila.get("sale_group_id") or "").strip() or f"mov-{fila['id']}"


def agrupar_ventas(filas: list[dict]) -> list[dict]:
    """`filas` son las columnas de inventory_movements + responsable, producto, sku, unit_type, precio_lista."""
    grupos: dict[str, list[dict]] = {}
    for fila in filas:
        tipo = tipo_para_front(fila.get("movement_type"), fila.get("destination_country"), fila.get("currency"))
        if tipo == "venta":
            grupos.setdefault(_clave_grupo(fila), []).append(fila)

    ventas: list[tuple[tuple, dict]] = []
    for lineas in grupos.values():
        lineas.sort(key=lambda f: (f["created_at"], f["id"]))
        primera = lineas[0]

        items = []
        for fila in lineas:
            mov = armar_movimiento(fila)
            precio = mov["unitSoldPrice"]
            if precio is None:                       # sin precio en el movimiento: el de lista
                precio = float(fila.get("precio_lista") or 0)
            items.append({
                "productId": mov["productId"],
                "name": mov["productName"],
                "sku": mov["sku"],
                "unitType": mov["unitType"],
                "unitPrice": precio,
                "quantity": mov["quantity"],
            })

        total = round(sum(i["unitPrice"] * i["quantity"] for i in items), 2)
        base = armar_movimiento(primera)
        folio = (primera.get("sale_group_id") or "").strip() or f"MOV-{primera['id']}"
        pago = decodificar_reason(primera.get("reason"))
        venta = {
            "id": primera["id"],
            "items": items,
            "tipoVenta": pago["canal"] if pago else (base["tipoVenta"] or "venta").lower(),
            "metodoPago": pago["pago"] if pago else METODO_PAGO_SIN_DATO,
            "subtotal": total,
            "total": total,
            "folio": folio,
            "responsable": base["responsable"],
            "createdAt": base["createdAt"],
        }
        if pago and pago["con"] is not None:
            venta["pagoCon"] = pago["con"]
            if pago["pago"] == "efectivo":
                venta["vuelto"] = round(max(pago["con"] - total, 0.0), 2)
        ventas.append(((primera["created_at"], primera["id"]), venta))

    ventas.sort(key=lambda par: par[0], reverse=True)       # la más reciente primero
    return [venta for _, venta in ventas]