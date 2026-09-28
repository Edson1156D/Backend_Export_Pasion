import os
import sys
from logging.config import fileConfig
import asyncio

# --- IMPORTANTE: Cargar el .env ANTES de importar la configuración de la app ---
from dotenv import load_dotenv
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)
load_dotenv(os.path.join(parent_dir, ".env"))
# ------------------------------------------------------------------------------

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.bd.base import Base
from app.modelo import usuarios

config = context.config
database_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL no está configurada. Crea .env a partir de .env.example "
        "o define DATABASE_URL antes de ejecutar Alembic."
    )
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_silent_migrations() -> None:
    # Cambiado de SQLite a un nombre genérico síncrono por consistencia si fuera necesario
    sync_database_url = database_url.replace("+aiosqlite", "")
    connectable = create_engine(sync_database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
elif database_url.startswith("sqlite"):
    run_silent_migrations()
else:
    asyncio.run(run_async_migrations())
