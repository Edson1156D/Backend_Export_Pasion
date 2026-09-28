from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.bd.base import Base


class MovimientoInventario(Base):
	__tablename__ = "inventory_movements"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
	responsable_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
	movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
	quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
	reason: Mapped[Optional[str]] = mapped_column(Text)
	unit_sold_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
	unit_cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
	waste_type: Mapped[Optional[str]] = mapped_column(String(100))
	sale_group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales.id", ondelete="RESTRICT"))
	supplier_name: Mapped[Optional[str]] = mapped_column(String(255))
	folio: Mapped[Optional[str]] = mapped_column(String(50))
	unit_price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
	exchange_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

	product = relationship("Producto")
	responsable = relationship("Usuario")
