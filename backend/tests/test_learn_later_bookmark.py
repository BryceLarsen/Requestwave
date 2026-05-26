"""
Tests for Learn Later bookmark toggle endpoint.

Endpoint: POST /api/songs/{song_id}/learn-later
- Toggles song membership in musician's 'Learn Later' playlist (idempotent)
- Lazily creates the playlist on first call
- Requires auth
- 404 for unknown / foreign songs
- Public musician songs endpoint must NOT leak in_learn_later=true
- Regression: other playlists' song_ids unchanged after toggle
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://show-analytics-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"
TEST_SLUG = "test"


# -------- fixtures --------

@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def songs(auth_headers):
    r = requests.get(f"{API}/songs", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0, "Test musician needs at least 1 song"
    return data


# -------- tests: response shape & in_learn_later field --------

def test_get_songs_includes_in_learn_later_field(songs):
    for s in songs:
        assert "in_learn_later" in s, f"song {s.get('id')} missing in_learn_later"
        assert isinstance(s["in_learn_later"], bool)


def test_toggle_requires_auth(songs):
    sid = songs[0]["id"]
    r = requests.post(f"{API}/songs/{sid}/learn-later", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


def test_toggle_response_shape(auth_headers, songs):
    sid = songs[0]["id"]
    r = requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "in_learn_later" in body and isinstance(body["in_learn_later"], bool)
    assert body.get("song_id") == sid
    assert isinstance(body.get("playlist_id"), str) and body["playlist_id"]
    # restore state with a 2nd toggle for cleanup
    requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)


def test_toggle_is_idempotent_flip(auth_headers, songs):
    sid = songs[1]["id"] if len(songs) > 1 else songs[0]["id"]
    # baseline
    r0 = requests.get(f"{API}/songs", headers=auth_headers, timeout=15)
    initial = next(s["in_learn_later"] for s in r0.json() if s["id"] == sid)

    r1 = requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)
    assert r1.status_code == 200
    state1 = r1.json()["in_learn_later"]
    assert state1 != initial

    r2 = requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)
    assert r2.status_code == 200
    state2 = r2.json()["in_learn_later"]
    assert state2 == initial, "second toggle should flip back to original"


def test_toggle_persists_in_get_songs(auth_headers, songs):
    sid = songs[0]["id"]
    # current state
    r0 = requests.get(f"{API}/songs", headers=auth_headers, timeout=15)
    initial = next(s["in_learn_later"] for s in r0.json() if s["id"] == sid)

    # toggle
    r1 = requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)
    assert r1.status_code == 200
    new_state = r1.json()["in_learn_later"]

    # re-fetch and confirm persistence
    r2 = requests.get(f"{API}/songs", headers=auth_headers, timeout=15)
    persisted = next(s["in_learn_later"] for s in r2.json() if s["id"] == sid)
    assert persisted == new_state

    # restore
    requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)


def test_toggle_unknown_song_returns_404(auth_headers):
    r = requests.post(f"{API}/songs/nonexistent-song-id-zzzz/learn-later", headers=auth_headers, timeout=15)
    assert r.status_code == 404


# -------- playlist lazy creation: only one "Learn Later" playlist --------

def test_only_one_learn_later_playlist(auth_headers, songs):
    # Force playlist to exist by toggling once
    sid = songs[0]["id"]
    requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)
    # toggle again to keep state stable
    requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)

    r = requests.get(f"{API}/playlists", headers=auth_headers, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"/api/playlists not available: {r.status_code}")
    pls = r.json()
    learn_later = [p for p in pls if (p.get("name") or "").strip().lower() == "learn later"]
    assert len(learn_later) == 1, f"expected exactly 1 Learn Later playlist, got {len(learn_later)}"


# -------- regression: other playlists unchanged --------

def test_toggle_does_not_modify_other_playlists(auth_headers, songs):
    r = requests.get(f"{API}/playlists", headers=auth_headers, timeout=15)
    if r.status_code != 200:
        pytest.skip("playlists endpoint unavailable")
    pls_before = r.json()
    other_before = {p["id"]: list(p.get("song_ids") or []) for p in pls_before
                    if (p.get("name") or "").strip().lower() != "learn later"}

    if not other_before:
        pytest.skip("no non-LearnLater playlists to check regression against")

    sid = songs[0]["id"]
    requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)
    requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)

    pls_after = requests.get(f"{API}/playlists", headers=auth_headers, timeout=15).json()
    other_after = {p["id"]: list(p.get("song_ids") or []) for p in pls_after
                   if (p.get("name") or "").strip().lower() != "learn later"}

    for pid, before in other_before.items():
        after = other_after.get(pid)
        assert after == before, f"playlist {pid} song_ids changed unexpectedly: {before} -> {after}"


# -------- public audience endpoint must not leak in_learn_later=true --------

def test_public_songs_does_not_expose_learn_later(auth_headers, songs):
    # Ensure at least one song IS in learn later
    sid = songs[0]["id"]
    cur = requests.get(f"{API}/songs", headers=auth_headers, timeout=15).json()
    in_ll = next(s["in_learn_later"] for s in cur if s["id"] == sid)
    if not in_ll:
        requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)

    r = requests.get(f"{API}/musicians/{TEST_SLUG}/songs", timeout=15)
    assert r.status_code == 200, r.text
    pub = r.json()
    # Either field is absent OR all values are False — never true on the audience endpoint
    for s in pub:
        assert s.get("in_learn_later", False) is False, \
            f"audience endpoint leaked in_learn_later=true for song {s.get('id')}"

    # clean up: restore state
    cur2 = requests.get(f"{API}/songs", headers=auth_headers, timeout=15).json()
    final = next(s["in_learn_later"] for s in cur2 if s["id"] == sid)
    if final != in_ll:
        requests.post(f"{API}/songs/{sid}/learn-later", headers=auth_headers, timeout=15)


# -------- musician scoping: foreign song returns 404 --------

def test_toggle_foreign_song_returns_404(auth_headers):
    """Register a 2nd musician, create a song under them, then try to toggle it as test@test.com."""
    import uuid as _uuid
    foreign_email = f"foreign_{_uuid.uuid4().hex[:8]}@test.com"
    reg = requests.post(f"{API}/auth/register", json={
        "name": "Foreign Musician",
        "email": foreign_email,
        "password": "testtest",
        "slug": f"foreign-{_uuid.uuid4().hex[:8]}",
    }, timeout=15)
    if reg.status_code not in (200, 201):
        pytest.skip(f"could not create foreign musician: {reg.status_code} {reg.text[:200]}")

    foreign_tok = reg.json().get("token")
    if not foreign_tok:
        # try login
        lg = requests.post(f"{API}/auth/login", json={"email": foreign_email, "password": "testtest"}, timeout=15)
        foreign_tok = lg.json().get("token")
    assert foreign_tok, "no foreign token"

    foreign_h = {"Authorization": f"Bearer {foreign_tok}", "Content-Type": "application/json"}
    create = requests.post(f"{API}/songs", headers=foreign_h, json={
        "title": "Foreign Song",
        "artist": "Foreign Artist",
        "genres": ["Rock"],
        "moods": ["Happy"],
        "year": 2020,
        "notes": "",
    }, timeout=15)
    if create.status_code not in (200, 201):
        pytest.skip(f"could not create foreign song: {create.status_code}")
    foreign_song_id = create.json()["id"]

    # Now try to toggle that song as test@test.com -> must 404 (scoping)
    r = requests.post(f"{API}/songs/{foreign_song_id}/learn-later", headers=auth_headers, timeout=15)
    assert r.status_code == 404, f"foreign song toggle should be 404 not {r.status_code}: {r.text}"
