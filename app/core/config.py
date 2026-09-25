import os

from dotenv import load_dotenv


load_dotenv()


def _required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria: {name}. "
            "Configúrala en el entorno o en un archivo .env."
        )
    return value


DATABASE_URL = _required_setting("DATABASE_URL")
SECRET_KEY = _required_setting("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]