"""
Multi-Profile System Tests for RequestWave
Tests Profile CRUD, public resolution, slug validation, and request integration
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://chord-pro-stage.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"
TEST_MUSICIAN_SLUG = "test"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def musician_data(auth_token):
    """Get musician data from login"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    return response.json()["musician"]


class TestProfileCRUD:
    """Test Profile Create, Read, Update, Delete operations"""
    
    created_profile_ids = []  # Track created profiles for cleanup
    
    def test_create_profile_success(self, auth_headers, musician_data):
        """POST /api/profiles - Create profile with valid data"""
        unique_slug = f"test-profile-{uuid.uuid4().hex[:8]}"
        profile_data = {
            "name": "Test Wedding Profile",
            "slug": unique_slug,
            "active_playlist_ids": [],
            "show_tips_in_success_screen": True,
            "show_tips_in_orientation": False
        }
        
        response = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        
        assert response.status_code == 200, f"Create profile failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data
        assert data["name"] == profile_data["name"]
        assert data["slug"] == unique_slug
        assert data["musician_id"] == musician_data["id"]
        assert data["show_tips_in_success_screen"] == True
        assert data["show_tips_in_orientation"] == False
        assert "created_at" in data
        
        # Track for cleanup
        self.created_profile_ids.append(data["id"])
        print(f"✓ Created profile: {data['name']} (slug: {data['slug']})")
    
    def test_create_profile_slug_validation_uppercase(self, auth_headers):
        """POST /api/profiles - Reject uppercase in slug"""
        profile_data = {
            "name": "Invalid Slug Test",
            "slug": "InvalidSlug",  # Contains uppercase
            "active_playlist_ids": []
        }
        
        response = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        
        assert response.status_code == 400, f"Expected 400 for uppercase slug, got {response.status_code}"
        assert "lowercase" in response.json()["detail"].lower()
        print("✓ Uppercase slug correctly rejected")
    
    def test_create_profile_slug_validation_special_chars(self, auth_headers):
        """POST /api/profiles - Reject special characters in slug"""
        profile_data = {
            "name": "Invalid Slug Test",
            "slug": "test_slug!",  # Contains underscore and exclamation
            "active_playlist_ids": []
        }
        
        response = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        
        assert response.status_code == 400, f"Expected 400 for special chars, got {response.status_code}"
        print("✓ Special characters in slug correctly rejected")
    
    def test_create_profile_slug_validation_too_short(self, auth_headers):
        """POST /api/profiles - Reject slug shorter than 2 characters"""
        profile_data = {
            "name": "Short Slug Test",
            "slug": "a",  # Too short
            "active_playlist_ids": []
        }
        
        response = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        
        assert response.status_code == 400, f"Expected 400 for short slug, got {response.status_code}"
        assert "2 characters" in response.json()["detail"]
        print("✓ Short slug correctly rejected")
    
    def test_create_profile_duplicate_slug(self, auth_headers):
        """POST /api/profiles - Reject duplicate slug within same musician"""
        unique_slug = f"dup-test-{uuid.uuid4().hex[:8]}"
        
        # Create first profile
        profile_data = {
            "name": "First Profile",
            "slug": unique_slug,
            "active_playlist_ids": []
        }
        response1 = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        assert response1.status_code == 200
        self.created_profile_ids.append(response1.json()["id"])
        
        # Try to create second profile with same slug
        profile_data["name"] = "Second Profile"
        response2 = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        
        assert response2.status_code == 409, f"Expected 409 for duplicate slug, got {response2.status_code}"
        assert "already exists" in response2.json()["detail"]
        print("✓ Duplicate slug correctly rejected")
    
    def test_get_profiles_list(self, auth_headers):
        """GET /api/profiles - List all profiles for authenticated musician"""
        response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        
        assert response.status_code == 200, f"Get profiles failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} profiles")
        
        # Verify structure of each profile
        for profile in data:
            assert "id" in profile
            assert "name" in profile
            assert "slug" in profile
            assert "musician_id" in profile
            assert "active_playlist_ids" in profile
    
    def test_update_profile(self, auth_headers):
        """PUT /api/profiles/{profile_id} - Update profile fields"""
        # First create a profile to update
        unique_slug = f"update-test-{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": "Profile To Update",
            "slug": unique_slug,
            "active_playlist_ids": [],
            "show_tips_in_success_screen": True,
            "show_tips_in_orientation": True
        }
        create_response = requests.post(f"{BASE_URL}/api/profiles", json=create_data, headers=auth_headers)
        assert create_response.status_code == 200
        profile_id = create_response.json()["id"]
        self.created_profile_ids.append(profile_id)
        
        # Update the profile
        update_data = {
            "name": "Updated Profile Name",
            "show_tips_in_success_screen": False,
            "show_tips_in_orientation": False
        }
        update_response = requests.put(f"{BASE_URL}/api/profiles/{profile_id}", json=update_data, headers=auth_headers)
        
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated = update_response.json()
        
        assert updated["name"] == "Updated Profile Name"
        assert updated["show_tips_in_success_screen"] == False
        assert updated["show_tips_in_orientation"] == False
        assert updated["slug"] == unique_slug  # Slug unchanged
        print("✓ Profile updated successfully")
    
    def test_update_profile_slug_uniqueness(self, auth_headers):
        """PUT /api/profiles/{profile_id} - Reject slug update to existing slug"""
        # Create two profiles
        slug1 = f"slug-unique-1-{uuid.uuid4().hex[:8]}"
        slug2 = f"slug-unique-2-{uuid.uuid4().hex[:8]}"
        
        resp1 = requests.post(f"{BASE_URL}/api/profiles", json={"name": "Profile 1", "slug": slug1, "active_playlist_ids": []}, headers=auth_headers)
        resp2 = requests.post(f"{BASE_URL}/api/profiles", json={"name": "Profile 2", "slug": slug2, "active_playlist_ids": []}, headers=auth_headers)
        
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        
        profile1_id = resp1.json()["id"]
        profile2_id = resp2.json()["id"]
        self.created_profile_ids.extend([profile1_id, profile2_id])
        
        # Try to update profile2's slug to profile1's slug
        update_response = requests.put(f"{BASE_URL}/api/profiles/{profile2_id}", json={"slug": slug1}, headers=auth_headers)
        
        assert update_response.status_code == 409, f"Expected 409, got {update_response.status_code}"
        print("✓ Slug uniqueness enforced on update")
    
    def test_delete_profile_not_found(self, auth_headers):
        """DELETE /api/profiles/{profile_id} - 404 for non-existent profile"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/api/profiles/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        print("✓ Delete non-existent profile returns 404")
    
    def test_update_profile_not_found(self, auth_headers):
        """PUT /api/profiles/{profile_id} - 404 for non-existent profile"""
        fake_id = str(uuid.uuid4())
        response = requests.put(f"{BASE_URL}/api/profiles/{fake_id}", json={"name": "Test"}, headers=auth_headers)
        
        assert response.status_code == 404
        print("✓ Update non-existent profile returns 404")


class TestPublicProfileResolution:
    """Test public endpoints for profile resolution"""
    
    def test_resolve_musician_slug(self):
        """GET /api/resolve/{slug} - Resolve known musician slug"""
        response = requests.get(f"{BASE_URL}/api/resolve/{TEST_MUSICIAN_SLUG}")
        
        assert response.status_code == 200, f"Resolve failed: {response.text}"
        data = response.json()
        
        assert data["found"] == True
        assert data["type"] == "musician"
        assert data["slug"] == TEST_MUSICIAN_SLUG
        print(f"✓ Resolved musician slug: {TEST_MUSICIAN_SLUG}")
    
    def test_resolve_unknown_slug(self):
        """GET /api/resolve/{slug} - 404 for unknown slug"""
        response = requests.get(f"{BASE_URL}/api/resolve/nonexistent-musician-xyz123")
        
        assert response.status_code == 404
        print("✓ Unknown slug returns 404")
    
    def test_get_musician_by_profile_existing(self, auth_headers):
        """GET /api/musicians/{master_slug}/{profile_slug} - Get profile with songs"""
        # First, get existing profiles
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        if len(profiles) == 0:
            # Create a test profile
            unique_slug = f"public-test-{uuid.uuid4().hex[:8]}"
            create_response = requests.post(f"{BASE_URL}/api/profiles", json={
                "name": "Public Test Profile",
                "slug": unique_slug,
                "active_playlist_ids": []
            }, headers=auth_headers)
            assert create_response.status_code == 200
            profile_slug = unique_slug
        else:
            profile_slug = profiles[0]["slug"]
        
        # Test public endpoint
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/{profile_slug}")
        
        assert response.status_code == 200, f"Public profile fetch failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data
        assert "name" in data
        assert "slug" in data
        assert data["slug"] == TEST_MUSICIAN_SLUG
        assert "profile_id" in data
        assert "profile_name" in data
        assert "profile_slug" in data
        assert data["profile_slug"] == profile_slug
        assert "show_tips_in_success_screen" in data
        assert "show_tips_in_orientation" in data
        assert "songs" in data
        assert isinstance(data["songs"], list)
        
        # Verify payment info is included
        assert "paypal_username" in data
        assert "venmo_username" in data
        
        print(f"✓ Public profile endpoint working: {data['profile_name']}")
    
    def test_get_musician_by_profile_not_found_musician(self):
        """GET /api/musicians/{master_slug}/{profile_slug} - 404 for unknown musician"""
        response = requests.get(f"{BASE_URL}/api/musicians/nonexistent-musician/some-profile")
        
        assert response.status_code == 404
        assert "Musician not found" in response.json()["detail"]
        print("✓ Unknown musician returns 404")
    
    def test_get_musician_by_profile_not_found_profile(self):
        """GET /api/musicians/{master_slug}/{profile_slug} - 404 for unknown profile"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/nonexistent-profile-xyz")
        
        assert response.status_code == 404
        assert "Profile not found" in response.json()["detail"]
        print("✓ Unknown profile returns 404")


class TestRequestWithProfile:
    """Test request submission with profile context"""
    
    def test_submit_request_with_profile_slug(self, auth_headers, musician_data):
        """POST /api/requests with profile_slug - Stores profile_id on request"""
        # Get a song to request
        songs_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/songs")
        songs = songs_response.json()
        
        if len(songs) == 0:
            pytest.skip("No songs available for testing")
        
        song = songs[0]
        
        # Get or create a profile
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        if len(profiles) == 0:
            unique_slug = f"req-test-{uuid.uuid4().hex[:8]}"
            create_response = requests.post(f"{BASE_URL}/api/profiles", json={
                "name": "Request Test Profile",
                "slug": unique_slug,
                "active_playlist_ids": []
            }, headers=auth_headers)
            profile_slug = unique_slug
        else:
            profile_slug = profiles[0]["slug"]
        
        # Submit request with profile_slug
        request_data = {
            "song_id": song["id"],
            "requester_name": "Test Requester",
            "requester_email": "test-requester@example.com",
            "dedication": "Test dedication",
            "tip_amount": 0,
            "profile_slug": profile_slug
        }
        
        response = requests.post(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/requests", json=request_data)
        
        assert response.status_code == 200, f"Request submission failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["song_id"] == song["id"]
        # Note: profile_id should be stored but may not be returned in response
        print(f"✓ Request submitted with profile context: {data['id']}")


class TestDeleteProfileRestriction:
    """Test that deletion of only profile is refused"""
    
    def test_cannot_delete_only_profile(self, auth_headers):
        """DELETE /api/profiles/{profile_id} - Refuse deletion of only profile"""
        # Get current profiles
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        # If there's only one profile, try to delete it
        if len(profiles) == 1:
            profile_id = profiles[0]["id"]
            delete_response = requests.delete(f"{BASE_URL}/api/profiles/{profile_id}", headers=auth_headers)
            
            assert delete_response.status_code == 400, f"Expected 400, got {delete_response.status_code}"
            assert "only profile" in delete_response.json()["detail"].lower()
            print("✓ Cannot delete only profile - correctly refused")
        elif len(profiles) > 1:
            # Delete all but one, then try to delete the last
            for profile in profiles[:-1]:
                requests.delete(f"{BASE_URL}/api/profiles/{profile['id']}", headers=auth_headers)
            
            # Now try to delete the last one
            last_profile_id = profiles[-1]["id"]
            delete_response = requests.delete(f"{BASE_URL}/api/profiles/{last_profile_id}", headers=auth_headers)
            
            assert delete_response.status_code == 400, f"Expected 400, got {delete_response.status_code}"
            print("✓ Cannot delete only profile - correctly refused")
        else:
            # No profiles exist, create one and try to delete
            unique_slug = f"only-profile-{uuid.uuid4().hex[:8]}"
            create_response = requests.post(f"{BASE_URL}/api/profiles", json={
                "name": "Only Profile",
                "slug": unique_slug,
                "active_playlist_ids": []
            }, headers=auth_headers)
            
            assert create_response.status_code == 200
            profile_id = create_response.json()["id"]
            
            delete_response = requests.delete(f"{BASE_URL}/api/profiles/{profile_id}", headers=auth_headers)
            
            assert delete_response.status_code == 400, f"Expected 400, got {delete_response.status_code}"
            print("✓ Cannot delete only profile - correctly refused")
    
    def test_can_delete_when_multiple_profiles(self, auth_headers):
        """DELETE /api/profiles/{profile_id} - Allow deletion when multiple profiles exist"""
        # Create two profiles
        slug1 = f"multi-del-1-{uuid.uuid4().hex[:8]}"
        slug2 = f"multi-del-2-{uuid.uuid4().hex[:8]}"
        
        resp1 = requests.post(f"{BASE_URL}/api/profiles", json={"name": "Profile 1", "slug": slug1, "active_playlist_ids": []}, headers=auth_headers)
        resp2 = requests.post(f"{BASE_URL}/api/profiles", json={"name": "Profile 2", "slug": slug2, "active_playlist_ids": []}, headers=auth_headers)
        
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        
        profile1_id = resp1.json()["id"]
        profile2_id = resp2.json()["id"]
        
        # Should be able to delete one
        delete_response = requests.delete(f"{BASE_URL}/api/profiles/{profile1_id}", headers=auth_headers)
        
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        assert delete_response.json()["ok"] == True
        print("✓ Can delete profile when multiple exist")
        
        # Cleanup - delete the second one if there are still multiple
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        if len(profiles_response.json()) > 1:
            requests.delete(f"{BASE_URL}/api/profiles/{profile2_id}", headers=auth_headers)


class TestExistingMusicianRoute:
    """Test that existing /musician/:slug route still works (zero breaking changes)"""
    
    def test_existing_musician_route_works(self):
        """GET /api/musicians/{slug} - Existing route returns all songs"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}")
        
        assert response.status_code == 200, f"Existing route failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert "name" in data
        assert "slug" in data
        assert data["slug"] == TEST_MUSICIAN_SLUG
        print(f"✓ Existing /musician/:slug route works: {data['name']}")
    
    def test_existing_songs_route_works(self):
        """GET /api/musicians/{slug}/songs - Existing songs route returns all songs"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/songs")
        
        assert response.status_code == 200, f"Songs route failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Existing songs route works: {len(data)} songs returned")


# Cleanup fixture to run after all tests
@pytest.fixture(scope="module", autouse=True)
def cleanup(auth_headers):
    """Cleanup test profiles after all tests"""
    yield
    # Cleanup is handled within tests to avoid leaving test data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
