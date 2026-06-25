"""
Tests for payment handle sigil cleaning (@ for PayPal/Venmo, $ for Cash App).
Covers:
- READ-side: GET /api/musicians/{master_slug}/{profile_slug} strips leading sigils
  + surrounding whitespace even from dirty stored values.
- SAVE-side: POST/PUT /api/profiles and POST/PUT /api/events normalize handles
  before DB write so the stored value is clean.
- Internal characters preserved (internal spaces, internal @).
- Empty-after-strip becomes None (not "").
"""
import os
import uuid
import pytest
import requests
from pathlib import Path


def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if url:
        return url.rstrip("/")
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set and not in /app/frontend/.env")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

EMAIL = "test@test.com"
PASSWORD = "test"
MASTER_SLUG = "test"
DEFAULT_PROFILE_SLUG = "main-stage"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(session):
    r = session.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text[:200]}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def default_profile(session, auth_headers):
    r = session.get(f"{API}/profiles", headers=auth_headers)
    assert r.status_code == 200, r.text
    profiles = r.json()
    assert profiles, "No profiles exist for test musician"
    for p in profiles:
        if p.get("is_default"):
            return p
    return profiles[0]


@pytest.fixture(scope="module")
def default_profile_id(default_profile):
    return default_profile["id"]


@pytest.fixture(scope="module")
def default_profile_slug(default_profile):
    return default_profile["slug"]


# Track created entities for cleanup
_created_profile_ids = []
_created_event_ids = []


@pytest.fixture(scope="module", autouse=True)
def cleanup(session, auth_headers):
    yield
    for eid in _created_event_ids:
        try:
            session.delete(f"{API}/events/{eid}", headers=auth_headers)
        except Exception:
            pass
    for pid in _created_profile_ids:
        try:
            session.delete(f"{API}/profiles/{pid}", headers=auth_headers)
        except Exception:
            pass


# ---------- READ-side + SAVE-side cleaning on default profile (PUT) ----------

class TestProfileUpdateAndPublicRead:
    """PUT /profiles/{id} should normalize handles before save, and
    GET /musicians/{master}/{profile} should also clean on-the-fly."""

    def test_put_profile_cleans_dirty_handles_and_public_endpoint_returns_clean(
        self, session, auth_headers, default_profile_id, default_profile_slug
    ):
        payload = {
            "paypal_username": "@johndoe",
            "venmo_username": " @jane-venmo ",
            "cashapp_username": "$cashuser",
        }
        r = session.put(
            f"{API}/profiles/{default_profile_id}", headers=auth_headers, json=payload
        )
        assert r.status_code == 200, r.text

        # SAVE-side: editor endpoint should now show cleaned stored values
        gr = session.get(f"{API}/profiles", headers=auth_headers)
        assert gr.status_code == 200
        prof = next(p for p in gr.json() if p["id"] == default_profile_id)
        assert prof["paypal_username"] == "johndoe", f"got {prof['paypal_username']!r}"
        assert prof["venmo_username"] == "jane-venmo", f"got {prof['venmo_username']!r}"
        assert prof["cashapp_username"] == "cashuser", f"got {prof['cashapp_username']!r}"

        # READ-side: public endpoint returns clean handles
        pr = session.get(f"{API}/musicians/{MASTER_SLUG}/{default_profile_slug}")
        assert pr.status_code == 200, pr.text
        pub = pr.json()
        assert pub["paypal_username"] == "johndoe"
        assert pub["venmo_username"] == "jane-venmo"
        assert pub["cash_app_username"] == "cashuser"


# ---------- Internal characters preserved ----------

class TestInternalCharsPreserved:
    def test_internal_space_and_internal_at_preserved(
        self, session, auth_headers, default_profile_id, default_profile_slug
    ):
        payload = {
            "paypal_username": " john doe ",  # internal space, surrounding ws
            "venmo_username": "@john@doe",    # leading @ only stripped; internal @ kept
            "cashapp_username": "$cash user",  # leading $; internal space kept
        }
        r = session.put(
            f"{API}/profiles/{default_profile_id}", headers=auth_headers, json=payload
        )
        assert r.status_code == 200, r.text

        gr = session.get(f"{API}/profiles", headers=auth_headers)
        prof = next(p for p in gr.json() if p["id"] == default_profile_id)
        assert prof["paypal_username"] == "john doe", f"got {prof['paypal_username']!r}"
        assert prof["venmo_username"] == "john@doe", f"got {prof['venmo_username']!r}"
        assert prof["cashapp_username"] == "cash user", f"got {prof['cashapp_username']!r}"

        pr = session.get(f"{API}/musicians/{MASTER_SLUG}/{default_profile_slug}")
        assert pr.status_code == 200
        pub = pr.json()
        assert pub["paypal_username"] == "john doe"
        assert pub["venmo_username"] == "john@doe"
        assert pub["cash_app_username"] == "cash user"


# ---------- Empty-after-strip => None ----------

class TestEmptyAfterStripBecomesNull:
    def test_handles_become_null_when_only_sigil(
        self, session, auth_headers, default_profile_id, default_profile_slug
    ):
        payload = {
            "paypal_username": "@",
            "venmo_username": "  ",
            "cashapp_username": "$",
        }
        r = session.put(
            f"{API}/profiles/{default_profile_id}", headers=auth_headers, json=payload
        )
        assert r.status_code == 200, r.text

        gr = session.get(f"{API}/profiles", headers=auth_headers)
        prof = next(p for p in gr.json() if p["id"] == default_profile_id)
        assert prof["paypal_username"] is None, f"got {prof['paypal_username']!r}"
        assert prof["venmo_username"] is None, f"got {prof['venmo_username']!r}"
        assert prof["cashapp_username"] is None, f"got {prof['cashapp_username']!r}"

        pr = session.get(f"{API}/musicians/{MASTER_SLUG}/{default_profile_slug}")
        assert pr.status_code == 200
        pub = pr.json()
        # Master account values may fall back; either None or non-sigil string is fine,
        # but the cleaning logic must ensure no leading sigils.
        for k in ("paypal_username", "venmo_username", "cash_app_username"):
            v = pub.get(k)
            if isinstance(v, str):
                assert not v.startswith("@") and not v.startswith("$") and v == v.strip(), (
                    f"{k} still dirty: {v!r}"
                )


# ---------- POST /profiles cleans on creation ----------

class TestCreateProfileCleansHandles:
    def test_post_profile_cleans_handles(self, session, auth_headers):
        slug = f"test-clean-{uuid.uuid4().hex[:6]}"
        payload = {
            "name": f"TEST_Clean_{slug}",
            "slug": slug,
            "paypal_username": "@newpaypal",
            "venmo_username": " @newvenmo ",
            "cashapp_username": "$newcash",
            "active_playlist_ids": ["__all__"],
        }
        r = session.post(f"{API}/profiles", headers=auth_headers, json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        pid = body["id"]
        _created_profile_ids.append(pid)

        # Returned response from create should also be clean
        assert body["paypal_username"] == "newpaypal", body
        assert body["venmo_username"] == "newvenmo", body
        assert body["cashapp_username"] == "newcash", body

        # Verify persistence via GET /profiles
        gr = session.get(f"{API}/profiles", headers=auth_headers)
        prof = next(p for p in gr.json() if p["id"] == pid)
        assert prof["paypal_username"] == "newpaypal"
        assert prof["venmo_username"] == "newvenmo"
        assert prof["cashapp_username"] == "newcash"

        # Public endpoint returns clean values too
        pr = session.get(f"{API}/musicians/{MASTER_SLUG}/{slug}")
        assert pr.status_code == 200, pr.text
        pub = pr.json()
        assert pub["paypal_username"] == "newpaypal"
        assert pub["venmo_username"] == "newvenmo"
        assert pub["cash_app_username"] == "newcash"


# ---------- POST /events and PUT /events/{id} clean handles ----------

class TestEventHandleCleaning:
    def test_post_and_put_event_clean_handles(
        self, session, auth_headers, default_profile_id
    ):
        slug = f"test-ev-clean-{uuid.uuid4().hex[:6]}"
        payload = {
            "profile_id": default_profile_id,
            "name": f"TEST_Event_{slug}",
            "slug": slug,
            "event_date": "2030-01-01",
            "paypal_username": "@evpay",
            "venmo_username": "$evvenmo",     # weird but tests $ stripping
            "cashapp_username": "$evcash",
        }
        r = session.post(f"{API}/events", headers=auth_headers, json=payload)
        assert r.status_code in (200, 201), r.text
        ev = r.json()
        eid = ev["id"]
        _created_event_ids.append(eid)

        assert ev.get("paypal_username") == "evpay", ev
        assert ev.get("venmo_username") == "evvenmo", ev
        assert ev.get("cashapp_username") == "evcash", ev

        # Now update with new dirty values
        upd = {
            "paypal_username": " @evpay2 ",
            "venmo_username": "@evvenmo2",
            "cashapp_username": "$evcash2",
        }
        ur = session.put(f"{API}/events/{eid}", headers=auth_headers, json=upd)
        assert ur.status_code == 200, ur.text
        ev2 = ur.json()
        assert ev2.get("paypal_username") == "evpay2", ev2
        assert ev2.get("venmo_username") == "evvenmo2", ev2
        assert ev2.get("cashapp_username") == "evcash2", ev2

        # Update with sigil-only => should become null
        ur2 = session.put(
            f"{API}/events/{eid}",
            headers=auth_headers,
            json={"paypal_username": "@", "venmo_username": "  ", "cashapp_username": "$"},
        )
        assert ur2.status_code == 200, ur2.text
        ev3 = ur2.json()
        assert ev3.get("paypal_username") in (None, ""), ev3
        assert ev3.get("venmo_username") in (None, ""), ev3
        assert ev3.get("cashapp_username") in (None, ""), ev3
        # Strict: spec says null, not empty string
        assert ev3.get("paypal_username") is None
        assert ev3.get("venmo_username") is None
        assert ev3.get("cashapp_username") is None
