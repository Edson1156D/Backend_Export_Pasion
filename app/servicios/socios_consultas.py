"""Lectura de socios comerciales desde la BD (filas de `warehouses` con nombre "SOCIO: ...")."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelo.almacenes import Almacen
from app.servicios.almacen_reglas import PREFIJO_SOCIO
from app.servicios.socios_comerciales import listar


async def listar_socios(db: AsyncSession) -> list[dict]:
    filas = (
        await db.execute(
            select(Almacen.id, Almacen.name, Almacen.country)
            .where(func.upper(func.trim(Almacen.name)).like(PREFIJO_SOCIO + "%"))
            .order_by(Almacen.id)
        )
    ).all()
    return listar([{"id": f.id, "name": f.name, "country": f.country} for f in filas])