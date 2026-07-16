"""
Tests for Moment 3 Email Attachment Endpoint

Validates:
1. Email endpoint stores requester_email on the request document
2. If request has audience_id and a different audience_id is provided, returns 403
3. audience.email_submitted event is emitted with correct context and does not include raw email
"""
import pytest
import requests
import os
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import MongoClient
import time

# Test database connection
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Get API URL from environment or use default
API_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://multi-profile-events-1.preview.emergentagent.com")


@pytest.fixture(scope="module")
def db():
    """Module-scoped MongoDB connection for verifications."""
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def test_musician(db):
    """Create a test musician for email attachment tests."""
    musician_id = f"test-musician-email-{uuid4().hex[:8]}"
    email = f"test-email-{uuid4().hex[:8]}@example.com"
    slug = f"test-musician-email-{uuid4().hex[:8]}"
    musician_data = {
        "id": musician_id,
        "email": email,
        "email_lc": email.lower(),
        "name": "Test Musician Email",
        "slug": slug,
        "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferBqGFbLhGi",
        "bio": "",
        "tips_enabled": True,
        "requests_enabled": True,
        "audience_link_active": True,
        "current_show_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    db.musicians.insert_one(musician_data)
    yield musician_data
    db.musicians.delete_one({"id": musician_id})


@pytest.fixture(scope="module")
def test_show(test_musician, db):
    """Create a test show."""
    show_id = f"show-email-{uuid4().hex[:8]}"
    show_data = {
        "id": show_id,
        "musician_id": test_musician["id"],
        "name": "Email Test Show",
        "date": "2026-01-20",
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }
    db.shows.insert_one(show_data)
    db.musicians.update_one(
        {"id": test_musician["id"]},
        {"$set": {"current_show_id": show_id}}
    )
    yield show_data
    db.shows.delete_one({"id": show_id})


@pytest.fixture(scope="module")
def test_song(test_musician, db):
    """Create a test song."""
    song_id = f"song-email-{uuid4().hex[:8]}"
    song_data = {
        "id": song_id,
        "musician_id": test_musician["id"],
        "title": "Email Test Song",
        "artist": "Test Artist",
        "genres": ["Pop"],
        "moods": ["Feel Good"],
        "year": 2024,
        "request_count": 0,
        "hidden": False,
        "created_at": datetime.now(timezone.utc),
    }
    db.songs.insert_one(song_data)
    yield song_data
    db.songs.delete_one({"id": song_id})


# =============================================================================
# TEST 1: Email endpoint stores requester_email on the request document
# =============================================================================

def test_email_endpoint_stores_email(test_musician, test_show, test_song, db):
    """Email endpoint stores requester_email on the request document."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # Create a request without email (as Moment 2 does now)
    create_response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Email Test User",
            "requester_email": "",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    assert create_response.status_code == 200
    request_id = create_response.json()["id"]
    
    # Verify request has no email
    request_doc = db.requests.find_one({"id": request_id})
    assert request_doc["requester_email"] == ""
    
    # Attach email via Moment 3 endpoint
    email_response = requests.post(
        f"{API_URL}/api/requests/{request_id}/email",
        json={
            "email": "testuser@example.com",
            "audience_id": audience_id
        }
    )
    
    assert email_response.status_code == 200
    data = email_response.json()
    assert data["ok"] == True
    assert data["request_id"] == request_id
    assert data["email"] == "testuser@example.com"
    
    # Verify email is stored on request
    updated_request = db.requests.find_one({"id": request_id})
    assert updated_request["requester_email"] == "testuser@example.com"
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


# =============================================================================
# TEST 2: Returns 403 if request has audience_id and different one is provided
# =============================================================================

def test_email_endpoint_403_on_audience_id_mismatch(test_musician, test_show, test_song, db):
    """Returns 403 if request has audience_id and a different audience_id is provided."""
    original_audience_id = f"original-audience-{uuid4().hex[:8]}"
    different_audience_id = f"different-audience-{uuid4().hex[:8]}"
    
    # Create a request with original audience_id
    create_response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Security Test User",
            "requester_email": "",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": original_audience_id
        }
    )
    assert create_response.status_code == 200
    request_id = create_response.json()["id"]
    
    # Try to attach email with different audience_id
    email_response = requests.post(
        f"{API_URL}/api/requests/{request_id}/email",
        json={
            "email": "hacker@example.com",
            "audience_id": different_audience_id
        }
    )
    
    assert email_response.status_code == 403
    assert "mismatch" in email_response.json()["detail"].lower()
    
    # Verify email was NOT updated
    request_doc = db.requests.find_one({"id": request_id})
    assert request_doc["requester_email"] == ""
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


# =============================================================================
# TEST 3: audience.email_submitted event emitted with correct context, no raw email
# =============================================================================

def test_email_submitted_event_emitted_correctly(test_musician, test_show, test_song, db):
    """audience.email_submitted event is emitted with correct context and no raw email."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # Create a request
    create_response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Analytics Test User",
            "requester_email": "",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    assert create_response.status_code == 200
    request_id = create_response.json()["id"]
    
    # Attach email
    email_response = requests.post(
        f"{API_URL}/api/requests/{request_id}/email",
        json={
            "email": "analytics@example.com",
            "audience_id": audience_id
        }
    )
    assert email_response.status_code == 200
    
    # Wait for async event to be written
    time.sleep(0.5)
    
    # Verify analytics event
    event = db.analytics_events.find_one({
        "event_type": "audience.email_submitted",
        "entity_id": request_id
    })
    
    assert event is not None, "audience.email_submitted event should be emitted"
    assert event["musician_id"] == test_musician["id"]
    assert event["show_id"] == test_show["id"]
    assert event["metadata"]["audience_id"] == audience_id
    assert event["metadata"]["email_provided"] == True
    
    # Verify NO raw email in metadata
    assert "email" not in event["metadata"] or event["metadata"].get("email") is None
    assert "analytics@example.com" not in str(event["metadata"])
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


# =============================================================================
# TEST 4: Invalid email format returns 400
# =============================================================================

def test_email_endpoint_validates_format(test_musician, test_show, test_song, db):
    """Invalid email format returns 400."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # Create a request
    create_response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Format Test User",
            "requester_email": "",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    assert create_response.status_code == 200
    request_id = create_response.json()["id"]
    
    # Try to attach invalid email
    email_response = requests.post(
        f"{API_URL}/api/requests/{request_id}/email",
        json={
            "email": "not-an-email",
            "audience_id": audience_id
        }
    )
    
    assert email_response.status_code == 400
    assert "invalid" in email_response.json()["detail"].lower()
    
    # Cleanup
    db.requests.delete_one({"id": request_id})


# =============================================================================
# TEST 5: Request not found returns 404
# =============================================================================

def test_email_endpoint_404_on_missing_request(db):
    """Returns 404 if request does not exist."""
    fake_request_id = f"nonexistent-{uuid4().hex}"
    
    email_response = requests.post(
        f"{API_URL}/api/requests/{fake_request_id}/email",
        json={
            "email": "test@example.com"
        }
    )
    
    assert email_response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
