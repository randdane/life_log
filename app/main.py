"""Main application file for the LifeLog API."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import attachments, auth, events, export
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_token
from app.schemas import PaginatedEvents, SortOrder

# RustFS Client Global
rustfs_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events.

    Initializes the RustFS client and ensures the required bucket exists.
    """
    # Startup
    global rustfs_client
    print("Starting up LifeLog...")

    # Initialize RustFS
    try:
        rustfs_client = Minio(
            settings.RUSTFS_ENDPOINT,
            access_key=settings.RUSTFS_ACCESS_KEY,
            secret_key=settings.RUSTFS_SECRET_KEY,
            secure=settings.RUSTFS_SECURE,
        )
        if not rustfs_client.bucket_exists(settings.RUSTFS_BUCKET):
            rustfs_client.make_bucket(settings.RUSTFS_BUCKET)
            print(f"Created RustFS bucket: {settings.RUSTFS_BUCKET}")
    except Exception as e:
        print(f"Error connecting to RustFS: {e}")

    yield

    # Shutdown
    print("Shutting down LifeLog...")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


# Include API routers
app.include_router(events.router, prefix="/api")
app.include_router(attachments.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/health")
def health_check():
    """Check the health of the API."""
    return {"status": "ok", "app": settings.PROJECT_NAME}


@app.get("/")
def read_root():
    """Root endpoint for the API."""
    return {"message": "Welcome to LifeLog API"}


@app.get("/api/search", response_model=PaginatedEvents, tags=["events"])
async def search_events_alias(
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
    """Alias for GET /api/events."""
    return await events.list_events(db, token, q, tags, start, end, page, page_size, sort)
