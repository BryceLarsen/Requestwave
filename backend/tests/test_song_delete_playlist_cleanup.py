"""
Regression tests for bug fix: DELETE /api/songs/{song_id} now $pulls the song id
from every playlist owned by the musician, so no orphaned song_ids remain and
subsequent PUT /api/playlists/{id}/songs no longer fails with
"Some songs are invalid or don't belong to you".
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://playlist-validator.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "test@test.com"
PASSWORD = "test"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


def _create_song(client, tag):
    payload = {
        "title": f"TEST_DelCleanup_{tag}_{uuid.uuid4().hex[:6]}",
        "artist": "TEST_Artist",
        "genres": ["Test"],
        "moods": ["Test"],
        "notes": "",
    }
    r = client.post(f"{API}/songs", json=payload, timeout=30)
    assert r.status_code == 200, f"Create song failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _create_playlist(client, name, song_ids=None):
    payload = {"name": name, "song_ids": song_ids or []}
    r = client.post(f"{API}/playlists", json=payload, timeout=30)
    assert r.status_code == 200, f"Create playlist failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _get_playlist(client, playlist_id):
    r = client.get(f"{API}/playlists/{playlist_id}", timeout=30)
    assert r.status_code == 200, f"Get playlist failed: {r.status_code} {r.text}"
    return r.json()


def _put_playlist_songs(client, playlist_id, song_ids):
    return client.put(f"{API}/playlists/{playlist_id}/songs", json={"song_ids": song_ids}, timeout=30)


# --- Tests ---

def test_delete_song_removes_id_from_playlist(client):
    """Deleting a song removes its id from the playlist's song_ids."""
    s1 = _create_song(client, "A1")
    s2 = _create_song(client, "A2")

    pl_id = _create_playlist(client, f"TEST_pl_{uuid.uuid4().hex[:6]}")
    r = _put_playlist_songs(client, pl_id, [s1, s2])
    assert r.status_code == 200, r.text
    assert set(r.json()["song_ids"]) == {s1, s2}

    # Delete s1
    d = client.delete(f"{API}/songs/{s1}", timeout=30)
    assert d.status_code == 200, d.text

    # Verify orphan cleanup
    pl = _get_playlist(client, pl_id)
    assert s1 not in pl["song_ids"], f"Orphaned song id remained: {pl['song_ids']}"
    assert s2 in pl["song_ids"]

    # Cleanup
    client.delete(f"{API}/songs/{s2}", timeout=30)
    client.delete(f"{API}/playlists/{pl_id}", timeout=30)


def test_put_playlist_songs_succeeds_after_song_delete(client):
    """After deleting a song that was in a playlist, PUT with remaining ids must succeed."""
    s1 = _create_song(client, "B1")
    s2 = _create_song(client, "B2")
    s3 = _create_song(client, "B3")

    pl_id = _create_playlist(client, f"TEST_pl_{uuid.uuid4().hex[:6]}")
    r = _put_playlist_songs(client, pl_id, [s1, s2, s3])
    assert r.status_code == 200, r.text

    # Delete s2
    d = client.delete(f"{API}/songs/{s2}", timeout=30)
    assert d.status_code == 200

    # PUT with remaining valid song ids must SUCCEED (regression check)
    r2 = _put_playlist_songs(client, pl_id, [s1, s3])
    assert r2.status_code == 200, f"Regression! PUT failed after delete: {r2.status_code} {r2.text}"
    assert set(r2.json()["song_ids"]) == {s1, s3}

    # Cleanup
    for sid in (s1, s3):
        client.delete(f"{API}/songs/{sid}", timeout=30)
    client.delete(f"{API}/playlists/{pl_id}", timeout=30)


def test_delete_song_removes_from_multiple_playlists(client):
    """Deleting a song referenced by MULTIPLE playlists cleans up ALL of them."""
    s1 = _create_song(client, "C1")
    s2 = _create_song(client, "C2")

    pl_a = _create_playlist(client, f"TEST_pA_{uuid.uuid4().hex[:6]}")
    pl_b = _create_playlist(client, f"TEST_pB_{uuid.uuid4().hex[:6]}")
    pl_c = _create_playlist(client, f"TEST_pC_{uuid.uuid4().hex[:6]}")

    assert _put_playlist_songs(client, pl_a, [s1, s2]).status_code == 200
    assert _put_playlist_songs(client, pl_b, [s1]).status_code == 200
    assert _put_playlist_songs(client, pl_c, [s2, s1]).status_code == 200

    d = client.delete(f"{API}/songs/{s1}", timeout=30)
    assert d.status_code == 200

    for pl_id in (pl_a, pl_b, pl_c):
        pl = _get_playlist(client, pl_id)
        assert s1 not in pl["song_ids"], f"Playlist {pl_id} still has orphaned id: {pl['song_ids']}"

    # PUT with s2 alone should still work on all
    for pl_id in (pl_a, pl_c):
        rr = _put_playlist_songs(client, pl_id, [s2])
        assert rr.status_code == 200, rr.text

    # Cleanup
    client.delete(f"{API}/songs/{s2}", timeout=30)
    for pl_id in (pl_a, pl_b, pl_c):
        client.delete(f"{API}/playlists/{pl_id}", timeout=30)


def test_delete_song_not_in_any_playlist_ok(client):
    """Deleting a song not referenced by any playlist returns 200."""
    sid = _create_song(client, "D1")
    d = client.delete(f"{API}/songs/{sid}", timeout=30)
    assert d.status_code == 200, d.text


def test_delete_nonexistent_song_returns_404(client):
    """Deleting a nonexistent song still returns 404."""
    d = client.delete(f"{API}/songs/{uuid.uuid4()}", timeout=30)
    assert d.status_code == 404, f"Expected 404, got {d.status_code}: {d.text}"
