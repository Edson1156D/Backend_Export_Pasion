import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.bd.base import Base
from app.core.seguridad import pwd_context
from app.main import app
from app.modelo.categorias import Categoria
from app.modelo.lotes import Lote
from app.modelo.proveedores import Proveedor
from app.modelo.socios_comerciales import SocioComercial
from app.modelo.usuarios import RolUsuario, Usuario


@pytest_asyncio.fixture
async def cliente_fase3() -> AsyncClient:
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
                Usuario(full_name="Admin", email="admin@fase3.pe", hashed_password=pwd_context.hash("admin123"), role=RolUsuario.ADMIN.value),
                Usuario(full_name="Vendedor", email="vendedor@fase3.pe", hashed_password=pwd_context.hash("vendedor123"), role=RolUsuario.VENDEDOR.value),
                Usuario(full_name="Taller", email="taller@fase3.pe", hashed_password=pwd_context.hash("taller123"), role=RolUsuario.TALLER.value),
                Categoria(id=1, name="Minerales"),
                Proveedor(id=1, name="Proveedor local"),
                SocioComercial(id=1, name="Socio exterior", country="Perú"),
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
    app.state.fase3_sessionmaker = sesiones
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        yield cliente
    app.dependency_overrides.clear()
    del app.state.fase3_sessionmaker
    await engine.dispose()


async def _headers(cliente: AsyncClient, rol: str) -> dict[str, str]:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": f"{rol}@fase3.pe", "password": f"{rol}123"},
    )
    return {"Authorization": f"Bearer {respuesta.json()['accessToken']}"}


@pytest.mark.asyncio
async def test_catalogos_productos_crud_y_numeros(cliente_fase3: AsyncClient):
    admin = await _headers(cliente_fase3, "admin")
    categorias = await cliente_fase3.get("/api/v1/categorias", headers=admin)
    assert categorias.status_code == 200
    assert categorias.json() == [{"id": 1, "parentId": None, "name": "Minerales", "description": None}]
    assert (await cliente_fase3.get("/api/v1/proveedores", headers=admin)).json()[0]["name"] == "Proveedor local"
    socio = (await cliente_fase3.get("/api/v1/comercio-exterior/socios-comerciales", headers=admin)).json()[0]
    assert socio == {"id": 1, "nombre": "Socio exterior", "pais": "Perú"}

    creado = await cliente_fase3.post(
        "/api/v1/productos",
        headers=admin,
        json={
            "sku": "PIE-001",
            "name": "Piedra pulida",
            "categoryId": 1,
            "unitType": "UNIDAD",
            "salePrice": 25,
            "minStockAlert": 2.5,
            "isActive": True,
            "currentStock": 99,
            "costPrice": 99,
        },
    )
    assert creado.status_code == 201
    cuerpo = creado.json()
    assert cuerpo["currentStock"] == 0
    assert cuerpo["costPrice"] == 0
    assert all(isinstance(cuerpo[campo], (int, float)) and not isinstance(cuerpo[campo], bool) for campo in ("salePrice", "costPrice", "currentStock", "minStockAlert"))

    duplicado = await cliente_fase3.post(
        "/api/v1/productos",
        headers=admin,
        json={"sku": "pie-001", "name": "Otra piedra", "categoryId": 1, "unitType": "UNIDAD", "salePrice": 1, "minStockAlert": 0, "isActive": True},
    )
    assert duplicado.status_code == 409
    assert duplicado.json() == {"detail": "Ya existe un producto con ese SKU"}

    activar_sin_precio = await cliente_fase3.put(
        f"/api/v1/productos/{cuerpo['id']}",
        headers=admin,
        json={"salePrice": 0},
    )
    assert activar_sin_precio.status_code == 400
    assert activar_sin_precio.json()["detail"] == "Para activar el producto, el precio de venta debe ser mayor a 0"


@pytest.mark.asyncio
async def test_permisos_y_borrado_con_historial(cliente_fase3: AsyncClient):
    vendedor = await _headers(cliente_fase3, "vendedor")
    assert (await cliente_fase3.post("/api/v1/productos", headers=vendedor, json={})).status_code == 403
    assert (await cliente_fase3.get("/api/v1/proveedores", headers=vendedor)).status_code == 403

    admin = await _headers(cliente_fase3, "admin")
    creado = await cliente_fase3.post(
        "/api/v1/productos",
        headers=admin,
        json={"sku": "HIST-001", "name": "Producto con historial", "categoryId": 1, "unitType": "KILOGRAMO", "salePrice": 10, "minStockAlert": 0, "isActive": True},
    )
    producto_id = creado.json()["id"]
    async with app.state.fase3_sessionmaker() as db:
        db.add(
            Lote(
                product_id=producto_id,
                code="LOTE-HIST-1",
                origin="apertura",
                initial_qty=1,
                available_qty=1,
                unit_cost_pen=1,
                responsable_id=1,
            )
        )
        await db.commit()
    eliminado = await cliente_fase3.delete(f"/api/v1/productos/{producto_id}", headers=admin)
    assert eliminado.status_code == 409
    assert eliminado.json() == {"detail": "No se puede eliminar: el producto tiene movimientos. Desactívalo en su lugar."}