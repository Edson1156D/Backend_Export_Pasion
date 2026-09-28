from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.entradas import CompraCrear, EntradaCrear, EntradaPublica
from app.esquemas.mermas import MermaCrear, MermaPublica
from app.modelo.entradas import EntradaStock
from app.modelo.mermas import Merma
from app.modelo.usuarios import Usuario
from app.servicios.operaciones_inventario import (
    registrar_compra,
    registrar_entrada_produccion,
    registrar_merma,
)

router = APIRouter(tags=["inventario"])


def _entrada_publica(entrada: EntradaStock) -> EntradaPublica:
    return EntradaPublica(
        id=entrada.id,
        product_id=entrada.product_id,
        quantity=float(entrada.quantity),
        created_at=entrada.created_at,
        proveedor_id=entrada.supplier_id,
        responsable=entrada.responsable.full_name if entrada.responsable else None,
    )


def _merma_publica(merma: Merma) -> MermaPublica:
    return MermaPublica(
        id=merma.id,
        product_id=merma.product_id,
        quantity=float(merma.quantity),
        motivo=merma.reason_code,
        detalle=merma.detail,
        responsable=merma.responsable.full_name,
        created_at=merma.created_at,
    )


@router.get("/entradas", response_model=list[EntradaPublica])
async def listar_entradas(
    _: Usuario = Depends(requiere_roles("admin", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[EntradaPublica]:
    entradas = (
        await db.scalars(
            select(EntradaStock)
            .options(selectinload(EntradaStock.responsable))
            .order_by(EntradaStock.created_at.desc(), EntradaStock.id.desc())
        )
    ).all()
    return [_entrada_publica(entrada) for entrada in entradas]


@router.post("/entradas", response_model=EntradaPublica, status_code=status.HTTP_201_CREATED)
async def crear_entrada(
    datos: EntradaCrear,
    usuario: Usuario = Depends(requiere_roles("taller")),
    db: AsyncSession = Depends(get_db),
) -> EntradaPublica:
    entrada = await registrar_entrada_produccion(
        db,
        product_id=datos.product_id,
        cantidad=datos.quantity,
        responsable=usuario,
        notas=datos.notas,
    )
    await db.commit()
    await db.refresh(entrada, ["responsable"])
    return _entrada_publica(entrada)


@router.post("/compras", response_model=EntradaPublica, status_code=status.HTTP_201_CREATED)
async def crear_compra(
    datos: CompraCrear,
    usuario: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> EntradaPublica:
    entrada = await registrar_compra(
        db,
        product_id=datos.product_id,
        cantidad=datos.quantity,
        proveedor_id=datos.proveedor_id,
        costo_unitario=datos.costo_unitario_soles,
        responsable=usuario,
        notas=datos.notas,
    )
    await db.commit()
    await db.refresh(entrada, ["responsable"])
    return _entrada_publica(entrada)


@router.get("/mermas", response_model=list[MermaPublica])
async def listar_mermas(
    _: Usuario = Depends(requiere_roles("admin", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[MermaPublica]:
    mermas = (
        await db.scalars(
            select(Merma)
            .options(selectinload(Merma.responsable))
            .order_by(Merma.created_at.desc(), Merma.id.desc())
        )
    ).all()
    return [_merma_publica(merma) for merma in mermas]


@router.post("/mermas", response_model=MermaPublica, status_code=status.HTTP_201_CREATED)
async def crear_merma(
    datos: MermaCrear,
    usuario: Usuario = Depends(requiere_roles("taller")),
    db: AsyncSession = Depends(get_db),
) -> MermaPublica:
    merma = await registrar_merma(
        db,
        product_id=datos.product_id,
        cantidad=datos.quantity,
        motivo=datos.motivo,
        detalle=datos.detalle,
        responsable=usuario,
    )
    await db.commit()
    await db.refresh(merma, ["responsable"])
    return _merma_publica(merma)