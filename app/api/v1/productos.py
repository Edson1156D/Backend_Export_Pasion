from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.productos import ProductoActualizar, ProductoCrear, ProductoPublico
from app.modelo.categorias import Categoria
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.servicios.productos import producto_tiene_historial, sku_en_uso

router = APIRouter(prefix="/productos", tags=["Productos"])


def _publico(producto: Producto) -> ProductoPublico:
    return ProductoPublico(
        id=producto.id,
        category_id=producto.category_id,
        sku=producto.sku,
        name=producto.name,
        unit_type=producto.unit_type,
        sale_price=float(producto.sale_price),
        cost_price=float(producto.cost_price),
        current_stock=float(producto.current_stock),
        min_stock_alert=float(producto.min_stock_alert),
        is_active=producto.is_active,
        created_at=producto.created_at,
    )


async def _obtener_producto(db: AsyncSession, producto_id: int) -> Producto:
    producto = await db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return producto


async def _validar_categoria(db: AsyncSession, category_id: int) -> None:
    if await db.get(Categoria, category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")


@router.get("", response_model=list[ProductoPublico], summary="Listar productos", description="Devuelve el catálogo completo de productos con stock y precios actuales.", responses={401: {"description": 'Autenticación requerida. Formato: {"detail": "texto"}.'}})
async def listar_productos(
    _: Usuario = Depends(requiere_roles("admin", "vendedor", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[ProductoPublico]:
    productos = (await db.scalars(select(Producto).order_by(Producto.created_at.desc(), Producto.id.desc()))).all()
    return [_publico(producto) for producto in productos]


@router.get("/{producto_id}", response_model=ProductoPublico, summary="Consultar producto", description="Devuelve el detalle de un producto por su identificador.", responses={404: {"description": 'Producto inexistente. Formato: {"detail": "Producto no encontrado"}.'}})
async def obtener_producto(
    producto_id: int,
    _: Usuario = Depends(requiere_roles("admin", "vendedor", "taller")),
    db: AsyncSession = Depends(get_db),
) -> ProductoPublico:
    return _publico(await _obtener_producto(db, producto_id))


@router.post("", response_model=ProductoPublico, status_code=status.HTTP_201_CREATED, summary="Crear producto", description="Registra un producto activo o inactivo; el stock y costo iniciales los controla el inventario.", responses={404: {"description": 'Categoría inexistente. Formato: {"detail": "texto"}.'}, 409: {"description": 'SKU duplicado. Formato: {"detail": "Ya existe un producto con ese SKU"}.'}, 422: {"description": 'Datos inválidos. Formato: {"detail": "texto"}.'}})
async def crear_producto(
    datos: ProductoCrear,
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> ProductoPublico:
    await _validar_categoria(db, datos.category_id)
    if await sku_en_uso(db, datos.sku):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un producto con ese SKU")
    producto = Producto(
        category_id=datos.category_id,
        sku=datos.sku,
        name=datos.name,
        unit_type=datos.unit_type,
        sale_price=datos.sale_price,
        cost_price=0,
        current_stock=0,
        min_stock_alert=datos.min_stock_alert,
        is_active=datos.is_active,
    )
    db.add(producto)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un producto con ese SKU") from None
    await db.commit()
    return _publico(producto)


@router.put("/{producto_id}", response_model=ProductoPublico, summary="Actualizar producto", description="Actualiza los datos editables de un producto sin permitir cambios directos de stock o costo.", responses={404: {"description": 'Producto o categoría inexistente. Formato: {"detail": "texto"}.'}, 409: {"description": 'SKU duplicado. Formato: {"detail": "Ya existe un producto con ese SKU"}.'}, 422: {"description": 'Datos inválidos. Formato: {"detail": "texto"}.'}})
async def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> ProductoPublico:
    producto = await _obtener_producto(db, producto_id)
    valores = datos.model_dump(exclude_unset=True)
    if "category_id" in valores:
        await _validar_categoria(db, valores["category_id"])
    if "sku" in valores and await sku_en_uso(db, valores["sku"], producto_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un producto con ese SKU")
    nuevo_activo = valores.get("is_active", producto.is_active)
    nuevo_precio = valores.get("sale_price", float(producto.sale_price))
    if nuevo_activo and nuevo_precio <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Para activar el producto, el precio de venta debe ser mayor a 0")
    for campo, valor in valores.items():
        setattr(producto, campo, valor)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un producto con ese SKU") from None
    await db.commit()
    return _publico(producto)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar producto", description="Elimina un producto solo cuando no tiene lotes, ventas ni movimientos asociados.", responses={404: {"description": 'Producto inexistente. Formato: {"detail": "Producto no encontrado"}.'}, 409: {"description": 'Producto con historial. Formato: {"detail": "texto"}.'}})
async def eliminar_producto(
    producto_id: int,
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    producto = await _obtener_producto(db, producto_id)
    if await producto_tiene_historial(db, producto_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: el producto tiene movimientos. Desactívalo en su lugar.",
        )
    await db.delete(producto)
    await db.commit()