"""API router for Attachment resources."""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_token
from app.models import Attachment, Event
from app.schemas import AttachmentRead
from app.services.storage_service import storage_service

router = APIRouter(tags=["attachments"])


@router.post(
    "/events/{event_id}/attachments",
    response_model=list[AttachmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachments(
    event_id: int,
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
):
    """Upload attachments for a specific event with validation."""
    # Check if event exists
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Validate attachment count
    result = await db.execute(select(func.count()).where(Attachment.event_id == event_id))
    existing_count = result.scalar_one()
    if existing_count + len(files) > settings.ATTACHMENT_MAX_PER_EVENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Too many attachments. Max allowed per event is "
                f"{settings.ATTACHMENT_MAX_PER_EVENT}."
            ),
        )

    attachments = []
    for file in files:
        # Validate MIME type
        if file.content_type not in settings.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} is not allowed.",
            )

        # Read file data to check size and upload
        file_content = await file.read()
        size = len(file_content)

        # Validate file size
        if size > settings.FILE_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds max size of {settings.FILE_MAX_BYTES} bytes.",
            )

        # Upload to RustFS
        key = await storage_service.upload_file(
            BytesIO(file_content), file.filename, file.content_type, size
        )

        # Create DB record
        db_attachment = Attachment(
            event_id=event_id,
            key=key,
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=size,
        )
        db.add(db_attachment)
        attachments.append(db_attachment)

    try:
        await db.commit()
        for att in attachments:
            await db.refresh(att)
    except Exception as e:
        # Cleanup uploaded files if DB fails
        for att in attachments:
            await storage_service.delete_file(att.key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save attachment metadata: {str(e)}",
        ) from e

    return attachments


@router.get("/attachments/{key}", response_model=dict)
async def get_attachment_url(
    key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
):
    """Get a presigned URL for an attachment."""
    # Verify key exists in DB
    result = await db.execute(select(Attachment).where(Attachment.key == key))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    url = await storage_service.get_presigned_url(key)
    return {"url": url}
