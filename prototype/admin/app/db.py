"""Database module."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.system_dsn,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Create async sessionmaker
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session
