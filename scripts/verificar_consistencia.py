import asyncio
import sys

from app.bd.session import AsyncSessionLocal
from app.servicios.inventario import verificar_consistencia_stock


async def main() -> int:
    async with AsyncSessionLocal() as db:
        inconsistentes = await verificar_consistencia_stock(db)

    if inconsistentes:
        print(
            "Productos inconsistentes (stock actual distinto al stock de lotes): "
            + ", ".join(str(product_id) for product_id in inconsistentes)
        )
        return 1

    print("Consistencia de inventario OK: todos los productos cuadran con sus lotes.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))