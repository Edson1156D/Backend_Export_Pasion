from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import usuario_actual
from app.api.v1.user import autenticar_usuario
from app.bd.session import get_db
from app.core.seguridad import crear_token
from app.esquemas.login import LoginRequest
from app.modelo.usuarios import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


def usuario_respuesta(usuario: Usuario) -> dict[str, str]:
    return {"id": str(usuario.id), "nombre": usuario.full_name, "email": usuario.email, "rol": usuario.role.lower()}


@router.post("/login")
async def login(datos: LoginRequest, db: AsyncSession = Depends(get_db)):
    usuario = await autenticar_usuario(db, datos.email.lower(), datos.password)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos")
    if not usuario.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu cuenta está inactiva. Contactá a un administrador.")
    return {"accessToken": crear_token({"id": usuario.id, "role": usuario.role}), "tokenType": "bearer", "usuario": usuario_respuesta(usuario)}


@router.get("/me")
async def me(usuario: Usuario = Depends(usuario_actual)):
    return usuario_respuesta(usuario)