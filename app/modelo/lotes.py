from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.bd.base import Base


class Lote(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    origin: Mapped[str] = mapped_column(String(30), nullable=False)
    initial_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    available_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost_pen: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    foreign_partner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("foreign_partners.id", ondelete="RESTRICT"))
    responsable_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product = relationship("Producto")
    supplier = relationship("Proveedor")
    foreign_partner = relationship("SocioComercial")
    responsable = relationship("Usuario")