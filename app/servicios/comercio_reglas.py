"""
Comercio exterior - reglas puras (sin base de datos ni FastAPI).

Sin tablas propias, una operación se guarda como un grupo de movimientos con el mismo
`sale_group_id` (el folio):
- Exportación = VENTA_MAYORISTA en USD, con el país del socio como país de destino.
  `unit_sold_price` guarda el precio en dólares.
- Importación = INGRESO en USD. `unit_cost_price` guarda el costo en SOLES (precio USD x tipo
  de cambio), como en el resto del sistema; el precio en dólares se recupera dividiendo.
- Socio, incoterm, transporte y notas van en `reason` (máx. 150): "socio=..;inc=..;trans=..;notas=..".
- `exchange_rate` son soles por dólar.
Los errores se lanzan como ReglaComercio(codigo, mensaje) y la ruta los vuelve HTTPException.
"""
import math
from datetime import date, datetime, time, timezone

from app.servicios.dashboard_calculos import ZONA
from app.servicios.movimientos_mapeo import armar_movimiento
from app.servicios.socios_comerciales import por_nombre

TIPOS_OPERACION = ("importacion", "exportacion")
INCOTERMS = ("EXW", "FOB", "CIF", "DAP", "DDP")                 # = frontend constants.ts
MEDIOS_TRANSPORTE = ("maritimo", "aereo", "terrestre")
MAX_REASON = 150
MAX_LINEAS = 50
MAX_TIPO_CAMBIO = 100.0
MAX_PRECIO_USD = 9_999_999.99
PAIS_LOCAL = "peru"
SOCIO_SIN_REGISTRAR = "Sin registrar"


class ReglaComercio(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _limpio(texto: str | None) -> str:
    """Una sola línea, sin ';' (separador del formato de `reason`)."""
    return " ".join((texto or "").replace(";", ",").split())


# --- validaciones ----------------------------------------------------------

def validar_tipo(tipo: str | None) -> str:
    if tipo not in TIPOS_OPERACION:
        raise ReglaComercio(422, "El tipo de operación no es válido")
    return tipo


def validar_fecha(texto: str | None, hoy: date) -> date:
    try:
        fecha = date.fromisoformat((texto or "").strip()[:10])
    except ValueError:
        raise ReglaComercio(422, "La fecha no es válida")
    if fecha > hoy:
        raise ReglaComercio(422, "La fecha de la operación no puede ser futura")
    return fecha


def validar_tipo_cambio(valor) -> float:
    if not _numero(valor) or valor <= 0:
        raise ReglaComercio(422, "El tipo de cambio debe ser mayor a 0")
    if valor > MAX_TIPO_CAMBIO:
        raise ReglaComercio(422, "El tipo de cambio es demasiado grande")
    return round(float(valor), 4)


def validar_opcionales(incoterm: str | None, medio: str | None) -> None:
    if incoterm is not None and incoterm not in INCOTERMS:
        raise ReglaComercio(422, "El incoterm no es válido")
    if medio is not None and medio not in MEDIOS_TRANSPORTE:
        raise ReglaComercio(422, "El medio de transporte no es válido")


def validar_lineas(lineas: list[tuple[int, float, float]]) -> list[tuple[int, float, float]]:
    """lineas = (producto_id, cantidad, precio_usd). Rechaza productos repetidos."""
    if not lineas:
        raise ReglaComercio(422, "Agregá al menos un producto")
    if len(lineas) > MAX_LINEAS:
        raise ReglaComercio(422, f"Una operación no puede tener más de {MAX_LINEAS} productos")
    vistos: set[int] = set()
    for producto_id, cantidad, precio in lineas:
        if producto_id in vistos:
            raise ReglaComercio(422, f"El producto {producto_id} está repetido: agrupa sus cantidades en una sola línea")
        vistos.add(producto_id)
        if not _numero(precio) or precio < 0:
            raise ReglaComercio(422, "El precio no puede ser negativo")
        if precio > MAX_PRECIO_USD:
            raise ReglaComercio(422, "El precio es demasiado grande")
    return [(p, c, round(float(pr), 4)) for p, c, pr in lineas]


def validar_socio(tipo: str, socio: dict | None) -> dict:
    if socio is None:
        raise ReglaComercio(422, "El socio comercial no existe")
    if tipo == "exportacion" and " ".join(socio["pais"].split()).lower() == PAIS_LOCAL:
        raise ReglaComercio(422, "Una exportación debe tener un socio fuera de Perú")
    return socio


# --- formato en `reason` / folio / fecha -----------------------------------

def armar_reason(*, socio: str, incoterm: str | None, medio: str | None, notas: str | None) -> str:
    partes = [f"socio={_limpio(socio)}"]
    if incoterm:
        partes.append(f"inc={incoterm}")
    if medio:
        partes.append(f"trans={medio}")
    texto = ";".join(partes)
    if _limpio(notas):
        texto += f";notas={_limpio(notas)}"
    if len(texto) > MAX_REASON:
        raise ReglaComercio(
            422,
            f"Socio, incoterm, transporte y notas suman {len(texto)} caracteres y el máximo es "
            f"{MAX_REASON}: acorta las notas",
        )
    return texto


def leer_reason(reason: str | None) -> dict:
    """Inverso de armar_reason. Un texto con otro formato devuelve todo en None."""
    datos = {"socio": None, "incoterm": None, "transporte": None, "notas": None}
    claves = {"socio": "socio", "inc": "incoterm", "trans": "transporte", "notas": "notas"}
    for parte in (reason or "").split(";"):
        clave, separador, valor = parte.partition("=")
        if separador and clave in claves and valor.strip():
            datos[claves[clave]] = valor.strip()
    return datos


def generar_folio(tipo: str, ahora_lima: datetime, sufijo: str) -> str:
    return f"{'EXP' if tipo == 'exportacion' else 'IMP'}-{ahora_lima:%Y%m%d}-{sufijo.upper()}"


def momento_de_registro(fecha: date, ahora_utc: datetime) -> datetime:
    """Hoy se registra con la hora real; una fecha pasada, a las 12:00 (Lima) de ese día."""
    if fecha == ahora_utc.astimezone(ZONA).date():
        return ahora_utc
    return datetime.combine(fecha, time(12, 0), tzinfo=ZONA).astimezone(timezone.utc)


# --- lectura: movimientos -> operaciones del front --------------------------

def agrupar_operaciones(filas: list[dict], socios: list[dict] | None = None) -> list[dict]:
    """`filas` = movimientos con responsable, producto, sku, unit_type (como en movimientos/ventas)."""
    socios = socios or []
    grupos: dict[str, list[dict]] = {}
    for fila in filas:
        if armar_movimiento(fila)["movementType"] in TIPOS_OPERACION:
            clave = (fila.get("sale_group_id") or "").strip() or f"mov-{fila['id']}"
            grupos.setdefault(clave, []).append(fila)

    resultado: list[tuple[tuple, dict]] = []
    for lineas in grupos.values():
        lineas.sort(key=lambda f: (f["created_at"], f["id"]))
        primera = lineas[0]
        base = armar_movimiento(primera)
        tipo = base["movementType"]
        tasa = base.get("tipoCambio") or 1.0

        detalle = []
        for fila in lineas:
            mov = armar_movimiento(fila)
            if tipo == "exportacion":
                precio = mov.get("unitPriceUSD") or 0.0
            else:                                        # importación: el costo guardado está en soles
                costo = mov.get("unitCostPrice")
                precio = round(costo / tasa, 4) if costo is not None else 0.0
            detalle.append({
                "producto": {"id": mov["productId"], "name": mov["productName"], "sku": mov["sku"],
                             "unitType": mov["unitType"]},
                "cantidad": mov["quantity"],
                "precioUSD": precio,
                "subtotalUSD": round(precio * mov["quantity"], 2),
            })

        total_usd = round(sum(l["subtotalUSD"] for l in detalle), 2)
        cabecera = leer_reason(primera.get("reason"))
        nombre = cabecera["socio"] or SOCIO_SIN_REGISTRAR
        socio = por_nombre(cabecera["socio"], socios)
        operacion = {
            "id": primera["id"],
            "folio": (primera.get("sale_group_id") or "").strip() or f"MOV-{primera['id']}",
            "fecha": primera["created_at"].astimezone(ZONA).date().isoformat(),
            "tipo": tipo,
            "socioComercial": {"id": socio["id"] if socio else 0, "nombre": nombre,
                               "pais": (primera.get("destination_country") or "").strip() or "—"},
            "incoterm": cabecera["incoterm"],
            "medioTransporte": cabecera["transporte"],
            "tipoCambio": tasa,
            "lineas": detalle,
            "subtotalUSD": total_usd,
            "totalUSD": total_usd,
            "totalPEN": round(total_usd * tasa, 2),
            "responsable": base["responsable"],
            "notas": cabecera["notas"],
            "createdAt": base["createdAt"],
        }
        resultado.append(((primera["created_at"], primera["id"]), operacion))

    resultado.sort(key=lambda par: par[0], reverse=True)
    return [operacion for _, operacion in resultado]