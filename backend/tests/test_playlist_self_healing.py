"""
Tests for the self-healing playlist song_ids filter in
POST /api/playlists and PUT /api/playlists/{playlist_id}.

Bug: previously the endpoints rejected the whole request with HTTP 400
"Some songs don't belong to you" if any song_id (including stale ids
already in the playlist) didn't belong to the musician.

Fix: song_ids are now filtered against db.songs for ownership; invalid
ids are silently dropped, valid ids preserved in order, and the endpoint
returns 200.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0].strip()

API = f"{BASE_URL}/api"

TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"


@pytest.fixture(scope="module")
def auth_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def _create_song(client, title_suffix):
    payload = {
        "title": f"TEST_song_{title_suffix}_{uuid.uuid4().hex[:6]}",
        "artist": "TEST_Artist",
        "genres": ["Rock"],
        "moods": ["Happy"],
        "year": 2020,
        "notes": "test",
    }
    r = client.post(f"{API}/songs", json=payload, timeout=30)
    assert r.status_code == 200, f"Create song failed: {r.status_code} {r.text}"
    return r.json()["id"]


@pytest.fixture(scope="module")
def owned_song_ids(auth_client):
    ids = [_create_song(auth_client, f"own{i}") for i in range(3)]
    yield ids
    for sid in ids:
        try:
            auth_client.delete(f"{API}/songs/{sid}", timeout=15)
        except Exception:
            pass


@pytest.fixture
def created_playlist(auth_client, owned_song_ids):
    r = auth_client.post(f"{API}/playlists", json={
        "name": f"TEST_playlist_{uuid.uuid4().hex[:6]}",
        "song_ids": [owned_song_ids[0]],
    }, timeout=30)
    assert r.status_code == 200, f"Create playlist failed: {r.status_code} {r.text}"
    pid = r.json()["id"]
    yield r.json()
    try:
        auth_client.delete(f"{API}/playlists/{pid}", timeout=15)
    except Exception:
        pass


class TestPlaylistSelfHealing:
    """Verify self-healing filter for playlist song_ids."""

    def test_create_playlist_with_only_valid_songs(self, auth_client, owned_song_ids):
        r = auth_client.post(f"{API}/playlists", json={
            "name": f"TEST_valid_only_{uuid.uuid4().hex[:6]}",
            "song_ids": owned_song_ids,
        }, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["song_ids"] == owned_song_ids
        assert data["song_count"] == len(owned_song_ids)
        auth_client.delete(f"{API}/playlists/{data['id']}", timeout=15)

    def test_create_playlist_with_mix_valid_and_stale(self, auth_client, owned_song_ids):
        stale = str(uuid.uuid4())
        mixed = [owned_song_ids[0], stale, owned_song_ids[1]]
        r = auth_client.post(f"{API}/playlists", json={
            "name": f"TEST_mixed_{uuid.uuid4().hex[:6]}",
            "song_ids": mixed,
        }, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Stale id filtered, order preserved
        assert data["song_ids"] == [owned_song_ids[0], owned_song_ids[1]]
        assert stale not in data["song_ids"]
        auth_client.delete(f"{API}/playlists/{data['id']}", timeout=15)

    def test_update_playlist_add_valid_song_succeeds(self, auth_client, owned_song_ids, created_playlist):
        pid = created_playlist["id"]
        current = created_playlist["song_ids"]
        # Add a second owned song (the actual reported flow)
        new_ids = current + [owned_song_ids[1]]
        r = auth_client.put(f"{API}/playlists/{pid}", json={"song_ids": new_ids}, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "don't belong to you" not in r.text.lower().replace("’", "'")

        # Verify persistence via GET /playlists
        r2 = auth_client.get(f"{API}/playlists", timeout=30)
        assert r2.status_code == 200
        found = next((p for p in r2.json() if p["id"] == pid), None)
        assert found is not None, "Playlist not found after update"
        assert found["song_ids"] == new_ids

    def test_update_playlist_with_stale_id_is_filtered(self, auth_client, owned_song_ids, created_playlist):
        pid = created_playlist["id"]
        stale = str(uuid.uuid4())
        # Simulate the exact reported scenario: stale leftover id + new valid id
        merged = [stale, owned_song_ids[2]]
        r = auth_client.put(f"{API}/playlists/{pid}", json={"song_ids": merged}, timeout=30)
        assert r.status_code == 200, f"Expected 200 (stale should be filtered), got {r.status_code}: {r.text}"

        r2 = auth_client.get(f"{API}/playlists", timeout=30)
        found = next((p for p in r2.json() if p["id"] == pid), None)
        assert found is not None
        assert stale not in found["song_ids"]
        assert owned_song_ids[2] in found["song_ids"]
        # Order preserved among valid ids
        assert found["song_ids"] == [owned_song_ids[2]]

    def test_update_playlist_all_valid_stores_all(self, auth_client, owned_song_ids, created_playlist):
        pid = created_playlist["id"]
        r = auth_client.put(f"{API}/playlists/{pid}", json={"song_ids": owned_song_ids}, timeout=30)
        assert r.status_code == 200, r.text
        r2 = auth_client.get(f"{API}/playlists", timeout=30)
        found = next((p for p in r2.json() if p["id"] == pid), None)
        assert found["song_ids"] == owned_song_ids
