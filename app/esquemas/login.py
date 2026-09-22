from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """
    Datos que el frontend debe enviar para iniciar sesión:
    el correo, la contraseña, y el rol que el usuario seleccionó
    con los botones (dueño / ventas / almacen).
    """
    email: EmailStr
    password: str
    role: str