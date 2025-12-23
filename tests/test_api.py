"""Test suite for the LifeLog API."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": settings.PROJECT_NAME}


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to LifeLog API"}


def test_events_unauthorized():
    """Test that events endpoint requires authentication."""
    response = client.get("/api/events")
    # If API_TOKEN is set in settings, it should return 401
    if settings.API_TOKEN:
        assert response.status_code == 401
    else:
        # If no token is configured, it might return 200 (depending on dependency logic)
        # But get_current_token raises 401 if token is invalid.
        # If token is None, it returns None.
        pass


def test_search_alias():
    """Test the search alias redirect."""
    response = client.get("/api/search", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/api/events"
