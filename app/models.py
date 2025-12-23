"""SQLModel models for the LifeLog API."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship

from app.database import Base


class Event(Base, table=True):
    """Represents a log entry or event in the LifeLog system."""

    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True, index=True, sa_type=BigInteger)
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    timestamp: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )
    title: str = Field(sa_column=Column(Text, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    tags: Any = Field(default=None, sa_column=Column(ARRAY(Text)))
    metadata_json: Any = Field(default=None, sa_column=Column("metadata", JSONB))

    # For now, we'll assume the search_vector will be handled via Alembic migrations
    # to add the GENERATED ALWAYS AS column or triggers, as SQLAlchemy support for
    # generated tsvector columns can be verbose.

    attachments: list[Attachment] = Relationship(
        back_populates="event",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )


class Attachment(Base, table=True):
    """Represents a file attachment associated with an Event."""

    __tablename__ = "attachments"

    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    event_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    )
    key: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    filename: str = Field(sa_column=Column(Text, nullable=False))
    content_type: str = Field(sa_column=Column(Text, nullable=False))
    size_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    uploaded_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    event: Event = Relationship(back_populates="attachments")
