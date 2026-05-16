"""Backend tests for the new Show Analytics Dashboard endpoints.

Endpoints under test:
  - GET /api/analytics/show-detail?show_id=<id>
  - GET /api/analytics/show-trends?profile_id=<id>&limit=<5|10|20>
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Read from frontend .env directly as a fallback for the test env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

LOGIN_EMAIL = "test@test.com"
LOGIN_PASSWORD = "test"


# ----------------------------- fixtures -----------------------------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(api):
    r = api.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    t = r.json().get("token")
    assert t
    return t


@pytest.fixture(scope="module")
def auth(api, token):
    api.headers.update({"Authorization": f"Bearer {token}"})
    return api


@pytest.fixture(scope="module")
def profiles(auth):
    r = auth.get(f"{BASE_URL}/api/profiles", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    profs = data.get("profiles") if isinstance(data, dict) else data
    assert profs and len(profs) > 0, "Need at least one profile"
    return profs


@pytest.fixture(scope="module")
def shows(auth):
    r = auth.get(f"{BASE_URL}/api/shows", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    sh = data.get("shows") if isinstance(data, dict) else data
    assert sh and len(sh) > 0, "Need at least one show"
    return sh


# ----------------------------- show-detail -----------------------------
class TestShowDetailAuth:
    def test_requires_auth(self, api):
        # ensure no Authorization header in this client
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/analytics/show-detail", params={"show_id": "anything"}, timeout=30)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_invalid_show_id_returns_404(self, auth):
        r = auth.get(
            f"{BASE_URL}/api/analytics/show-detail",
            params={"show_id": "does-not-exist-xyz"},
            timeout=30,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


class TestShowDetailStructure:
    def test_returns_full_structure(self, auth, shows):
        sid = shows[0]["id"]
        r = auth.get(f"{BASE_URL}/api/analytics/show-detail", params={"show_id": sid}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()

        # top-level keys
        for key in ("show", "metrics", "top_songs", "top_tippers", "repeat_requesters"):
            assert key in data, f"missing key: {key}"

        # show subobject
        assert data["show"]["id"] == sid

        # metrics subobject
        m = data["metrics"]
        for key in (
            "total_requests",
            "requests_with_email",
            "email_capture_rate",
            "total_tip_revenue",
            "tip_count",
            "click_through_rate",
            "requests_with_click",
        ):
            assert key in m, f"missing metric: {key}"

        # types
        assert isinstance(m["total_requests"], int)
        assert isinstance(m["requests_with_email"], int)
        assert isinstance(m["email_capture_rate"], (int, float))
        assert isinstance(m["total_tip_revenue"], (int, float))
        assert isinstance(m["tip_count"], int)
        assert isinstance(m["click_through_rate"], (int, float))
        assert isinstance(m["requests_with_click"], int)

        # lists
        assert isinstance(data["top_songs"], list)
        assert isinstance(data["top_tippers"], list)
        assert isinstance(data["repeat_requesters"], list)

    def test_top_songs_sorted_desc_and_capped_at_5(self, auth, shows):
        # Pick a show with the most requests to maximize chance of multiple songs
        best = None
        for s in shows[:20]:
            r = auth.get(
                f"{BASE_URL}/api/analytics/show-detail",
                params={"show_id": s["id"]},
                timeout=30,
            )
            if r.status_code != 200:
                continue
            d = r.json()
            total = d["metrics"]["total_requests"]
            if best is None or total > best[0]:
                best = (total, d)
        assert best is not None, "Could not get any show-detail response"
        d = best[1]
        ts = d["top_songs"]
        assert len(ts) <= 5
        # sorted desc
        counts = [s["count"] for s in ts]
        assert counts == sorted(counts, reverse=True)

    def test_top_tippers_sorted_desc_and_capped_at_5(self, auth, shows):
        # Just ensure invariants on whichever show we pick
        sid = shows[0]["id"]
        r = auth.get(f"{BASE_URL}/api/analytics/show-detail", params={"show_id": sid}, timeout=30)
        assert r.status_code == 200
        tt = r.json()["top_tippers"]
        assert len(tt) <= 5
        amounts = [t["amount"] for t in tt]
        assert amounts == sorted(amounts, reverse=True)
        # name is always set; empty -> Anonymous
        for t in tt:
            assert t.get("name")  # non-empty string

    def test_email_capture_rate_math(self, auth, shows):
        sid = shows[0]["id"]
        r = auth.get(f"{BASE_URL}/api/analytics/show-detail", params={"show_id": sid}, timeout=30)
        assert r.status_code == 200
        m = r.json()["metrics"]
        if m["total_requests"] > 0:
            expected = round((m["requests_with_email"] / m["total_requests"]) * 100, 1)
            assert m["email_capture_rate"] == expected
        else:
            assert m["email_capture_rate"] == 0.0
        # rate between 0 and 100
        assert 0.0 <= m["email_capture_rate"] <= 100.0

    def test_click_through_rate_math(self, auth, shows):
        sid = shows[0]["id"]
        r = auth.get(f"{BASE_URL}/api/analytics/show-detail", params={"show_id": sid}, timeout=30)
        assert r.status_code == 200
        m = r.json()["metrics"]
        if m["total_requests"] > 0:
            expected = round((m["requests_with_click"] / m["total_requests"]) * 100, 1)
            assert m["click_through_rate"] == expected
        else:
            assert m["click_through_rate"] == 0.0
        assert 0.0 <= m["click_through_rate"] <= 100.0

    def test_tip_revenue_non_negative(self, auth, shows):
        sid = shows[0]["id"]
        r = auth.get(f"{BASE_URL}/api/analytics/show-detail", params={"show_id": sid}, timeout=30)
        assert r.status_code == 200
        m = r.json()["metrics"]
        assert m["total_tip_revenue"] >= 0
        assert m["tip_count"] >= 0

    def test_repeat_requesters_shape(self, auth, shows):
        # Look across the first few shows to find a non-empty repeat_requesters
        found = False
        for s in shows[:25]:
            r = auth.get(
                f"{BASE_URL}/api/analytics/show-detail",
                params={"show_id": s["id"]},
                timeout=30,
            )
            if r.status_code != 200:
                continue
            rr = r.json().get("repeat_requesters", [])
            for item in rr:
                # shows_count >= 2 always (THIS show + at least one other)
                assert item.get("shows_count", 0) >= 2, item
                assert "email" in item
                # request_count integer
                assert isinstance(item.get("request_count", 0), int)
                found = True
                break
            if found:
                break
        # not asserting found=True since seeded data may not include repeat requesters


# ----------------------------- show-trends -----------------------------
class TestShowTrendsAuth:
    def test_requires_auth(self):
        s = requests.Session()
        r = s.get(
            f"{BASE_URL}/api/analytics/show-trends",
            params={"profile_id": "xxx", "limit": 5},
            timeout=30,
        )
        assert r.status_code in (401, 403)


class TestShowTrendsBehavior:
    @pytest.mark.parametrize("limit", [5, 10, 20])
    def test_valid_limits(self, auth, profiles, limit):
        pid = profiles[0]["id"]
        r = auth.get(
            f"{BASE_URL}/api/analytics/show-trends",
            params={"profile_id": pid, "limit": limit},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["limit"] == limit
        assert data["profile_id"] == pid
        assert isinstance(data["shows"], list)
        assert len(data["shows"]) <= limit

    def test_invalid_limit_defaults_to_5(self, auth, profiles):
        pid = profiles[0]["id"]
        r = auth.get(
            f"{BASE_URL}/api/analytics/show-trends",
            params={"profile_id": pid, "limit": 7},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 5, f"expected default 5, got {data['limit']}"
        assert len(data["shows"]) <= 5

    def test_shows_have_required_fields(self, auth, profiles):
        pid = profiles[0]["id"]
        r = auth.get(
            f"{BASE_URL}/api/analytics/show-trends",
            params={"profile_id": pid, "limit": 20},
            timeout=30,
        )
        assert r.status_code == 200
        for s in r.json()["shows"]:
            for key in (
                "show_id",
                "show_name",
                "date",
                "total_requests",
                "email_capture_count",
                "tip_revenue",
                "click_through_rate",
            ):
                assert key in s, f"missing {key} in trend show entry"
            # CTR & email_capture_count invariants
            if s["total_requests"] > 0:
                assert s["email_capture_count"] <= s["total_requests"]
                assert 0.0 <= s["click_through_rate"] <= 100.0
            else:
                assert s["click_through_rate"] == 0.0

    def test_shows_sorted_oldest_to_newest(self, auth, profiles):
        """Returned chronologically (oldest first) for plotting."""
        pid = profiles[0]["id"]
        r = auth.get(
            f"{BASE_URL}/api/analytics/show-trends",
            params={"profile_id": pid, "limit": 20},
            timeout=30,
        )
        assert r.status_code == 200
        shows = r.json()["shows"]
        if len(shows) < 2:
            pytest.skip("Need at least 2 shows in profile to verify order")
        # We cross-check chronology by comparing against /api/shows for the same profile.
        all_shows_resp = auth.get(f"{BASE_URL}/api/shows", timeout=30)
        all_data = all_shows_resp.json()
        all_shows = all_data.get("shows") if isinstance(all_data, dict) else all_data
        profile_shows = [s for s in all_shows if s.get("profile_id") == pid]
        # newest first per /api/shows; build map id->created_at order index
        order = {s["id"]: idx for idx, s in enumerate(profile_shows)}
        idxs = [order.get(s["show_id"]) for s in shows if s["show_id"] in order]
        # idxs should be in descending order (since 0 = newest in /api/shows
        # and the trend returns oldest -> newest)
        if len(idxs) >= 2 and all(i is not None for i in idxs):
            assert idxs == sorted(idxs, reverse=True), (
                f"Expected oldest->newest ordering. order indices: {idxs}"
            )

    def test_unknown_profile_returns_empty(self, auth):
        r = auth.get(
            f"{BASE_URL}/api/analytics/show-trends",
            params={"profile_id": "nope-xyz", "limit": 5},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["shows"] == []
        assert data["limit"] == 5
