from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.bd.base import Base


class Producto(Base):
	__tablename__ = "products"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
	sku: Mapped[str] = mapped_column(String(50), nullable=False)
	name: Mapped[str] = mapped_column(String(150), nullable=False)
	unit_type: Mapped[str] = mapped_column(String(20), nullable=False)
	sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
	cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
	current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
	min_stock_alert: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
	is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

	category = relationship("Categoria")

	__table_args__ = (Index("ix_products_sku_lower", func.lower(sku), unique=True),)
