from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.user import (
    a_usuario_sesion,
    autenticar_usuario,
    obtener_usuario_por_id,
)
from app.bd.session import get_db
from app.core.seguridad import crear_token, obtener_usuario_actual
from app.esquemas.login import LoginRequest, LoginResponse, UsuarioSesion

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(datos: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Valida email y contraseña y devuelve el token JWT con el usuario."""
    usuario = await autenticar_usuario(db, datos.email, datos.password)

    if not usuario:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    # Se revisa DESPUÉS de la contraseña para no revelar si una cuenta existe.
    if not usuario.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    sesion = a_usuario_sesion(usuario)
    token = crear_token({"id": usuario.id, "role": usuario.role})
    return LoginResponse(accessToken=token, usuario=sesion)


@router.get("/me", response_model=UsuarioSesion)
async def me(
    token_datos: dict = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve el usuario del token. El front lo usa para validar la sesión al cargar."""
    usuario = await obtener_usuario_por_id(db, token_datos.get("id"))

    # Si ya no existe o fue desactivado, la sesión deja de ser válida.
    if not usuario or not usuario.is_active:
        raise HTTPException(status_code=401, detail="Sesión no válida, vuelve a iniciar sesión")

    return a_usuario_sesion(usuario)
