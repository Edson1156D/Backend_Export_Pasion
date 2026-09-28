import enum

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.bd.base import Base


class RolUsuario(str, enum.Enum):
    ADMIN = "ADMIN"
    VENDEDOR = "VENDEDOR"
    TALLER = "TALLER"


class Usuario(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=RolUsuario.VENDEDOR.value, server_default=RolUsuario.VENDEDOR.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_users_email_lower", func.lower(email), unique=True),)
