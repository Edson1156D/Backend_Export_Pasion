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
async def cliente_fase9() -> AsyncClient:
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
            email="admin@fase9.pe",
            hashed_password=pwd_context.hash("admin123"),
            role=RolUsuario.ADMIN.value,
        )
        vendedor = Usuario(
            full_name="Vendedor",
            email="vendedor@fase9.pe",
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
                    name="Mineral rojo",
                    unit_type="UNIDAD",
                    sale_price=30,
                    cost_price=7,
                    current_stock=2,
                    min_stock_alert=3,
                    is_active=True,
                ),
                Producto(
                    id=2,
                    category_id=1,
                    sku="MIN-002",
                    name="Mineral azul",
                    unit_type="KILOGRAMO",
                    sale_price=45,
                    cost_price=10,
                    current_stock=0,
                    min_stock_alert=1,
                    is_active=True,
                ),
                Producto(
                    id=3,
                    category_id=1,
                    sku="MIN-003",
                    name="Mineral inactivo",
                    unit_type="UNIDAD",
                    sale_price=20,
                    cost_price=5,
                    current_stock=5,
                    min_stock_alert=0,
                    is_active=False,
                ),
            ]
        )
        await db.flush()
        venta = Venta(
            folio="BLT-0001",
            sale_type="tienda",
            payment_method="efectivo",
            subtotal=Decimal("90.00"),
            total=Decimal("90.00"),
            responsable_id=vendedor.id,
            created_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        )
        db.add(venta)
        await db.flush()
        db.add_all(
            [
                MovimientoInventario(
                    product_id=1,
                    responsable_id=vendedor.id,
                    movement_type="venta",
                    quantity=Decimal("2.00"),
                    unit_sold_price=Decimal("30.00"),
                    unit_cost_price=Decimal("7.00"),
                    sale_group_id=venta.id,
                    created_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
                ),
                MovimientoInventario(
                    product_id=2,
                    responsable_id=vendedor.id,
                    movement_type="venta",
                    quantity=Decimal("1.00"),
                    unit_sold_price=Decimal("30.00"),
                    unit_cost_price=Decimal("10.00"),
                    sale_group_id=venta.id,
                    created_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
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
async def test_dashboard_calcula_kpis_top_serie_y_alertas(cliente_fase9: AsyncClient) -> None:
    respuesta = await cliente_fase9.get(
        "/api/v1/dashboard/resumen?periodo=mes",
        headers=_token(1, "admin"),
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["resumenVentas"] == {
        "totalVentas": 90.0,
        "cantidadVentas": 1,
        "promedioPorVenta": 90.0,
        "piezasVendidas": 3.0,
        "margenBruto": 66.0,
    }
    assert len(cuerpo["serieSemanal"]) == 8
    assert cuerpo["topProductos"][0] == {
        "productId": 1,
        "nombre": "Mineral rojo",
        "sku": "MIN-001",
        "totalVentas": 60.0,
        "piezasVendidas": 2.0,
        "margenBruto": 46.0,
    }
    assert cuerpo["alertasStock"]["total"] == 3
    assert cuerpo["alertasStock"]["agotados"] == 1
    assert cuerpo["alertasStock"]["stockBajo"] == 1
    assert cuerpo["alertasStock"]["inactivos"] == 1


@pytest.mark.asyncio
async def test_dashboard_restringe_rol_y_periodo(cliente_fase9: AsyncClient) -> None:
    sin_permiso = await cliente_fase9.get(
        "/api/v1/dashboard/resumen",
        headers=_token(2, "vendedor"),
    )
    periodo_invalido = await cliente_fase9.get(
        "/api/v1/dashboard/resumen?periodo=trimestre",
        headers=_token(1, "admin"),
    )

    assert sin_permiso.status_code == 403
    assert periodo_invalido.status_code == 422
    assert isinstance(periodo_invalido.json()["detail"], str)