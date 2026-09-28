from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.bd.base import Base
from app.core.config import ALGORITHM, SECRET_KEY
from app.core.seguridad import pwd_context
from app.main import app
from app.modelo.usuarios import RolUsuario, Usuario


@pytest_asyncio.fixture
async def cliente(monkeypatch) -> AsyncClient:
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
                Usuario(full_name="Admin Principal", email="admin@pasion.pe", hashed_password=pwd_context.hash("admin123"), role=RolUsuario.ADMIN.value, is_active=True),
                Usuario(full_name="Vendedor Principal", email="vendedor@pasion.pe", hashed_password=pwd_context.hash("vendedor123"), role=RolUsuario.VENDEDOR.value, is_active=True),
                Usuario(full_name="Taller Principal", email="taller@pasion.pe", hashed_password=pwd_context.hash("taller123"), role=RolUsuario.TALLER.value, is_active=True),
                Usuario(full_name="Usuario Inactivo", email="inactivo@pasion.pe", hashed_password=pwd_context.hash("inactivo123"), role=RolUsuario.TALLER.value, is_active=False),
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
    app.state.fase2_sessionmaker = sesiones
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
    del app.state.fase2_sessionmaker
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email", "password", "rol"),
    [
        ("admin@pasion.pe", "admin123", "admin"),
        ("vendedor@pasion.pe", "vendedor123", "vendedor"),
        ("taller@pasion.pe", "taller123", "taller"),
    ],
)
async def test_login_devuelve_contrato_por_rol(cliente: AsyncClient, email: str, password: str, rol: str):
    respuesta = await cliente.post("/api/v1/auth/login", json={"email": email, "password": password})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["tokenType"] == "bearer"
    assert isinstance(cuerpo["usuario"]["id"], str)
    assert cuerpo["usuario"]["id"].isdigit()
    assert cuerpo["usuario"]["rol"] == rol
    assert "role" not in cuerpo["usuario"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "datos",
    [
        {"email": "no-existe@pasion.pe", "password": "admin123"},
        {"email": "admin@pasion.pe", "password": "incorrecta"},
    ],
)
async def test_login_credenciales_invalidas_mismo_401(cliente: AsyncClient, datos: dict[str, str]):
    respuesta = await cliente.post("/api/v1/auth/login", json=datos)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Email o contraseña incorrectos"}


@pytest.mark.asyncio
async def test_login_usuario_inactivo_es_403(cliente: AsyncClient):
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "inactivo@pasion.pe", "password": "inactivo123"},
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Tu cuenta está inactiva. Contactá a un administrador."


@pytest.mark.asyncio
async def test_me_rechaza_token_expirado(cliente: AsyncClient):
    token = jwt.encode(
        {"id": 1, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    respuesta = await cliente.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401
    assert isinstance(respuesta.json()["detail"], str)


@pytest.mark.asyncio
@pytest.mark.parametrize("rol", ["vendedor", "taller"])
async def test_usuarios_solo_admin(cliente: AsyncClient, rol: str):
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": f"{rol}@pasion.pe", "password": f"{rol}123"},
    )
    token = login.json()["accessToken"]
    respuesta = await cliente.get("/api/v1/usuarios", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": "No tienes permiso para acceder a esto"}


@pytest.mark.asyncio
async def test_crud_usuarios_admin_y_campos_camel_case(cliente: AsyncClient):
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "admin@pasion.pe", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    creado = await cliente.post(
        "/api/v1/usuarios",
        headers=headers,
        json={
            "fullName": "Nuevo Usuario",
            "email": "nuevo@pasion.pe",
            "role": "taller",
            "password": "nuevo123",
            "isActive": True,
        },
    )
    assert creado.status_code == 201
    assert creado.json()["fullName"] == "Nuevo Usuario"
    assert "hashedPassword" not in creado.json()

    usuarios = await cliente.get("/api/v1/usuarios", headers=headers)
    assert usuarios.status_code == 200
    assert any(usuario["email"] == "nuevo@pasion.pe" for usuario in usuarios.json())

    actualizado = await cliente.put(
        f"/api/v1/usuarios/{creado.json()['id']}",
        headers=headers,
        json={
            "fullName": "Usuario Actualizado",
            "email": "nuevo@pasion.pe",
            "role": "taller",
            "isActive": False,
            "password": "",
        },
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["isActive"] is False

    eliminado = await cliente.delete(f"/api/v1/usuarios/{creado.json()['id']}", headers=headers)
    assert eliminado.status_code == 204


@pytest.mark.asyncio
async def test_no_se_puede_desactivar_al_ultimo_admin(cliente: AsyncClient):
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "admin@pasion.pe", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    admin_id = login.json()["usuario"]["id"]
    respuesta = await cliente.put(
        f"/api/v1/usuarios/{admin_id}",
        headers=headers,
        json={
            "fullName": "Admin Principal",
            "email": "admin@pasion.pe",
            "role": "admin",
            "isActive": False,
            "password": "",
        },
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Debe quedar al menos un administrador activo"


@pytest.mark.asyncio
async def test_no_se_puede_eliminar_usuario_con_registros(cliente: AsyncClient):
    login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "admin@pasion.pe", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    vendedor = await cliente.post(
        "/api/v1/usuarios",
        headers=headers,
        json={
            "fullName": "Vendedor Historico",
            "email": "historico@pasion.pe",
            "role": "vendedor",
            "password": "historico123",
            "isActive": True,
        },
    )
    assert vendedor.status_code == 201

    from app.modelo.ventas import Venta

    async with app.state.fase2_sessionmaker() as db:
        db.add(
            Venta(
                folio="BLT-TEST-1",
                sale_type="tienda",
                payment_method="efectivo",
                subtotal=0,
                total=0,
                responsable_id=int(vendedor.json()["id"]),
            )
        )
        await db.commit()

    respuesta = await cliente.delete(f"/api/v1/usuarios/{vendedor.json()['id']}", headers=headers)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "No se puede eliminar: tiene registros asociados. Desactívalo en su lugar."
