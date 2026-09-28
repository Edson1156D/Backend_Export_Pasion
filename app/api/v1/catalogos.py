from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.catalogos import CategoriaPublica, ProveedorPublico, SocioComercialPublico
from app.modelo.categorias import Categoria
from app.modelo.proveedores import Proveedor
from app.modelo.socios_comerciales import SocioComercial
from app.modelo.usuarios import Usuario

router = APIRouter(tags=["catalogos"])


@router.get("/categorias", response_model=list[CategoriaPublica])
async def listar_categorias(
    _: Usuario = Depends(requiere_roles("admin", "vendedor", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[Categoria]:
    return (await db.scalars(select(Categoria).order_by(Categoria.id))).all()


@router.get("/proveedores", response_model=list[ProveedorPublico])
async def listar_proveedores(
    _: Usuario = Depends(requiere_roles("admin", "taller")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[Proveedor]:
    return (await db.scalars(select(Proveedor).order_by(Proveedor.id))).all()


@router.get("/comercio-exterior/socios-comerciales", response_model=list[SocioComercialPublico])
async def listar_socios_comerciales(
    _: Usuario = Depends(requiere_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> Sequence[SocioComercialPublico]:
    socios = (await db.scalars(select(SocioComercial).order_by(SocioComercial.id))).all()
    return [SocioComercialPublico(id=socio.id, nombre=socio.name, pais=socio.country) for socio in socios]