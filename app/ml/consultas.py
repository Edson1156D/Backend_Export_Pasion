"""Consultas a la base de datos para la zona 1 (demanda)."""
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.suficiencia import TIPOS_VENTA, ZONA_HORARIA_SQL, FilaSemanal
from app.modelo.movimientos import MovimientoInventario

from datetime import datetime

from app.ml.anomalias import TIPOS_ANALIZADOS, Movimiento
from app.servicios.dashboard_calculos import ZONA

async def ventas_semanales(
    db: AsyncSession, product_id: int | None = None
) -> list[FilaSemanal]:
    """
    Unidades vendidas por producto y por semana (semana = lunes, hora de Lima).
    Solo cuentan los tipos de TIPOS_VENTA; transferencias, mermas, etc. se ignoran.
    """
    # literal_column (y no un parámetro) para que la expresión sea idéntica en
    # SELECT y GROUP BY; con parámetros PostgreSQL rechaza el GROUP BY.
    semana = func.date_trunc(
        literal_column("'week'"),
        func.timezone(literal_column(f"'{ZONA_HORARIA_SQL}'"), MovimientoInventario.created_at),
    )

    consulta = (
        select(
            MovimientoInventario.product_id,
            semana.label("semana"),
            func.sum(MovimientoInventario.quantity).label("unidades"),
            func.count().label("lineas"),
        )
        # movement_type es texto libre: se compara sin espacios ni mayúsculas/minúsculas.
        .where(func.upper(func.trim(MovimientoInventario.movement_type)).in_(TIPOS_VENTA))
        .group_by(MovimientoInventario.product_id, semana)
        .order_by(MovimientoInventario.product_id, semana)
    )
    if product_id is not None:
        consulta = consulta.where(MovimientoInventario.product_id == product_id)

    filas = (await db.execute(consulta)).all()
    return [
        FilaSemanal(
            product_id=fila.product_id,
            semana=fila.semana.date(),
            unidades=float(fila.unidades),
            lineas=int(fila.lineas),
        )
        for fila in filas
    ]

async def movimientos_recientes(db: AsyncSession, desde: datetime) -> list[Movimiento]:
    """Ventas y mermas desde `desde`, con la fecha en hora de Lima."""
    consulta = (
        select(
            MovimientoInventario.id,
            MovimientoInventario.product_id,
            MovimientoInventario.movement_type,
            MovimientoInventario.created_at,
            MovimientoInventario.quantity,
        )
        # movement_type es texto libre: mismo criterio que en ventas_semanales
        .where(func.upper(func.trim(MovimientoInventario.movement_type)).in_(TIPOS_ANALIZADOS))
        .where(MovimientoInventario.created_at >= desde)
        .order_by(MovimientoInventario.created_at, MovimientoInventario.id)
    )
    filas = (await db.execute(consulta)).all()
    return [
        Movimiento(
            mov_id=f.id,
            product_id=f.product_id,
            tipo=f.movement_type,
            fecha=f.created_at.astimezone(ZONA),
            cantidad=float(f.quantity),
        )
        for f in filas
    ]