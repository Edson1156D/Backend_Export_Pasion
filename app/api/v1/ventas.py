import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.user import obtener_usuario_por_id
from app.bd.session import get_db
from app.core.seguridad import obtener_usuario_actual, requiere_rol, requiere_roles
from app.esquemas.ventas import VentaCrear, VentaOut
from app.modelo.movimientos import MovimientoInventario as Mov
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.servicios import ventas_reglas as reglas
from app.servicios.almacen_consultas import almacen_principal_id, stock_disponible
from app.servicios.almacen_reglas import ReglaAlmacen
from app.servicios.dashboard_calculos import ZONA
from app.servicios.ventas_agrupar import agrupar_ventas

router = APIRouter(tags=["ventas"])

# Se leen todos los tipos de venta y agrupar_ventas descarta las exportaciones.
TIPOS_VENTA_BD = ("VENTA_MAYORISTA", "VENTA_MINORISTA")
MAX_LINEAS = 5000      # las más recientes; una venta en el corte podría salir incompleta


async def _leer_ventas(db: AsyncSession, usuario_id: int | None = None) -> list[dict]:
    consulta = (
        select(
            Mov.id, Mov.product_id, Mov.movement_type, Mov.quantity, Mov.created_at,
            Mov.reason, Mov.unit_sold_price, Mov.unit_cost_price, Mov.waste_type,
            Mov.sale_group_id, Mov.currency, Mov.exchange_rate, Mov.destination_country,
            Usuario.full_name.label("responsable"),
            Producto.name.label("producto"),
            Producto.sku,
            Producto.unit_type,
            Producto.sale_price.label("precio_lista"),
        )
        .select_from(Mov)
        .outerjoin(Usuario, Usuario.id == Mov.user_id)
        .outerjoin(Producto, Producto.id == Mov.product_id)
        .where(func.upper(func.trim(Mov.movement_type)).in_(TIPOS_VENTA_BD))
    )
    if usuario_id is not None:
        consulta = consulta.where(Mov.user_id == usuario_id)

    consulta = consulta.order_by(Mov.created_at.desc(), Mov.id.desc()).limit(MAX_LINEAS)
    filas = (await db.execute(consulta)).all()
    return agrupar_ventas([fila._asdict() for fila in filas])


@router.get(
    "/ventas", response_model=list[VentaOut], response_model_exclude_none=True,
    dependencies=[Depends(requiere_rol("ADMIN"))],
)
async def listar_ventas(db: AsyncSession = Depends(get_db)):
    """Todas las ventas (solo admin), de la más reciente a la más antigua."""
    return await _leer_ventas(db)


@router.get("/ventas/mias", response_model=list[VentaOut], response_model_exclude_none=True)
async def listar_mis_ventas(actual: dict = Depends(obtener_usuario_actual), db: AsyncSession = Depends(get_db)):
    """Las ventas registradas por el usuario autenticado (la usa el vendedor)."""
    return await _leer_ventas(db, usuario_id=actual.get("id"))


@router.post("/ventas", response_model=VentaOut, response_model_exclude_none=True, status_code=201)
async def registrar_venta(
    datos: VentaCrear,
    actual: dict = Depends(requiere_roles("ADMIN", "VENDEDOR")),
    db: AsyncSession = Depends(get_db),
):
    """
    Registra una venta del punto de venta. El servidor pone los precios, valida el stock del
    almacén principal y escribe una línea VENTA_MINORISTA por producto; el trigger de la base
    descuenta el stock (el backend NO lo toca).
    """
    try:
        pedido = reglas.validar_items([(i.productId, i.quantity) for i in datos.items])

        encontrados = (await db.execute(select(Producto).where(Producto.id.in_(list(pedido))))).scalars().all()
        productos = {p.id: p for p in encontrados}
        inexistentes = sorted(set(pedido) - set(productos))
        if inexistentes:
            raise reglas.ReglaVenta(422, f"El producto {inexistentes[0]} no existe")

        for product_id, cantidad in pedido.items():
            p = productos[product_id]
            reglas.validar_producto(
                nombre=p.name, unit_type=p.unit_type, activo=p.is_active is not False, cantidad=cantidad
            )

        total = round(sum(float(productos[pid].sale_price) * c for pid, c in pedido.items()), 2)
        pago = reglas.validar_pago(
            tipo_venta=datos.tipoVenta, metodo_pago=datos.metodoPago, pago_con=datos.pagoCon, total=total
        )

        almacen_id = await almacen_principal_id(db)
        disponible = await stock_disponible(db, almacen_id, list(pedido))
        reglas.validar_stock(pedido, disponible, {pid: p.name for pid, p in productos.items()})
    except (reglas.ReglaVenta, ReglaAlmacen) as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje)

    ahora = datetime.now(timezone.utc)
    folio = reglas.generar_folio(ahora.astimezone(ZONA), uuid.uuid4().hex[:4])
    motivo = reglas.codificar_reason(pago["canal"], pago["metodo"], pago["pago_con"])

    movimientos = [
        Mov(
            product_id=product_id,
            user_id=actual["id"],
            movement_type=reglas.TIPO_MOVIMIENTO_POS,
            quantity=Decimal(str(round(cantidad, 3))),
            reason=motivo,
            created_at=ahora,
            unit_sold_price=productos[product_id].sale_price,     # precio del servidor, no del cliente
            unit_cost_price=productos[product_id].cost_price,
            sale_group_id=folio,
            origin_warehouse_id=almacen_id,                       # sin destino: es una salida definitiva
            destination_warehouse_id=None,
            currency="PEN",
            exchange_rate=Decimal("1"),
            destination_country="Peru",
        )
        for product_id, cantidad in pedido.items()
    ]
    db.add_all(movimientos)
    try:
        await db.flush()      # asigna los id de cada línea
        await db.commit()     # libera el bloqueo del stock
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo registrar la venta; inténtalo de nuevo")

    usuario = await obtener_usuario_por_id(db, actual["id"])
    filas = [
        {
            "id": m.id, "product_id": m.product_id, "movement_type": m.movement_type, "quantity": m.quantity,
            "created_at": ahora, "reason": m.reason, "unit_sold_price": m.unit_sold_price,
            "unit_cost_price": m.unit_cost_price, "waste_type": None, "sale_group_id": folio,
            "currency": "PEN", "exchange_rate": Decimal("1"), "destination_country": "Peru",
            "responsable": usuario.full_name if usuario else None,
            "producto": productos[m.product_id].name, "sku": productos[m.product_id].sku,
            "unit_type": productos[m.product_id].unit_type, "precio_lista": productos[m.product_id].sale_price,
        }
        for m in movimientos
    ]
    return agrupar_ventas(filas)[0]