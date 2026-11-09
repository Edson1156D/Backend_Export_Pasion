import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.user import obtener_usuario_por_id
from app.bd.session import get_db
from app.core.seguridad import requiere_rol
from app.esquemas.comercio import OperacionCrear, OperacionOut, SocioCrear, SocioOut
from app.modelo.almacenes import Almacen
from app.modelo.movimientos import MovimientoInventario as Mov
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.servicios import comercio_reglas as reglas
from app.servicios import inventario_reglas as inventario
from app.servicios import ventas_reglas as ventas
from app.servicios.almacen_consultas import almacen_principal_id, stock_disponible
from app.servicios.almacen_reglas import ReglaAlmacen
from app.servicios.dashboard_calculos import ZONA
from app.servicios import socios_comerciales as socios_reglas
from app.servicios.socios_comerciales import por_id
from app.servicios.socios_consultas import listar_socios

router = APIRouter(
    prefix="/comercio-exterior",
    tags=["comercio-exterior"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)
solo_admin = Depends(requiere_rol("ADMIN"))

MAX_FILAS = 5000
_REGLAS = (reglas.ReglaComercio, inventario.ReglaInventario, ventas.ReglaVenta, ReglaAlmacen, socios_reglas.ReglaSocio)


@router.get("/socios-comerciales", response_model=list[SocioOut])
async def obtener_socios(db: AsyncSession = Depends(get_db)):
    """Socios = filas de `warehouses` cuyo nombre empieza por "SOCIO:" (la BD no tiene tabla de socios)."""
    return await listar_socios(db)


@router.post("/socios-comerciales", response_model=SocioOut, status_code=201)
async def crear_socio(datos: SocioCrear, db: AsyncSession = Depends(get_db)):
    """Agrega un socio comercial (se guarda como una fila de `warehouses` con nombre "SOCIO: ...")."""
    try:
        nombre, pais = socios_reglas.validar_nuevo(datos.nombre, datos.pais, await listar_socios(db))
    except socios_reglas.ReglaSocio as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje)

    almacen = Almacen(
        name=socios_reglas.nombre_de_almacen(nombre),
        country=pais,
        is_temporary=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(almacen)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo guardar el socio; inténtalo de nuevo")
    return {"id": almacen.id, "nombre": nombre, "pais": pais}


@router.get("/operaciones", response_model=list[OperacionOut], response_model_exclude_none=True)
async def listar_operaciones(db: AsyncSession = Depends(get_db)):
    """Exportaciones (VENTA_MAYORISTA en USD) e importaciones (INGRESO en USD), de la más reciente a la más antigua."""
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
        .where(
            func.upper(func.trim(Mov.movement_type)).in_(("VENTA_MAYORISTA", "INGRESO")),
            func.upper(func.trim(Mov.currency)) == "USD",
        )
        .order_by(Mov.created_at.desc(), Mov.id.desc())
        .limit(MAX_FILAS)
    )
    filas = [fila._asdict() for fila in (await db.execute(consulta)).all()]
    return reglas.agrupar_operaciones(filas, await listar_socios(db))


@router.post("/operaciones", response_model=OperacionOut, response_model_exclude_none=True, status_code=201)
async def registrar_operacion(
    datos: OperacionCrear,
    actual: dict = solo_admin,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra una exportación (sale stock de Taller Principal Lima) o una importación (entra a
    Taller Principal Lima y recalcula el costo promedio en soles). Una línea de movimiento por producto.
    """
    ahora = datetime.now(timezone.utc)
    try:
        tipo = reglas.validar_tipo(datos.tipo)
        fecha = reglas.validar_fecha(datos.fecha, ahora.astimezone(ZONA).date())
        tasa = reglas.validar_tipo_cambio(datos.tipoCambio)
        reglas.validar_opcionales(datos.incoterm, datos.medioTransporte)
        lineas = reglas.validar_lineas([(l.productoId, l.cantidad, l.precioUSD) for l in datos.lineas])
        socios = await listar_socios(db)
        socio = reglas.validar_socio(tipo, por_id(datos.socioComercialId, socios))
        motivo = reglas.armar_reason(
            socio=socio["nombre"], incoterm=datos.incoterm, medio=datos.medioTransporte, notas=datos.notas
        )

        ids = sorted(producto_id for producto_id, _, _ in lineas)
        consulta = select(Producto).where(Producto.id.in_(ids)).order_by(Producto.id)
        if tipo == "importacion":
            consulta = consulta.with_for_update()        # el costo promedio depende del stock actual
        productos = {p.id: p for p in (await db.execute(consulta)).scalars().all()}
        faltantes = [i for i in ids if i not in productos]
        if faltantes:
            raise reglas.ReglaComercio(422, f"El producto {faltantes[0]} no existe")

        cantidades: dict[int, float] = {}
        for producto_id, cantidad, _ in lineas:
            p = productos[producto_id]
            cantidades[producto_id] = inventario.validar_cantidad(cantidad, nombre=p.name, unit_type=p.unit_type)
            activo = p.is_active is not False
            if tipo == "exportacion":
                ventas.validar_producto(nombre=p.name, unit_type=p.unit_type, activo=activo, cantidad=cantidades[producto_id])
            else:
                inventario.validar_producto_activo(nombre=p.name, activo=activo)

        almacen_id = await almacen_principal_id(db)
        if tipo == "exportacion":
            disponible = await stock_disponible(db, almacen_id, ids)
            ventas.validar_stock(cantidades, disponible, {i: p.name for i, p in productos.items()})
    except _REGLAS as error:
        raise HTTPException(status_code=error.codigo, detail=error.mensaje)

    folio = reglas.generar_folio(tipo, ahora.astimezone(ZONA), uuid.uuid4().hex[:6])
    momento = reglas.momento_de_registro(fecha, ahora)
    movimientos = []
    for producto_id, _, precio_usd in lineas:
        p = productos[producto_id]
        cantidad = Decimal(str(cantidades[producto_id]))
        comunes = dict(
            product_id=producto_id, user_id=actual["id"], quantity=cantidad, reason=motivo,
            created_at=momento, sale_group_id=folio, currency="USD",
            exchange_rate=Decimal(str(tasa)), destination_country=socio["pais"],
        )
        if tipo == "exportacion":
            movimientos.append(Mov(
                movement_type="VENTA_MAYORISTA",
                unit_sold_price=Decimal(str(precio_usd)),        # precio en dólares
                unit_cost_price=p.cost_price,                    # costo en soles, para el margen
                origin_warehouse_id=almacen_id, destination_warehouse_id=None, **comunes,
            ))
        else:
            costo_soles = round(precio_usd * tasa, 4)
            # El stock y el costo se leen ANTES de insertar: el trigger suma la importación al insertar.
            p.cost_price = inventario.costo_promedio(
                stock_actual=p.current_stock, costo_actual=p.cost_price,
                cantidad=cantidades[producto_id], costo_compra=costo_soles,
            )
            movimientos.append(Mov(
                movement_type="INGRESO",
                unit_cost_price=Decimal(str(costo_soles)),       # soles = precio USD x tipo de cambio
                origin_warehouse_id=None, destination_warehouse_id=almacen_id, **comunes,
            ))

    db.add_all(movimientos)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo registrar la operación; inténtalo de nuevo")

    usuario = await obtener_usuario_por_id(db, actual["id"])
    filas = [
        {
            "id": m.id, "product_id": m.product_id, "movement_type": m.movement_type, "quantity": m.quantity,
            "created_at": m.created_at, "reason": m.reason, "unit_sold_price": m.unit_sold_price,
            "unit_cost_price": m.unit_cost_price, "waste_type": None, "sale_group_id": folio,
            "currency": "USD", "exchange_rate": m.exchange_rate, "destination_country": socio["pais"],
            "responsable": usuario.full_name if usuario else None,
            "producto": productos[m.product_id].name, "sku": productos[m.product_id].sku,
            "unit_type": productos[m.product_id].unit_type,
        }
        for m in movimientos
    ]
    return reglas.agrupar_operaciones(filas, socios)[0]