from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.bd.base import Base


class ContadorFolio(Base):
    __tablename__ = "foreign_trade_counters"

    type: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)