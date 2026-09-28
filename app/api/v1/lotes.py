from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.lotes import LotePublico, ProveedorLote
from app.modelo.lotes import Lote
from app.modelo.usuarios import Usuario

router = APIRouter(prefix="/lotes", tags=["lotes"])


def _publico(lote: Lote) -> LotePublico:
    proveedor = None
    if lote.supplier is not None:
        proveedor = ProveedorLote(id=lote.supplier.id, name=lote.supplier.name)
    return LotePublico(
        id=lote.id,
        product_id=lote.product_id,
        codigo=lote.code,
        origen=lote.origin,
        cantidad_inicial=float(lote.initial_qty),
        cantidad_disponible=float(lote.available_qty),
        costo_unitario_soles=float(lote.unit_cost_pen),
        proveedor=proveedor,
        responsable=lote.responsable.full_name,
        fecha_ingreso=lote.received_at,
    )


_OPCIONES_CARGA = (selectinload(Lote.supplier), selectinload(Lote.responsable))


@router.get("/producto/{producto_id}", response_model=list[LotePublico])
async def listar_lotes_producto(
    producto_id: int,
    _: Usuario = Depends(requiere_roles("admin", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[LotePublico]:
    lotes = (
        await db.scalars(
            select(Lote)
            .options(*_OPCIONES_CARGA)
            .where(Lote.product_id == producto_id)
            .order_by(Lote.received_at, Lote.id)
        )
    ).all()
    return [_publico(lote) for lote in lotes]


@router.get("", response_model=list[LotePublico])
async def listar_lotes(
    product_id: int | None = Query(default=None),
    origen: str | None = Query(default=None),
    _: Usuario = Depends(requiere_roles("admin", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[LotePublico]:
    consulta = select(Lote).options(*_OPCIONES_CARGA)
    if product_id is not None:
        consulta = consulta.where(Lote.product_id == product_id)
    if origen is not None:
        consulta = consulta.where(Lote.origin == origen)
    lotes = (await db.scalars(consulta.order_by(Lote.received_at.desc(), Lote.id.desc()))).all()
    return [_publico(lote) for lote in lotes]
