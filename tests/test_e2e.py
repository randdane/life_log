import httpx
import pytest

from app.config import settings

BASE_URL = "http://localhost:8000"


@pytest.fixture
def auth_headers():
    """Get auth headers for API requests."""
    if not settings.API_TOKEN:
        pytest.fail("APP_AUTH_API_TOKEN is not set in environment")
    return {"Authorization": f"Bearer {settings.API_TOKEN}"}


def test_event_creation_with_attachment(auth_headers):
    """Test event creation with attachment."""
    # 1. Create an event for E2E testing.
    event_data = {
        "title": "E2E Test Event",
        "description": "Created by E2E test suite",
        "tags": ["test", "e2e"],
        "metadata_json": {"source": "pytest"},
    }

    with httpx.Client(base_url=BASE_URL) as client:
        # Create the event.
        response = client.post("/api/events/", json=event_data, headers=auth_headers)
        assert response.status_code == 201, response.text
        event = response.json()
        event_id = event["id"]
        assert event["title"] == event_data["title"]

        # 2. Upload an attachment to the event.
        files = {"files": ("test_attachment.txt", b"Hello from E2E test!", "text/plain")}
        response = client.post(
            f"/api/events/{event_id}/attachments", files=files, headers=auth_headers
        )
        assert response.status_code == 201, response.text
        attachments = response.json()
        assert len(attachments) == 1
        attachment = attachments[0]
        assert attachment["filename"] == "test_attachment.txt"
        attachment_key = attachment["key"]

        # 3. Query the event to ensure attachment is there.
        response = client.get(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 200
        event_with_att = response.json()
        assert len(event_with_att["attachments"]) == 1
        assert event_with_att["attachments"][0]["key"] == attachment_key

        # 4. Get presigned URL and verify it's accessible.
        response = client.get(f"/api/attachments/{attachment_key}", headers=auth_headers)
        assert response.status_code == 200
        url_data = response.json()
        assert "url" in url_data

        # 5. Delete the event.
        response = client.delete(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 204

        # 6. Verify event is gone.
        response = client.get(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 404
