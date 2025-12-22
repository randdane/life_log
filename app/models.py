from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, BigInteger, func, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from datetime import datetime
from typing import List, Optional
from app.database import Base

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    
    # For now, we'll assume the search_vector will be handled via Alembic migrations 
    # to add the GENERATED ALWAYS AS column or triggers, as SQLAlchemy support for 
    # generated tsvector columns can be verbose.
    
    attachments: Mapped[List["Attachment"]] = relationship("Attachment", back_populates="event", cascade="all, delete-orphan")

class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped["Event"] = relationship("Event", back_populates="attachments")
