"""
Backend tests for FIX 1 + FIX 2 of the Requests tab per-profile shows feature.

FIX 1: POST /api/shows/start scoping
- Defaults to the musician's default profile when neither profile_id nor event_id is provided
- Uses the supplied profile_id when provided (scoped to non-default profile)
- Honors event_id with precedence over profile_id (existing backend contract)

FIX 2: POST /api/shows/stop per-profile scoping
- Stops only the supplied profile_id's show; other profiles' shows stay active
- Defaults to default profile when no profile_id passed
"""

import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "test@test.com"
PASSWORD = "test"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    token = r.json().get("token")
    if not token:
        pytest.skip("No token returned from login")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---------- helpers ----------
def _list_profiles(auth_session):
    r = auth_session.get(f"{API}/profiles")
    assert r.status_code == 200, r.text
    return r.json()


def _get_default_profile(auth_session):
    profs = _list_profiles(auth_session)
    for p in profs:
        if p.get("is_default"):
            return p
    pytest.skip("No default profile exists for this account")


def _ensure_second_profile(auth_session):
    """Find or create a non-default profile for testing."""
    profs = _list_profiles(auth_session)
    for p in profs:
        if not p.get("is_default"):
            return p
    # Create one
    unique = uuid.uuid4().hex[:6]
    payload = {"name": f"TEST_ProfileB_{unique}", "slug": f"test-profileb-{unique}"}
    r = auth_session.post(f"{API}/profiles", json=payload)
    assert r.status_code in (200, 201), f"Profile creation failed: {r.status_code} {r.text}"
    return r.json()


def _stop_all(auth_session):
    """Best-effort: stop shows on every profile."""
    for p in _list_profiles(auth_session):
        try:
            auth_session.post(f"{API}/shows/stop", json={"profile_id": p["id"]})
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _cleanup_between(auth_session):
    _stop_all(auth_session)
    yield
    _stop_all(auth_session)


# ============================================================================
# FIX 1: Start show scoping
# ============================================================================
class TestStartShowScoping:
    def test_start_show_defaults_to_default_profile(self, auth_session):
        """No profile_id, no event_id -> uses default profile."""
        default_profile = _get_default_profile(auth_session)
        show_name = f"TEST_default_{uuid.uuid4().hex[:6]}"
        r = auth_session.post(f"{API}/shows/start", json={"name": show_name})
        assert r.status_code == 200, r.text
        body = r.json()
        # show.profile_id matches default profile
        show = body.get("show") or {}
        assert show.get("profile_id") == default_profile["id"], (
            f"Expected default profile_id {default_profile['id']}, got {show.get('profile_id')}"
        )
        assert show.get("name") == show_name
        # default profile's current_show_id is updated
        profs = _list_profiles(auth_session)
        d2 = next(p for p in profs if p["id"] == default_profile["id"])
        assert d2.get("current_show_id") == show.get("id")
        assert d2.get("current_show_name") == show_name

    def test_start_show_with_profile_id_scopes_to_that_profile(self, auth_session):
        """Pass profile_id == non-default profile -> show created on that profile only."""
        default_profile = _get_default_profile(auth_session)
        second = _ensure_second_profile(auth_session)
        assert second["id"] != default_profile["id"]

        show_name = f"TEST_second_{uuid.uuid4().hex[:6]}"
        r = auth_session.post(
            f"{API}/shows/start",
            json={"name": show_name, "profile_id": second["id"]},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        show = body.get("show") or {}
        assert show.get("profile_id") == second["id"], (
            f"Expected profile_id {second['id']} got {show.get('profile_id')}"
        )

        profs = _list_profiles(auth_session)
        s2 = next(p for p in profs if p["id"] == second["id"])
        d2 = next(p for p in profs if p["id"] == default_profile["id"])
        assert s2.get("current_show_id") == show.get("id")
        assert s2.get("current_show_name") == show_name
        # default profile should NOT have been started
        assert d2.get("current_show_id") in (None, "")

    def test_start_show_with_event_id_takes_precedence(self, auth_session):
        """event_id > profile_id: when both passed, event_id wins (existing contract)."""
        default_profile = _get_default_profile(auth_session)
        second = _ensure_second_profile(auth_session)

        # Create an event under default_profile
        ev_uniq = uuid.uuid4().hex[:6]
        ev_payload = {
            "name": f"TEST_event_{ev_uniq}",
            "slug": f"test-event-{ev_uniq}",
            "profile_id": default_profile["id"],
            "event_date": "2030-01-01",
        }
        r = auth_session.post(f"{API}/events", json=ev_payload)
        if r.status_code not in (200, 201):
            pytest.skip(f"Event creation not supported / failed: {r.status_code} {r.text}")
        event = r.json()
        event_id = event.get("id")
        assert event_id

        show_name = f"TEST_event_show_{uuid.uuid4().hex[:6]}"
        r = auth_session.post(
            f"{API}/shows/start",
            json={
                "name": show_name,
                "event_id": event_id,
                "profile_id": second["id"],  # should be ignored due to event precedence
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        show = body.get("show") or {}
        # show is tagged with event_id and event's profile_id (default), NOT second.id
        assert show.get("event_id") == event_id
        assert show.get("profile_id") == default_profile["id"], (
            f"event_id should override profile_id. Expected default profile, got {show.get('profile_id')}"
        )

        # Event's current_show_id is updated
        r = auth_session.get(f"{API}/events")
        assert r.status_code == 200
        ev2 = next((e for e in r.json() if e["id"] == event_id), None)
        assert ev2 is not None
        assert ev2.get("current_show_id") == show.get("id")

        # Cleanup: stop via event_id, then delete event
        auth_session.post(f"{API}/shows/stop", json={"event_id": event_id})
        auth_session.delete(f"{API}/events/{event_id}")


# ============================================================================
# FIX 2: Per-profile stop semantics
# ============================================================================
class TestPerProfileStop:
    def test_stop_only_target_profile_keeps_others_active(self, auth_session):
        """Start shows on two profiles; stop only one; the other should remain active."""
        default_profile = _get_default_profile(auth_session)
        second = _ensure_second_profile(auth_session)

        # Start show on default
        sn1 = f"TEST_default_show_{uuid.uuid4().hex[:6]}"
        r1 = auth_session.post(f"{API}/shows/start", json={"name": sn1})
        assert r1.status_code == 200, r1.text
        show1 = r1.json()["show"]
        assert show1["profile_id"] == default_profile["id"]

        # Start show on second
        sn2 = f"TEST_second_show_{uuid.uuid4().hex[:6]}"
        r2 = auth_session.post(
            f"{API}/shows/start", json={"name": sn2, "profile_id": second["id"]}
        )
        assert r2.status_code == 200, r2.text
        show2 = r2.json()["show"]
        assert show2["profile_id"] == second["id"]

        # Sanity: both profiles have current_show_id
        profs = _list_profiles(auth_session)
        d = next(p for p in profs if p["id"] == default_profile["id"])
        s = next(p for p in profs if p["id"] == second["id"])
        assert d["current_show_id"] == show1["id"]
        assert s["current_show_id"] == show2["id"]

        # Stop ONLY second
        rs = auth_session.post(f"{API}/shows/stop", json={"profile_id": second["id"]})
        assert rs.status_code == 200, rs.text

        # Verify: second cleared, default UNCHANGED
        profs = _list_profiles(auth_session)
        d = next(p for p in profs if p["id"] == default_profile["id"])
        s = next(p for p in profs if p["id"] == second["id"])
        assert s["current_show_id"] in (None, ""), f"Second profile should be cleared, got {s['current_show_id']}"
        assert s["current_show_name"] in (None, "")
        assert d["current_show_id"] == show1["id"], (
            f"Default profile show should remain active after stopping second profile only. "
            f"Got current_show_id={d['current_show_id']}, expected {show1['id']}"
        )
        assert d["current_show_name"] == sn1

    def test_stop_without_payload_defaults_to_default_profile(self, auth_session):
        """POST /shows/stop with no body stops the default profile only."""
        default_profile = _get_default_profile(auth_session)
        second = _ensure_second_profile(auth_session)

        sn1 = f"TEST_default_show_{uuid.uuid4().hex[:6]}"
        auth_session.post(f"{API}/shows/start", json={"name": sn1})
        sn2 = f"TEST_second_show_{uuid.uuid4().hex[:6]}"
        auth_session.post(f"{API}/shows/start", json={"name": sn2, "profile_id": second["id"]})

        # No payload -> default profile
        rs = auth_session.post(f"{API}/shows/stop", json={})
        assert rs.status_code == 200, rs.text

        profs = _list_profiles(auth_session)
        d = next(p for p in profs if p["id"] == default_profile["id"])
        s = next(p for p in profs if p["id"] == second["id"])
        assert d["current_show_id"] in (None, "")
        assert s["current_show_id"] not in (None, ""), "Second profile show should NOT have been stopped"
