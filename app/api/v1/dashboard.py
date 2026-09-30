from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.dashboard import DashboardResumen
from app.modelo.usuarios import Usuario
from app.servicios.dashboard import obtener_resumen_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/resumen", response_model=DashboardResumen)
async def resumen_dashboard(
    periodo: Literal["dia", "semana", "mes"] = Query("mes"),
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> DashboardResumen:
    return await obtener_resumen_dashboard(db, periodo)