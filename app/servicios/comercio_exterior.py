from __future__ import annotations

from decimal import Decimal

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errores import ErrorDeNegocio
from app.modelo.comercio_exterior import LineaComercioExterior, OperacionComercioExterior
from app.modelo.contadores import ContadorFolio
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.socios_comerciales import SocioComercial
from app.modelo.usuarios import Usuario
from app.servicios.inventario import (
	consumir_lotes,
	costo_consumo_total,
	ingresar_lote,
	round2,
	validar_cantidad_positiva,
)


async def _siguiente_folio(db: AsyncSession, tipo: str) -> str:
	prefijo = "IMP" if tipo == "importacion" else "EXP"
	contador = await db.scalar(
		select(ContadorFolio).where(ContadorFolio.type == prefijo).with_for_update()
	)
	if contador is None:
		# La migración crea la tabla, pero las bases ya migradas pueden no tener
		# todavía sus dos filas iniciales.
		if db.get_bind().dialect.name == "postgresql":
			from sqlalchemy.dialects.postgresql import insert as postgres_insert

			await db.execute(
				postgres_insert(ContadorFolio)
				.values(type=prefijo, last_number=0)
				.on_conflict_do_nothing(index_elements=[ContadorFolio.type])
			)
		else:
			await db.execute(insert(ContadorFolio).values(type=prefijo, last_number=0).prefix_with("OR IGNORE"))
		contador = await db.scalar(
				select(ContadorFolio).where(ContadorFolio.type == prefijo).with_for_update()
			)
	contador.last_number += 1
	await db.flush()
	return f"{prefijo}-{contador.last_number:04d}"


async def _obtener_socio(db: AsyncSession, socio_id: int) -> SocioComercial:
	socio = await db.get(SocioComercial, socio_id)
	if socio is None:
		raise ErrorDeNegocio("Socio comercial no encontrado", 404)
	return socio


async def _obtener_producto(db: AsyncSession, product_id: int) -> Producto:
	producto = await db.get(Producto, product_id)
	if producto is None:
		raise ErrorDeNegocio("Producto no encontrado", 404)
	return producto


async def registrar_operacion(
	db: AsyncSession,
	*,
	fecha,
	tipo: str,
	socio_comercial_id: int,
	incoterm: str | None,
	medio_transporte: str | None,
	tipo_cambio: Decimal,
	notas: str | None,
	lineas: list[dict[str, Decimal | int]],
	responsable: Usuario,
) -> OperacionComercioExterior:
	socio = await _obtener_socio(db, socio_comercial_id)
	productos: list[tuple[Producto, Decimal, Decimal]] = []
	for linea in lineas:
		producto = await _obtener_producto(db, int(linea["producto_id"]))
		cantidad = validar_cantidad_positiva(linea["cantidad"])
		if producto.unit_type == "UNIDAD" and cantidad != cantidad.to_integral_value():
			raise ErrorDeNegocio("La cantidad debe ser un número entero para productos por unidad", 400)
		precio_usd = round2(linea["precio_usd"])
		productos.append((producto, cantidad, precio_usd))

	subtotal_usd = round2(
		sum((cantidad * precio_usd for _, cantidad, precio_usd in productos), Decimal("0"))
	)
	total_usd = subtotal_usd
	total_pen = round2(total_usd * tipo_cambio)
	folio = await _siguiente_folio(db, tipo)
	operacion = OperacionComercioExterior(
		folio=folio,
		date=fecha,
		type=tipo,
		partner_id=socio.id,
		incoterm=incoterm,
		transport=medio_transporte,
		exchange_rate=tipo_cambio,
		subtotal_usd=subtotal_usd,
		total_usd=total_usd,
		total_pen=total_pen,
		notes=notas,
		responsable_id=responsable.id,
	)
	db.add(operacion)
	await db.flush()

	for producto, cantidad, precio_usd in productos:
		subtotal_linea = round2(cantidad * precio_usd)
		if tipo == "importacion":
			costo = round2(precio_usd * tipo_cambio)
			await ingresar_lote(
				db,
				product_id=producto.id,
				cantidad=cantidad,
				origen="importacion",
				responsable_id=responsable.id,
				costo_unitario_soles=costo,
				foreign_partner_id=socio.id,
			)
			cantidad_ledger = cantidad
			costo_ledger = costo
			precio_ledger = round2(producto.sale_price)
		else:
			detalle_fifo = await consumir_lotes(db, product_id=producto.id, cantidad=cantidad)
			cantidad_ledger = -cantidad
			costo_ledger = round2(costo_consumo_total(detalle_fifo) / cantidad)
			precio_ledger = round2(precio_usd * tipo_cambio)

		db.add(
			LineaComercioExterior(
				operation_id=operacion.id,
				product_id=producto.id,
				name=producto.name,
				sku=producto.sku,
				unit_type=producto.unit_type,
				quantity=cantidad,
				price_usd=precio_usd,
				subtotal_usd=subtotal_linea,
			)
		)
		db.add(
			MovimientoInventario(
				product_id=producto.id,
				responsable_id=responsable.id,
				movement_type=tipo,
				quantity=cantidad_ledger,
				unit_sold_price=precio_ledger,
				unit_cost_price=costo_ledger,
				supplier_name=socio.name,
				reason=socio.country,
				folio=folio,
				unit_price_usd=precio_usd,
				exchange_rate=tipo_cambio,
			)
		)
	await db.flush()
	return operacion


async def listar_operaciones(db: AsyncSession) -> list[OperacionComercioExterior]:
	consulta = (
		select(OperacionComercioExterior)
		.options(
			selectinload(OperacionComercioExterior.partner),
			selectinload(OperacionComercioExterior.responsable),
			selectinload(OperacionComercioExterior.lines),
		)
		.order_by(OperacionComercioExterior.date.desc(), OperacionComercioExterior.id.desc())
	)
	return list((await db.scalars(consulta)).all())
