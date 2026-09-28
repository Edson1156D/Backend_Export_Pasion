import asyncio

from app.bd.session import AsyncSessionLocal
from app.servicios.apertura import crear_lotes_apertura


async def main() -> None:
    async with AsyncSessionLocal() as db:
        try:
            lotes = await crear_lotes_apertura(db)
            await db.commit()
            print(f"Lotes de apertura creados: {len(lotes)}")
        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
