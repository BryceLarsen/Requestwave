"""
Test show state integrity - verifies that:
1. Start show => active_show_id set, current_show_name returned
2. Stop show => active_show_id cleared, current_show_name null
3. Start new show after stop => current_show_name matches new show
4. Stop then refetch => show does not reappear
"""
import pytest
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8001/api"
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"


@pytest.fixture
def auth_headers():
    """Get authentication headers for test user"""
    response = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def musician_slug():
    """Get the test musician's slug"""
    response = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    return response.json()["musician"]["slug"]


def cleanup_active_show(auth_headers):
    """Helper to ensure no active show before test"""
    try:
        httpx.post(f"{BASE_URL}/shows/stop", headers=auth_headers)
    except:
        pass


class TestShowStateIntegrity:
    """Test suite for show state integrity"""

    def test_start_show_sets_active_show(self, auth_headers, musician_slug):
        """Test that starting a show sets active_show_id and returns current_show_name"""
        # Cleanup any existing active show
        cleanup_active_show(auth_headers)
        
        show_name = f"Test Show {datetime.now().strftime('%H%M%S')}"
        
        # Start a new show
        response = httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": show_name},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Start show failed: {response.text}"
        data = response.json()
        
        # Verify response contains musician state
        assert "musician" in data, "Response should contain musician field"
        assert data["musician"]["current_show_id"] is not None, "current_show_id should be set"
        assert data["musician"]["current_show_name"] == show_name, "current_show_name should match"
        
        # Verify public endpoint reflects the active show
        public_response = httpx.get(f"{BASE_URL}/musicians/{musician_slug}")
        assert public_response.status_code == 200
        public_data = public_response.json()
        assert public_data["current_show_name"] == show_name, "Public endpoint should show active show name"
        
        # Cleanup
        cleanup_active_show(auth_headers)

    def test_stop_show_clears_active_show(self, auth_headers, musician_slug):
        """Test that stopping a show clears active_show_id and current_show_name"""
        # Start a show first
        show_name = f"Stop Test Show {datetime.now().strftime('%H%M%S')}"
        start_response = httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": show_name},
            headers=auth_headers
        )
        assert start_response.status_code == 200
        
        # Verify show is active
        public_response = httpx.get(f"{BASE_URL}/musicians/{musician_slug}")
        assert public_response.json()["current_show_name"] == show_name
        
        # Stop the show
        stop_response = httpx.post(
            f"{BASE_URL}/shows/stop",
            headers=auth_headers
        )
        assert stop_response.status_code == 200, f"Stop show failed: {stop_response.text}"
        stop_data = stop_response.json()
        
        # Verify response contains cleared musician state
        assert "musician" in stop_data, "Response should contain musician field"
        assert stop_data["musician"]["current_show_id"] is None, "current_show_id should be None"
        assert stop_data["musician"]["current_show_name"] is None, "current_show_name should be None"
        
        # Verify public endpoint no longer shows active show
        public_response = httpx.get(f"{BASE_URL}/musicians/{musician_slug}")
        assert public_response.status_code == 200
        public_data = public_response.json()
        assert public_data.get("current_show_name") is None, "Public endpoint should not show active show name"

    def test_start_new_show_after_stop(self, auth_headers, musician_slug):
        """Test that starting a new show after stopping shows the new show name"""
        cleanup_active_show(auth_headers)
        
        # Start first show
        first_show_name = f"First Show {datetime.now().strftime('%H%M%S')}"
        httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": first_show_name},
            headers=auth_headers
        )
        
        # Stop it
        httpx.post(f"{BASE_URL}/shows/stop", headers=auth_headers)
        
        # Start second show
        second_show_name = f"Second Show {datetime.now().strftime('%H%M%S')}"
        start_response = httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": second_show_name},
            headers=auth_headers
        )
        assert start_response.status_code == 200
        
        # Verify public endpoint shows the NEW show name
        public_response = httpx.get(f"{BASE_URL}/musicians/{musician_slug}")
        assert public_response.status_code == 200
        public_data = public_response.json()
        assert public_data["current_show_name"] == second_show_name, \
            f"Expected '{second_show_name}', got '{public_data.get('current_show_name')}'"
        
        # Cleanup
        cleanup_active_show(auth_headers)

    def test_stop_then_refetch_no_resurrection(self, auth_headers, musician_slug):
        """Test that stopped show does not reappear after refetching"""
        cleanup_active_show(auth_headers)
        
        # Start a show
        show_name = f"Resurrection Test {datetime.now().strftime('%H%M%S')}"
        httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": show_name},
            headers=auth_headers
        )
        
        # Stop it
        httpx.post(f"{BASE_URL}/shows/stop", headers=auth_headers)
        
        # Multiple fetches should all show no active show
        for i in range(3):
            public_response = httpx.get(f"{BASE_URL}/musicians/{musician_slug}")
            assert public_response.status_code == 200
            public_data = public_response.json()
            assert public_data.get("current_show_name") is None, \
                f"Fetch #{i+1}: Show should not resurrect after stop"
            
            # Also check the current show endpoint
            current_response = httpx.get(f"{BASE_URL}/shows/current", headers=auth_headers)
            assert current_response.status_code == 200
            current_data = current_response.json()
            assert current_data["active"] is False, \
                f"Fetch #{i+1}: /shows/current should report no active show"

    def test_profile_endpoint_returns_show_state(self, auth_headers):
        """Test that /profile endpoint returns current_show_id and current_show_name"""
        cleanup_active_show(auth_headers)
        
        # Check profile with no active show
        profile_response = httpx.get(f"{BASE_URL}/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert "current_show_id" in profile_data, "Profile should include current_show_id"
        assert "current_show_name" in profile_data, "Profile should include current_show_name"
        assert profile_data["current_show_id"] is None, "current_show_id should be None when no show active"
        assert profile_data["current_show_name"] is None, "current_show_name should be None when no show active"
        
        # Start a show and check profile
        show_name = f"Profile Test {datetime.now().strftime('%H%M%S')}"
        httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": show_name},
            headers=auth_headers
        )
        
        profile_response = httpx.get(f"{BASE_URL}/profile", headers=auth_headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["current_show_id"] is not None, "current_show_id should be set"
        assert profile_data["current_show_name"] == show_name, "current_show_name should match"
        
        # Cleanup
        cleanup_active_show(auth_headers)

    def test_show_ended_at_set_on_stop(self, auth_headers):
        """Test that stopped show has ended_at timestamp set"""
        cleanup_active_show(auth_headers)
        
        # Start a show
        show_name = f"EndedAt Test {datetime.now().strftime('%H%M%S')}"
        start_response = httpx.post(
            f"{BASE_URL}/shows/start",
            json={"name": show_name},
            headers=auth_headers
        )
        show_id = start_response.json()["show"]["id"]
        
        # Stop it
        httpx.post(f"{BASE_URL}/shows/stop", headers=auth_headers)
        
        # Fetch shows and check the stopped one has ended_at
        shows_response = httpx.get(f"{BASE_URL}/shows", headers=auth_headers)
        assert shows_response.status_code == 200
        shows = shows_response.json()
        
        stopped_show = next((s for s in shows if s["id"] == show_id), None)
        assert stopped_show is not None, "Stopped show should still exist in shows list"
        assert stopped_show.get("status") == "ended", "Stopped show should have status='ended'"
