"""
Backend tests for the Zelle derivation logic in _build_profile_public_response.

Bug fix being verified (server.py ~line 8916):
The profile stores Zelle as a single string field `zelle_info` (email OR phone).
The audience tip UI reads `zelle_email` / `zelle_phone`. The serializer must:
  - When zelle_info has "@"  -> zelle_email=value, zelle_phone=None
  - When zelle_info has no "@" -> zelle_phone=value, zelle_email=None
  - When zelle_info is empty/null -> fall back to musician.zelle_email/zelle_phone,
    and the returned zelle_info should be None
  - Whitespace surrounding zelle_info must be stripped

Public endpoints exercised by this serializer:
  - GET /api/musicians/{master_slug}/{profile_slug}  (named-profile endpoint)
  - GET /api/musicians/{master_slug}                 (default-profile endpoint)

Auth: test@test.com / test  (master slug: 'test')
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://chord-pro-viewer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"
MASTER_SLUG = "test"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok, "No token in login response"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def default_profile(auth_headers):
    """Discover the musician's default profile dynamically (NOT hardcoded)."""
    r = requests.get(f"{API}/profiles", headers=auth_headers, timeout=20)
    assert r.status_code == 200, f"GET /api/profiles failed: {r.status_code} {r.text}"
    profiles = r.json()
    if isinstance(profiles, dict) and "profiles" in profiles:
        profiles = profiles["profiles"]
    assert isinstance(profiles, list) and len(profiles) > 0, "No profiles returned"
    defaults = [p for p in profiles if p.get("is_default") is True]
    assert defaults, f"No default profile found in {profiles}"
    return defaults[0]


# ---------- Helpers ----------

def _put_zelle_info(auth_headers, profile_id, value):
    """PUT /api/profiles/{id} with zelle_info=value (use None to send None)."""
    payload = {"zelle_info": value}
    r = requests.put(f"{API}/profiles/{profile_id}", headers=auth_headers, json=payload, timeout=20)
    assert r.status_code == 200, f"PUT profile failed: {r.status_code} {r.text}"
    return r.json()


def _get_public_named(profile_slug):
    r = requests.get(f"{API}/musicians/{MASTER_SLUG}/{profile_slug}", timeout=20)
    assert r.status_code == 200, f"Named public GET failed: {r.status_code} {r.text}"
    return r.json()


def _get_public_default():
    r = requests.get(f"{API}/musicians/{MASTER_SLUG}", timeout=20)
    assert r.status_code == 200, f"Default public GET failed: {r.status_code} {r.text}"
    return r.json()


# ---------- Tests ----------

class TestZelleDerivation:
    """Verify the zelle_info -> zelle_email/zelle_phone derivation for the public profile serializer."""

    def test_zelle_info_email(self, auth_headers, default_profile):
        """zelle_info containing '@' should populate zelle_email and null zelle_phone."""
        slug = default_profile["slug"]
        _put_zelle_info(auth_headers, default_profile["id"], "pay@zelle.com")

        for body in (_get_public_named(slug), _get_public_default()):
            assert body.get("zelle_info") == "pay@zelle.com", body
            assert body.get("zelle_email") == "pay@zelle.com", body
            assert body.get("zelle_phone") is None, body

    def test_zelle_info_phone(self, auth_headers, default_profile):
        """zelle_info without '@' should populate zelle_phone and null zelle_email."""
        slug = default_profile["slug"]
        _put_zelle_info(auth_headers, default_profile["id"], "555-123-4567")

        for body in (_get_public_named(slug), _get_public_default()):
            assert body.get("zelle_info") == "555-123-4567", body
            assert body.get("zelle_phone") == "555-123-4567", body
            assert body.get("zelle_email") is None, body

    def test_zelle_info_whitespace_stripped(self, auth_headers, default_profile):
        """Surrounding whitespace must be stripped in both zelle_info and the derived field."""
        slug = default_profile["slug"]
        _put_zelle_info(auth_headers, default_profile["id"], "  pay@zelle.com  ")

        for body in (_get_public_named(slug), _get_public_default()):
            assert body.get("zelle_info") == "pay@zelle.com", body
            assert body.get("zelle_email") == "pay@zelle.com", body
            assert body.get("zelle_phone") is None, body

    def test_zelle_info_empty_falls_back_to_master(self, auth_headers, default_profile):
        """Empty/null zelle_info -> serializer falls back to musician.zelle_email / zelle_phone.
        Sends empty string which the PUT endpoint coerces to None on the profile doc."""
        slug = default_profile["slug"]
        _put_zelle_info(auth_headers, default_profile["id"], "")

        # Fetch master musician's stored zelle_email / zelle_phone for expected fallback values.
        r = requests.get(f"{API}/profile", headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        master = r.json()
        expected_email = master.get("zelle_email")
        expected_phone = master.get("zelle_phone")

        for body in (_get_public_named(slug), _get_public_default()):
            assert body.get("zelle_info") is None, body
            assert body.get("zelle_email") == expected_email, body
            assert body.get("zelle_phone") == expected_phone, body

    def test_other_payment_handles_intact(self, auth_headers, default_profile):
        """Regression: other payment handle fields are still serialized properly."""
        # Restore the profile to an email so all fields are populated
        _put_zelle_info(auth_headers, default_profile["id"], "pay@zelle.com")

        body = _get_public_named(default_profile["slug"])

        # Required keys present
        for key in (
            "paypal_username", "venmo_username", "cash_app_username",
            "zelle_info", "zelle_email", "zelle_phone",
            "paypal_enabled", "venmo_enabled", "cash_app_enabled", "zelle_enabled",
            "id", "name", "slug", "profile_id", "profile_name", "profile_slug",
        ):
            assert key in body, f"Missing key '{key}' in public response: {list(body.keys())}"

        # Toggle/enable fields should be booleans
        for flag in ("paypal_enabled", "venmo_enabled", "cash_app_enabled", "zelle_enabled"):
            assert isinstance(body[flag], bool), f"{flag} not bool: {body[flag]!r}"

        # Sigils (@ / $) should NOT appear on the cleaned handles in the public response.
        for handle_key in ("paypal_username", "venmo_username", "cash_app_username"):
            val = body.get(handle_key)
            if isinstance(val, str):
                assert not val.startswith("@") and not val.startswith("$"), f"{handle_key} not cleaned: {val!r}"


# ---------- Cleanup ----------

@pytest.fixture(scope="module", autouse=True)
def _cleanup(auth_headers, default_profile):
    """Restore zelle_info to None after the module runs to avoid polluting the env."""
    yield
    try:
        requests.put(
            f"{API}/profiles/{default_profile['id']}",
            headers=auth_headers,
            json={"zelle_info": ""},
            timeout=20,
        )
    except Exception:
        pass
