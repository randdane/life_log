"""API router for Event resources."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_token
from app.schemas import EventCreate, EventRead, EventUpdate, PaginatedEvents, SortOrder
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
):
    """Create a new life log event."""
    return await EventService.create_event(db, event_in)


@router.get("/", response_model=PaginatedEvents)
async def list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
    q: Annotated[str | None, Query(description="Search query")] = None,
    tags: Annotated[str | None, Query(description="Comma-separated tags")] = None,
    start: Annotated[datetime | None, Query(description="Start date filter")] = None,
    end: Annotated[datetime | None, Query(description="End date filter")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    sort: SortOrder = SortOrder.NEWEST,
):
    """List events with optional filtering and search."""
    skip = (page - 1) * page_size
    tags_list = tags.split(",") if tags else None

    items, total = await EventService.list_events(
        db,
        skip=skip,
        limit=page_size,
        query=q,
        tags=tags_list,
        start_date=start,
        end_date=end,
        sort=sort,
    )

    return PaginatedEvents(items=items, total=total, page=page, page_size=page_size)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
):
    """Get a specific event by ID."""
    event = await EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
):
    """Update an existing event."""
    event = await EventService.update_event(db, event_id, event_in)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(get_current_token)],
):
    """Delete an event and its associated attachments."""
    # Note: Service handles DB cascade and attachment cleanup
    # would happen here or via background task
    success = await EventService.delete_event(db, event_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
