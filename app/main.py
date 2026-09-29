from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.v1.auth import router as auth_router
from app.api.v1.catalogos import router as catalogos_router
from app.api.v1.productos import router as productos_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.lotes import router as lotes_router
from app.api.v1.inventario import router as inventario_router
from app.api.v1.movimientos import router as movimientos_router
from app.api.v1.ventas import router as ventas_router
from app.api.v1.comercio_exterior import router as comercio_exterior_router
from app.core.config import CORS_ORIGINS
from app.core.errores import ErrorDeNegocio, manejar_error_de_negocio, manejar_error_no_controlado, manejar_http_exception, manejar_validacion

 
app = FastAPI(title="Sistema Inventario - Backend")
app.add_exception_handler(HTTPException, manejar_http_exception)
app.add_exception_handler(ErrorDeNegocio, manejar_error_de_negocio)
app.add_exception_handler(RequestValidationError, manejar_validacion)
app.add_exception_handler(Exception, manejar_error_no_controlado)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalogos_router, prefix="/api/v1")
app.include_router(productos_router, prefix="/api/v1")
app.include_router(usuarios_router, prefix="/api/v1")
app.include_router(lotes_router, prefix="/api/v1")
app.include_router(inventario_router, prefix="/api/v1")
app.include_router(movimientos_router, prefix="/api/v1")
app.include_router(ventas_router, prefix="/api/v1")
app.include_router(comercio_exterior_router, prefix="/api/v1")

 
 
@app.get("/")
async def raiz():
    return {"mensaje": "El backend está funcionando"}