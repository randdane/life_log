"""Configuration settings for the LifeLog API."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the LifeLog API."""

    # App
    PROJECT_NAME: str = "LifeLog"
    DEBUG: bool = True
    API_V1_STR: str = "/api"

    # Auth
    APP_AUTH_ADMIN_PASSWORD: str
    APP_AUTH_API_TOKEN: str | None = None

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    DATABASE_URL: str

    # MinIO
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_ENDPOINT: str
    MINIO_BUCKET: str
    MINIO_SECURE: bool = False

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
