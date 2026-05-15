"""
Tests for unique-show-count based popularity ranking.

Covers:
- GET /api/songs returns `unique_show_count` per song and sorts by it when
  sort_by=popularity.
- GET /api/musicians/{slug}/songs (public) returns `unique_show_count` and
  preserves request_count / requests_this_show semantics.
- GET /api/analytics/daily top_songs is ranked by unique-show count and
  the helper raised limit to 50.
- Regression: POST /api/requests still increments request_count.
- Distinct-show counting: creating ephemeral shows + requests for the same
  song across multiple shows yields the expected unique_show_count.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
LOGIN = {"email": "test@test.com", "password": "test"}
SLUG = "test"

# Globals shared across tests (created in fixture)
@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=LOGIN, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    return {
        "token": data["token"],
        "musician_id": data["musician"]["id"],
        "headers": {"Authorization": f"Bearer {data['token']}", "Content-Type": "application/json"},
    }


@pytest.fixture(scope="module")
def seed_unique_shows(auth):
    """Create a TEST song and two ephemeral shows; post requests so the song
    appears in two distinct shows. Returns (song_id, show_ids).

    Cleanup is best-effort: we archive the requests and stop shows at the end.
    """
    headers = auth["headers"]
    title = f"TEST_UniqueShowSong_{uuid.uuid4().hex[:6]}"
    artist = f"TEST_Artist_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/api/songs", json={
        "title": title, "artist": artist, "genres": ["Pop"], "moods": ["Happy"], "year": 2024,
        "notes": "TEST_unique_show_count",
    }, headers=headers, timeout=15)
    assert r.status_code == 200, f"create song failed: {r.status_code} {r.text[:300]}"
    song = r.json()
    song_id = song["id"]

    show_ids = []
    # Make sure no show is currently active to start
    try:
        requests.post(f"{BASE_URL}/api/shows/stop", json={}, headers=headers, timeout=10)
    except Exception:
        pass

    for i in range(2):
        sr = requests.post(f"{BASE_URL}/api/shows/start", json={
            "name": f"TEST_Show_{uuid.uuid4().hex[:6]}",
            "date": "2026-01-01",
            "venue": "TEST",
            "notes": "TEST_unique_show_count seed",
        }, headers=headers, timeout=15)
        assert sr.status_code == 200, f"start show failed: {sr.status_code} {sr.text[:300]}"
        sid = sr.json().get("show", {}).get("id") or sr.json().get("id")
        assert sid, f"no show id in {sr.json()}"
        show_ids.append(sid)

        # Post 2 requests against this song in this show
        for _ in range(2):
            rq = requests.post(f"{BASE_URL}/api/requests", json={
                "song_id": song_id,
                "requester_name": f"TEST_user_{uuid.uuid4().hex[:5]}",
                "requester_email": f"TEST_{uuid.uuid4().hex[:5]}@example.com",
                "dedication": "TEST",
                "tip_amount": 0,
                "profile_slug": None,
            }, timeout=15)
            assert rq.status_code in (200, 201), f"create request failed: {rq.status_code} {rq.text[:300]}"

        # Stop the show so we can start another
        requests.post(f"{BASE_URL}/api/shows/stop", json={}, headers=headers, timeout=10)

    yield {"song_id": song_id, "show_ids": show_ids, "title": title, "artist": artist}

    # Teardown: best-effort archive seeded requests for this song
    try:
        # Fetch this musician's requests, archive those for our seed song
        rr = requests.get(f"{BASE_URL}/api/requests", headers=headers, timeout=15)
        if rr.status_code == 200:
            for req in rr.json() or []:
                if req.get("song_id") == song_id and req.get("status") != "archived":
                    requests.put(
                        f"{BASE_URL}/api/requests/{req['id']}",
                        json={"status": "archived"},
                        headers=headers, timeout=10,
                    )
    except Exception:
        pass


# ---------------- Tests ----------------

class TestUniqueShowCountFields:
    def test_get_songs_includes_unique_show_count(self, auth, seed_unique_shows):
        r = requests.get(f"{BASE_URL}/api/songs", headers=auth["headers"], timeout=20)
        assert r.status_code == 200, r.text[:300]
        songs = r.json()
        assert isinstance(songs, list) and len(songs) > 0
        # field present on every song
        for s in songs:
            assert "unique_show_count" in s, f"missing unique_show_count on song {s.get('id')}"
            assert isinstance(s["unique_show_count"], int)
        # Our seeded song should have unique_show_count >= 2 (two distinct shows)
        seeded = next((s for s in songs if s["id"] == seed_unique_shows["song_id"]), None)
        assert seeded is not None, "seed song not in /songs response"
        assert seeded["unique_show_count"] >= 2, (
            f"expected >=2 distinct shows, got {seeded['unique_show_count']}"
        )
        # request_count should be >= 4 (2 shows * 2 requests)
        assert seeded.get("request_count", 0) >= 4

    def test_get_songs_popularity_sort_orders_by_unique_show_count(self, auth):
        r = requests.get(
            f"{BASE_URL}/api/songs?sort_by=popularity",
            headers=auth["headers"], timeout=20,
        )
        assert r.status_code == 200
        songs = r.json()
        usc = [s.get("unique_show_count", 0) for s in songs]
        assert usc == sorted(usc, reverse=True), f"not sorted desc by unique_show_count: {usc[:10]}"

    def test_get_songs_popularity_not_by_request_count(self, auth):
        """Independence check: popularity sort should NOT necessarily match
        request_count desc. Confirm response is ordered by unique_show_count;
        if any pair exists where unique_show_count is tied but request_count
        differs, ordering must still follow unique_show_count (i.e., raw
        request_count is no longer the primary signal)."""
        r = requests.get(
            f"{BASE_URL}/api/songs?sort_by=popularity",
            headers=auth["headers"], timeout=20,
        )
        assert r.status_code == 200
        songs = r.json()
        # primary key MUST be unique_show_count desc
        for i in range(len(songs) - 1):
            a, b = songs[i], songs[i + 1]
            assert a["unique_show_count"] >= b["unique_show_count"], (
                f"order violation at {i}: {a['title']}({a['unique_show_count']}) "
                f"-> {b['title']}({b['unique_show_count']})"
            )

    def test_public_musician_songs_includes_unique_show_count(self, seed_unique_shows):
        r = requests.get(f"{BASE_URL}/api/musicians/{SLUG}/songs", timeout=20)
        assert r.status_code == 200, r.text[:300]
        songs = r.json()
        assert isinstance(songs, list) and len(songs) > 0
        for s in songs:
            assert "unique_show_count" in s
            assert "request_count" in s
            assert "requests_this_show" in s
        seeded = next((s for s in songs if s["id"] == seed_unique_shows["song_id"]), None)
        assert seeded is not None
        assert seeded["unique_show_count"] >= 2


class TestAnalyticsTopSongs:
    def test_analytics_daily_top_songs_ranked_by_unique_shows(self, auth, seed_unique_shows):
        r = requests.get(
            f"{BASE_URL}/api/analytics/daily?days=365",
            headers=auth["headers"], timeout=30,
        )
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert "top_songs" in data
        ts = data["top_songs"]
        assert isinstance(ts, list)
        # all items have count int, sorted desc
        counts = [t.get("count", 0) for t in ts]
        assert counts == sorted(counts, reverse=True), f"top_songs not sorted desc: {counts[:10]}"
        # limit must accommodate Top 50 UI
        assert len(ts) <= 50
        # Seeded song's label should be in list with count >= 2
        label = f"{seed_unique_shows['title']} - {seed_unique_shows['artist']}"
        match = next((t for t in ts if t.get("song") == label), None)
        assert match is not None, f"seeded song label not found in top_songs: {label}"
        assert match["count"] >= 2


class TestRegression:
    def test_request_count_still_increments(self, auth):
        # create a brand new TEST song and post a single request
        headers = auth["headers"]
        title = f"TEST_RegSong_{uuid.uuid4().hex[:6]}"
        artist = f"TEST_RegArt_{uuid.uuid4().hex[:6]}"
        cr = requests.post(f"{BASE_URL}/api/songs", json={
            "title": title, "artist": artist, "genres": ["Rock"], "moods": ["Energetic"], "year": 2024,
        }, headers=headers, timeout=15)
        assert cr.status_code == 200
        song = cr.json()
        sid = song["id"]
        assert song.get("request_count", 0) == 0

        # Start a show so request goes into a known show
        try:
            requests.post(f"{BASE_URL}/api/shows/stop", json={}, headers=headers, timeout=10)
        except Exception:
            pass
        sr = requests.post(f"{BASE_URL}/api/shows/start", json={
            "name": f"TEST_RegShow_{uuid.uuid4().hex[:6]}", "date": "2026-01-01"
        }, headers=headers, timeout=15)
        assert sr.status_code == 200

        rq = requests.post(f"{BASE_URL}/api/requests", json={
            "song_id": sid,
            "requester_name": "TEST_reg",
            "requester_email": f"TEST_reg_{uuid.uuid4().hex[:5]}@example.com",
            "dedication": "TEST",
            "tip_amount": 0,
        }, timeout=15)
        assert rq.status_code in (200, 201), rq.text[:300]

        # Re-fetch songs, find ours
        sg = requests.get(f"{BASE_URL}/api/songs", headers=headers, timeout=20)
        found = next((s for s in sg.json() if s["id"] == sid), None)
        assert found is not None
        assert found["request_count"] >= 1, f"request_count should have incremented, got {found.get('request_count')}"
        # requests_this_show should be at least 1 (active show now)
        assert found["requests_this_show"] >= 1
        # unique_show_count should be 1 (only one show so far)
        assert found["unique_show_count"] == 1

        # cleanup: stop the show & archive the request
        try:
            rr = requests.get(f"{BASE_URL}/api/requests", headers=headers, timeout=15)
            if rr.status_code == 200:
                for req in rr.json() or []:
                    if req.get("song_id") == sid and req.get("status") != "archived":
                        requests.put(
                            f"{BASE_URL}/api/requests/{req['id']}",
                            json={"status": "archived"},
                            headers=headers, timeout=10,
                        )
            requests.post(f"{BASE_URL}/api/shows/stop", json={}, headers=headers, timeout=10)
        except Exception:
            pass
