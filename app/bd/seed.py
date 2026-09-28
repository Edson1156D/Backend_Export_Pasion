from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from app.modelo.categorias import Categoria
from app.modelo.proveedores import Proveedor
from app.modelo.socios_comerciales import SocioComercial


def seed_catalogos(
    connection: Connection,
    categories: Iterable[dict[str, Any]] = (),
    suppliers: Iterable[dict[str, Any]] = (),
    foreign_partners: Iterable[dict[str, Any]] = (),
) -> None:
    """Insert explicit catalog rows only when each catalog is empty.

    The real schema currently contains no authoritative catalog data, so the
    migration passes empty iterables until those values are supplied.
    """
    catalogs = (
        (Categoria, categories),
        (Proveedor, suppliers),
        (SocioComercial, foreign_partners),
    )
    for model, rows in catalogs:
        if connection.execute(select(func.count()).select_from(model.__table__)).scalar_one() == 0:
            rows = tuple(rows)
            if rows:
                connection.execute(model.__table__.insert(), list(rows))