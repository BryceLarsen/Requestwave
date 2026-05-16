"""Backend tests for Unassigned Requests panel feature.

Covers:
- GET /api/requests/unassigned
- POST /api/requests/{request_id}/assign-show
- Reuse: PUT /api/requests/{id}/archive, DELETE /api/requests/{id}
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

# Load REACT_APP_BACKEND_URL from frontend/.env if not in env
def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if url:
        return url.rstrip("/")
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    return ""


BASE_URL = _load_backend_url()
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    data = r.json()
    token = data.get("token") or data.get("access_token")
    musician = data.get("musician") or data.get("user") or {}
    musician_id = musician.get("id")
    if not token or not musician_id:
        pytest.skip(f"Missing token/musician_id in login response: {data}")
    return {"token": token, "musician_id": musician_id}


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token['token']}"}


# Insert an orphan request directly via DB to bypass the auto-assign-to-show
# behavior of POST /api/musicians/test/requests.
@pytest.fixture
def orphan_request(mongo_db, auth_token):
    musician_id = auth_token["musician_id"]
    req = {
        "id": str(uuid.uuid4()),
        "musician_id": musician_id,
        "song_title": f"TEST_OrphanSong_{uuid.uuid4().hex[:6]}",
        "song_artist": "TEST_Artist",
        "requester_name": "TEST_Requester",
        "requester_email": "test_orphan@example.com",
        "status": "pending",
        # No show_id — make it a true orphan
        "created_at": datetime.now(timezone.utc),
        "tip_amount": 0.0,
    }
    mongo_db.requests.insert_one(dict(req))
    yield req
    # Cleanup
    mongo_db.requests.delete_one({"id": req["id"]})


# ---------- GET /api/requests/unassigned ----------

class TestGetUnassignedRequests:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/requests/unassigned", timeout=15)
        assert r.status_code in (401, 403), f"Expected 401/403 got {r.status_code} body={r.text}"

    def test_returns_orphan_request(self, auth_headers, orphan_request):
        r = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "requests" in body and isinstance(body["requests"], list)
        ids = [x.get("id") for x in body["requests"]]
        assert orphan_request["id"] in ids, "Newly inserted orphan should appear"
        # Each item must lack show_id (null/missing/empty)
        for x in body["requests"]:
            sid = x.get("show_id")
            assert sid in (None, ""), f"Found request with show_id={sid!r} in unassigned list"

    def test_excludes_archived(self, mongo_db, auth_headers, auth_token):
        # Insert an archived orphan
        musician_id = auth_token["musician_id"]
        archived = {
            "id": str(uuid.uuid4()),
            "musician_id": musician_id,
            "song_title": "TEST_ArchivedOrphan",
            "requester_name": "TEST_R",
            "status": "archived",
            "created_at": datetime.now(timezone.utc),
            "tip_amount": 0.0,
        }
        mongo_db.requests.insert_one(dict(archived))
        try:
            r = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
            assert r.status_code == 200
            ids = [x.get("id") for x in r.json().get("requests", [])]
            assert archived["id"] not in ids, "Archived requests must be excluded"
        finally:
            mongo_db.requests.delete_one({"id": archived["id"]})

    def test_excludes_assigned(self, mongo_db, auth_headers, auth_token):
        musician_id = auth_token["musician_id"]
        # request with show_id present
        assigned = {
            "id": str(uuid.uuid4()),
            "musician_id": musician_id,
            "song_title": "TEST_AssignedReq",
            "requester_name": "TEST_R",
            "status": "pending",
            "show_id": "some-show-id",
            "show_name": "Some Show",
            "created_at": datetime.now(timezone.utc),
            "tip_amount": 0.0,
        }
        mongo_db.requests.insert_one(dict(assigned))
        try:
            r = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
            assert r.status_code == 200
            ids = [x.get("id") for x in r.json().get("requests", [])]
            assert assigned["id"] not in ids
        finally:
            mongo_db.requests.delete_one({"id": assigned["id"]})

    def test_sorted_desc_by_created_at(self, mongo_db, auth_headers, auth_token):
        musician_id = auth_token["musician_id"]
        older = {
            "id": str(uuid.uuid4()),
            "musician_id": musician_id,
            "song_title": "TEST_OrphanOlder",
            "requester_name": "TEST_R",
            "status": "pending",
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "tip_amount": 0.0,
        }
        newer = {
            "id": str(uuid.uuid4()),
            "musician_id": musician_id,
            "song_title": "TEST_OrphanNewer",
            "requester_name": "TEST_R",
            "status": "pending",
            "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "tip_amount": 0.0,
        }
        mongo_db.requests.insert_many([dict(older), dict(newer)])
        try:
            r = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
            assert r.status_code == 200
            ids = [x.get("id") for x in r.json().get("requests", [])]
            assert newer["id"] in ids and older["id"] in ids
            assert ids.index(newer["id"]) < ids.index(older["id"]), "Newer must come first"
        finally:
            mongo_db.requests.delete_many({"id": {"$in": [older["id"], newer["id"]]}})

    def test_scoped_to_current_musician(self, mongo_db, auth_headers):
        # Insert orphan for a different musician
        other = {
            "id": str(uuid.uuid4()),
            "musician_id": "some-other-musician-id-xyz",
            "song_title": "TEST_OtherMusicianOrphan",
            "requester_name": "TEST_R",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "tip_amount": 0.0,
        }
        mongo_db.requests.insert_one(dict(other))
        try:
            r = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
            assert r.status_code == 200
            ids = [x.get("id") for x in r.json().get("requests", [])]
            assert other["id"] not in ids
        finally:
            mongo_db.requests.delete_one({"id": other["id"]})


# ---------- POST /api/requests/{id}/assign-show ----------

class TestAssignShowEndpoint:
    def test_requires_auth(self, orphan_request):
        r = requests.post(
            f"{BASE_URL}/api/requests/{orphan_request['id']}/assign-show",
            json={"show_id": "anything"},
            timeout=15,
        )
        assert r.status_code in (401, 403)

    def test_assigns_show_id_and_show_name(self, mongo_db, auth_headers, orphan_request, auth_token):
        musician_id = auth_token["musician_id"]
        # Create a show belonging to this musician
        show = {
            "id": str(uuid.uuid4()),
            "musician_id": musician_id,
            "name": "TEST_AssignTargetShow",
            "date": "2025-12-31",
            "venue": "Test Venue",
            "created_at": datetime.now(timezone.utc),
        }
        mongo_db.shows.insert_one(dict(show))
        try:
            r = requests.post(
                f"{BASE_URL}/api/requests/{orphan_request['id']}/assign-show",
                headers=auth_headers,
                json={"show_id": show["id"]},
                timeout=15,
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body.get("success") is True
            assert body.get("request_id") == orphan_request["id"]
            assert body.get("show_id") == show["id"]
            assert body.get("show_name") == show["name"]

            # Verify persisted
            doc = mongo_db.requests.find_one({"id": orphan_request["id"]})
            assert doc["show_id"] == show["id"]
            assert doc["show_name"] == show["name"]

            # And now it should NOT appear in unassigned list
            r2 = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
            ids = [x.get("id") for x in r2.json().get("requests", [])]
            assert orphan_request["id"] not in ids
        finally:
            mongo_db.shows.delete_one({"id": show["id"]})

    def test_missing_show_id_returns_400(self, auth_headers, orphan_request):
        r = requests.post(
            f"{BASE_URL}/api/requests/{orphan_request['id']}/assign-show",
            headers=auth_headers,
            json={},
            timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_request_not_found_returns_404(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/requests/non-existent-request-id-12345/assign-show",
            headers=auth_headers,
            json={"show_id": "any"},
            timeout=15,
        )
        assert r.status_code == 404, r.text

    def test_show_not_found_returns_404(self, auth_headers, orphan_request):
        r = requests.post(
            f"{BASE_URL}/api/requests/{orphan_request['id']}/assign-show",
            headers=auth_headers,
            json={"show_id": "non-existent-show-id-xyz"},
            timeout=15,
        )
        assert r.status_code == 404, r.text

    def test_cross_musician_returns_404(self, mongo_db, auth_headers):
        # Insert request belonging to a different musician
        other = {
            "id": str(uuid.uuid4()),
            "musician_id": "some-other-musician-xyz",
            "song_title": "TEST_OtherMusicianReq",
            "requester_name": "TEST_R",
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "tip_amount": 0.0,
        }
        mongo_db.requests.insert_one(dict(other))
        try:
            r = requests.post(
                f"{BASE_URL}/api/requests/{other['id']}/assign-show",
                headers=auth_headers,
                json={"show_id": "any"},
                timeout=15,
            )
            assert r.status_code == 404, r.text
        finally:
            mongo_db.requests.delete_one({"id": other["id"]})


# ---------- Reused endpoints ----------

class TestReusedEndpoints:
    def test_archive_orphan(self, mongo_db, auth_headers, orphan_request):
        r = requests.put(
            f"{BASE_URL}/api/requests/{orphan_request['id']}/archive",
            headers=auth_headers,
            json={},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        doc = mongo_db.requests.find_one({"id": orphan_request["id"]})
        assert doc.get("status") == "archived"
        # And no longer in unassigned
        r2 = requests.get(f"{BASE_URL}/api/requests/unassigned", headers=auth_headers, timeout=15)
        ids = [x.get("id") for x in r2.json().get("requests", [])]
        assert orphan_request["id"] not in ids

    def test_delete_orphan(self, mongo_db, auth_headers, orphan_request):
        r = requests.delete(
            f"{BASE_URL}/api/requests/{orphan_request['id']}",
            headers=auth_headers,
            timeout=15,
        )
        assert r.status_code in (200, 204), r.text
        assert mongo_db.requests.find_one({"id": orphan_request["id"]}) is None
