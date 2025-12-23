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
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_search_alias():
    """Test that search endpoint requires authentication."""
    # Without auth, should fail
    response = client.get("/api/search")
    assert response.status_code == 401
