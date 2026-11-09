from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.bd.session import Base


class Almacen(Base):
    """Tabla real `warehouses` (ya existe). NO crear ni migrar desde el código."""
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    country = Column(String)
    is_temporary = Column(Boolean)
    created_at = Column(DateTime(timezone=True))