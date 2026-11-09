from typing import Literal

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Lo que envía el front al iniciar sesión (el rol sale de la base de datos)."""
    email: str
    password: str


class UsuarioSesion(BaseModel):
    """Usuario tal como lo espera el front (frontend/src/types/auth.ts)."""
    id: str
    nombre: str
    rol: Literal["admin", "vendedor", "taller"]


class LoginResponse(BaseModel):
    """Respuesta de POST /auth/login (frontend/.../auth.service.ts)."""
    accessToken: str
    tokenType: str = "bearer"
    usuario: UsuarioSesion
