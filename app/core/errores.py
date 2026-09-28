from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorDeNegocio(Exception):
    def __init__(self, mensaje: str, status_code: int = 400):
        self.mensaje = mensaje
        self.status_code = status_code
        super().__init__(mensaje)


async def manejar_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


async def manejar_error_de_negocio(request: Request, exc: ErrorDeNegocio) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


async def manejar_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    errores = []
    for error in exc.errors():
        ubicacion = ".".join(str(parte) for parte in error.get("loc", []) if parte != "body")
        mensaje = error.get("msg", "Valor inválido")
        errores.append(f"{ubicacion}: {mensaje}" if ubicacion else str(mensaje))
    return JSONResponse(status_code=422, content={"detail": "; ".join(errores)})


async def manejar_error_no_controlado(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})