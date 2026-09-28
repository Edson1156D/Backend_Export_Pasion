from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic sees the complete metadata graph.
from app.modelo import categorias, comercio_exterior, contadores, entradas, lotes, mermas, movimientos, productos, proveedores, socios_comerciales, usuarios, ventas  # noqa: E402,F401
