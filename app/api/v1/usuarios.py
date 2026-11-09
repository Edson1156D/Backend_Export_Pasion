import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.user import obtener_usuario_por_email, obtener_usuario_por_id, pwd_context
from app.bd.session import get_db
from app.core.seguridad import requiere_rol
from app.esquemas.usuarios import UsuarioActualizar, UsuarioCrear, UsuarioOut, usuario_a_out
from app.modelo.movimientos import MovimientoInventario
from app.modelo.usuarios import Usuario
from app.servicios import usuarios_reglas as reglas

solo_admin = requiere_rol("ADMIN")
router = APIRouter(tags=["usuarios"], dependencies=[Depends(solo_admin)])

CORREO_DUPLICADO = "Ya existe un usuario con ese correo"


def _http(error: reglas.ReglaUsuario) -> HTTPException:
    # El front muestra `detail` tal cual, así que siempre es texto.
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


async def _guardar(db: AsyncSession, mensaje_conflicto: str) -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=mensaje_conflicto)


async def _buscar(db: AsyncSession, usuario_id: int) -> Usuario:
    usuario = await obtener_usuario_por_id(db, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.get("/usuarios", response_model=list[UsuarioOut])
async def listar_usuarios(db: AsyncSession = Depends(get_db)):
    filas = (await db.execute(select(Usuario).order_by(Usuario.id))).scalars().all()
    return [usuario_a_out(u) for u in filas]


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
async def crear_usuario(datos: UsuarioCrear, db: AsyncSession = Depends(get_db)):
    try:
        nombre = reglas.validar_nombre(datos.fullName)
        email = reglas.validar_email(datos.email)
        password = reglas.validar_password(datos.password)
    except reglas.ReglaUsuario as error:
        raise _http(error)

    if await obtener_usuario_por_email(db, email):
        raise HTTPException(status_code=409, detail=CORREO_DUPLICADO)

    usuario = Usuario(
        full_name=nombre,
        email=email,
        # bcrypt es lento a propósito: se hace en otro hilo para no frenar la API
        hashed_password=await asyncio.to_thread(pwd_context.hash, password),
        role=datos.role.upper(),
        is_active=datos.isActive,
    )
    db.add(usuario)
    await _guardar(db, CORREO_DUPLICADO)
    await db.refresh(usuario)
    return usuario_a_out(usuario)


@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut)
async def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizar,
    actual: dict = Depends(solo_admin),
    db: AsyncSession = Depends(get_db),
):
    usuario = await _buscar(db, usuario_id)

    try:
        nombre = reglas.validar_nombre(datos.fullName)
        email = reglas.validar_email(datos.email)
        password = reglas.validar_password(datos.password) if datos.password else None
        reglas.validar_edicion_propia(
            es_propio=actual.get("id") == usuario.id,
            rol_actual=reglas.rol_para_front(usuario.role),
            nuevo_rol=datos.role,
            nuevo_activo=datos.isActive,
        )
    except reglas.ReglaUsuario as error:
        raise _http(error)

    otro = await obtener_usuario_por_email(db, email)
    if otro is not None and otro.id != usuario.id:
        raise HTTPException(status_code=409, detail=CORREO_DUPLICADO)

    usuario.full_name = nombre
    usuario.email = email
    usuario.role = datos.role.upper()
    usuario.is_active = datos.isActive
    if password:
        usuario.hashed_password = await asyncio.to_thread(pwd_context.hash, password)

    await _guardar(db, CORREO_DUPLICADO)
    await db.refresh(usuario)
    return usuario_a_out(usuario)


@router.delete("/usuarios/{usuario_id}", status_code=204)
async def eliminar_usuario(
    usuario_id: int,
    actual: dict = Depends(solo_admin),
    db: AsyncSession = Depends(get_db),
):
    usuario = await _buscar(db, usuario_id)

    movimientos = (
        await db.execute(
            select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.user_id == usuario.id)
        )
    ).scalar_one()

    try:
        reglas.validar_eliminacion(es_propio=actual.get("id") == usuario.id, movimientos=movimientos)
    except reglas.ReglaUsuario as error:
        raise _http(error)

    await db.delete(usuario)
    await _guardar(db, "No se puede eliminar: el usuario está en uso; desactívalo en su lugar")