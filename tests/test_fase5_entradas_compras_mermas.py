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
from app.modelo.entradas import EntradaStock
from app.modelo.mermas import Merma
from app.modelo.movimientos import MovimientoInventario
from app.modelo.productos import Producto
from app.modelo.proveedores import Proveedor
from app.modelo.usuarios import RolUsuario, Usuario
from app.servicios.apertura import crear_lotes_apertura


@pytest_asyncio.fixture
async def cliente_fase5() -> AsyncClient:
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
                Usuario(full_name="Admin", email="admin@fase5.pe", hashed_password=pwd_context.hash("admin123"), role=RolUsuario.ADMIN.value),
                Usuario(full_name="Taller", email="taller@fase5.pe", hashed_password=pwd_context.hash("taller123"), role=RolUsuario.TALLER.value),
                Usuario(full_name="Vendedor", email="vendedor@fase5.pe", hashed_password=pwd_context.hash("vendedor123"), role=RolUsuario.VENDEDOR.value),
                Categoria(id=1, name="Minerales"),
                Proveedor(id=1, name="Proveedor local"),
                Producto(id=1, category_id=1, sku="MIN-001", name="Mineral", unit_type="UNIDAD", sale_price=30, cost_price=7, current_stock=2, min_stock_alert=1, is_active=True),
                Producto(id=2, category_id=1, sku="MIN-002", name="Sin stock", unit_type="KILOGRAMO", sale_price=40, cost_price=0, current_stock=0, min_stock_alert=1, is_active=True),
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
    app.state.fase5_sessionmaker = sesiones
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        yield cliente
    app.dependency_overrides.clear()
    del app.state.fase5_sessionmaker
    await engine.dispose()


def _token(usuario_id: int, rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token({'id': str(usuario_id), 'role': rol})}"}


@pytest.mark.asyncio
async def test_compra_crea_lote_entrada_ledger_y_exige_costo_sin_stock(cliente_fase5: AsyncClient) -> None:
    admin = _token(1, "admin")
    sin_costo = await cliente_fase5.post(
        "/api/v1/compras", json={"productId": 2, "quantity": 4}, headers=admin
    )
    assert sin_costo.status_code == 400
    assert sin_costo.json() == {
        "detail": "El costo de compra es obligatorio cuando el producto aún no tiene stock"
    }

    respuesta = await cliente_fase5.post(
        "/api/v1/compras",
        json={"productId": 2, "quantity": 4, "proveedorId": 1, "costoUnitarioSoles": 10},
        headers=admin,
    )
    assert respuesta.status_code == 201
    assert isinstance(respuesta.json()["quantity"], float)

    async with app.state.fase5_sessionmaker() as db:
        producto = await db.get(Producto, 2)
        movimiento = await db.scalar(select(MovimientoInventario).where(MovimientoInventario.product_id == 2))
        assert producto.current_stock == Decimal("4.00")
        assert producto.cost_price == Decimal("10.00")
        assert movimiento.movement_type == "entrada"
        assert movimiento.unit_cost_price == Decimal("10.00")


@pytest.mark.asyncio
async def test_entrada_produccion_usa_costo_promedio_y_permisos(cliente_fase5: AsyncClient) -> None:
    respuesta = await cliente_fase5.post(
        "/api/v1/entradas",
        json={"productId": 1, "quantity": 3},
        headers=_token(2, "taller"),
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["responsable"] == "Taller"

    vendedor = await cliente_fase5.get("/api/v1/entradas", headers=_token(3, "vendedor"))
    assert vendedor.status_code == 403
    taller = await cliente_fase5.get("/api/v1/entradas", headers=_token(2, "taller"))
    assert taller.status_code == 200

    async with app.state.fase5_sessionmaker() as db:
        producto = await db.get(Producto, 1)
        entrada = await db.scalar(select(EntradaStock).where(EntradaStock.product_id == 1).order_by(EntradaStock.id.desc()))
        assert producto.current_stock == Decimal("5.00")
        assert producto.cost_price == Decimal("7.00")
        assert entrada.notes == "Producción del taller"


@pytest.mark.asyncio
async def test_merma_consume_fifo_escribe_ledger_y_es_atomica(cliente_fase5: AsyncClient) -> None:
    taller = _token(2, "taller")
    respuesta = await cliente_fase5.post(
        "/api/v1/mermas",
        json={"productId": 1, "quantity": 1, "motivo": "Defecto de calidad", "detalle": "Control"},
        headers=taller,
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["quantity"] == 1.0

    insuficiente = await cliente_fase5.post(
        "/api/v1/mermas",
        json={"productId": 1, "quantity": 100, "motivo": "Otro"},
        headers=taller,
    )
    assert insuficiente.status_code == 409
    assert insuficiente.json()["detail"] == "Stock insuficiente: hay 1.00 y se requieren 100.00"

    async with app.state.fase5_sessionmaker() as db:
        assert len((await db.scalars(select(Merma))).all()) == 1
        movimientos = (await db.scalars(select(MovimientoInventario).where(MovimientoInventario.movement_type == "merma"))).all()
        assert len(movimientos) == 1
        assert movimientos[0].quantity == Decimal("-1.00")