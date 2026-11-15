from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.session import get_db
from app.core.seguridad import requiere_rol
from app.esquemas.movimientos import MovimientoOut
from app.modelo.movimientos import MovimientoInventario as Mov
from app.modelo.productos import Producto
from app.modelo.usuarios import Usuario
from app.servicios.movimientos_mapeo import (
    INCLUIR_TRANSFERENCIAS,
    TIPO_TRANSFERENCIA,
    armar_movimiento,
)

# Solo el admin ve el historial completo de movimientos.
router = APIRouter(tags=["movimientos"], dependencies=[Depends(requiere_rol("ADMIN"))])


@router.get("/movimientos", response_model=list[MovimientoOut], response_model_exclude_none=True)
async def listar_movimientos(
    limite: int = Query(2000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Historial de movimientos, del más reciente al más antiguo (hasta `limite`)."""
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
        # outer join: un movimiento nunca desaparece aunque falte su usuario o producto
        .outerjoin(Usuario, Usuario.id == Mov.user_id)
        .outerjoin(Producto, Producto.id == Mov.product_id)
    )
    if not INCLUIR_TRANSFERENCIAS:
        consulta = consulta.where(func.upper(func.trim(Mov.movement_type)) != TIPO_TRANSFERENCIA)

    consulta = consulta.order_by(Mov.created_at.desc(), Mov.id.desc()).limit(limite)
    filas = (await db.execute(consulta)).all()
    return [armar_movimiento(fila._asdict()) for fila in filas]