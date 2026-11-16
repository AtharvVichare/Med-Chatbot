from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Aarogya-Drishti EHR API"
    VERSION: str = "2.0.0"

    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://aarogya:K9vX3mP7rL2wT8aF@localhost:5432/aarogya_db",
        description="Main PostgreSQL Database Connection URL"
    )
    TEST_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://aarogya:K9vX3mP7rL2wT8aF@localhost:5432/aarogya_db_test",
        description="Dedicated Test Database Connection URL"
    )
    SQL_ECHO: bool = False

    # JWT Security Configuration
    JWT_SECRET_KEY: str = Field(
        default="aarogya-super-secret-synthetic-jwt-key-2026-drishti",
        description="Secret key for signing JWTs"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    # CORS Allowed Origins (Comma-separated string in .env, e.g. "http://localhost:5173,https://myportal.com")
    ALLOWED_ORIGINS: str = Field(
        default="*",
        description="Allowed CORS origins"
    )

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Google OAuth 2.0 Web Client ID"
    )

settings = Settings()
