import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("SECRET_KEY", "test-only-secret")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:4000")
    from app.main import app

    return app


@pytest.mark.asyncio
async def test_app_arranca_y_expone_auth(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "/api/v1/auth/login" in {route.path for route in app.routes}


@pytest.mark.asyncio
async def test_422_detail_es_texto(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


@pytest.mark.asyncio
async def test_cors_usa_origenes_configurados(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"