"""Test fixtures and configuration"""
# ── Set required env vars BEFORE any app imports ─────────────────────────────
import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("OAUTH_CLIENT_ID", "test-client-id")
os.environ.setdefault("OAUTH_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SYSTEM_DSN", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("VECTOR_DSN", "sqlite+aiosqlite:///:memory:")
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db import Base, get_system_db, get_vector_db
from app.main import app
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def test_system_db():
    """In-memory SQLite database for system_db (users, roles, policies, logs)"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_system_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_system_db] = override_get_system_db
    yield SessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_vector_db():
    """In-memory SQLite database for vector_db reads (no schema needed for unit tests)"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_vector_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_vector_db] = override_get_vector_db
    yield SessionLocal
    await engine.dispose()


@pytest.fixture
async def client(test_system_db, test_vector_db):
    """FastAPI test client using ASGI transport"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
