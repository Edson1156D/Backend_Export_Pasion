from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.movimientos import MovimientoPublico
from app.modelo.usuarios import Usuario
from app.servicios.movimientos import listar_movimientos

router = APIRouter(tags=["Movimientos"])


@router.get("/movimientos", response_model=list[MovimientoPublico], summary="Listar movimientos", description="Devuelve el ledger de movimientos de inventario enriquecido con datos del producto y la venta.", responses={401: {"description": 'Autenticación requerida. Formato: {"detail": "texto"}.'}, 403: {"description": 'Se requiere rol admin. Formato: {"detail": "texto"}.'}})
async def listar_movimientos_admin(
	_: Usuario = Depends(requiere_roles("admin")),
	db: AsyncSession = Depends(get_db),
) -> Sequence[MovimientoPublico]:
	return await listar_movimientos(db)
