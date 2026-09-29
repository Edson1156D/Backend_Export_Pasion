from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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
from app.modelo.ventas import Venta


@pytest_asyncio.fixture
async def cliente_fase7() -> AsyncClient:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sesiones = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    async with sesiones() as db:
        admin = Usuario(
            full_name="Admin",
            email="admin@fase7.pe",
            hashed_password=pwd_context.hash("admin123"),
            role=RolUsuario.ADMIN.value,
        )
        vendedor = Usuario(
            full_name="Vendedor",
            email="vendedor@fase7.pe",
            hashed_password=pwd_context.hash("vendedor123"),
            role=RolUsuario.VENDEDOR.value,
        )
        db.add_all(
            [
                admin,
                vendedor,
                Categoria(id=1, name="Minerales"),
                Producto(
                    id=1,
                    category_id=1,
                    sku="MIN-001",
                    name="Mineral",
                    unit_type="UNIDAD",
                    sale_price=30,
                    cost_price=7,
                    current_stock=1,
                    min_stock_alert=1,
                    is_active=True,
                ),
            ]
        )
        await db.flush()
        venta = Venta(
            folio="BLT-0001",
            sale_type="digital",
            payment_method="billetera-digital",
            subtotal=30,
            total=30,
            responsable_id=vendedor.id,
        )
        db.add(venta)
        await db.flush()
        db.add_all(
            [
                MovimientoInventario(
                    product_id=1,
                    responsable_id=admin.id,
                    movement_type="entrada",
                    quantity=Decimal("1.00"),
                    unit_sold_price=Decimal("30.00"),
                    unit_cost_price=Decimal("7.00"),
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                ),
                MovimientoInventario(
                    product_id=1,
                    responsable_id=vendedor.id,
                    movement_type="venta",
                    quantity=Decimal("-1.00"),
                    unit_sold_price=Decimal("30.00"),
                    unit_cost_price=Decimal("7.00"),
                    sale_group_id=venta.id,
                    created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                ),
            ]
        )
        await db.commit()

    async def override_get_db():
        async with sesiones() as db:
            try:
                yield db
            finally:
                await db.rollback()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        yield cliente
    app.dependency_overrides.clear()
    await engine.dispose()


def _token(usuario_id: int, rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token({'id': str(usuario_id), 'role': rol})}"}


@pytest.mark.asyncio
async def test_movimientos_admin_enriquece_venta_y_serializa_numeros(cliente_fase7: AsyncClient) -> None:
    respuesta = await cliente_fase7.get("/api/v1/movimientos", headers=_token(1, "admin"))

    assert respuesta.status_code == 200
    movimientos = respuesta.json()
    assert [movimiento["movementType"] for movimiento in movimientos] == ["venta", "entrada"]
    venta = movimientos[0]
    assert venta["productName"] == "Mineral"
    assert venta["sku"] == "MIN-001"
    assert venta["unitType"] == "UNIDAD"
    assert venta["tipoVenta"] == "Digital"
    assert venta["folio"] == "BLT-0001"
    assert venta["quantity"] == -1.0
    assert isinstance(venta["unitSoldPrice"], float)
    assert isinstance(venta["unitCostPrice"], float)


@pytest.mark.asyncio
async def test_movimientos_solo_admin(cliente_fase7: AsyncClient) -> None:
    respuesta = await cliente_fase7.get("/api/v1/movimientos", headers=_token(2, "vendedor"))

    assert respuesta.status_code == 403