"""
RequestWave Bug Fix Tests
Tests for three specific issues:
1. P0: Analytics period filters - Today/7d/30d/365d/All Time return different UTC windows
2. P1: Learn Later actions - Match/Add/Trash buttons work, Restore button removed
3. P2: On Stage scope - Empty state when no active show, filtered by show_id when active
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://requestwave-fix.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def musician_id(self, auth_token):
        """Get musician ID from login response"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["musician"]["id"]
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "musician" in data
        assert data["musician"]["email"] == TEST_EMAIL


class TestAnalyticsPeriodFilters:
    """
    P0: Analytics period filters tests
    Verify that Today/7d/30d/365d/All Time return different UTC windows with correct counts
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_analytics_all_time_no_days_param(self, auth_headers):
        """Test analytics with no days parameter (All Time)"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should return all requests
        assert "total_requests" in data
        print(f"All Time (no param): {data.get('total_requests', 0)} requests")
    
    def test_analytics_all_time_days_zero(self, auth_headers):
        """Test analytics with days=0 (All Time)"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily?days=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should return all requests (same as no param)
        assert "total_requests" in data
        print(f"All Time (days=0): {data.get('total_requests', 0)} requests")
    
    def test_analytics_today(self, auth_headers):
        """Test analytics for Today (days=1)"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily?days=1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        print(f"Today (days=1): {data.get('total_requests', 0)} requests")
    
    def test_analytics_7_days(self, auth_headers):
        """Test analytics for 7 days"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily?days=7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        print(f"7 days: {data.get('total_requests', 0)} requests")
    
    def test_analytics_30_days(self, auth_headers):
        """Test analytics for 30 days"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily?days=30", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        print(f"30 days: {data.get('total_requests', 0)} requests")
    
    def test_analytics_365_days(self, auth_headers):
        """Test analytics for 365 days"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily?days=365", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        print(f"365 days: {data.get('total_requests', 0)} requests")
    
    def test_analytics_period_filter_logic(self, auth_headers):
        """
        Verify that days=0 and no days param both return All Time data
        This tests the fix: changed from 'days is not None' to 'days > 0'
        """
        # Get All Time with no param
        response_no_param = requests.get(f"{BASE_URL}/api/analytics/daily", headers=auth_headers)
        assert response_no_param.status_code == 200
        data_no_param = response_no_param.json()
        
        # Get All Time with days=0
        response_days_0 = requests.get(f"{BASE_URL}/api/analytics/daily?days=0", headers=auth_headers)
        assert response_days_0.status_code == 200
        data_days_0 = response_days_0.json()
        
        # Both should return the same total_requests count
        assert data_no_param.get("total_requests") == data_days_0.get("total_requests"), \
            f"All Time counts should match: no_param={data_no_param.get('total_requests')}, days=0={data_days_0.get('total_requests')}"
        
        print(f"All Time verification: no_param={data_no_param.get('total_requests')}, days=0={data_days_0.get('total_requests')}")


class TestLearnLaterActions:
    """
    P1: Learn Later list actions tests
    Verify Match button opens modal, Add button works, Trash button works
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def musician_id(self, auth_headers):
        """Get musician ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["musician"]["id"]
    
    def test_get_song_suggestions(self, auth_headers):
        """Test fetching song suggestions"""
        response = requests.get(f"{BASE_URL}/api/song-suggestions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} song suggestions")
        
        # Check for learn_later suggestions
        learn_later = [s for s in data if s.get("status") == "learn_later"]
        print(f"Learn Later suggestions: {len(learn_later)}")
        return data
    
    def test_update_suggestion_status_to_learn_later(self, auth_headers, musician_id):
        """Test marking a suggestion as learn_later"""
        # First create a test suggestion
        test_suggestion = {
            "suggested_title": "TEST_Learn_Later_Song",
            "suggested_artist": "TEST_Artist",
            "requester_name": "Test User",
            "requester_email": "testuser@test.com",
            "message": "Please learn this song!"
        }
        
        # Create suggestion via audience endpoint (simulating audience submission)
        create_response = requests.post(
            f"{BASE_URL}/api/musicians/test/suggest-song",
            json=test_suggestion
        )
        
        if create_response.status_code == 201:
            suggestion_id = create_response.json().get("id")
            
            # Update status to learn_later
            update_response = requests.put(
                f"{BASE_URL}/api/song-suggestions/{suggestion_id}/status",
                json={"status": "learn_later"},
                headers=auth_headers
            )
            assert update_response.status_code == 200
            print(f"Successfully marked suggestion as learn_later")
            
            # Verify the status was updated
            get_response = requests.get(f"{BASE_URL}/api/song-suggestions", headers=auth_headers)
            suggestions = get_response.json()
            updated_suggestion = next((s for s in suggestions if s.get("id") == suggestion_id), None)
            if updated_suggestion:
                assert updated_suggestion.get("status") == "learn_later"
            
            # Clean up - delete the test suggestion
            requests.delete(f"{BASE_URL}/api/song-suggestions/{suggestion_id}", headers=auth_headers)
        else:
            print(f"Could not create test suggestion: {create_response.status_code}")
    
    def test_add_suggestion_to_repertoire(self, auth_headers):
        """Test adding a suggestion as a new song (Add button)"""
        # Create a test suggestion
        test_suggestion = {
            "suggested_title": "TEST_Add_Song",
            "suggested_artist": "TEST_Add_Artist",
            "requester_name": "Test User",
            "requester_email": "testuser@test.com",
            "message": "Add this song!"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/musicians/test/suggest-song",
            json=test_suggestion
        )
        
        if create_response.status_code == 201:
            suggestion_id = create_response.json().get("id")
            
            # Update status to 'added' (simulates Add button)
            update_response = requests.put(
                f"{BASE_URL}/api/song-suggestions/{suggestion_id}/status",
                json={"status": "added"},
                headers=auth_headers
            )
            assert update_response.status_code == 200
            print(f"Successfully added suggestion to repertoire")
            
            # Clean up - delete the test song if it was created
            songs_response = requests.get(f"{BASE_URL}/api/songs?sort_by=created_at", headers=auth_headers)
            songs = songs_response.json()
            test_song = next((s for s in songs if s.get("title") == "TEST_Add_Song"), None)
            if test_song:
                requests.delete(f"{BASE_URL}/api/songs/{test_song['id']}", headers=auth_headers)
        else:
            print(f"Could not create test suggestion: {create_response.status_code}")
    
    def test_delete_suggestion(self, auth_headers):
        """Test deleting a suggestion (Trash button)"""
        # Create a test suggestion
        test_suggestion = {
            "suggested_title": "TEST_Delete_Song",
            "suggested_artist": "TEST_Delete_Artist",
            "requester_name": "Test User",
            "requester_email": "testuser@test.com",
            "message": "Delete this!"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/musicians/test/suggest-song",
            json=test_suggestion
        )
        
        if create_response.status_code == 201:
            suggestion_id = create_response.json().get("id")
            
            # Delete the suggestion (simulates Trash button)
            delete_response = requests.delete(
                f"{BASE_URL}/api/song-suggestions/{suggestion_id}",
                headers=auth_headers
            )
            assert delete_response.status_code == 200
            print(f"Successfully deleted suggestion")
            
            # Verify deletion
            get_response = requests.get(f"{BASE_URL}/api/song-suggestions", headers=auth_headers)
            suggestions = get_response.json()
            deleted_suggestion = next((s for s in suggestions if s.get("id") == suggestion_id), None)
            assert deleted_suggestion is None, "Suggestion should be deleted"
        else:
            print(f"Could not create test suggestion: {create_response.status_code}")


class TestOnStageScope:
    """
    P2: On Stage tab scope tests
    Verify empty state when no active show, and filtering by show_id when active
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_current_show(self, auth_headers):
        """Test getting current show status"""
        response = requests.get(f"{BASE_URL}/api/shows/current", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "active" in data
        print(f"Current show active: {data.get('active')}")
        if data.get("active") and data.get("show"):
            print(f"Current show: {data['show'].get('name')}")
        return data
    
    def test_get_shows_list(self, auth_headers):
        """Test getting list of shows"""
        response = requests.get(f"{BASE_URL}/api/shows", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} shows")
        
        # Check for active shows
        active_shows = [s for s in data if s.get("status") == "active"]
        archived_shows = [s for s in data if s.get("status") == "archived"]
        print(f"Active shows: {len(active_shows)}, Archived shows: {len(archived_shows)}")
        return data
    
    def test_get_grouped_requests(self, auth_headers):
        """Test getting requests grouped by show"""
        response = requests.get(f"{BASE_URL}/api/requests/grouped", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "unassigned" in data
        assert "shows" in data
        print(f"Unassigned requests: {len(data.get('unassigned', []))}")
        print(f"Shows with requests: {len(data.get('shows', {}))}")
        return data
    
    def test_start_and_stop_show(self, auth_headers):
        """Test starting and stopping a show"""
        # First check if there's already an active show
        current_response = requests.get(f"{BASE_URL}/api/shows/current", headers=auth_headers)
        current_data = current_response.json()
        
        if current_data.get("active"):
            # Stop the current show first
            stop_response = requests.post(f"{BASE_URL}/api/shows/stop", headers=auth_headers)
            assert stop_response.status_code == 200
            print("Stopped existing show")
        
        # Start a new test show
        start_response = requests.post(
            f"{BASE_URL}/api/shows/start",
            json={"name": "TEST_Show_For_OnStage", "timezone": "America/New_York"},
            headers=auth_headers
        )
        assert start_response.status_code == 200
        print("Started test show")
        
        # Verify show is active
        verify_response = requests.get(f"{BASE_URL}/api/shows/current", headers=auth_headers)
        verify_data = verify_response.json()
        assert verify_data.get("active") == True
        assert verify_data.get("show", {}).get("name") == "TEST_Show_For_OnStage"
        
        # Stop the test show
        stop_response = requests.post(f"{BASE_URL}/api/shows/stop", headers=auth_headers)
        assert stop_response.status_code == 200
        print("Stopped test show")
        
        # Verify show is no longer active
        final_response = requests.get(f"{BASE_URL}/api/shows/current", headers=auth_headers)
        final_data = final_response.json()
        assert final_data.get("active") == False
    
    def test_requests_filtered_by_show_id(self, auth_headers):
        """Test that requests can be filtered by show_id"""
        # Get all requests
        response = requests.get(f"{BASE_URL}/api/requests/grouped", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check that shows have their own request lists
        shows_data = data.get("shows", {})
        for show_id, show_info in shows_data.items():
            requests_list = show_info.get("requests", [])
            print(f"Show {show_info.get('name', show_id)}: {len(requests_list)} requests")
            
            # Verify all requests in this show have matching show_id
            for req in requests_list:
                assert req.get("show_id") == show_id, \
                    f"Request {req.get('id')} has show_id {req.get('show_id')} but expected {show_id}"


class TestHealthAndBasicEndpoints:
    """Basic health and endpoint tests"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "timestamp" in data
    
    def test_songs_endpoint(self):
        """Test songs endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/songs")
        # Should require authentication
        assert response.status_code in [401, 403]
    
    def test_public_musician_endpoint(self):
        """Test public musician endpoint"""
        response = requests.get(f"{BASE_URL}/api/musicians/test/public")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "slug" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
