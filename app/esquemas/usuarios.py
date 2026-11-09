from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.servicios.usuarios_reglas import rol_para_front

Rol = Literal["admin", "vendedor", "taller"]


class UsuarioOut(BaseModel):
    """Igual a `User` en frontend/src/features/usuarios/types.ts."""
    id: str
    fullName: str
    email: str
    role: Rol
    isActive: bool
    createdAt: datetime | None


class UsuarioCrear(BaseModel):
    """Solo comprueba tipos; las reglas de negocio están en servicios/usuarios_reglas.py."""
    fullName: str
    email: str
    role: Rol
    password: str
    isActive: bool = True


class UsuarioActualizar(BaseModel):
    fullName: str
    email: str
    role: Rol
    isActive: bool
    password: str | None = None      # vacío o ausente = no cambiar la contraseña


def usuario_a_out(u) -> UsuarioOut:
    return UsuarioOut(
        id=str(u.id),
        fullName=u.full_name,
        email=u.email,
        role=rol_para_front(u.role),
        isActive=u.is_active is not False,    # NULL se trata como activo
        createdAt=u.created_at,
    )