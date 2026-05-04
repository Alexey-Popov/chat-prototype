"""Configuration management using pydantic-settings"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database
    system_dsn: str = "postgresql+asyncpg://user:password@system_db:5432/systemdb"
    vector_dsn: str = "postgresql+asyncpg://user:password@vector_db:5432/vectordb"

    # OpenAI
    openai_api_key: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 15

    # OAuth
    oauth_provider: str = "google"
    oauth_client_id: str
    oauth_client_secret: str

    # Dev override
    dev_mock_user: Optional[str] = None

    # Browser UI (chat-ui) calls this API from another origin — comma-separated list
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def jwt_expiry_seconds(self) -> int:
        """Convert expiry minutes to seconds"""
        return self.jwt_expiry_minutes * 60


settings = Settings()
