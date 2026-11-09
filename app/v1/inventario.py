from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.user import obtener_usuario_por_id
from app.bd.session import get_db
from app.core.seguridad import obtener_usuario_actual, requiere_roles
from app.esquemas.inventario import (
    CompraCrear,
    EntradaCrear,
    EntradaOut,
    LoteOut,
    MermaCrear,
    MermaOut,
    ProveedorOut,
)
from app.modelo.movimientos import MovimientoInventario as Mov
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.servicios import inventario_reglas as reglas
from app.servicios.almacen_consultas import almacen_principal_id, stock_disponible
from app.servicios.almacen_reglas import ReglaAlmacen
from app.servicios.inventario_listas import a_entradas, a_mermas
from app.servicios.ventas_reglas import ReglaVenta, validar_stock

router = APIRouter(tags=["inventario"])
admin_o_taller = Depends(requiere_roles("ADMIN", "TALLER"))

MAX_FILAS = 5000
_REGLAS = (reglas.ReglaInventario, ReglaAlmacen, ReglaVenta)


# --------------------------------------------------------------------------- lecturas

async def _leer(db: AsyncSession, tipos_bd: tuple[str, ...]) -> list[dict]:
    """Movimientos de los tipos pedidos, del más reciente al más antiguo."""
    consulta = (
        select(
            Mov.id, Mov.product_id, Mov.movement_type, Mov.quantity, Mov.created_at,
            Mov.reason, Mov.unit_sold_price, Mov.unit_cost_price, Mov.waste_type,
            Mov.sale_group_id, Mov.currency, Mov.exchange_rate, Mov.destination_country,
            Usuario.full_name.label("responsable"),
            Producto.name.label("producto"),
            Producto.sku,
            Producto.unit_type,
        )
        .select_from(Mov)
        .outerjoin(Usuario, Usuario.id == Mov.user_id)
        .outerjoin(Producto, Producto.id == Mov.product_id)
        .where(func.upper(func.trim(Mov.movement_type)).in_(tipos_bd))
        .order_by(Mov.created_at.desc(), Mov.id.desc())
        .limit(MAX_FILAS)
    )
    return [fila._asdict() for fila in (await db.execute(consulta)).all()]


@router.get("/mermas", response_model=list[MermaOut], response_model_exclude_none=True, dependencies=[admin_o_taller])
async def listar_mermas(db: AsyncSession = Depends(get_db)):
    return a_mermas(await _leer(db, ("MERMA",)))


@router.get("/entradas", response_model=list[EntradaOut], dependencies=[admin_o_taller])
async def listar_entradas(db: AsyncSession = Depends(get_db)):
    return a_entradas(await _leer(db, ("INGRESO",)))


# La BD no tiene lotes ni proveedores: se responde vacío para que el front muestre
# "sin datos" en lugar de un error. Cuando exista el concepto, se reemplaza aquí.
@router.get("/lotes", response_model=list[LoteOut], dependencies=[Depends(obtener_usuario_actual)])
async def listar_lotes():
    return []


@router.get("/lotes/producto/{producto_id}", response_model=list[LoteOut], dependencies=[Depends(obtener_usuario_actual)])
async def listar_lotes_de_producto(producto_id: int):
    return []


@router.get("/proveedores", response_model=list[ProveedorOut], dependencies=[Depends(obtener_usuario_actual)])
async def listar_proveedores():
    return []


# ------------------------------------------------------------------------- escrituras
# Cada operación escribe UN movimiento; el trigger de la base mueve el stock del almacén
# (el backend nunca lo toca) y NO valida stock, por eso las salidas lo validan aquí.

async def _producto(db: AsyncSession, producto_id: int, *, bloquear: bool = False) -> Producto:
    consulta = select(Producto).where(Producto.id == producto_id)
    if bloquear:
        consulta = consulta.with_for_update()      # serializa compras: el costo promedio depende del stock
    producto = (await db.execute(consulta)).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


def _nuevo_ingreso(actual: dict, producto: Producto, almacen_id: int, cantidad: float,
                   notas: str | None, costo: float | None) -> Mov:
    return Mov(
        product_id=producto.id,
        user_id=actual["id"],
        movement_type="INGRESO",
        quantity=Decimal(str(cantidad)),
        reason=notas,
        created_at=datetime.now(timezone.utc),
        unit_cost_price=None if costo is None else Decimal(str(costo)),
        origin_warehouse_id=None,                    # sin origen: entra stock
        destination_warehouse_id=almacen_id,
        currency="PEN",
        exchange_rate=Decimal("1"),
        destination_country="Peru",
    )


async def _guardar(db: AsyncSession, mov: Mov) -> None:
    db.add(mov)
    try:
        await db.flush()       # asigna el id
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo registrar el movimiento; inténtalo de nuevo")


async def _fila(db: AsyncSession, actual: dict, mov: Mov, producto: Producto) -> dict:
    usuario = await obtener_usuario_por_id(db, actual["id"])
    return {
        "id": mov.id, "product_id": mov.product_id, "movement_type": mov.movement_type,
        "quantity": mov.quantity, "created_at": mov.created_at, "reason": mov.reason,
        "unit_sold_price": None, "unit_cost_price": mov.unit_cost_price, "waste_type": mov.waste_type,
        "sale_group_id": None, "currency": mov.currency, "exchange_rate": mov.exchange_rate,
        "destination_country": mov.destination_country,
        "responsable": usuario.full_name if usuario else None,
        "producto": producto.name, "sku": producto.sku, "unit_type": producto.unit_type,
    }


@router.post("/entradas", response_model=EntradaOut, status_code=201)
async def registrar_entrada(
    datos: EntradaCrear,
    actual: dict = admin_o_taller,
    db: AsyncSession = Depends(get_db),
):
    """Ingreso de producción del taller: suma stock y NO altera el costo promedio."""
    producto = await _producto(db, datos.productId)
    try:
        cantidad = reglas.validar_cantidad(datos.quantity, nombre=producto.name, unit_type=producto.unit_type)
        reglas.validar_producto_activo(nombre=producto.name, activo=producto.is_active is not False)
        notas = reglas.validar_texto_opcional(datos.notas, "Las notas")
        almacen_id = await almacen_principal_id(db)
    except _REGLAS as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje)

    mov = _nuevo_ingreso(actual, producto, almacen_id, cantidad, notas, costo=None)
    await _guardar(db, mov)
    return a_entradas([await _fila(db, actual, mov, producto)])[0]


@router.post("/compras", response_model=EntradaOut, status_code=201)
async def registrar_compra(
    datos: CompraCrear,
    actual: dict = Depends(requiere_roles("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """
    Compra a proveedor: suma stock y, si trae costo unitario, recalcula el costo promedio
    ponderado del producto. `proveedorId` se acepta pero no se guarda (no hay proveedores).
    """
    producto = await _producto(db, datos.productId, bloquear=True)
    try:
        cantidad = reglas.validar_cantidad(datos.quantity, nombre=producto.name, unit_type=producto.unit_type)
        reglas.validar_producto_activo(nombre=producto.name, activo=producto.is_active is not False)
        costo = reglas.validar_costo(datos.costoUnitarioSoles) if datos.costoUnitarioSoles is not None else None
        notas = reglas.validar_texto_opcional(datos.notas, "Las notas")
        almacen_id = await almacen_principal_id(db)
    except _REGLAS as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje)

    # El stock y el costo se leen ANTES de insertar: el trigger suma la compra al insertar.
    if costo is not None:
        producto.cost_price = reglas.costo_promedio(
            stock_actual=producto.current_stock, costo_actual=producto.cost_price,
            cantidad=cantidad, costo_compra=costo,
        )

    mov = _nuevo_ingreso(actual, producto, almacen_id, cantidad, notas, costo)
    await _guardar(db, mov)
    return a_entradas([await _fila(db, actual, mov, producto)])[0]


@router.post("/mermas", response_model=MermaOut, response_model_exclude_none=True, status_code=201)
async def registrar_merma(
    datos: MermaCrear,
    actual: dict = admin_o_taller,
    db: AsyncSession = Depends(get_db),
):
    """Descarte de producto: resta stock del almacén principal (no puede superar lo que hay)."""
    producto = await _producto(db, datos.productId)
    try:
        cantidad = reglas.validar_cantidad(datos.quantity, nombre=producto.name, unit_type=producto.unit_type)
        motivo = reglas.validar_motivo(datos.motivo)
        detalle = reglas.validar_texto_opcional(datos.detalle, "El detalle")
        almacen_id = await almacen_principal_id(db)
        disponible = await stock_disponible(db, almacen_id, [producto.id])
        validar_stock({producto.id: cantidad}, disponible, {producto.id: producto.name})
    except _REGLAS as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje)

    mov = Mov(
        product_id=producto.id,
        user_id=actual["id"],
        movement_type="MERMA",
        quantity=Decimal(str(cantidad)),
        reason=detalle,
        created_at=datetime.now(timezone.utc),
        unit_cost_price=producto.cost_price,        # lo que cuesta lo perdido
        waste_type=motivo,
        origin_warehouse_id=almacen_id,             # sin destino: sale stock
        destination_warehouse_id=None,
        currency="PEN",
        exchange_rate=Decimal("1"),
    )
    await _guardar(db, mov)
    return a_mermas([await _fila(db, actual, mov, producto)])[0]