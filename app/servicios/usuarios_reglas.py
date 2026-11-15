"""
Usuarios - reglas de negocio puras (sin base de datos ni FastAPI).

Los errores se lanzan como ReglaUsuario(codigo, mensaje); la ruta los convierte en
HTTPException con `detail` de texto, que es lo que el front muestra tal cual.
"""
import re

ROLES = ("admin", "vendedor", "taller")
ROL_POR_DEFECTO = "vendedor"       # el de menos privilegios, si la BD trae un rol no válido

MIN_NOMBRE = 3
MAX_NOMBRE = 120                   # varchar(120) en la BD
MAX_EMAIL = 120
MIN_PASSWORD = 6
MAX_PASSWORD_BYTES = 72            # límite de bcrypt: más allá se ignora en silencio

_NOMBRE_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s'-]+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ReglaUsuario(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def normalizar_email(email: str | None) -> str:
    return (email or "").strip().lower()


def validar_nombre(nombre: str | None) -> str:
    limpio = " ".join((nombre or "").split())
    if len(limpio) < MIN_NOMBRE:
        raise ReglaUsuario(422, f"El nombre debe tener al menos {MIN_NOMBRE} caracteres")
    if len(limpio) > MAX_NOMBRE:
        raise ReglaUsuario(422, f"El nombre no puede superar los {MAX_NOMBRE} caracteres")
    if not _NOMBRE_RE.match(limpio):
        raise ReglaUsuario(422, "El nombre solo puede contener letras, espacios, guiones y apóstrofes")
    return limpio


def validar_email(email: str | None) -> str:
    limpio = normalizar_email(email)
    if len(limpio) > MAX_EMAIL or not _EMAIL_RE.match(limpio):
        raise ReglaUsuario(422, "El email no tiene un formato válido")
    return limpio


def validar_password(password: str | None) -> str:
    texto = password or ""
    if len(texto) < MIN_PASSWORD:
        raise ReglaUsuario(422, f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres")
    if len(texto.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ReglaUsuario(422, f"La contraseña es demasiado larga (máximo {MAX_PASSWORD_BYTES} caracteres)")
    return texto


def validar_edicion_propia(*, es_propio: bool, rol_actual: str, nuevo_rol: str, nuevo_activo: bool) -> None:
    """Nadie puede quitarse a sí mismo el acceso: así el sistema nunca se queda sin administrador."""
    if not es_propio:
        return
    if not nuevo_activo:
        raise ReglaUsuario(403, "No puedes desactivar tu propia cuenta")
    if rol_actual == "admin" and nuevo_rol != "admin":
        raise ReglaUsuario(403, "No puedes quitarte el rol de administrador")


def validar_eliminacion(*, es_propio: bool, movimientos: int) -> None:
    if es_propio:
        raise ReglaUsuario(403, "No puedes eliminar tu propia cuenta")
    if movimientos > 0:
        plural = "s" if movimientos != 1 else ""
        raise ReglaUsuario(
            409,
            f"Este usuario tiene {movimientos} movimiento{plural} registrado{plural} y no se puede "
            "eliminar; desactívalo en su lugar",
        )


def rol_para_front(rol_bd: str | None) -> str:
    """'ADMIN' -> 'admin'. Un rol desconocido se muestra como el de menos privilegios."""
    rol = (rol_bd or "").strip().lower()
    return rol if rol in ROLES else ROL_POR_DEFECTO