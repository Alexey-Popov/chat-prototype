"""Database engine and session factories"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

Base = declarative_base()


def _make_engine(dsn: str, pool_size: int = 10, max_overflow: int = 0):
    """Create an async engine. SQLite doesn't support pool_size/max_overflow."""
    if dsn.startswith("sqlite"):
        return create_async_engine(dsn, echo=False, future=True)
    return create_async_engine(
        dsn, echo=False, future=True,
        pool_size=pool_size, max_overflow=max_overflow,
    )


system_engine = _make_engine(settings.system_dsn, pool_size=20)
vector_engine = _make_engine(settings.vector_dsn, pool_size=10)

SystemSessionLocal = async_sessionmaker(
    system_engine, class_=AsyncSession, expire_on_commit=False,
)
VectorSessionLocal = async_sessionmaker(
    vector_engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_system_db() -> AsyncGenerator[AsyncSession, None]:
    async with SystemSessionLocal() as session:
        yield session


async def get_vector_db() -> AsyncGenerator[AsyncSession, None]:
    async with VectorSessionLocal() as session:
        yield session
