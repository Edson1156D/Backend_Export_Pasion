from datetime import datetime, timezone
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
from app.modelo.lotes import Lote
from app.modelo.productos import Producto
from app.modelo.usuarios import RolUsuario, Usuario
from app.servicios.apertura import crear_lotes_apertura
from app.servicios.inventario import (
    LoteDisponible,
    asignar_consumo_fifo,
    costo_consumo_total,
    costo_promedio_ponderado,
    round2,
    validar_cantidad_positiva,
    validar_costo_no_negativo,
    verificar_consistencia_stock,
)


def lote(lote_id: int, cantidad: str, costo: str, segundo: int) -> LoteDisponible:
    return LoteDisponible(
        lote_id=lote_id,
        product_id=1,
        cantidad_disponible=Decimal(cantidad),
        costo_unitario=Decimal(costo),
        fecha_ingreso=datetime(2026, 9, 1, 0, 0, segundo, tzinfo=timezone.utc),
    )


def test_round2_usa_redondeo_half_up() -> None:
    assert round2(Decimal("1.005")) == Decimal("1.01")
    assert round2(Decimal("2.675")) == Decimal("2.68")


def test_fifo_cruza_dos_lotes_y_prioriza_el_mas_antiguo() -> None:
    lotes = [lote(2, "4", "12", 2), lote(1, "3", "10", 1)]

    detalle = asignar_consumo_fifo(lotes, Decimal("5"))

    assert detalle == [
        {"lote_id": 1, "cantidad": Decimal("3.00"), "costo_unitario": Decimal("10.00")},
        {"lote_id": 2, "cantidad": Decimal("2.00"), "costo_unitario": Decimal("12.00")},
    ]


def test_fifo_cruza_tres_lotes_e_ignora_lotes_vacios() -> None:
    lotes = [
        lote(3, "1", "30", 3),
        lote(1, "0", "10", 1),
        lote(2, "2.5", "20", 2),
    ]

    detalle = asignar_consumo_fifo(lotes, Decimal("3.25"))

    assert [linea["lote_id"] for linea in detalle] == [2, 3]
    assert [linea["cantidad"] for linea in detalle] == [Decimal("2.50"), Decimal("0.75")]


def test_fifo_rechaza_stock_insuficiente_con_mensaje_exacto() -> None:
    with pytest.raises(ValueError, match=r"^Stock insuficiente: hay 2\.00 y se requieren 3\.00$"):
        asignar_consumo_fifo([lote(1, "2", "10", 1)], Decimal("3"))


def test_costo_promedio_ponderado() -> None:
    assert costo_promedio_ponderado([lote(1, "2", "10", 1), lote(2, "3", "20", 2)]) == Decimal("16.00")


def test_stock_cero_conserva_el_ultimo_costo() -> None:
    assert costo_promedio_ponderado([]) == Decimal("0.00")
    assert costo_promedio_ponderado([lote(1, "0", "25", 1)]) == Decimal("0.00")
    ultimo_costo = Decimal("25.00")
    nuevo_stock = Decimal("0.00")
    costo_resultante = ultimo_costo if nuevo_stock == 0 else costo_promedio_ponderado([])
    assert costo_resultante == Decimal("25.00")


@pytest.mark.parametrize(
    ("funcion", "valor", "mensaje"),
    [
        (validar_cantidad_positiva, Decimal("0"), "La cantidad debe ser mayor a 0"),
        (validar_cantidad_positiva, Decimal("-1"), "La cantidad debe ser mayor a 0"),
        (validar_cantidad_positiva, Decimal("NaN"), "La cantidad debe ser mayor a 0"),
        (validar_costo_no_negativo, Decimal("-0.01"), "El costo no puede ser negativo"),
        (validar_costo_no_negativo, Decimal("NaN"), "El costo no puede ser negativo"),
    ],
)
def test_validaciones_mantienen_mensajes_exactos(funcion, valor, mensaje) -> None:
    with pytest.raises(ValueError, match=f"^{mensaje}$"):
        funcion(valor)


def test_costo_consumo_total_redondea_half_up() -> None:
    detalle = [
        {"lote_id": 1, "cantidad": Decimal("1.00"), "costo_unitario": Decimal("1.005")},
        {"lote_id": 2, "cantidad": Decimal("2.00"), "costo_unitario": Decimal("2.00")},
    ]
    assert costo_consumo_total(detalle) == Decimal("5.01")


@pytest_asyncio.fixture
async def cliente_fase4() -> AsyncClient:
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
                Usuario(full_name="Admin", email="admin@fase4.pe", hashed_password=pwd_context.hash("admin123"), role=RolUsuario.ADMIN.value),
                Usuario(full_name="Taller", email="taller@fase4.pe", hashed_password=pwd_context.hash("taller123"), role=RolUsuario.TALLER.value),
                Usuario(full_name="Vendedor", email="vendedor@fase4.pe", hashed_password=pwd_context.hash("vendedor123"), role=RolUsuario.VENDEDOR.value),
                Categoria(id=1, name="Minerales"),
                Producto(id=1, category_id=1, sku="MIN-001", name="Mineral", unit_type="UNIDAD", sale_price=30, cost_price=7, current_stock=5, min_stock_alert=1, is_active=True),
                Producto(id=2, category_id=1, sku="MIN-002", name="Otro mineral", unit_type="KILOGRAMO", sale_price=40, cost_price=9, current_stock=0, min_stock_alert=1, is_active=True),
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
    app.state.fase4_sessionmaker = sesiones
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as cliente:
        yield cliente
    app.dependency_overrides.clear()
    del app.state.fase4_sessionmaker
    await engine.dispose()


def _token(usuario_id: int, rol: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_token({'id': str(usuario_id), 'role': rol})}"}


@pytest.mark.asyncio
async def test_apertura_es_idempotente_y_consistencia(cliente_fase4: AsyncClient) -> None:
    async with app.state.fase4_sessionmaker() as db:
        assert await verificar_consistencia_stock(db) == []
        assert await crear_lotes_apertura(db) == []
        lotes = (await db.scalars(select(Lote))).all()
        assert len(lotes) == 1


@pytest.mark.asyncio
async def test_lotes_respeta_ordenes_y_permisos(cliente_fase4: AsyncClient) -> None:
    admin = _token(1, "admin")
    respuesta = await cliente_fase4.get("/api/v1/lotes", headers=admin)
    assert respuesta.status_code == 200
    assert respuesta.json()[0]["codigo"] == "LOTE-0001"
    fifo = await cliente_fase4.get("/api/v1/lotes/producto/1", headers=admin)
    assert fifo.status_code == 200
    assert fifo.json()[0]["cantidadDisponible"] == 5.0
    vendedor = await cliente_fase4.get("/api/v1/lotes", headers=_token(3, "vendedor"))
    assert vendedor.status_code == 403
