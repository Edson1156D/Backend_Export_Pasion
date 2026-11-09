from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.session import get_db
from app.core.seguridad import obtener_usuario_actual, requiere_rol
from app.esquemas.productos import (
    CategoriaOut,
    ProductoActualizar,
    ProductoCrear,
    ProductoOut,
    categoria_a_out,
    producto_a_out,
)
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Categoria, Producto, StockPorAlmacen
from app.servicios import productos_reglas as reglas
from decimal import Decimal


# Lectura para cualquier usuario con sesión (el POS y el catálogo la necesitan).
router = APIRouter(tags=["productos"], dependencies=[Depends(obtener_usuario_actual)])
solo_admin = Depends(requiere_rol("ADMIN"))
SKU_DUPLICADO = "Ya existe un producto con ese SKU"

def _http(error: reglas.ReglaProducto) -> HTTPException:
    # El front muestra `detail` tal cual, así que siempre es texto.
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


async def _guardar(db: AsyncSession, mensaje_conflicto: str) -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=mensaje_conflicto)


async def _buscar(db: AsyncSession, producto_id: int) -> Producto:
    producto = await db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


async def _validar_categoria(db: AsyncSession, categoria_id: int) -> None:
    if await db.get(Categoria, categoria_id) is None:
        raise HTTPException(status_code=422, detail="La categoría seleccionada no existe")


async def _sku_en_uso(db: AsyncSession, sku: str, excepto_id: int | None = None) -> bool:
    consulta = select(Producto.id).where(func.upper(Producto.sku) == sku.upper())
    if excepto_id is not None:
        consulta = consulta.where(Producto.id != excepto_id)
    return (await db.execute(consulta.limit(1))).first() is not None


async def _contar_movimientos(db: AsyncSession, producto_id: int) -> int:
    consulta = select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.product_id == producto_id
    )
    return (await db.execute(consulta)).scalar_one()

@router.get("/productos", response_model=list[ProductoOut])
async def listar_productos(db: AsyncSession = Depends(get_db)):
    """Todos los productos (activos e inactivos); el front filtra por isActive."""
    filas = (await db.execute(select(Producto).order_by(Producto.id))).scalars().all()
    return [producto_a_out(p) for p in filas]


@router.get("/productos/{producto_id}", response_model=ProductoOut)
async def obtener_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    return producto_a_out(await _buscar(db, producto_id))


@router.post("/productos", response_model=ProductoOut, status_code=201, dependencies=[solo_admin])
async def crear_producto(datos: ProductoCrear, db: AsyncSession = Depends(get_db)):
    try:
        sku = reglas.validar_sku(datos.sku)
        nombre = reglas.validar_nombre(datos.name)
        precio = reglas.validar_precio(datos.salePrice)
        minimo = reglas.validar_stock_minimo(datos.minStockAlert)
        reglas.validar_activacion(activo=datos.isActive, precio=precio)
    except reglas.ReglaProducto as error:
        raise _http(error)

    await _validar_categoria(db, datos.categoryId)
    if await _sku_en_uso(db, sku):
        raise HTTPException(status_code=409, detail=SKU_DUPLICADO)

    producto = Producto(
        category_id=datos.categoryId,
        sku=sku,
        name=nombre,
        unit_type=datos.unitType,
        sale_price=Decimal(str(precio)),
        cost_price=None,          # lo define el sistema con las compras, no el formulario
        current_stock=0,          # el stock solo cambia con movimientos (lo mueve el trigger)
        min_stock_alert=Decimal(str(minimo)),
        is_active=datos.isActive,
    )
    db.add(producto)
    await _guardar(db, SKU_DUPLICADO)
    await db.refresh(producto)
    return producto_a_out(producto)


@router.put("/productos/{producto_id}", response_model=ProductoOut, dependencies=[solo_admin])
async def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: AsyncSession = Depends(get_db),
):
    producto = await _buscar(db, producto_id)
    # Solo se tocan los campos enviados; un null se ignora.
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}

    try:
        sku = reglas.validar_sku(cambios["sku"]) if "sku" in cambios else None
        nombre = reglas.validar_nombre(cambios["name"]) if "name" in cambios else None
        precio = reglas.validar_precio(cambios["salePrice"]) if "salePrice" in cambios else None
        minimo = reglas.validar_stock_minimo(cambios["minStockAlert"]) if "minStockAlert" in cambios else None
        if "unitType" in cambios:
            reglas.validar_unidad(cambios["unitType"])
            reglas.validar_cambio_unidad(
                unidad_actual=(producto.unit_type or "").strip().upper(),
                unidad_nueva=cambios["unitType"],
                movimientos=await _contar_movimientos(db, producto.id),
            )
        if precio is not None or "isActive" in cambios:
            reglas.validar_activacion(
                activo=cambios.get("isActive", producto.is_active is not False),
                precio=precio if precio is not None else float(producto.sale_price),
            )
    except reglas.ReglaProducto as error:
        raise _http(error)

    if "categoryId" in cambios:
        await _validar_categoria(db, cambios["categoryId"])
        producto.category_id = cambios["categoryId"]
    if sku is not None:
        if await _sku_en_uso(db, sku, excepto_id=producto.id):
            raise HTTPException(status_code=409, detail=SKU_DUPLICADO)
        producto.sku = sku
    if nombre is not None:
        producto.name = nombre
    if "unitType" in cambios:
        producto.unit_type = cambios["unitType"]
    if precio is not None:
        producto.sale_price = Decimal(str(precio))
    if minimo is not None:
        producto.min_stock_alert = Decimal(str(minimo))
    if "isActive" in cambios:
        producto.is_active = cambios["isActive"]

    await _guardar(db, SKU_DUPLICADO)
    await db.refresh(producto)
    return producto_a_out(producto)


@router.delete("/productos/{producto_id}", status_code=204, dependencies=[solo_admin])
async def eliminar_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    producto = await _buscar(db, producto_id)

    movimientos = await _contar_movimientos(db, producto.id)
    filas_con_stock = (
        await db.execute(
            select(func.count()).select_from(StockPorAlmacen).where(
                StockPorAlmacen.product_id == producto.id, StockPorAlmacen.stock != 0
            )
        )
    ).scalar_one()
    hay_stock = float(producto.current_stock or 0) != 0 or filas_con_stock > 0

    try:
        reglas.validar_eliminacion(movimientos=movimientos, hay_stock=hay_stock)
    except reglas.ReglaProducto as error:
        raise _http(error)

    # Solo quedan filas de stock en cero (p. ej. sembradas al crear la base): se limpian.
    await db.execute(delete(StockPorAlmacen).where(StockPorAlmacen.product_id == producto.id))
    await db.delete(producto)
    await _guardar(db, "No se puede eliminar: el producto está en uso; desactívalo en su lugar")

@router.get("/categorias", response_model=list[CategoriaOut])
async def listar_categorias(db: AsyncSession = Depends(get_db)):
    filas = (await db.execute(select(Categoria).order_by(Categoria.id))).scalars().all()
    return [categoria_a_out(c) for c in filas]