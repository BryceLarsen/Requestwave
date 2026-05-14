"""
Backend tests for the show-scoped per-song request count feature.

Verifies:
- Song model includes `requests_this_show` int on every song
- GET /api/songs (auth musician) returns 0 for all songs when no active show
- GET /api/songs returns the correct count for the active show after creating
  audience requests, while other songs remain 0
- GET /api/musicians/{slug}/songs (public audience) mirrors the same behavior
- POST /api/shows/stop resets requests_this_show back to 0 for all songs
- request_count (all-time) still increments normally and is not affected
"""

import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "test@test.com"
PASSWORD = "test"
SLUG = "test"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_token(session):
    r = session.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    token = r.json().get("token")
    if not token:
        pytest.skip("No token returned from login")
    return token


@pytest.fixture(scope="module")
def auth_session(session, auth_token):
    session.headers.update({"Authorization": f"Bearer {auth_token}"})
    return session


# ---------- helpers ----------
def _stop_active_show(auth_session):
    """Best-effort stop any active show."""
    try:
        auth_session.post(f"{API}/shows/stop", json={})
    except Exception:
        pass


def _start_show(auth_session, name=None):
    name = name or f"TEST_show_{uuid.uuid4().hex[:6]}"
    r = auth_session.post(
        f"{API}/shows/start",
        json={"name": name, "timezone": "America/New_York"},
    )
    assert r.status_code == 200, f"start_show failed: {r.status_code} {r.text}"
    return r.json()


def _get_my_songs(auth_session):
    r = auth_session.get(f"{API}/songs")
    assert r.status_code == 200, f"GET /songs failed: {r.status_code} {r.text}"
    return r.json()


def _get_public_songs():
    r = requests.get(f"{API}/musicians/{SLUG}/songs")
    assert r.status_code == 200, f"GET /musicians/{SLUG}/songs failed: {r.status_code} {r.text}"
    return r.json()


def _create_request(song, requester_suffix=""):
    """Public audience submits a request for a song."""
    payload = {
        "song_id": song["id"],
        "song_title": song["title"],
        "song_artist": song["artist"],
        "requester_name": f"TEST_Tester_{requester_suffix or uuid.uuid4().hex[:4]}",
        "requester_email": f"TEST_{uuid.uuid4().hex[:6]}@example.com",
        "dedication": "",
        "musician_slug": SLUG,
        "tip_clicked": False,
    }
    r = requests.post(f"{API}/requests", json=payload)
    return r


# ---------- field presence ----------
class TestRequestsThisShowFieldPresence:
    def test_field_present_on_auth_songs(self, auth_session):
        _stop_active_show(auth_session)
        songs = _get_my_songs(auth_session)
        assert len(songs) > 0, "Test musician should have at least one song"
        for s in songs:
            assert "requests_this_show" in s, f"Song {s.get('id')} missing requests_this_show"
            assert isinstance(s["requests_this_show"], int)

    def test_field_present_on_public_songs(self, auth_session):
        _stop_active_show(auth_session)
        songs = _get_public_songs()
        assert len(songs) > 0
        for s in songs:
            assert "requests_this_show" in s
            assert isinstance(s["requests_this_show"], int)


# ---------- zero when no active show ----------
class TestZeroWhenNoActiveShow:
    def test_auth_songs_all_zero(self, auth_session):
        _stop_active_show(auth_session)
        songs = _get_my_songs(auth_session)
        non_zero = [s for s in songs if s["requests_this_show"] != 0]
        assert non_zero == [], f"Expected all 0 with no active show, got: {[(s['title'], s['requests_this_show']) for s in non_zero]}"

    def test_public_songs_all_zero(self, auth_session):
        _stop_active_show(auth_session)
        songs = _get_public_songs()
        non_zero = [s for s in songs if s["requests_this_show"] != 0]
        assert non_zero == [], f"Expected all 0 with no active show on public list, got: {[(s['title'], s['requests_this_show']) for s in non_zero]}"


# ---------- end-to-end flow ----------
class TestEndToEndShowScopedCount:
    def test_full_flow(self, auth_session):
        # 1. Ensure clean baseline
        _stop_active_show(auth_session)

        # 2. Pick a target song
        songs = _get_my_songs(auth_session)
        assert len(songs) >= 2, "Need at least 2 songs to compare target vs others"
        target = songs[0]
        other = songs[1]
        target_id = target["id"]
        other_id = other["id"]

        # capture all-time request_count baselines
        baseline_target_count = target.get("request_count", 0)
        baseline_other_count = other.get("request_count", 0)

        # 3. Start a new show
        _start_show(auth_session, name=f"TEST_show_{uuid.uuid4().hex[:6]}")

        # 4. Audience submits 2 requests for the target song
        for i in range(2):
            r = _create_request(target, requester_suffix=str(i))
            assert r.status_code in (200, 201), f"POST /requests failed: {r.status_code} {r.text}"
            time.sleep(0.1)

        # 5. Verify /api/songs: target=2, other=0
        songs_after = _get_my_songs(auth_session)
        by_id = {s["id"]: s for s in songs_after}
        assert by_id[target_id]["requests_this_show"] == 2, (
            f"Expected requests_this_show=2 on target, got {by_id[target_id]['requests_this_show']}"
        )
        assert by_id[other_id]["requests_this_show"] == 0, (
            f"Expected requests_this_show=0 on other, got {by_id[other_id]['requests_this_show']}"
        )
        # All other songs should be 0
        others_non_zero = [
            (s["id"], s["requests_this_show"])
            for s in songs_after
            if s["id"] != target_id and s["requests_this_show"] != 0
        ]
        assert others_non_zero == [], f"Other songs should be 0: {others_non_zero}"

        # 6. request_count (all-time) regression check: target incremented by 2
        assert by_id[target_id]["request_count"] == baseline_target_count + 2, (
            f"request_count regression: baseline={baseline_target_count}, "
            f"now={by_id[target_id]['request_count']}"
        )
        assert by_id[other_id]["request_count"] == baseline_other_count, (
            f"Other song request_count must remain unchanged: "
            f"baseline={baseline_other_count}, now={by_id[other_id]['request_count']}"
        )

        # 7. Verify public endpoint mirrors the same counts (only non-hidden)
        public_songs = _get_public_songs()
        public_by_id = {s["id"]: s for s in public_songs}
        # The target song should be visible to audience for the test to be meaningful
        if target_id in public_by_id:
            assert public_by_id[target_id]["requests_this_show"] == 2
        if other_id in public_by_id:
            assert public_by_id[other_id]["requests_this_show"] == 0
        # And all the rest should be 0
        non_zero_public = [
            (s["id"], s["requests_this_show"])
            for s in public_songs
            if s["id"] != target_id and s["requests_this_show"] != 0
        ]
        assert non_zero_public == [], f"Public list non-zero on non-target songs: {non_zero_public}"

        # 8. Stop the show
        stop_r = auth_session.post(f"{API}/shows/stop", json={})
        assert stop_r.status_code == 200, f"shows/stop failed: {stop_r.status_code} {stop_r.text}"

        # 9. After stop, all requests_this_show should be 0 on both endpoints
        songs_after_stop = _get_my_songs(auth_session)
        non_zero_after_stop = [
            (s["id"], s["requests_this_show"])
            for s in songs_after_stop
            if s["requests_this_show"] != 0
        ]
        assert non_zero_after_stop == [], (
            f"After shows/stop, expected all 0 on /api/songs, got: {non_zero_after_stop}"
        )

        public_after_stop = _get_public_songs()
        non_zero_public_after_stop = [
            (s["id"], s["requests_this_show"])
            for s in public_after_stop
            if s["requests_this_show"] != 0
        ]
        assert non_zero_public_after_stop == [], (
            f"After shows/stop, expected all 0 on /api/musicians/{SLUG}/songs, "
            f"got: {non_zero_public_after_stop}"
        )

        # 10. request_count still reflects the +2 lifetime
        final = _get_my_songs(auth_session)
        final_by_id = {s["id"]: s for s in final}
        assert final_by_id[target_id]["request_count"] == baseline_target_count + 2, (
            "All-time request_count must persist after show stop"
        )
