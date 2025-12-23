"""API router for Data Export."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_token
from app.models import Event
from app.schemas import EventRead

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/", response_model=list[EventRead])
async def export_data(
    db: Annotated[AsyncSession, Depends(get_db)], token: Annotated[str, Depends(get_current_token)]
):
    """Export all events and attachment metadata as JSON."""
    result = await db.execute(select(Event).order_by(Event.timestamp.desc()))
    return result.scalars().all()
