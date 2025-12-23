"""SQLModel models for the LifeLog API."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship

from app.database import Base


class Event(Base, table=True):
    """Represents a log entry or event in the LifeLog system."""

    __tablename__ = "events"

    id: int | None = Field(
        default=None, sa_column=mapped_column(BigInteger, primary_key=True, index=True)
    )
    created_at: datetime = Field(
        sa_column=mapped_column(DateTime(timezone=True), server_default=func.now())
    )
    timestamp: datetime = Field(
        sa_column=mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    )
    title: str = Field(sa_column=mapped_column(Text, nullable=False))
    description: str | None = Field(default=None, sa_column=mapped_column(Text))
    tags: list[str] | None = Field(default=None, sa_column=mapped_column(ARRAY(Text)))
    metadata_json: dict | None = Field(default=None, sa_column=mapped_column("metadata", JSONB))

    # For now, we'll assume the search_vector will be handled via Alembic migrations
    # to add the GENERATED ALWAYS AS column or triggers, as SQLAlchemy support for
    # generated tsvector columns can be verbose.

    attachments: list[Attachment] = Relationship(
        back_populates="event", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Attachment(Base, table=True):
    """Represents a file attachment associated with an Event."""

    __tablename__ = "attachments"

    id: int | None = Field(default=None, sa_column=mapped_column(BigInteger, primary_key=True))
    event_id: int = Field(
        sa_column=mapped_column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    )
    key: str = Field(sa_column=mapped_column(Text, unique=True, nullable=False))
    filename: str = Field(sa_column=mapped_column(Text, nullable=False))
    content_type: str = Field(sa_column=mapped_column(Text, nullable=False))
    size_bytes: int = Field(sa_column=mapped_column(BigInteger, nullable=False))
    uploaded_at: datetime = Field(
        sa_column=mapped_column(DateTime(timezone=True), server_default=func.now())
    )

    event: Event = Relationship(back_populates="attachments")
