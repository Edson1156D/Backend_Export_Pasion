from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.session import get_db
from app.core.seguridad import leer_token
from app.modelo.usuarios import Usuario

security = HTTPBearer()


async def usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    payload = leer_token(credenciales.credentials)
    if payload is None or payload.get("id") is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado, vuelve a iniciar sesión")

    usuario = await db.scalar(select(Usuario).where(Usuario.id == payload["id"]))
    if usuario is None or not usuario.is_active:
        raise HTTPException(status_code=401, detail="Token inválido o expirado, vuelve a iniciar sesión")
    return usuario


def requiere_roles(*roles: str) -> Callable:
    roles_normalizados = {role.upper() for role in roles}

    async def verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.role.upper() not in roles_normalizados:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para acceder a esto")
        return usuario

    return verificar