from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, SECRET_KEY

# Le dice a FastAPI que espere el token como "Bearer <token>",
# y en /docs mostrará un simple campo de texto para pegarlo.
seguridad = HTTPBearer(auto_error=False)

def crear_token(datos: dict) -> str:
    """
    Genera un JWT nuevo. 'datos' es la información que va DENTRO del token
    (ej. id del usuario y su rol), para poder leerla después sin
    volver a consultar la base de datos.
    """
    datos_a_codificar = datos.copy()
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    datos_a_codificar.update({"exp": expiracion})

    token = jwt.encode(datos_a_codificar, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def leer_token(token: str) -> dict | None:
    """
    Verifica que el token sea válido (firma correcta y no expirado).
    Si es válido, devuelve la información guardada adentro (id, rol, etc.).
    Si no es válido, devuelve None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.JWTError:
        return None


def obtener_usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(seguridad)) -> dict:
    """
    Lee el token que viene en la petición y devuelve sus datos (id, rol).
    Si el token no es válido o expiró, rechaza la petición con error 401.
    """
    # Sin header Authorization devolvemos 401 (HTTPBearer por defecto daría 403),
    # que es lo que el front espera para redirigir al login.
    if credenciales is None:
        raise HTTPException(status_code=401, detail="No autenticado")

    datos = leer_token(credenciales.credentials)
    if datos is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado, vuelve a iniciar sesión"
        )
    return datos


def requiere_rol(rol_permitido: str):
    """
    Genera una dependencia que solo deja pasar si el usuario tiene
    exactamente ese rol. Se usa así en una ruta:

        @router.get("/productos")
        async def ver_productos(usuario = Depends(requiere_rol("ALMACEN"))):
            ...
    """
    def verificar(usuario_actual: dict = Depends(obtener_usuario_actual)) -> dict:
        if usuario_actual.get("role") != rol_permitido:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para acceder a esto"
            )
        return usuario_actual

    return verificar

def requiere_roles(*roles_permitidos: str):
    """
    Como requiere_rol, pero deja pasar a cualquiera de los roles indicados:

        Depends(requiere_roles("ADMIN", "TALLER"))
    """
    def verificar(usuario_actual: dict = Depends(obtener_usuario_actual)) -> dict:
        if usuario_actual.get("role") not in roles_permitidos:
            raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción")
        return usuario_actual

    return verificar

# Prueba rápida: genera un token de ejemplo y lo vuelve a leer.
if __name__ == "__main__":
    token_prueba = crear_token({"id": 5, "role": "ADMIN"})
    print("Token generado:")
    print(token_prueba)

    datos_leidos = leer_token(token_prueba)
    print("\nDatos leídos de vuelta del token:")
    print(datos_leidos)