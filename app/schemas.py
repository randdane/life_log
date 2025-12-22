from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime

class AttachmentBase(BaseModel):
    filename: str
    content_type: str
    size_bytes: int

class AttachmentRead(AttachmentBase):
    id: int
    key: str
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    timestamp: Optional[datetime] = None
    metadata_json: Optional[dict] = None

class EventCreate(EventBase):
    pass

class EventRead(EventBase):
    id: int
    created_at: datetime
    timestamp: datetime # Override because it's guaranteed in Read
    attachments: List[AttachmentRead] = []
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedEvents(BaseModel):
    items: List[EventRead]
    total: int
    page: int
    page_size: int
