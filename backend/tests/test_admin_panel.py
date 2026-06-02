"""Admin panel endpoint tests.

Covers POST /api/admin/login, GET /api/admin/users, GET /api/admin/users/{id},
GET /api/admin/users/{id}/requests, POST /api/admin/requests/reassign,
POST /api/admin/requests/delete.

Auth model: admin endpoints expect a JWT minted by admin_login (role=requestwave-admin).
Musician (non-admin) tokens must be rejected.
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://multi-show-analytics.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_PASSWORD = "changeme-admin-pwd"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/login", json={"password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 0
    return data["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def musician_token():
    r = requests.post(f"{API}/auth/login", json={"email": "test@test.com", "password": "test"}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"musician login failed: {r.status_code} {r.text}")
    return r.json().get("token")


@pytest.fixture(scope="module")
def test_musician(admin_headers):
    """Find the test musician (test@test.com) id via admin list."""
    r = requests.get(f"{API}/admin/users", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    users = r.json().get("users", [])
    for u in users:
        if u.get("email") == "test@test.com":
            return u
    pytest.skip("test@test.com musician not found")


# ---------- /api/admin/login ----------
class TestAdminLogin:
    def test_wrong_password_returns_401(self):
        r = requests.post(f"{API}/admin/login", json={"password": "nope-wrong"}, timeout=20)
        assert r.status_code == 401

    def test_empty_password_returns_401(self):
        r = requests.post(f"{API}/admin/login", json={"password": ""}, timeout=20)
        assert r.status_code == 401

    def test_correct_password_returns_token(self):
        r = requests.post(f"{API}/admin/login", json={"password": ADMIN_PASSWORD}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert isinstance(body["token"], str) and len(body["token"]) > 20


# ---------- /api/admin/users ----------
class TestAdminListUsers:
    def test_no_auth_returns_401_or_403(self):
        r = requests.get(f"{API}/admin/users", timeout=20)
        assert r.status_code in (401, 403)

    def test_musician_token_rejected(self, musician_token):
        r = requests.get(f"{API}/admin/users",
                         headers={"Authorization": f"Bearer {musician_token}"}, timeout=20)
        assert r.status_code == 401

    def test_admin_returns_users_with_counts(self, admin_headers):
        r = requests.get(f"{API}/admin/users", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "users" in body and isinstance(body["users"], list)
        assert len(body["users"]) >= 1
        u = body["users"][0]
        for k in ("id", "name", "email", "created_at", "profile_count", "show_count", "request_count"):
            assert k in u, f"missing key {k} in {u}"
        assert isinstance(u["profile_count"], int)
        assert isinstance(u["show_count"], int)
        assert isinstance(u["request_count"], int)


# ---------- /api/admin/users/{id} ----------
class TestAdminUserDetail:
    def test_no_auth(self, test_musician):
        r = requests.get(f"{API}/admin/users/{test_musician['id']}", timeout=20)
        assert r.status_code in (401, 403)

    def test_unknown_id_404(self, admin_headers):
        r = requests.get(f"{API}/admin/users/does-not-exist-xyz", headers=admin_headers, timeout=20)
        assert r.status_code == 404

    def test_valid_id_returns_structure(self, admin_headers, test_musician):
        r = requests.get(f"{API}/admin/users/{test_musician['id']}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        for k in ("musician", "profiles", "orphan_shows", "unassigned_request_count"):
            assert k in body
        assert body["musician"]["id"] == test_musician["id"]
        assert isinstance(body["profiles"], list)
        assert isinstance(body["unassigned_request_count"], int)
        # each profile shape
        if body["profiles"]:
            p = body["profiles"][0]
            for k in ("id", "name", "slug", "is_default", "shows"):
                assert k in p
            for s in p["shows"]:
                for k in ("id", "name", "date", "request_count"):
                    assert k in s


# ---------- /api/admin/users/{id}/requests ----------
class TestAdminUserRequests:
    def test_no_auth(self, test_musician):
        r = requests.get(f"{API}/admin/users/{test_musician['id']}/requests", timeout=20)
        assert r.status_code in (401, 403)

    def test_unassigned_filter(self, admin_headers, test_musician):
        r = requests.get(f"{API}/admin/users/{test_musician['id']}/requests",
                         params={"show_id": "unassigned"}, headers=admin_headers, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "requests" in body and "count" in body
        for req in body["requests"]:
            assert req.get("show_id") in (None, "", ) or "show_id" not in req

    def test_specific_show_filter(self, admin_headers, test_musician):
        # Find a real show via detail
        d = requests.get(f"{API}/admin/users/{test_musician['id']}", headers=admin_headers, timeout=30).json()
        show_id = None
        for p in d.get("profiles", []):
            if p.get("shows"):
                show_id = p["shows"][0]["id"]
                break
        if not show_id:
            pytest.skip("no shows found for test musician")
        r = requests.get(f"{API}/admin/users/{test_musician['id']}/requests",
                         params={"show_id": show_id}, headers=admin_headers, timeout=30)
        assert r.status_code == 200
        for req in r.json()["requests"]:
            assert req.get("show_id") == show_id


# ---------- /api/admin/requests/reassign + /delete ----------
class TestAdminBulkActions:
    def _seed_request(self, musician_id):
        """Seed a request directly via MongoDB (audience POST requires real song_id).
        Returns the request id. Caller is responsible for cleanup via admin delete.
        """
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = "mongodb://localhost:27017"
        db_name = os.environ.get("DB_NAME", "test_database")

        async def _insert(req_id):
            client = AsyncIOMotorClient(mongo_url)
            await client[db_name].requests.insert_one({
                "id": req_id,
                "musician_id": musician_id,
                "song_id": f"TEST_song_{uuid.uuid4().hex[:8]}",
                "song_title": f"TEST_AdminPanel_{uuid.uuid4().hex[:6]}",
                "song_artist": "TEST Admin",
                "requester_name": "TEST",
                "requester_email": "test-admin@example.com",
                "dedication": "",
                "status": "pending",
                "show_id": None,
                "show_name": "",
                "created_at": __import__("datetime").datetime.utcnow(),
            })
            client.close()

        req_id = f"TEST_admin_req_{uuid.uuid4().hex[:10]}"
        asyncio.get_event_loop().run_until_complete(_insert(req_id))
        return req_id

    def test_reassign_no_auth(self):
        r = requests.post(f"{API}/admin/requests/reassign",
                          json={"request_ids": ["x"], "show_id": "y"}, timeout=20)
        assert r.status_code in (401, 403)

    def test_reassign_empty_ids_400(self, admin_headers):
        r = requests.post(f"{API}/admin/requests/reassign",
                          json={"request_ids": [], "show_id": "any"},
                          headers=admin_headers, timeout=20)
        assert r.status_code == 400

    def test_reassign_missing_show_id_400(self, admin_headers):
        r = requests.post(f"{API}/admin/requests/reassign",
                          json={"request_ids": ["x"]},
                          headers=admin_headers, timeout=20)
        assert r.status_code == 400

    def test_reassign_unknown_show_404(self, admin_headers):
        r = requests.post(f"{API}/admin/requests/reassign",
                          json={"request_ids": ["x"], "show_id": "nonexistent-show-zzz"},
                          headers=admin_headers, timeout=20)
        assert r.status_code == 404

    def test_reassign_then_delete_full_flow(self, admin_headers, test_musician):
        # Find a real show for the test musician
        detail = requests.get(f"{API}/admin/users/{test_musician['id']}",
                              headers=admin_headers, timeout=30).json()
        target_show = None
        for p in detail.get("profiles", []):
            for s in p.get("shows", []):
                target_show = s
                break
            if target_show:
                break
        if not target_show:
            pytest.skip("no show available to reassign into")

        req_id = self._seed_request(test_musician["id"])

        # Reassign
        r = requests.post(f"{API}/admin/requests/reassign",
                          json={"request_ids": [req_id], "show_id": target_show["id"]},
                          headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["matched"] >= 1
        assert body["modified"] >= 0  # may be 0 if already assigned to that show
        assert body["show_id"] == target_show["id"]

        # Verify via GET admin requests for that show
        r2 = requests.get(f"{API}/admin/users/{test_musician['id']}/requests",
                          params={"show_id": target_show["id"]},
                          headers=admin_headers, timeout=20)
        assert r2.status_code == 200
        ids = [x.get("id") for x in r2.json()["requests"]]
        assert req_id in ids

        # Delete
        rd = requests.post(f"{API}/admin/requests/delete",
                           json={"request_ids": [req_id]},
                           headers=admin_headers, timeout=20)
        assert rd.status_code == 200
        body = rd.json()
        assert body["success"] is True
        assert body["deleted"] >= 1

        # Verify removal
        r3 = requests.get(f"{API}/admin/users/{test_musician['id']}/requests",
                          params={"show_id": target_show["id"]},
                          headers=admin_headers, timeout=20)
        ids3 = [x.get("id") for x in r3.json()["requests"]]
        assert req_id not in ids3

    def test_delete_no_auth(self):
        r = requests.post(f"{API}/admin/requests/delete",
                          json={"request_ids": ["x"]}, timeout=20)
        assert r.status_code in (401, 403)

    def test_delete_empty_ids_400(self, admin_headers):
        r = requests.post(f"{API}/admin/requests/delete",
                          json={"request_ids": []},
                          headers=admin_headers, timeout=20)
        assert r.status_code == 400
