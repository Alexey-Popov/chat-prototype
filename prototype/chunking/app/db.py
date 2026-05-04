"""Database connection management."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from app.config import settings


async def get_source_engine() -> AsyncEngine:
    """Create async engine for source database (read-only)."""
    engine = create_async_engine(
        settings.source_dsn,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    return engine


async def get_vector_engine() -> AsyncEngine:
    """Create async engine for vector database (read-write)."""
    engine = create_async_engine(
        settings.vector_dsn,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    return engine


# Module-level engines
_source_engine: AsyncEngine | None = None
_vector_engine: AsyncEngine | None = None


async def init_engines() -> tuple[AsyncEngine, AsyncEngine]:
    """Initialize and cache engines."""
    global _source_engine, _vector_engine
    if _source_engine is None:
        _source_engine = await get_source_engine()
    if _vector_engine is None:
        _vector_engine = await get_vector_engine()
    return _source_engine, _vector_engine


def get_cached_source_engine() -> AsyncEngine:
    """Get cached source engine."""
    assert _source_engine is not None
    return _source_engine


def get_cached_vector_engine() -> AsyncEngine:
    """Get cached vector engine."""
    assert _vector_engine is not None
    return _vector_engine


async def close_engines() -> None:
    """Close all engine connections."""
    global _source_engine, _vector_engine
    if _source_engine:
        await _source_engine.dispose()
        _source_engine = None
    if _vector_engine:
        await _vector_engine.dispose()
        _vector_engine = None
