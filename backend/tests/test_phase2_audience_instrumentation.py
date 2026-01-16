"""
Tests for Phase 2: Audience Interaction Capture

Validates:
1. audience_id is stored correctly on requests and tips
2. Four new analytics events are emitted with correct context:
   - audience.dedication_submitted (conditional on dedication being present)
   - audience.tip_clicked
   - audience.follow_clicked
   - audience.tip_completed
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# Configure pytest-asyncio to use session scope for event loop
pytestmark = pytest.mark.asyncio

# Set up test database connection directly
TEST_MONGO_URL = "mongodb://localhost:27017"
TEST_DB_NAME = "test_database"

# Add backend to path and import app
sys.path.insert(0, '/app/backend')

# Override the db before importing app
os.environ["MONGO_URL"] = TEST_MONGO_URL
os.environ["DB_NAME"] = TEST_DB_NAME

from server import app

# Create db connection inside fixture to avoid event loop issues
async def get_test_db():
    client = AsyncIOMotorClient(TEST_MONGO_URL)
    return client[TEST_DB_NAME]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_db_conn():
    """Get test database connection."""
    client = AsyncIOMotorClient(TEST_MONGO_URL)
    db = client[TEST_DB_NAME]
    yield db
    client.close()


@pytest_asyncio.fixture
async def test_musician(test_db_conn):
    """Create a test musician for Phase 2 tests."""
    db = test_db_conn
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
        "current_show_id": None,  # Will be set by test_show
        "created_at": datetime.now(timezone.utc),
    }
    await db.musicians.insert_one(musician_data)
    yield musician_data
    # Cleanup
    await db.musicians.delete_one({"id": musician_id})


@pytest_asyncio.fixture
async def test_show(test_musician, test_db_conn):
    """Create a test show for the musician."""
    db = test_db_conn
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
    
    await db.shows.insert_one(show_data)
    
    # Update musician's current_show_id
    await db.musicians.update_one(
        {"id": test_musician["id"]},
        {"$set": {"current_show_id": show_id, "current_show_name": "Phase 2 Test Show"}}
    )
    
    yield show_data
    
    # Cleanup
    await db.shows.delete_one({"id": show_id})


@pytest_asyncio.fixture
async def test_song(test_musician, test_db_conn):
    """Create a test song for request tests."""
    db = test_db_conn
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
    
    await db.songs.insert_one(song_data)
    yield song_data
    
    # Cleanup
    await db.songs.delete_one({"id": song_id})


@pytest_asyncio.fixture
async def cleanup_analytics(test_db_conn):
    """Clean up analytics events after each test."""
    db = test_db_conn
    yield
    # Clean up Phase 2 test analytics events
    await db.analytics_events.delete_many({
        "event_type": {
            "$in": [
                "audience.dedication_submitted",
                "audience.tip_clicked",
                "audience.follow_clicked",
                "audience.tip_completed",
                "audience.request_submitted"
            ]
        },
        "metadata.audience_id": {"$regex": "^test-audience-"}
    })


@pytest_asyncio.fixture
async def cleanup_requests(test_musician, test_db_conn):
    """Clean up test requests after tests."""
    db = test_db_conn
    yield
    await db.requests.delete_many({"musician_id": test_musician["id"]})


@pytest_asyncio.fixture
async def cleanup_tips(test_musician, test_db_conn):
    """Clean up test tips after tests."""
    db = test_db_conn
    yield
    await db.tips.delete_many({"musician_id": test_musician["id"]})


# =============================================================================
# TEST: audience_id is stored correctly on requests
# =============================================================================

@pytest.mark.asyncio
async def test_audience_id_stored_on_request(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """audience_id is stored on the request document when provided."""
    db = test_db_conn
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
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
        data = response.json()
        request_id = data["id"]
        
        # Verify audience_id is stored in the request
        request_doc = await db.requests.find_one({"id": request_id})
        assert request_doc is not None
        assert request_doc.get("audience_id") == audience_id


@pytest.mark.asyncio
async def test_request_without_audience_id_still_works(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """Requests can be created without audience_id (backward compatible)."""
    db = test_db_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
            json={
                "song_id": test_song["id"],
                "requester_name": "Test Requester",
                "requester_email": "requester@test.com",
                "dedication": "",
                "tip_amount": 0
                # No audience_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        request_id = data["id"]
        
        # Verify request was created
        request_doc = await db.requests.find_one({"id": request_id})
        assert request_doc is not None
        # audience_id should be None or not present
        assert request_doc.get("audience_id") is None


# =============================================================================
# TEST: audience.dedication_submitted event (conditional)
# =============================================================================

@pytest.mark.asyncio
async def test_dedication_submitted_event_emitted_when_dedication_present(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """audience.dedication_submitted event is emitted when dedication is non-empty."""
    db = test_db_conn
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    dedication_text = "Happy Birthday to my friend!"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
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
        
        # Give a moment for async event to be written
        await asyncio.sleep(0.3)
        
        # Verify audience.dedication_submitted event was emitted
        event = await db.analytics_events.find_one({
            "event_type": "audience.dedication_submitted",
            "entity_id": request_id
        })
        
        assert event is not None, "audience.dedication_submitted event should be emitted"
        assert event["musician_id"] == test_musician["id"]
        assert event["show_id"] == test_show["id"]
        assert event["metadata"]["audience_id"] == audience_id
        assert event["metadata"]["dedication_length"] == len(dedication_text)


@pytest.mark.asyncio
async def test_dedication_submitted_event_not_emitted_when_dedication_empty(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """audience.dedication_submitted event is NOT emitted when dedication is empty."""
    db = test_db_conn
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
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
        
        # Give a moment for async event to potentially be written
        await asyncio.sleep(0.3)
        
        # Verify audience.dedication_submitted event was NOT emitted
        event = await db.analytics_events.find_one({
            "event_type": "audience.dedication_submitted",
            "entity_id": request_id
        })
        
        assert event is None, "audience.dedication_submitted should NOT be emitted for empty dedication"


@pytest.mark.asyncio
async def test_dedication_submitted_event_not_emitted_when_dedication_whitespace_only(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """audience.dedication_submitted event is NOT emitted when dedication is whitespace only."""
    db = test_db_conn
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
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
        
        # Give a moment for async event to potentially be written
        await asyncio.sleep(0.3)
        
        # Verify audience.dedication_submitted event was NOT emitted
        event = await db.analytics_events.find_one({
            "event_type": "audience.dedication_submitted",
            "entity_id": request_id
        })
        
        assert event is None, "audience.dedication_submitted should NOT be emitted for whitespace-only dedication"


# =============================================================================
# TEST: audience.tip_clicked event
# =============================================================================

@pytest.mark.asyncio
async def test_tip_clicked_event_emitted(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """audience.tip_clicked event is emitted when tip link is clicked."""
    db = test_db_conn
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # First create a request
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
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
        
        # Now track tip click
        click_response = await client.post(
            f"/api/requests/{request_id}/track-click",
            json={
                "type": "tip",
                "platform": "venmo",
                "audience_id": audience_id
            }
        )
        
        assert click_response.status_code == 200
        
        # Give a moment for async event to be written
        await asyncio.sleep(0.3)
        
        # Verify audience.tip_clicked event was emitted
        event = await db.analytics_events.find_one({
            "event_type": "audience.tip_clicked",
            "entity_id": request_id
        })
        
        assert event is not None, "audience.tip_clicked event should be emitted"
        assert event["musician_id"] == test_musician["id"]
        assert event["show_id"] == test_show["id"]
        assert event["metadata"]["platform"] == "venmo"
        assert event["metadata"]["audience_id"] == audience_id


# =============================================================================
# TEST: audience.follow_clicked event
# =============================================================================

@pytest.mark.asyncio
async def test_follow_clicked_event_emitted(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, test_db_conn
):
    """audience.follow_clicked event is emitted when social link is clicked."""
    db = test_db_conn
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    # First create a request
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
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
        
        # Now track social click
        click_response = await client.post(
            f"/api/requests/{request_id}/track-click",
            json={
                "type": "social",
                "platform": "instagram",
                "audience_id": audience_id
            }
        )
        
        assert click_response.status_code == 200
        
        # Give a moment for async event to be written
        await asyncio.sleep(0.3)
        
        # Verify audience.follow_clicked event was emitted
        event = await db.analytics_events.find_one({
            "event_type": "audience.follow_clicked",
            "entity_id": request_id
        })
        
        assert event is not None, "audience.follow_clicked event should be emitted"
        assert event["musician_id"] == test_musician["id"]
        assert event["show_id"] == test_show["id"]
        assert event["metadata"]["platform"] == "instagram"
        assert event["metadata"]["audience_id"] == audience_id


# =============================================================================
# TEST: audience.tip_completed event
# =============================================================================

@pytest.mark.asyncio
async def test_tip_completed_event_emitted(
    test_musician, test_show, cleanup_analytics, cleanup_tips
):
    """audience.tip_completed event is emitted when tip is submitted."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/tips",
            json={
                "amount": 10.0,
                "platform": "paypal",
                "tipper_name": "Generous Fan",
                "message": "Great show!",
                "audience_id": audience_id,
                "show_id": test_show["id"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        tip_id = data["tip_id"]
        
        # Give a moment for async event to be written
        import asyncio
        await asyncio.sleep(0.3)
        
        # Verify audience.tip_completed event was emitted
        event = await test_db.analytics_events.find_one({
            "event_type": "audience.tip_completed",
            "entity_id": tip_id
        })
        
        assert event is not None, "audience.tip_completed event should be emitted"
        assert event["musician_id"] == test_musician["id"]
        assert event["show_id"] == test_show["id"]
        assert event["metadata"]["amount"] == 10.0
        assert event["metadata"]["platform"] == "paypal"
        assert event["metadata"]["audience_id"] == audience_id


@pytest.mark.asyncio
async def test_audience_id_stored_on_tip(
    test_musician, test_show, cleanup_analytics, cleanup_tips
):
    """audience_id is stored on the tip document when provided."""
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/tips",
            json={
                "amount": 5.0,
                "platform": "venmo",
                "tipper_name": "Test Tipper",
                "audience_id": audience_id,
                "show_id": test_show["id"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        tip_id = data["tip_id"]
        
        # Verify audience_id is stored in the tip
        tip_doc = await test_db.tips.find_one({"id": tip_id})
        assert tip_doc is not None
        assert tip_doc.get("audience_id") == audience_id
        assert tip_doc.get("show_id") == test_show["id"]


# =============================================================================
# TEST: Events contain correct context (musician_id, show_id, audience_id)
# =============================================================================

@pytest.mark.asyncio
async def test_all_events_have_correct_context(
    test_musician, test_show, test_song, cleanup_analytics, cleanup_requests, cleanup_tips
):
    """
    Summary test: All Phase 2 events include correct musician_id, show_id, and audience_id.
    """
    audience_id = f"test-audience-{uuid4().hex[:8]}"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create request with dedication (triggers dedication_submitted)
        response = await client.post(
            f"/api/musicians/{test_musician['slug']}/requests",
            json={
                "song_id": test_song["id"],
                "requester_name": "Test Requester",
                "requester_email": "requester@test.com",
                "dedication": "For my friend!",
                "tip_amount": 5.0,
                "audience_id": audience_id
            }
        )
        assert response.status_code == 200
        request_id = response.json()["id"]
        
        # 2. Track tip click (triggers tip_clicked)
        await client.post(
            f"/api/requests/{request_id}/track-click",
            json={"type": "tip", "platform": "paypal", "audience_id": audience_id}
        )
        
        # 3. Track social click (triggers follow_clicked)
        await client.post(
            f"/api/requests/{request_id}/track-click",
            json={"type": "social", "platform": "spotify", "audience_id": audience_id}
        )
        
        # 4. Submit tip (triggers tip_completed)
        tip_response = await client.post(
            f"/api/musicians/{test_musician['slug']}/tips",
            json={
                "amount": 20.0,
                "platform": "venmo",
                "tipper_name": "Big Tipper",
                "audience_id": audience_id,
                "show_id": test_show["id"]
            }
        )
        assert tip_response.status_code == 200
        
        # Give time for all async events
        import asyncio
        await asyncio.sleep(0.5)
        
        # Verify all 4 event types
        event_types = [
            "audience.dedication_submitted",
            "audience.tip_clicked",
            "audience.follow_clicked",
            "audience.tip_completed"
        ]
        
        for event_type in event_types:
            event = await test_db.analytics_events.find_one({
                "event_type": event_type,
                "metadata.audience_id": audience_id
            })
            
            assert event is not None, f"{event_type} event should exist"
            assert event["musician_id"] == test_musician["id"], f"{event_type} should have correct musician_id"
            assert event["show_id"] == test_show["id"], f"{event_type} should have correct show_id"
            assert event["metadata"]["audience_id"] == audience_id, f"{event_type} should have correct audience_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
