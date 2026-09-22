from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from app.modelo.usuarios import Usuario

# Configura passlib para verificar contraseñas con bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def obtener_usuario_por_email(db: AsyncSession, email: str) -> Usuario | None:
    """Busca un usuario en la base de datos por su email."""
    resultado = await db.execute(select(Usuario).where(Usuario.email == email))
    return resultado.scalar_one_or_none()


def verificar_password(password_texto_plano: str, password_hasheado: str) -> bool:
    """Compara la contraseña escrita por el usuario contra la guardada (hasheada)."""
    return pwd_context.verify(password_texto_plano, password_hasheado)


async def autenticar_usuario(db: AsyncSession, email: str, password: str, role: str) -> Usuario | None:
    """
    Verifica que:
    1. El usuario exista
    2. La contraseña sea correcta
    3. El rol seleccionado coincida con el rol real del usuario

    Devuelve el usuario si todo es correcto, o None si algo falla.
    """
    usuario = await obtener_usuario_por_email(db, email)

    if not usuario:
        return None

    if not verificar_password(password, usuario.hashed_password):
        return None

    if usuario.role != role:
        return None

    return usuario