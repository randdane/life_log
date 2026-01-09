"""Configuration settings for the LifeLog API."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the LifeLog API."""

    # App
    PROJECT_NAME: str = "LifeLog"
    DEBUG: bool = True
    API_V1_STR: str = "/api"

    # Auth
    ADMIN_PASSWORD: str = Field(alias="APP_AUTH_ADMIN_PASSWORD")

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    DATABASE_URL: str

    # RustFS
    RUSTFS_ACCESS_KEY: str
    RUSTFS_SECRET_KEY: str
    RUSTFS_ENDPOINT: str
    RUSTFS_BUCKET: str
    RUSTFS_SECURE: bool = False

    # Limits
    FILE_MAX_BYTES: int = 10_485_760  # 10MB
    ATTACHMENT_MAX_PER_EVENT: int = 10
    ALLOWED_MIME_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "video/mp4",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
