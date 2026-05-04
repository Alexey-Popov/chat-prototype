"""Alembic environment script"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _sync_migration_url() -> str:
    """Alembic online mode uses a sync engine; asyncpg URLs are converted to psycopg."""
    dsn = os.getenv(
        "SYSTEM_DSN",
        "postgresql://user:password@system_db:5432/systemdb",
    )
    if "+asyncpg" in dsn:
        return dsn.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return dsn


# Get DSN from environment (sync driver for Alembic)
system_dsn = _sync_migration_url()
config.set_main_option("sqlalchemy.url", system_dsn)

from app.db import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = _sync_migration_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
