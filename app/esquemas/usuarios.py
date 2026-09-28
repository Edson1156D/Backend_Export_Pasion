from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.esquemas.comun import CamelModel

RolAPI = Literal["admin", "vendedor", "taller"]


class UsuarioPublico(CamelModel):
    id: str
    full_name: str
    email: EmailStr
    role: RolAPI
    is_active: bool
    created_at: datetime


class UsuarioCrear(CamelModel):
    full_name: str = Field(min_length=3)
    email: EmailStr
    role: RolAPI
    password: str = Field(min_length=6)
    is_active: bool = True


class UsuarioActualizar(CamelModel):
    full_name: str = Field(min_length=3)
    email: EmailStr
    role: RolAPI
    is_active: bool
    password: str | None = None
