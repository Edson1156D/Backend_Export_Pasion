from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.bd.session import Base


class Categoria(Base):
    """Tabla real `categories` (ya existe). NO crear ni migrar desde el código."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer)
    name = Column(String, nullable=False)
    description = Column(Text)


class Producto(Base):
    """Tabla real `products` (ya existe). NO crear ni migrar desde el código."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, nullable=False)
    sku = Column(String, nullable=False)
    name = Column(String, nullable=False)
    unit_type = Column(String, nullable=False)
    sale_price = Column(Numeric, nullable=False)
    cost_price = Column(Numeric)
    current_stock = Column(Numeric, nullable=False)
    min_stock_alert = Column(Numeric, nullable=False)
    is_active = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockPorAlmacen(Base):
    """Tabla real `product_stock_by_warehouse` (ya existe). La mantiene el trigger de los movimientos."""
    __tablename__ = "product_stock_by_warehouse"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=False)
    stock = Column(Numeric, nullable=False)
    updated_at = Column(DateTime(timezone=True))