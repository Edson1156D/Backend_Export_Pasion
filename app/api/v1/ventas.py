from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.ventas import VentaCrear, VentaItemPublica, VentaPublica
from app.modelo.usuarios import Usuario
from app.modelo.ventas import Venta
from app.servicios.ventas import listar_ventas, registrar_venta

router = APIRouter(tags=["Ventas"])


def _venta_publica(venta: Venta) -> VentaPublica:
    return VentaPublica(
        id=venta.id,
        folio=venta.folio,
        items=[
            VentaItemPublica(
                product_id=item.product_id,
                name=item.name,
                sku=item.sku,
                unit_type=item.unit_type,
                unit_price=float(item.unit_price),
                quantity=float(item.quantity),
            )
            for item in venta.items
        ],
        tipo_venta=venta.sale_type,
        metodo_pago=venta.payment_method,
        subtotal=float(venta.subtotal),
        total=float(venta.total),
        pago_con=float(venta.paid_with) if venta.paid_with is not None else None,
        vuelto=float(venta.change_amount) if venta.change_amount is not None else None,
        responsable=venta.responsable.full_name,
        created_at=venta.created_at,
    )


@router.get("/ventas", response_model=list[VentaPublica], summary="Listar ventas", description="Devuelve todas las ventas registradas, ordenadas de la más reciente a la más antigua.", responses={401: {"description": 'Autenticación requerida. Formato: {"detail": "texto"}.'}, 403: {"description": 'Se requiere rol admin. Formato: {"detail": "texto"}.'}})
async def listar_todas_las_ventas(
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[VentaPublica]:
    return [_venta_publica(venta) for venta in await listar_ventas(db)]


@router.get("/ventas/mias", response_model=list[VentaPublica], summary="Listar mis ventas", description="Devuelve únicamente las ventas registradas por el usuario autenticado.", responses={401: {"description": 'Autenticación requerida. Formato: {"detail": "texto"}.'}, 403: {"description": 'Se requiere rol vendedor. Formato: {"detail": "texto"}.'}})
async def listar_mis_ventas(
    usuario: Usuario = Depends(requiere_roles("vendedor")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[VentaPublica]:
    return [_venta_publica(venta) for venta in await listar_ventas(db, usuario.id)]


@router.post("/ventas", response_model=VentaPublica, status_code=status.HTTP_201_CREATED, summary="Registrar venta", description="Registra una venta, recalcula precios y consume el stock usando FIFO.", responses={404: {"description": 'Producto inexistente. Formato: {"detail": "Producto no encontrado"}.'}, 409: {"description": 'Stock insuficiente o conflicto de pago. Formato: {"detail": "texto"}.'}, 422: {"description": 'Datos inválidos. Formato: {"detail": "texto"}.'}})
async def crear_venta(
    datos: VentaCrear,
    usuario: Usuario = Depends(requiere_roles("admin", "vendedor")),
    db: AsyncSession = Depends(get_db),
) -> VentaPublica:
    venta = await registrar_venta(
        db,
        items=[{"product_id": item.product_id, "quantity": item.quantity} for item in datos.items],
        tipo_venta=datos.tipo_venta,
        metodo_pago=datos.metodo_pago,
        pago_con=datos.pago_con,
        responsable=usuario,
    )
    await db.commit()
    await db.refresh(venta, ["items", "responsable"])
    return _venta_publica(venta)