from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.session import get_db
from app.core.seguridad import requiere_rol
from app.esquemas.dashboard import DashboardResumenResponse
from app.servicios.dashboard_servicio import obtener_resumen

# Solo el admin ve el dashboard (igual que la analítica).
router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@router.get("/resumen", response_model=DashboardResumenResponse)
async def resumen_dashboard(
    periodo: Literal["dia", "semana", "mes"] = "semana",
    db: AsyncSession = Depends(get_db),
):
    """Resumen gerencial. ?periodo=dia|semana|mes (por defecto, semana)."""
    return await obtener_resumen(db, periodo)