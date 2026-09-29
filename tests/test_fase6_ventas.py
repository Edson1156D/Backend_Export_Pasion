import asyncio
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
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.usuarios import RolUsuario, Usuario
from app.modelo.ventas import DetalleVenta, Venta
from app.servicios.apertura import crear_lotes_apertura


@pytest_asyncio.fixture
async def cliente_fase6() -> AsyncClient:
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
                Usuario(full_name="Admin", email="admin@fase6.pe", hashed_password=pwd_context.hash("admin123"), role=RolUsuario.ADMIN.value),
                Usuario(full_name="Vendedor", email="vendedor@fase6.pe", hashed_password=pwd_context.hash("vendedor123"), role=RolUsuario.VENDEDOR.value),
                Usuario(full_name="Otro vendedor", email="otro@fase6.pe", hashed_password=pwd_context.hash("otro123"), role=RolUsuario.VENDEDOR.value),
                Categoria(id=1, name="Minerales"),
                Producto(id=1, category_id=1, sku="MIN-001", name="Mineral", unit_type="UNIDAD", sale_price=30, cost_price=7, current_stock=2, min_stock_alert=1, is_active=True),
                Producto(id=2, category_id=1, sku="MIN-002", name="Piedra", unit_type="KILOGRAMO", sale_price=45, cost_price=10, current_stock=1, min_stock_alert=1, is_active=True),
            ]
        )
        await db.commit()
        await crear_lotes_apertura(db)
        await db.commit()

    async def override_get_db():
        async with sesiones() as db:
            try:
                yield db
            finally:
                await db.rollback()

    app.dependency_overrides[get_db] = override_get_db
    app.state.fase6_sessionmaker = sesiones
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        yield cliente
    app.dependency_overrides.clear()
    del app.state.fase6_sessionmaker
    await engine.dispose()


def _token(usuario_id: int, rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token({'id': str(usuario_id), 'role': rol})}"}


@pytest.mark.asyncio
async def test_venta_recalcula_snapshot_fifo_y_ledger(cliente_fase6: AsyncClient) -> None:
    respuesta = await cliente_fase6.post(
        "/api/v1/ventas",
        json={
            "items": [{"productId": 1, "quantity": 1, "name": "falso", "unitPrice": 999}],
            "tipoVenta": "tienda",
            "metodoPago": "efectivo",
            "pagoCon": 40,
            "vuelto": 999,
        },
        headers=_token(2, "vendedor"),
    )
    assert respuesta.status_code == 201
    venta = respuesta.json()
    assert venta["folio"] == "BLT-0001"
    assert venta["items"][0]["name"] == "Mineral"
    assert venta["items"][0]["unitPrice"] == 30.0
    assert venta["subtotal"] == venta["total"] == 30.0
    assert venta["pagoCon"] == 40.0
    assert venta["vuelto"] == 10.0

    async with app.state.fase6_sessionmaker() as db:
        producto = await db.get(Producto, 1)
        item = await db.scalar(select(DetalleVenta).where(DetalleVenta.sale_id == 1))
        movimiento = await db.scalar(select(MovimientoInventario).where(MovimientoInventario.sale_group_id == 1))
        assert producto.current_stock == Decimal("1.00")
        assert item.unit_price == Decimal("30.00")
        assert movimiento.quantity == Decimal("-1.00")
        assert movimiento.unit_cost_price == Decimal("7.00")


@pytest.mark.asyncio
async def test_venta_es_atomica_y_listados_filtran_por_usuario(cliente_fase6: AsyncClient) -> None:
    respuesta = await cliente_fase6.post(
        "/api/v1/ventas",
        json={
            "items": [
                {"productId": 1, "quantity": 1},
                {"productId": 2, "quantity": 2},
            ],
            "tipoVenta": "digital",
            "metodoPago": "billetera-digital",
        },
        headers=_token(2, "vendedor"),
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Stock insuficiente: hay 1.00 y se requieren 2.00"

    mis_ventas = await cliente_fase6.get("/api/v1/ventas/mias", headers=_token(2, "vendedor"))
    assert mis_ventas.status_code == 200
    assert mis_ventas.json() == []
    todas = await cliente_fase6.get("/api/v1/ventas", headers=_token(1, "admin"))
    assert todas.status_code == 200
    assert todas.json() == []
    assert (await cliente_fase6.get("/api/v1/ventas", headers=_token(2, "vendedor"))).status_code == 403

    async with app.state.fase6_sessionmaker() as db:
        assert (await db.scalars(select(Venta))).all() == []
        assert (await db.scalars(select(MovimientoInventario))).all() == []


@pytest.mark.skip(reason="SQLite ignora SELECT FOR UPDATE; ejecutar esta prueba contra PostgreSQL")
@pytest.mark.asyncio
async def test_dos_ventas_simultaneas_del_ultimo_stock_solo_una_gana(cliente_fase6: AsyncClient) -> None:
    async def vender(usuario_id: int) -> int:
        respuesta = await cliente_fase6.post(
            "/api/v1/ventas",
            json={
                "items": [{"productId": 1, "quantity": 2}],
                "tipoVenta": "tienda",
                "metodoPago": "billetera-digital",
            },
            headers=_token(usuario_id, "vendedor"),
        )
        return respuesta.status_code

    estados = await asyncio.gather(vender(2), vender(3))
    assert sorted(estados) == [201, 409]