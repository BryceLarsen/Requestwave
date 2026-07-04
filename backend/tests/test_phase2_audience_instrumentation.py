"""
Tests for Phase 2: Audience Interaction Capture

Uses HTTP requests against the running backend server to validate:
1. audience_id is stored on requests when provided
2. audience_id is stored on tips when provided
3. audience.tip_clicked and audience.follow_clicked events are emitted with correct context
4. audience.tip_completed is emitted with show_id when provided
5. audience.dedication_submitted fires only when dedication is non-empty

These tests require the backend server to be running.
"""
import pytest
import requests
import os
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import MongoClient
import time

# Test database connection (direct, not via Motor)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Get API URL from environment or use default
API_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://profile-events-1.preview.emergentagent.com")


@pytest.fixture(scope="module")
def db():
    """Module-scoped MongoDB connection for verifications."""
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def test_musician(db):
    """Create a test musician for Phase 2 tests."""
    musician_id = f"test-musician-p2-{uuid4().hex[:8]}"
    email = f"test-p2-{uuid4().hex[:8]}@example.com"
    slug = f"test-musician-p2-{uuid4().hex[:8]}"
    musician_data = {
        "id": musician_id,
        "email": email,
        "email_lc": email.lower(),
        "name": "Test Musician Phase 2",
        "slug": slug,
        "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferBqGFbLhGi",  # "test"
        "bio": "",
        "website": "",
        "tips_enabled": True,
        "requests_enabled": True,
        "paypal_username": "testmusician",
        "paypal_enabled": True,
        "venmo_enabled": True,
        "cash_app_enabled": True,
        "zelle_enabled": True,
        "audience_link_active": True,
        "current_show_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    db.musicians.insert_one(musician_data)
    yield musician_data
    # Cleanup
    db.musicians.delete_one({"id": musician_id})


@pytest.fixture(scope="module")
def test_show(test_musician, db):
    """Create a test show and set it as current for the musician."""
    show_id = f"show-p2-{uuid4().hex[:8]}"
    
    show_data = {
        "id": show_id,
        "musician_id": test_musician["id"],
        "name": "Phase 2 Test Show",
        "date": "2026-01-20",
        "venue": "Test Venue",
        "notes": "",
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }
    
    db.shows.insert_one(show_data)
    
    # Update musician's current_show_id
    db.musicians.update_one(
        {"id": test_musician["id"]},
        {"$set": {"current_show_id": show_id, "current_show_name": "Phase 2 Test Show"}}
    )
    
    yield show_data
    
    # Cleanup
    db.shows.delete_one({"id": show_id})


@pytest.fixture(scope="module")
def test_song(test_musician, db):
    """Create a test song for request tests."""
    song_id = f"song-p2-{uuid4().hex[:8]}"
    
    song_data = {
        "id": song_id,
        "musician_id": test_musician["id"],
        "title": "Phase 2 Test Song",
        "artist": "Test Artist",
        "genres": ["Pop"],
        "moods": ["Feel Good"],
        "year": 2024,
        "notes": "",
        "request_count": 0,
        "hidden": False,
        "created_at": datetime.now(timezone.utc),
    }
    
    db.songs.insert_one(song_data)
    yield song_data
    
    # Cleanup
    db.songs.delete_one({"id": song_id})


# =============================================================================
# TEST 1: audience_id is stored on requests when provided
# =============================================================================

def test_audience_id_stored_on_request(test_musician, test_show, test_song, db):
    """audience_id is stored on the request document when provided."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Test Requester",
            "requester_email": "requester@test.com",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    request_id = data["id"]
    
    # Verify audience_id is stored in the request
    request_doc = db.requests.find_one({"id": request_id})
    assert request_doc is not None
    assert request_doc.get("audience_id") == audience_id
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


# =============================================================================
# TEST 2: audience_id is stored on tips when provided
# =============================================================================

def test_audience_id_stored_on_tip(test_musician, test_show, db):
    """audience_id is stored on the tip document when provided."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/tips",
        json={
            "amount": 5.0,
            "platform": "paypal",
            "tipper_name": "Test Tipper",
            "audience_id": audience_id,
            "show_id": test_show["id"]
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    tip_id = data["tip_id"]
    
    # Verify audience_id and show_id are stored in the tip
    tip_doc = db.tips.find_one({"id": tip_id})
    assert tip_doc is not None
    assert tip_doc.get("audience_id") == audience_id
    assert tip_doc.get("show_id") == test_show["id"]
    
    # Cleanup
    db.tips.delete_one({"id": tip_id})
    db.analytics_events.delete_many({"entity_id": tip_id})


# =============================================================================
# TEST 3: audience.tip_clicked event emitted with correct context
# =============================================================================

def test_tip_clicked_event_has_correct_context(test_musician, test_show, test_song, db):
    """audience.tip_clicked event has correct musician_id, show_id, audience_id."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # First create a request
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Test Requester",
            "requester_email": "requester@test.com",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    
    assert response.status_code == 200
    request_id = response.json()["id"]
    
    # Track tip click
    click_response = requests.post(
        f"{API_URL}/api/requests/{request_id}/track-click",
        json={
            "type": "tip",
            "platform": "venmo",
            "audience_id": audience_id
        }
    )
    
    assert click_response.status_code == 200
    
    # Wait for async event to be written
    time.sleep(0.5)
    
    # Verify event was emitted with correct context
    event = db.analytics_events.find_one({
        "event_type": "audience.tip_clicked",
        "entity_id": request_id
    })
    
    assert event is not None, "audience.tip_clicked event should be emitted"
    assert event["musician_id"] == test_musician["id"]
    assert event["show_id"] == test_show["id"]
    assert event["metadata"]["audience_id"] == audience_id
    assert event["metadata"]["platform"] == "venmo"
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


# =============================================================================
# TEST 4: audience.follow_clicked event emitted with correct context
# =============================================================================

def test_follow_clicked_event_has_correct_context(test_musician, test_show, test_song, db):
    """audience.follow_clicked event has correct musician_id, show_id, audience_id."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # First create a request
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Test Requester",
            "requester_email": "requester@test.com",
            "dedication": "",
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    
    assert response.status_code == 200
    request_id = response.json()["id"]
    
    # Track social click
    click_response = requests.post(
        f"{API_URL}/api/requests/{request_id}/track-click",
        json={
            "type": "social",
            "platform": "instagram",
            "audience_id": audience_id
        }
    )
    
    assert click_response.status_code == 200
    
    # Wait for async event to be written
    time.sleep(0.5)
    
    # Verify event was emitted with correct context
    event = db.analytics_events.find_one({
        "event_type": "audience.follow_clicked",
        "entity_id": request_id
    })
    
    assert event is not None, "audience.follow_clicked event should be emitted"
    assert event["musician_id"] == test_musician["id"]
    assert event["show_id"] == test_show["id"]
    assert event["metadata"]["audience_id"] == audience_id
    assert event["metadata"]["platform"] == "instagram"
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


# =============================================================================
# TEST 5: audience.tip_completed event emitted with show_id when provided
# =============================================================================

def test_tip_completed_event_has_show_id(test_musician, test_show, db):
    """audience.tip_completed event includes show_id when provided."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/tips",
        json={
            "amount": 10.0,
            "platform": "paypal",
            "tipper_name": "Generous Fan",
            "message": "Great show!",
            "audience_id": audience_id,
            "show_id": test_show["id"]
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    tip_id = data["tip_id"]
    
    # Wait for async event to be written
    time.sleep(0.5)
    
    # Verify event was emitted with correct context
    event = db.analytics_events.find_one({
        "event_type": "audience.tip_completed",
        "entity_id": tip_id
    })
    
    assert event is not None, "audience.tip_completed event should be emitted"
    assert event["musician_id"] == test_musician["id"]
    assert event["show_id"] == test_show["id"], "show_id should match provided value"
    assert event["metadata"]["amount"] == 10.0
    assert event["metadata"]["platform"] == "paypal"
    assert event["metadata"]["audience_id"] == audience_id
    
    # Cleanup
    db.tips.delete_one({"id": tip_id})
    db.analytics_events.delete_many({"entity_id": tip_id})


# =============================================================================
# TEST 6: audience.dedication_submitted fires ONLY when dedication is non-empty
# =============================================================================

def test_dedication_event_fires_when_dedication_present(test_musician, test_show, test_song, db):
    """audience.dedication_submitted is emitted when dedication is non-empty."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    dedication_text = "Happy Birthday to my friend!"
    
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Test Requester",
            "requester_email": "requester@test.com",
            "dedication": dedication_text,
            "tip_amount": 5.0,
            "audience_id": audience_id
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    request_id = data["id"]
    
    # Wait for async event to be written
    time.sleep(0.5)
    
    # Verify dedication event was emitted
    event = db.analytics_events.find_one({
        "event_type": "audience.dedication_submitted",
        "entity_id": request_id
    })
    
    assert event is not None, "audience.dedication_submitted event should be emitted"
    assert event["musician_id"] == test_musician["id"]
    assert event["show_id"] == test_show["id"]
    assert event["metadata"]["audience_id"] == audience_id
    assert event["metadata"]["dedication_length"] == len(dedication_text)
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


def test_dedication_event_does_not_fire_when_empty(test_musician, test_show, test_song, db):
    """audience.dedication_submitted is NOT emitted when dedication is empty."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Test Requester",
            "requester_email": "requester@test.com",
            "dedication": "",  # Empty dedication
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    request_id = data["id"]
    
    # Wait for async event to potentially be written
    time.sleep(0.5)
    
    # Verify dedication event was NOT emitted
    event = db.analytics_events.find_one({
        "event_type": "audience.dedication_submitted",
        "entity_id": request_id
    })
    
    assert event is None, "audience.dedication_submitted should NOT be emitted for empty dedication"
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


def test_dedication_event_does_not_fire_when_whitespace_only(test_musician, test_show, test_song, db):
    """audience.dedication_submitted is NOT emitted when dedication is whitespace only."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    response = requests.post(
        f"{API_URL}/api/musicians/{test_musician['slug']}/requests",
        json={
            "song_id": test_song["id"],
            "requester_name": "Test Requester",
            "requester_email": "requester@test.com",
            "dedication": "   ",  # Whitespace only
            "tip_amount": 0,
            "audience_id": audience_id
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    request_id = data["id"]
    
    # Wait for async event to potentially be written
    time.sleep(0.5)
    
    # Verify dedication event was NOT emitted
    event = db.analytics_events.find_one({
        "event_type": "audience.dedication_submitted",
        "entity_id": request_id
    })
    
    assert event is None, "audience.dedication_submitted should NOT be emitted for whitespace-only dedication"
    
    # Cleanup
    db.requests.delete_one({"id": request_id})
    db.analytics_events.delete_many({"entity_id": request_id})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
