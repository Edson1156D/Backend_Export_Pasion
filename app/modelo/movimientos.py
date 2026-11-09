from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String

from app.bd.session import Base


class MovimientoInventario(Base):
    """
    Tabla real `inventory_movements` (ya existe en la base de datos).
    El tipo de movimiento es texto libre; hoy se usan 'TRANSFERENCIA' y
    'VENTA_MAYORISTA'. NO crear ni migrar esta tabla desde el código.
    """
    __tablename__ = "inventory_movements"

    id = Column(BigInteger, primary_key=True)
    product_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    movement_type = Column(String(15), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    reason = Column(String(150))
    created_at = Column(DateTime(timezone=True), nullable=False)
    unit_sold_price = Column(Numeric)
    unit_cost_price = Column(Numeric)
    batch_code = Column(String)
    waste_type = Column(String)
    sale_group_id = Column(String)
    origin_warehouse_id = Column(Integer)
    destination_warehouse_id = Column(Integer)
    currency = Column(String)
    exchange_rate = Column(Numeric)
    destination_country = Column(String)