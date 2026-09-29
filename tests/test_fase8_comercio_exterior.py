from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.bd.base import Base
from app.core.seguridad import crear_token, pwd_context
from app.main import app
from app.modelo.categorias import Categoria
from app.modelo.comercio_exterior import LineaComercioExterior, OperacionComercioExterior
from app.modelo.lotes import Lote
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.socios_comerciales import SocioComercial
from app.modelo.usuarios import RolUsuario, Usuario
from app.servicios.inventario import ingresar_lote


@pytest_asyncio.fixture
async def cliente_fase8() -> AsyncClient:
	engine = create_async_engine(
		"sqlite+aiosqlite://",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)
	sesiones = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
	async with engine.begin() as conexion:
		await conexion.run_sync(Base.metadata.create_all)
	async with sesiones() as db:
		db.add_all(
			[
				Usuario(full_name="Admin", email="admin@fase8.pe", hashed_password=pwd_context.hash("admin123"), role=RolUsuario.ADMIN.value),
				Usuario(full_name="Vendedor", email="vendedor@fase8.pe", hashed_password=pwd_context.hash("vendedor123"), role=RolUsuario.VENDEDOR.value),
				Categoria(id=1, name="Minerales"),
				Producto(id=1, category_id=1, sku="MIN-001", name="Mineral", unit_type="KILOGRAMO", sale_price=30, cost_price=0, current_stock=0, min_stock_alert=1, is_active=True),
				Producto(id=2, category_id=1, sku="MIN-002", name="Piedra", unit_type="UNIDAD", sale_price=45, cost_price=10, current_stock=0, min_stock_alert=1, is_active=True),
				SocioComercial(id=1, name="Jade Trade LLC", country="Estados Unidos"),
			]
		)
		await db.commit()
		admin = await db.scalar(select(Usuario).where(Usuario.email == "admin@fase8.pe"))
		await ingresar_lote(db, product_id=2, cantidad=Decimal("5"), origen="apertura", responsable_id=admin.id, costo_unitario_soles=Decimal("10"))
		await db.commit()

	async def override_get_db():
		async with sesiones() as db:
			try:
				yield db
			finally:
				await db.rollback()

	app.dependency_overrides[get_db] = override_get_db
	app.state.fase8_sessionmaker = sesiones
	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
		yield cliente
	app.dependency_overrides.clear()
	del app.state.fase8_sessionmaker
	await engine.dispose()


def _token(usuario_id: int, rol: str) -> dict[str, str]:
	return {"Authorization": f"Bearer {crear_token({'id': str(usuario_id), 'role': rol})}"}


@pytest.mark.asyncio
async def test_importacion_crea_lote_ledger_y_calcula_totales(cliente_fase8: AsyncClient) -> None:
	respuesta = await cliente_fase8.post(
		"/api/v1/comercio-exterior/operaciones",
		json={
			"fecha": "2026-09-28",
			"tipo": "importacion",
			"socioComercialId": 1,
			"tipoCambio": 3.75,
			"lineas": [{"productoId": 1, "cantidad": 2.5, "precioUSD": 10}],
			"responsable": "No confiar en el body",
		},
		headers=_token(1, "admin"),
	)

	assert respuesta.status_code == 201, respuesta.text
	operacion = respuesta.json()
	assert operacion["folio"] == "IMP-0001"
	assert operacion["subtotalUSD"] == 25.0
	assert operacion["totalUSD"] == 25.0
	assert operacion["totalPEN"] == 93.75
	assert operacion["responsable"] == "Admin"
	assert isinstance(operacion["lineas"][0]["subtotalUSD"], float)

	async with app.state.fase8_sessionmaker() as db:
		lote = await db.scalar(select(Lote).where(Lote.product_id == 1))
		movimiento = await db.scalar(select(MovimientoInventario).where(MovimientoInventario.folio == "IMP-0001"))
		assert lote.origin == "importacion"
		assert lote.foreign_partner_id == 1
		assert lote.unit_cost_pen == Decimal("37.50")
		assert movimiento.quantity == Decimal("2.50")
		assert movimiento.unit_sold_price == Decimal("30.00")
		assert movimiento.unit_cost_price == Decimal("37.50")
		assert movimiento.supplier_name == "Jade Trade LLC"
		assert movimiento.reason == "Estados Unidos"


@pytest.mark.asyncio
async def test_exportacion_consumo_fifo_y_ledger(cliente_fase8: AsyncClient) -> None:
	respuesta = await cliente_fase8.post(
		"/api/v1/comercio-exterior/operaciones",
		json={
			"fecha": "2026-09-28",
			"tipo": "exportacion",
			"socioComercialId": 1,
			"tipoCambio": 3.8,
			"incoterm": "FOB",
			"medioTransporte": "aereo",
			"lineas": [{"productoId": 2, "cantidad": 3, "precioUSD": 12}],
		},
		headers=_token(1, "admin"),
	)

	assert respuesta.status_code == 201
	assert respuesta.json()["folio"] == "EXP-0001"
	assert respuesta.json()["totalPEN"] == 136.8
	async with app.state.fase8_sessionmaker() as db:
		producto = await db.get(Producto, 2)
		movimiento = await db.scalar(select(MovimientoInventario).where(MovimientoInventario.folio == "EXP-0001"))
		assert producto.current_stock == Decimal("2.00")
		assert movimiento.quantity == Decimal("-3.00")
		assert movimiento.unit_sold_price == Decimal("45.60")
		assert movimiento.unit_cost_price == Decimal("10.00")


@pytest.mark.asyncio
async def test_exportacion_insuficiente_es_atomica_y_solo_admin(cliente_fase8: AsyncClient) -> None:
	respuesta = await cliente_fase8.post(
		"/api/v1/comercio-exterior/operaciones",
		json={
			"fecha": "2026-09-28",
			"tipo": "exportacion",
			"socioComercialId": 1,
			"tipoCambio": 3.8,
			"lineas": [{"productoId": 2, "cantidad": 6, "precioUSD": 12}],
		},
		headers=_token(1, "admin"),
	)
	assert respuesta.status_code == 409
	assert respuesta.json()["detail"] == "Stock insuficiente: hay 5.00 y se requieren 6.00"
	assert (await cliente_fase8.get("/api/v1/comercio-exterior/operaciones", headers=_token(1, "admin"))).json() == []
	assert (await cliente_fase8.get("/api/v1/comercio-exterior/operaciones", headers=_token(2, "vendedor"))).status_code == 403
	async with app.state.fase8_sessionmaker() as db:
		assert (await db.scalar(select(Producto).where(Producto.id == 2))).current_stock == Decimal("5.00")
		assert (await db.scalars(select(MovimientoInventario))).all() == []


@pytest.mark.asyncio
async def test_folios_son_independientes_por_tipo(cliente_fase8: AsyncClient) -> None:
	base = {"fecha": "2026-09-28", "socioComercialId": 1, "tipoCambio": 3.75, "lineas": [{"productoId": 1, "cantidad": 1, "precioUSD": 1}]}
	for tipo, folio in (("importacion", "IMP-0001"), ("importacion", "IMP-0002"), ("exportacion", "EXP-0001")):
		respuesta = await cliente_fase8.post(
			"/api/v1/comercio-exterior/operaciones",
			json={**base, "tipo": tipo},
			headers=_token(1, "admin"),
		)
		assert respuesta.status_code == 201
		assert respuesta.json()["folio"] == folio


@pytest.mark.skip(reason="SQLite ignora SELECT FOR UPDATE; ejecutar contra PostgreSQL")
@pytest.mark.asyncio
async def test_folios_no_se_dupliquen_bajo_concurrencia(cliente_fase8: AsyncClient) -> None:
	# La prueba se habilita en la suite PostgreSQL, donde el contador queda bloqueado por fila.
	import asyncio

	base = {"fecha": "2026-09-28", "tipo": "importacion", "socioComercialId": 1, "tipoCambio": 3.75, "lineas": [{"productoId": 1, "cantidad": 1, "precioUSD": 1}]}
	respuestas = await asyncio.gather(
		*(cliente_fase8.post("/api/v1/comercio-exterior/operaciones", json=base, headers=_token(1, "admin")) for _ in range(4))
	)
	assert sorted(respuesta.json()["folio"] for respuesta in respuestas) == ["IMP-0001", "IMP-0002", "IMP-0003", "IMP-0004"]