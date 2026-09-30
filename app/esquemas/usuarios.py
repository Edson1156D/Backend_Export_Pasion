from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.esquemas.comun import CamelModel

RolAPI = Literal["admin", "vendedor", "taller"]


class UsuarioPublico(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"id": "7", "fullName": "Ana Torres", "email": "ana@importexportpasion.com", "role": "admin", "isActive": True, "createdAt": "2026-09-29T15:30:00Z"}]}}

    id: str
    full_name: str
    email: EmailStr
    role: RolAPI
    is_active: bool
    created_at: datetime


class UsuarioCrear(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"fullName": "Ana Torres", "email": "ana@importexportpasion.com", "role": "admin", "password": "secreto123", "isActive": True}]}}

    full_name: str = Field(min_length=3)
    email: EmailStr
    role: RolAPI
    password: str = Field(min_length=6)
    is_active: bool = True


class UsuarioActualizar(CamelModel):
    model_config = {"json_schema_extra": {"examples": [{"fullName": "Ana Torres", "email": "ana@importexportpasion.com", "role": "vendedor", "isActive": True, "password": "nueva-clave"}]}}

    full_name: str = Field(min_length=3)
    email: EmailStr
    role: RolAPI
    is_active: bool
    password: str | None = None
