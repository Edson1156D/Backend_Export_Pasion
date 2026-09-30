from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.core.seguridad import pwd_context
from app.esquemas.usuarios import RolAPI, UsuarioActualizar, UsuarioCrear, UsuarioPublico
from app.modelo.entradas import EntradaStock
from app.modelo.lotes import Lote
from app.modelo.mermas import Merma
from app.modelo.movimientos import MovimientoInventario
from app.modelo.usuarios import RolUsuario, Usuario
from app.modelo.ventas import Venta
from app.modelo.comercio_exterior import OperacionComercioExterior

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

ROL_BD: dict[RolAPI, str] = {
    "admin": RolUsuario.ADMIN.value,
    "vendedor": RolUsuario.VENDEDOR.value,
    "taller": RolUsuario.TALLER.value,
}


def _publico(usuario: Usuario) -> UsuarioPublico:
    return UsuarioPublico(
        id=str(usuario.id),
        full_name=usuario.full_name,
        email=usuario.email,
        role=usuario.role.lower(),
        is_active=usuario.is_active,
        created_at=usuario.created_at,
    )


async def _buscar_por_email(db: AsyncSession, email: str, excluir_id: int | None = None) -> Usuario | None:
    consulta = select(Usuario).where(func.lower(Usuario.email) == email.lower())
    if excluir_id is not None:
        consulta = consulta.where(Usuario.id != excluir_id)
    return await db.scalar(consulta)


async def _hay_registros_asociados(db: AsyncSession, usuario_id: int) -> bool:
    relaciones = (
        (Venta, Venta.responsable_id),
        (MovimientoInventario, MovimientoInventario.responsable_id),
        (EntradaStock, EntradaStock.responsable_id),
        (Lote, Lote.responsable_id),
        (Merma, Merma.responsable_id),
        (OperacionComercioExterior, OperacionComercioExterior.responsable_id),
    )
    for modelo, columna in relaciones:
        if await db.scalar(select(modelo.id).where(columna == usuario_id).limit(1)) is not None:
            return True
    return False


async def _es_ultimo_admin_activo(db: AsyncSession, usuario: Usuario, nuevo_rol: str, nuevo_activo: bool) -> bool:
    deja_de_ser_admin = usuario.role == RolUsuario.ADMIN.value and (
        nuevo_rol != RolUsuario.ADMIN.value or not nuevo_activo
    )
    if not deja_de_ser_admin:
        return False
    cantidad = await db.scalar(
        select(func.count(Usuario.id)).where(
            Usuario.role == RolUsuario.ADMIN.value,
            Usuario.is_active.is_(True),
        )
    )
    return cantidad <= 1


@router.get("", response_model=list[UsuarioPublico], summary="Listar usuarios", description="Devuelve todos los usuarios registrados, ordenados del más reciente al más antiguo.", responses={401: {"description": 'Autenticación requerida. Formato: {"detail": "texto"}.'}, 403: {"description": 'Se requiere rol admin. Formato: {"detail": "texto"}.'}})
async def listar_usuarios(
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[UsuarioPublico]:
    usuarios = (await db.scalars(select(Usuario).order_by(Usuario.created_at.desc(), Usuario.id.desc()))).all()
    return [_publico(usuario) for usuario in usuarios]


@router.post("", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED, summary="Crear usuario", description="Registra un usuario con rol, credenciales y estado inicial.", responses={409: {"description": 'Email duplicado. Formato: {"detail": "Ya existe un usuario con ese email"}.'}, 422: {"description": 'Datos inválidos. Formato: {"detail": "texto"}.'}})
async def crear_usuario(
    datos: UsuarioCrear,
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> UsuarioPublico:
    email = str(datos.email).lower()
    if await _buscar_por_email(db, email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email")
    usuario = Usuario(
        full_name=datos.full_name,
        email=email,
        hashed_password=pwd_context.hash(datos.password),
        role=ROL_BD[datos.role],
        is_active=datos.is_active,
    )
    db.add(usuario)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email") from None
    await db.commit()
    return _publico(usuario)


@router.put("/{usuario_id}", response_model=UsuarioPublico, summary="Actualizar usuario", description="Actualiza los datos y permisos de un usuario existente.", responses={404: {"description": 'Usuario inexistente. Formato: {"detail": "Usuario no encontrado"}.'}, 409: {"description": 'Conflicto de email o administrador activo. Formato: {"detail": "texto"}.'}, 422: {"description": 'Datos inválidos. Formato: {"detail": "texto"}.'}})
async def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizar,
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> UsuarioPublico:
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if await _buscar_por_email(db, str(datos.email).lower(), usuario_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email")
    nuevo_rol = ROL_BD[datos.role]
    if await _es_ultimo_admin_activo(db, usuario, nuevo_rol, datos.is_active):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Debe quedar al menos un administrador activo")

    usuario.full_name = datos.full_name
    usuario.email = str(datos.email).lower()
    usuario.role = nuevo_rol
    usuario.is_active = datos.is_active
    if datos.password:
        usuario.hashed_password = pwd_context.hash(datos.password)
    await db.flush()
    await db.commit()
    return _publico(usuario)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar usuario", description="Elimina un usuario que no tenga registros asociados ni viole las reglas de administradores.", responses={404: {"description": 'Usuario inexistente. Formato: {"detail": "Usuario no encontrado"}.'}, 409: {"description": 'Eliminación no permitida. Formato: {"detail": "texto"}.'}})
async def eliminar_usuario(
    usuario_id: int,
    actual: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if actual.id == usuario.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes eliminar tu propio usuario")
    if await _es_ultimo_admin_activo(db, usuario, "ELIMINAR", False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Debe quedar al menos un administrador activo")
    if await _hay_registros_asociados(db, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: tiene registros asociados. Desactívalo en su lugar.",
        )
    await db.delete(usuario)
    await db.commit()