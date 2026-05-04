"""Configuration module."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    system_dsn: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # Same as core: when set, enables GET /auth/dev-login for demo / local admin UI
    dev_mock_user: Optional[str] = None

    cors_origins: str = "http://localhost:3001,http://127.0.0.1:3001,http://localhost:5174,http://127.0.0.1:5174"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


settings = Settings()
