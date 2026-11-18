import logging
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.modelo  # noqa: F401
from app.api.v1 import (
    almacenes,
    analisis,
    auth,
    comercio_exterior,
    dashboard,
    inventario,
    movimientos,
    productos,
    usuarios,
    ventas,
)
from app.core.config import CORS_ORIGINS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("eip.backend")


class ErrorDeNegocio(Exception):
    def __init__(self, mensaje: str, codigo_estado: int = 400):
        self.mensaje = mensaje
        self.codigo_estado = codigo_estado
        super().__init__(mensaje)


async def manejar_http_exception(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def manejar_error_de_negocio(request: Request, exc: ErrorDeNegocio):
    return JSONResponse(
        status_code=exc.codigo_estado,
        content={"detail": exc.mensaje},
    )


async def manejar_validacion(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def manejar_error_no_controlado(request: Request, exc: Exception):
    logger.exception("Error interno no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


app = FastAPI(
    title="Import & Export Pasión API",
    description="API para gestionar inventario, productos, ventas y operaciones de comercio exterior de Import & Export Pasión.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Autenticación y sesión de usuarios."},
        {"name": "Usuarios", "description": "Administración de usuarios y permisos."},
        {"name": "Productos", "description": "Catálogos y gestión de productos."},
        {"name": "Inventario", "description": "Entradas, lotes y mermas de inventario."},
        {"name": "Ventas", "description": "Registro y consulta de ventas."},
        {"name": "Comercio Exterior", "description": "Importaciones, exportaciones y socios comerciales."},
        {"name": "Movimientos", "description": "Consulta del ledger de movimientos de inventario."},
        {"name": "Dashboard", "description": "Indicadores y alertas del negocio."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_exception_handler(HTTPException, manejar_http_exception)
app.add_exception_handler(ErrorDeNegocio, manejar_error_de_negocio)
app.add_exception_handler(RequestValidationError, manejar_validacion)
app.add_exception_handler(Exception, manejar_error_no_controlado)


@app.middleware("http")
async def registrar_peticion(request: Request, call_next):
    inicio = perf_counter()
    response = await call_next(request)
    duracion_ms = (perf_counter() - inicio) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duracion_ms,
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(analisis.router, prefix="/api/v1")
app.include_router(productos.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(movimientos.router, prefix="/api/v1")
app.include_router(usuarios.router, prefix="/api/v1")
app.include_router(almacenes.router, prefix="/api/v1")
app.include_router(ventas.router, prefix="/api/v1")
app.include_router(inventario.router, prefix="/api/v1")
app.include_router(comercio_exterior.router, prefix="/api/v1")


@app.get("/")
async def raiz():
    return {"mensaje": "El backend está funcionando"}
