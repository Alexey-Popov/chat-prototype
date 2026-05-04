"""Configuration management for the chunking service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    source_dsn: str = "postgresql+asyncpg://user:password@source_db:5432/sourcedb"
    vector_dsn: str = "postgresql+asyncpg://user:password@vector_db:5432/vectordb"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    batch_size: int = 100
    max_retries: int = 3
    initial_retry_delay: float = 1.0

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
