from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.esquemas.login import UsuarioSesion
from app.modelo.usuarios import Usuario

# Configura passlib para verificar contraseñas con bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLES_VALIDOS = {"admin", "vendedor", "taller"}


async def obtener_usuario_por_email(db: AsyncSession, email: str) -> Usuario | None:
    """Busca un usuario por email, sin distinguir mayúsculas de minúsculas."""
    resultado = await db.execute(
        select(Usuario).where(func.lower(Usuario.email) == email.strip().lower())
    )
    return resultado.scalar_one_or_none()


async def obtener_usuario_por_id(db: AsyncSession, usuario_id: int) -> Usuario | None:
    """Busca un usuario por su id."""
    resultado = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    return resultado.scalar_one_or_none()


def verificar_password(password_texto_plano: str, password_hasheado: str) -> bool:
    """Compara la contraseña escrita por el usuario contra la guardada (hasheada)."""
    return pwd_context.verify(password_texto_plano, password_hasheado)


async def autenticar_usuario(db: AsyncSession, email: str, password: str) -> Usuario | None:
    """
    Verifica que el usuario exista y que la contraseña sea correcta.
    Devuelve el usuario, o None si algo falla. (El rol lo define la BD.)
    """
    usuario = await obtener_usuario_por_email(db, email)

    if not usuario:
        return None

    if not verificar_password(password, usuario.hashed_password):
        return None

    return usuario


def a_usuario_sesion(usuario: Usuario) -> UsuarioSesion:
    """
    Convierte el usuario de la BD al formato del front:
    id como texto y rol en minúsculas ("ADMIN" -> "admin").
    """
    rol = (usuario.role or "").strip().lower()
    if rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=403, detail="El usuario tiene un rol no válido")

    return UsuarioSesion(id=str(usuario.id), nombre=usuario.full_name, rol=rol)
