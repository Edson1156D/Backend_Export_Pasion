from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.bd.session import get_db
from app.esquemas.login import LoginRequest
from app.api.v1.user import autenticar_usuario
from app.core.seguridad import crear_token

router = APIRouter()


@router.post("/login")
async def login(datos: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Recibe email, password y role (desde el schema LoginRequest),
    verifica con el crud si son correctos, y responde según el resultado.
    """
    usuario = await autenticar_usuario(db, datos.email, datos.password, datos.role)

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Correo, contraseña o rol incorrectos"
        )
    # El token lleva adentro el id y el rol, para poder identificarlo
    # en futuras peticiones sin volver a consultar la base de datos.
    token = crear_token({"id": usuario.id, "role": usuario.role})
    return {
        "mensaje": "Login exitoso",
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.full_name,
            "email": usuario.email,
            "rol": usuario.role
        }
    }