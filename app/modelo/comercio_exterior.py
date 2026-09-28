from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.bd.base import Base


class OperacionComercioExterior(Base):
    __tablename__ = "foreign_trade_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    partner_id: Mapped[int] = mapped_column(ForeignKey("foreign_partners.id", ondelete="RESTRICT"), nullable=False)
    incoterm: Mapped[Optional[str]] = mapped_column(String(10))
    transport: Mapped[Optional[str]] = mapped_column(String(20))
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    subtotal_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_pen: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    responsable_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    partner = relationship("SocioComercial")
    responsable = relationship("Usuario")
    lines = relationship("LineaComercioExterior", back_populates="operation")


class LineaComercioExterior(Base):
    __tablename__ = "foreign_trade_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("foreign_trade_operations.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    operation = relationship("OperacionComercioExterior", back_populates="lines")
    product = relationship("Producto")