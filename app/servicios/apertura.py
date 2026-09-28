from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelo.lotes import Lote
from app.modelo.productos import Producto
from app.modelo.usuarios import RolUsuario, Usuario
from app.servicios.inventario import ingresar_lote

EMAIL_SISTEMA = "sistema@internal.invalid"
HASH_SISTEMA = "!cuenta-interna-sin-login!"


async def _obtener_responsable_sistema(db: AsyncSession) -> Usuario:
    usuario = await db.scalar(select(Usuario).where(Usuario.email == EMAIL_SISTEMA))
    if usuario is None:
        usuario = Usuario(
            full_name="Sistema",
            email=EMAIL_SISTEMA,
            hashed_password=HASH_SISTEMA,
            role=RolUsuario.ADMIN.value,
            is_active=True,
        )
        db.add(usuario)
        await db.flush()
    return usuario


async def crear_lotes_apertura(db: AsyncSession) -> list[Lote]:
    responsable = await _obtener_responsable_sistema(db)
    productos = (await db.scalars(select(Producto).where(Producto.current_stock > 0).order_by(Producto.id))).all()
    creados: list[Lote] = []
    for producto in productos:
        cantidad_lotes = await db.scalar(
            select(func.count(Lote.id)).where(Lote.product_id == producto.id)
        )
        if cantidad_lotes:
            continue
        creados.append(
            await ingresar_lote(
                db,
                product_id=producto.id,
                cantidad=producto.current_stock,
                origen="apertura",
                responsable_id=responsable.id,
                costo_unitario_soles=producto.cost_price,
                received_at=producto.created_at,
            )
        )
    await db.flush()
    return creados
