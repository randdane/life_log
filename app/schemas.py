"""Pydantic schemas for data validation and serialization in the LifeLog API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentBase(BaseModel):
    """Base schema for attachment data."""

    filename: str
    content_type: str
    size_bytes: int


class AttachmentRead(AttachmentBase):
    """Schema for reading attachment information."""

    id: int
    key: str
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    """Base schema for event data."""

    title: str
    description: str | None = None
    tags: list[str] | None = []
    timestamp: datetime | None = None
    metadata_json: dict | None = None


class EventCreate(EventBase):
    """Schema for creating a new event."""

    pass


class EventRead(EventBase):
    """Schema for reading event information, including attachments."""

    id: int
    created_at: datetime
    timestamp: datetime  # Override because it's guaranteed in Read
    attachments: list[AttachmentRead] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedEvents(BaseModel):
    """Schema for a paginated list of events."""

    items: list[EventRead]
    total: int
    page: int
    page_size: int
