"""Pytest configuration and fixtures."""
import os

# Set required env vars BEFORE any app imports so pydantic-settings doesn't fail.
os.environ.setdefault("SYSTEM_DSN", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-characters-long")

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from app.main import app  # noqa: E402
from app.db import get_db  # noqa: E402
from app.models.system import Base, User, Role, UserRole  # noqa: E402
from app.core.jwt import create_token  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session."""
    AsyncSessionLocal = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    """Create test client with overridden dependencies."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create admin user for testing."""
    admin_role = Role(id=uuid4(), name="admin")
    db_session.add(admin_role)

    admin = User(
        id=uuid4(),
        email="admin@example.com",
        oauth_sub="admin-sub",
        active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
    db_session.add(user_role)
    await db_session.commit()

    return admin, admin_role


@pytest.fixture
def admin_token(admin_user):
    """Create valid admin JWT token."""
    admin, admin_role = admin_user
    return create_token({
        "sub": str(admin.id),
        "role_ids": [str(admin_role.id)],
    })


@pytest.fixture
def admin_headers(admin_token):
    """Create authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}
