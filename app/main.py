from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.v1.auth import router as auth_router
from app.api.v1.usuarios import router as usuarios_router
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
app.include_router(usuarios_router, prefix="/api/v1")

 
 
@app.get("/")
async def raiz():
    return {"mensaje": "El backend está funcionando"}