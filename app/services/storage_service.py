"""Service layer for handling RustFS storage operations."""

import asyncio
import os
import uuid
from datetime import timedelta
from typing import BinaryIO

from minio import Minio

from app.config import settings


class StorageService:
    """Service layer for RustFS storage operations."""

    def __init__(self):
        """Initialize the RustFS client."""
        self.client = Minio(
            settings.RUSTFS_ENDPOINT,
            access_key=settings.RUSTFS_ACCESS_KEY,
            secret_key=settings.RUSTFS_SECRET_KEY,
            secure=settings.RUSTFS_SECURE,
        )

    async def upload_file(
        self, file_data: BinaryIO, filename: str, content_type: str, size: int
    ) -> str:
        """Upload a file to RustFS and return the generated key."""
        # Generate unique key
        ext = os.path.splitext(filename)[1]
        key = f"{uuid.uuid4().hex}{ext}"

        await asyncio.to_thread(
            self.client.put_object,
            settings.RUSTFS_BUCKET,
            key,
            file_data,
            size,
            content_type=content_type,
        )
        return key

    async def get_presigned_url(self, key: str, expires_minutes: int = 15) -> str:
        """Generate a presigned URL for downloading a file."""
        return await asyncio.to_thread(
            self.client.presigned_get_object,
            settings.RUSTFS_BUCKET,
            key,
            expires=timedelta(minutes=expires_minutes),
        )

    async def delete_file(self, key: str):
        """Delete a file from RustFS."""
        await asyncio.to_thread(self.client.remove_object, settings.RUSTFS_BUCKET, key)


storage_service = StorageService()
