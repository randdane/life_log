import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "LifeLog"
    DEBUG: bool = True
    API_V1_STR: str = "/api"
    
    # Auth
    ADMIN_PASSWORD: str
    API_TOKEN: Optional[str] = None
    
    # Database
    DATABASE_URL: str
    
    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "lifelog-attachments"
    MINIO_SECURE: bool = False
    
    # Limits
    FILE_MAX_BYTES: int = 10_485_760  # 10MB
    ATTACHMENT_MAX_PER_EVENT: int = 10
    ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg", "image/png", "image/webp", 
        "application/pdf", 
        "text/plain", "text/markdown", "text/csv", 
        "video/mp4"
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
