"""
Tests for API-level show_id scoping on requests and suggestions endpoints.

Phase 1 Requirement: All live views must be correctly scoped by show_id at the API level.
"""
import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

# Add backend to path
sys.path.insert(0, '/app/backend')

from server import app, db


@pytest.fixture
async def test_musician():
    """Create a test musician for scoping tests."""
    musician_id = f"test-musician-{uuid4().hex[:8]}"
    musician_data = {
        "id": musician_id,
        "email": f"test-{uuid4().hex[:8]}@example.com",
        "email_lc": f"test-{uuid4().hex[:8]}@example.com".lower(),
        "name": "Test Musician",
        "slug": f"test-musician-{uuid4().hex[:8]}",
        "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V4ferBqGFbLhGi",  # "test"
        "bio": "",
        "website": "",
        "created_at": datetime.now(timezone.utc),
    }
    await db.musicians.insert_one(musician_data)
    yield musician_data
    # Cleanup
    await db.musicians.delete_one({"id": musician_id})


@pytest.fixture
async def test_shows(test_musician):
    """Create two test shows for the musician."""
    show1_id = f"show-1-{uuid4().hex[:8]}"
    show2_id = f"show-2-{uuid4().hex[:8]}"
    
    shows = [
        {
            "id": show1_id,
            "musician_id": test_musician["id"],
            "name": "Show 1",
            "date": "2026-01-15",
            "venue": "Venue 1",
            "notes": "",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        },
        {
            "id": show2_id,
            "musician_id": test_musician["id"],
            "name": "Show 2",
            "date": "2026-01-16",
            "venue": "Venue 2",
            "notes": "",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        }
    ]
    
    for show in shows:
        await db.shows.insert_one(show)
    
    yield {"show1_id": show1_id, "show2_id": show2_id}
    
    # Cleanup
    await db.shows.delete_many({"id": {"$in": [show1_id, show2_id]}})


@pytest.fixture
async def test_requests(test_musician, test_shows):
    """Create test requests for both shows."""
    request_ids = []
    
    # 3 requests for show 1
    for i in range(3):
        req_id = f"req-s1-{i}-{uuid4().hex[:8]}"
        request_ids.append(req_id)
        await db.requests.insert_one({
            "id": req_id,
            "musician_id": test_musician["id"],
            "show_id": test_shows["show1_id"],
            "show_name": "Show 1",
            "song_id": f"song-{i}",
            "song_title": f"Song {i}",
            "song_artist": "Artist",
            "requester_name": "Requester",
            "requester_email": "req@example.com",
            "dedication": "",
            "status": "pending",
            "tip_amount": 0,
            "tip_clicked": False,
            "social_clicks": [],
            "created_at": datetime.now(timezone.utc),
        })
    
    # 2 requests for show 2
    for i in range(2):
        req_id = f"req-s2-{i}-{uuid4().hex[:8]}"
        request_ids.append(req_id)
        await db.requests.insert_one({
            "id": req_id,
            "musician_id": test_musician["id"],
            "show_id": test_shows["show2_id"],
            "show_name": "Show 2",
            "song_id": f"song-{i}",
            "song_title": f"Song {i}",
            "song_artist": "Artist",
            "requester_name": "Requester",
            "requester_email": "req@example.com",
            "dedication": "",
            "status": "pending",
            "tip_amount": 0,
            "tip_clicked": False,
            "social_clicks": [],
            "created_at": datetime.now(timezone.utc),
        })
    
    yield request_ids
    
    # Cleanup
    await db.requests.delete_many({"id": {"$in": request_ids}})


@pytest.fixture
async def test_suggestions(test_musician, test_shows):
    """Create test suggestions for both shows and some without show_id (legacy)."""
    suggestion_ids = []
    
    # 2 suggestions for show 1
    for i in range(2):
        sugg_id = f"sugg-s1-{i}-{uuid4().hex[:8]}"
        suggestion_ids.append(sugg_id)
        await db.song_suggestions.insert_one({
            "id": sugg_id,
            "musician_id": test_musician["id"],
            "show_id": test_shows["show1_id"],
            "show_name": "Show 1",
            "suggested_title": f"Suggested Song {i}",
            "suggested_artist": "Artist",
            "requester_name": "Suggester",
            "requester_email": "sugg@example.com",
            "message": "",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        })
    
    # 3 suggestions for show 2
    for i in range(3):
        sugg_id = f"sugg-s2-{i}-{uuid4().hex[:8]}"
        suggestion_ids.append(sugg_id)
        await db.song_suggestions.insert_one({
            "id": sugg_id,
            "musician_id": test_musician["id"],
            "show_id": test_shows["show2_id"],
            "show_name": "Show 2",
            "suggested_title": f"Suggested Song {i}",
            "suggested_artist": "Artist",
            "requester_name": "Suggester",
            "requester_email": "sugg@example.com",
            "message": "",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        })
    
    # 1 legacy suggestion without show_id
    legacy_id = f"sugg-legacy-{uuid4().hex[:8]}"
    suggestion_ids.append(legacy_id)
    await db.song_suggestions.insert_one({
        "id": legacy_id,
        "musician_id": test_musician["id"],
        # No show_id - legacy data
        "suggested_title": "Legacy Suggestion",
        "suggested_artist": "Artist",
        "requester_name": "Suggester",
        "requester_email": "sugg@example.com",
        "message": "",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })
    
    yield suggestion_ids
    
    # Cleanup
    await db.song_suggestions.delete_many({"id": {"$in": suggestion_ids}})


@pytest.fixture
async def auth_headers(test_musician):
    """Get auth token for test musician."""
    import jwt
    from server import JWT_SECRET, JWT_ALGORITHM
    
    payload = {
        "musician_id": test_musician["id"],
        "exp": datetime.now(timezone.utc).timestamp() + 3600
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# TESTS: GET /api/song-suggestions with show_id parameter
# =============================================================================

@pytest.mark.asyncio
async def test_suggestions_with_show_id_returns_only_that_show(
    test_musician, test_shows, test_suggestions, auth_headers
):
    """With show_id param, only suggestions for that show are returned."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get suggestions for show 1 only
        response = await client.get(
            f"/api/song-suggestions?show_id={test_shows['show1_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        suggestions = response.json()
        
        # Should have exactly 2 suggestions (all from show 1)
        assert len(suggestions) == 2
        
        # All should have show_id matching show 1
        for sugg in suggestions:
            assert sugg.get("show_id") == test_shows["show1_id"]


@pytest.mark.asyncio
async def test_suggestions_with_different_show_id_returns_different_set(
    test_musician, test_shows, test_suggestions, auth_headers
):
    """Different show_id returns different suggestions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get suggestions for show 2 only
        response = await client.get(
            f"/api/song-suggestions?show_id={test_shows['show2_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        suggestions = response.json()
        
        # Should have exactly 3 suggestions (all from show 2)
        assert len(suggestions) == 3
        
        # All should have show_id matching show 2
        for sugg in suggestions:
            assert sugg.get("show_id") == test_shows["show2_id"]


@pytest.mark.asyncio
async def test_suggestions_without_show_id_returns_all(
    test_musician, test_shows, test_suggestions, auth_headers
):
    """Without show_id param, all suggestions are returned (backward compatible)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get all suggestions (no show_id filter)
        response = await client.get(
            "/api/song-suggestions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        suggestions = response.json()
        
        # Should have all 6 suggestions (2 + 3 + 1 legacy)
        assert len(suggestions) == 6


# =============================================================================
# TESTS: GET /api/requests/musician/{musician_id} with show_id parameter
# =============================================================================

@pytest.mark.asyncio
async def test_requests_with_show_id_returns_only_that_show(
    test_musician, test_shows, test_requests, auth_headers
):
    """With show_id param, only requests for that show are returned."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get requests for show 1 only
        response = await client.get(
            f"/api/requests/musician/{test_musician['id']}?show_id={test_shows['show1_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        requests = data["requests"]
        
        # Should have exactly 3 requests (all from show 1)
        assert len(requests) == 3
        
        # All should have show_id matching show 1
        for req in requests:
            assert req.get("show_id") == test_shows["show1_id"]


@pytest.mark.asyncio
async def test_requests_with_different_show_id_returns_different_set(
    test_musician, test_shows, test_requests, auth_headers
):
    """Different show_id returns different requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get requests for show 2 only
        response = await client.get(
            f"/api/requests/musician/{test_musician['id']}?show_id={test_shows['show2_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        requests = data["requests"]
        
        # Should have exactly 2 requests (all from show 2)
        assert len(requests) == 2
        
        # All should have show_id matching show 2
        for req in requests:
            assert req.get("show_id") == test_shows["show2_id"]


@pytest.mark.asyncio
async def test_requests_without_show_id_returns_all(
    test_musician, test_shows, test_requests, auth_headers
):
    """Without show_id param, all requests are returned (backward compatible)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get all requests (no show_id filter)
        response = await client.get(
            f"/api/requests/musician/{test_musician['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        requests = data["requests"]
        
        # Should have all 5 requests (3 + 2)
        assert len(requests) == 5


# =============================================================================
# TESTS: GET /api/requests/grouped with show_id parameter
# =============================================================================

@pytest.mark.asyncio
async def test_grouped_requests_with_show_id_returns_only_that_show(
    test_musician, test_shows, test_requests, auth_headers
):
    """With show_id param, only requests for that show are in the grouped response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get grouped requests for show 1 only
        response = await client.get(
            f"/api/requests/grouped?show_id={test_shows['show1_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Count total requests in grouped response
        total = 0
        for show_name, requests in data.get("shows", {}).items():
            total += len(requests)
        total += len(data.get("unassigned", []))
        
        # Should have exactly 3 requests (all from show 1)
        assert total == 3


@pytest.mark.asyncio
async def test_grouped_requests_without_show_id_returns_all(
    test_musician, test_shows, test_requests, auth_headers
):
    """Without show_id param, all requests are returned grouped."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get all grouped requests (no show_id filter)
        response = await client.get(
            "/api/requests/grouped",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Count total requests in grouped response
        total = 0
        for show_name, requests in data.get("shows", {}).items():
            total += len(requests)
        total += len(data.get("unassigned", []))
        
        # Should have all 5 requests (3 + 2)
        assert total == 5


# =============================================================================
# SUMMARY TEST
# =============================================================================

@pytest.mark.asyncio
async def test_show_scoping_exact_counts(
    test_musician, test_shows, test_requests, test_suggestions, auth_headers
):
    """
    Summary test: Verify exact counts for Phase 1 done criteria.
    
    Test data:
    - Show 1: 3 requests, 2 suggestions
    - Show 2: 2 requests, 3 suggestions
    - Legacy: 0 requests, 1 suggestion (no show_id)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Verify Show 1 counts
        resp_req_s1 = await client.get(
            f"/api/requests/musician/{test_musician['id']}?show_id={test_shows['show1_id']}",
            headers=auth_headers
        )
        resp_sugg_s1 = await client.get(
            f"/api/song-suggestions?show_id={test_shows['show1_id']}",
            headers=auth_headers
        )
        assert len(resp_req_s1.json()["requests"]) == 3, "Show 1 should have exactly 3 requests"
        assert len(resp_sugg_s1.json()) == 2, "Show 1 should have exactly 2 suggestions"
        
        # Verify Show 2 counts
        resp_req_s2 = await client.get(
            f"/api/requests/musician/{test_musician['id']}?show_id={test_shows['show2_id']}",
            headers=auth_headers
        )
        resp_sugg_s2 = await client.get(
            f"/api/song-suggestions?show_id={test_shows['show2_id']}",
            headers=auth_headers
        )
        assert len(resp_req_s2.json()["requests"]) == 2, "Show 2 should have exactly 2 requests"
        assert len(resp_sugg_s2.json()) == 3, "Show 2 should have exactly 3 suggestions"
        
        # Verify ALL (no filter) returns total
        resp_req_all = await client.get(
            f"/api/requests/musician/{test_musician['id']}",
            headers=auth_headers
        )
        resp_sugg_all = await client.get(
            "/api/song-suggestions",
            headers=auth_headers
        )
        assert len(resp_req_all.json()["requests"]) == 5, "Total requests should be 5"
        assert len(resp_sugg_all.json()) == 6, "Total suggestions should be 6 (including legacy)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
