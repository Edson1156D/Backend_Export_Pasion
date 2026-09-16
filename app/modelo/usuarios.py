import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.bd.session import Base


class RolUsuario(str, enum.Enum):
    """
    Lista fija de roles permitidos.
    Esto valida los datos en Python, pero no cambia el tipo de
    columna en la base de datos (sigue siendo VARCHAR(20)).
    """
    DUENO = "ADMIN"
    VENTAS = "VENDEDOR"
    ALMACEN = "TALLER"


class Usuario(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Se guarda como texto normal (String) para coincidir con la columna
    # VARCHAR(20) que ya existe en la base de datos.
    role = Column(String(20), nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Esto SOLO se ejecuta si corres "python -m app.models.usuario" directamente.
# Solo verifica que el modelo esté bien definido, no toca la base de datos real.
if __name__ == "__main__":
    print("✅ El modelo se cargó sin errores")
    print(f"Nombre de la tabla: {Usuario.__tablename__}")
    print("Columnas definidas:")
    for columna in Usuario.__table__.columns:
        print(f"  - {columna.name} ({columna.type})")