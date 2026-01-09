"""Service layer for handling Event business logic and database operations."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Event
from app.schemas import EventCreate, EventUpdate, SortOrder


class EventService:
    """Service layer for event-related database operations."""

    @staticmethod
    async def create_event(db: AsyncSession, event_in: EventCreate) -> Event:
        """Create a new event."""
        db_event = Event.model_validate(event_in)
        if not db_event.timestamp:
            db_event.timestamp = datetime.now()
        db.add(db_event)
        await db.commit()
        # Refresh with attachments to ensure they are available for serialization
        await db.refresh(db_event, ["attachments"])
        return db_event

    @staticmethod
    async def get_event(db: AsyncSession, event_id: int) -> Event | None:
        """Get an event by ID with its attachments."""
        result = await db.execute(
            select(Event).where(Event.id == event_id).options(selectinload(Event.attachments))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_events(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 25,
        query: str | None = None,
        tags: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sort: SortOrder = SortOrder.NEWEST,
    ) -> tuple[Sequence[Event], int]:
        """List events with filtering, search, and pagination."""
        stmt = select(Event).options(selectinload(Event.attachments))

        # Filtering
        if tags:
            # PostgreSQL array overlap operator &&
            stmt = stmt.where(Event.tags.overlap(tags))

        if start_date:
            stmt = stmt.where(Event.timestamp >= start_date)

        if end_date:
            stmt = stmt.where(Event.timestamp <= end_date)

        # Full Text Search (Basic implementation for now, should use tsvector in production)
        if query:
            # We use ILIKE for a simple case-insensitive search if search_vector is not yet used
            stmt = stmt.where(
                (Event.title.ilike(f"%{query}%")) | (Event.description.ilike(f"%{query}%"))
            )

        # Total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        # Sorting
        if sort == SortOrder.NEWEST:
            stmt = stmt.order_by(Event.timestamp.desc())
        else:
            stmt = stmt.order_by(Event.timestamp.asc())

        # Pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all(), total

    @staticmethod
    async def update_event(db: AsyncSession, event_id: int, event_in: EventUpdate) -> Event | None:
        """Partially update an event."""
        db_event = await EventService.get_event(db, event_id)
        if not db_event:
            return None

        update_data = event_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_event, key, value)

        db.add(db_event)
        await db.commit()
        await db.refresh(db_event, ["attachments"])
        return db_event

    @staticmethod
    async def delete_event(db: AsyncSession, event_id: int) -> bool:
        """Delete an event and its associated files from storage."""
        from app.services.storage_service import storage_service

        db_event = await EventService.get_event(db, event_id)
        if not db_event:
            return False

        # Pre-fetch attachment keys for storage cleanup
        attachment_keys = [att.key for att in db_event.attachments]

        await db.delete(db_event)
        await db.commit()

        # Delete from RustFS after DB commit for safety
        import contextlib

        for key in attachment_keys:
            with contextlib.suppress(Exception):
                await storage_service.delete_file(key)

        return True
