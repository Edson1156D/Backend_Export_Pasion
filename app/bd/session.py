from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import asyncio

from app.core.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

if __name__ == "__main__":
    async def probar_conexion():
        try:
            async with engine.connect() as conexion:
                await conexion.execute(text("SELECT 1"))
                print("✅ Conexión exitosa a la base de datos")
        except Exception as error:
            print("❌ No se pudo conectar:", error)

    asyncio.run(probar_conexion())

    