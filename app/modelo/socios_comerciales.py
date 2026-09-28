from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.bd.base import Base


class SocioComercial(Base):
    __tablename__ = "foreign_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)