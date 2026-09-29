from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere_roles
from app.bd.session import get_db
from app.esquemas.comercio_exterior import (
	LineaOperacionPublica,
	OperacionCrear,
	OperacionPublica,
	ProductoOperacionPublico,
	SocioOperacionPublico,
)
from app.modelo.comercio_exterior import OperacionComercioExterior
from app.modelo.usuarios import Usuario
from app.servicios.comercio_exterior import listar_operaciones, registrar_operacion

router = APIRouter(prefix="/comercio-exterior", tags=["comercio exterior"])


def _operacion_publica(operacion: OperacionComercioExterior) -> OperacionPublica:
	return OperacionPublica(
		id=operacion.id,
		folio=operacion.folio,
		fecha=operacion.date,
		tipo=operacion.type,
		socio_comercial=SocioOperacionPublico(
			id=operacion.partner.id,
			nombre=operacion.partner.name,
			pais=operacion.partner.country,
		),
		incoterm=operacion.incoterm,
		medio_transporte=operacion.transport,
		tipo_cambio=float(operacion.exchange_rate),
		lineas=[
			LineaOperacionPublica(
				producto=ProductoOperacionPublico(
					id=linea.product_id,
					name=linea.name,
					sku=linea.sku,
					unit_type=linea.unit_type,
				),
				cantidad=float(linea.quantity),
				precio_usd=float(linea.price_usd),
				subtotal_usd=float(linea.subtotal_usd),
			)
			for linea in operacion.lines
		],
		subtotal_usd=float(operacion.subtotal_usd),
		total_usd=float(operacion.total_usd),
		total_pen=float(operacion.total_pen),
		responsable=operacion.responsable.full_name,
		notas=operacion.notes,
		created_at=operacion.created_at,
	)


@router.get("/operaciones", response_model=list[OperacionPublica])
async def listar_operaciones_admin(
	_: Usuario = Depends(requiere_roles("admin")),
	db: AsyncSession = Depends(get_db),
) -> Sequence[OperacionPublica]:
	return [_operacion_publica(operacion) for operacion in await listar_operaciones(db)]


@router.post("/operaciones", response_model=OperacionPublica, status_code=status.HTTP_201_CREATED)
async def crear_operacion(
	datos: OperacionCrear,
	usuario: Usuario = Depends(requiere_roles("admin")),
	db: AsyncSession = Depends(get_db),
) -> OperacionPublica:
	operacion = await registrar_operacion(
		db,
		fecha=datos.fecha,
		tipo=datos.tipo,
		socio_comercial_id=datos.socio_comercial_id,
		incoterm=datos.incoterm,
		medio_transporte=datos.medio_transporte,
		tipo_cambio=datos.tipo_cambio,
		notas=datos.notas,
		lineas=[
			{"producto_id": linea.producto_id, "cantidad": linea.cantidad, "precio_usd": linea.precio_usd}
			for linea in datos.lineas
		],
		responsable=usuario,
	)
	await db.commit()
	operaciones = await listar_operaciones(db)
	return _operacion_publica(next(item for item in operaciones if item.id == operacion.id))