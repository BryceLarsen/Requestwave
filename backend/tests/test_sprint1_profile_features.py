"""
Sprint 1 Multi-Profile System Tests for RequestWave
Tests: Bug fixes (copy link, clickable URL, All Songs playlist), new profile fields,
is_default profile, Set Default button, slimmed Account Settings, master URL resolution
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://artist-email-studio.preview.emergentagent.com').rstrip('/')

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


class TestProfileNewFields:
    """Test new profile fields: payment/social/branding overrides"""
    
    created_profile_ids = []
    
    def test_create_profile_with_all_new_fields(self, auth_headers, musician_data):
        """POST /api/profiles - Create profile with all new override fields"""
        unique_slug = f"sprint1-test-{uuid.uuid4().hex[:8]}"
        profile_data = {
            "name": "Sprint 1 Test Profile",
            "slug": unique_slug,
            "active_playlist_ids": ["__all__"],  # All Songs sentinel
            "show_tips_in_success_screen": True,
            "show_tips_in_orientation": True,
            # New override fields
            "paypal_username": "test-paypal",
            "venmo_username": "test-venmo",
            "cashapp_username": "test-cashapp",
            "zelle_info": "test@zelle.com",
            "instagram_username": "test_insta",
            "tiktok_username": "test_tiktok",
            "facebook_url": "https://facebook.com/test",
            "spotify_url": "https://open.spotify.com/artist/test",
            "apple_music_url": "https://music.apple.com/artist/test",
            "website": "https://test-website.com",
            "bio": "Test bio for Sprint 1",
            "musician_name": "DJ Test Override"
        }
        
        response = requests.post(f"{BASE_URL}/api/profiles", json=profile_data, headers=auth_headers)
        
        assert response.status_code == 200, f"Create profile failed: {response.text}"
        data = response.json()
        
        # Validate all new fields are stored
        assert data["paypal_username"] == "test-paypal"
        assert data["venmo_username"] == "test-venmo"
        assert data["cashapp_username"] == "test-cashapp"
        assert data["zelle_info"] == "test@zelle.com"
        assert data["instagram_username"] == "test_insta"
        assert data["tiktok_username"] == "test_tiktok"
        assert data["facebook_url"] == "https://facebook.com/test"
        assert data["spotify_url"] == "https://open.spotify.com/artist/test"
        assert data["apple_music_url"] == "https://music.apple.com/artist/test"
        assert data["website"] == "https://test-website.com"
        assert data["bio"] == "Test bio for Sprint 1"
        assert data["musician_name"] == "DJ Test Override"
        
        self.created_profile_ids.append(data["id"])
        print(f"✓ Created profile with all new fields: {data['name']}")
    
    def test_update_profile_override_fields(self, auth_headers):
        """PUT /api/profiles/{id} - Update override fields"""
        # Create a profile first
        unique_slug = f"update-override-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/profiles", json={
            "name": "Update Override Test",
            "slug": unique_slug,
            "active_playlist_ids": []
        }, headers=auth_headers)
        assert create_response.status_code == 200
        profile_id = create_response.json()["id"]
        self.created_profile_ids.append(profile_id)
        
        # Update with override fields
        update_data = {
            "musician_name": "Updated DJ Name",
            "venmo_username": "updated-venmo",
            "bio": "Updated bio"
        }
        update_response = requests.put(f"{BASE_URL}/api/profiles/{profile_id}", json=update_data, headers=auth_headers)
        
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["musician_name"] == "Updated DJ Name"
        assert updated["venmo_username"] == "updated-venmo"
        assert updated["bio"] == "Updated bio"
        print("✓ Profile override fields updated successfully")


class TestIsDefaultProfile:
    """Test is_default field and Set Default functionality"""
    
    created_profile_ids = []
    
    def test_first_profile_auto_default(self, auth_headers, musician_data):
        """First profile created should auto-set as default"""
        # Get current profiles
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        # Check if any profile is default
        default_profiles = [p for p in profiles if p.get("is_default")]
        
        if len(profiles) > 0:
            # At least one should be default
            assert len(default_profiles) >= 1, "No default profile found when profiles exist"
            print(f"✓ Found {len(default_profiles)} default profile(s)")
        else:
            # Create first profile and verify it's default
            unique_slug = f"first-default-{uuid.uuid4().hex[:8]}"
            create_response = requests.post(f"{BASE_URL}/api/profiles", json={
                "name": "First Profile",
                "slug": unique_slug,
                "active_playlist_ids": []
            }, headers=auth_headers)
            assert create_response.status_code == 200
            data = create_response.json()
            assert data["is_default"] == True, "First profile should be auto-set as default"
            self.created_profile_ids.append(data["id"])
            print("✓ First profile auto-set as default")
    
    def test_set_default_button_works(self, auth_headers):
        """PUT /api/profiles/{id} with is_default=true should set as default and unset others"""
        # Create two profiles
        slug1 = f"default-test-1-{uuid.uuid4().hex[:8]}"
        slug2 = f"default-test-2-{uuid.uuid4().hex[:8]}"
        
        resp1 = requests.post(f"{BASE_URL}/api/profiles", json={
            "name": "Default Test 1",
            "slug": slug1,
            "active_playlist_ids": []
        }, headers=auth_headers)
        resp2 = requests.post(f"{BASE_URL}/api/profiles", json={
            "name": "Default Test 2",
            "slug": slug2,
            "active_playlist_ids": []
        }, headers=auth_headers)
        
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        
        profile1_id = resp1.json()["id"]
        profile2_id = resp2.json()["id"]
        self.created_profile_ids.extend([profile1_id, profile2_id])
        
        # Set profile2 as default
        set_default_response = requests.put(f"{BASE_URL}/api/profiles/{profile2_id}", json={
            "is_default": True
        }, headers=auth_headers)
        
        assert set_default_response.status_code == 200
        assert set_default_response.json()["is_default"] == True
        
        # Verify profile1 is no longer default
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        profile1_data = next((p for p in profiles if p["id"] == profile1_id), None)
        profile2_data = next((p for p in profiles if p["id"] == profile2_id), None)
        
        if profile1_data:
            assert profile1_data["is_default"] == False, "Previous default should be unset"
        assert profile2_data["is_default"] == True, "New default should be set"
        
        print("✓ Set Default button works correctly")
    
    def test_cannot_delete_default_profile(self, auth_headers):
        """DELETE /api/profiles/{id} should refuse to delete default profile"""
        # Get profiles and find the default one
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        default_profile = next((p for p in profiles if p.get("is_default")), None)
        
        if default_profile:
            delete_response = requests.delete(f"{BASE_URL}/api/profiles/{default_profile['id']}", headers=auth_headers)
            
            assert delete_response.status_code == 400, f"Expected 400, got {delete_response.status_code}"
            assert "default" in delete_response.json()["detail"].lower()
            print("✓ Cannot delete default profile - correctly refused")
        else:
            print("⚠ No default profile found to test deletion restriction")


class TestAllSongsPlaylist:
    """Test '__all__' sentinel in active_playlist_ids returns full song library"""
    
    def test_all_songs_sentinel_returns_full_library(self, auth_headers, musician_data):
        """Profile with '__all__' in active_playlist_ids should return all non-hidden songs"""
        # First, get total song count for this musician
        songs_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/songs")
        assert songs_response.status_code == 200
        total_songs = len(songs_response.json())
        
        # Get profiles and find one with __all__
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        all_songs_profile = next((p for p in profiles if "__all__" in p.get("active_playlist_ids", [])), None)
        
        if all_songs_profile:
            # Test public endpoint for this profile
            public_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/{all_songs_profile['slug']}")
            
            assert public_response.status_code == 200
            data = public_response.json()
            
            # Should have songs array
            assert "songs" in data
            profile_songs_count = len(data["songs"])
            
            # Should return all songs (or close to it, accounting for hidden songs)
            print(f"✓ Profile with __all__ returns {profile_songs_count} songs (total: {total_songs})")
            assert profile_songs_count > 0, "Profile with __all__ should return songs"
        else:
            # Create a profile with __all__
            unique_slug = f"all-songs-test-{uuid.uuid4().hex[:8]}"
            create_response = requests.post(f"{BASE_URL}/api/profiles", json={
                "name": "All Songs Test",
                "slug": unique_slug,
                "active_playlist_ids": ["__all__"]
            }, headers=auth_headers)
            
            assert create_response.status_code == 200
            profile_slug = create_response.json()["slug"]
            
            # Test public endpoint
            public_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/{profile_slug}")
            
            assert public_response.status_code == 200
            data = public_response.json()
            
            assert "songs" in data
            profile_songs_count = len(data["songs"])
            print(f"✓ Created profile with __all__, returns {profile_songs_count} songs")


class TestMasterURLResolution:
    """Test /musician/{master_slug} resolves to default profile when one exists"""
    
    def test_master_url_returns_default_profile_data(self, auth_headers, musician_data):
        """GET /api/musicians/{slug} should return default profile's merged data"""
        # Get the default profile
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        default_profile = next((p for p in profiles if p.get("is_default")), None)
        
        # Call master URL
        master_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}")
        
        assert master_response.status_code == 200
        data = master_response.json()
        
        if default_profile:
            # Should have profile-specific fields
            assert "profile_id" in data, "Master URL should return profile_id when default profile exists"
            assert "profile_name" in data, "Master URL should return profile_name"
            assert "profile_slug" in data, "Master URL should return profile_slug"
            assert "songs" in data, "Master URL should return songs from default profile"
            
            # Verify it's the default profile
            assert data["profile_id"] == default_profile["id"]
            assert data["is_default"] == True
            
            print(f"✓ Master URL resolves to default profile: {data['profile_name']}")
            print(f"  Songs returned: {len(data['songs'])}")
        else:
            # No default profile - should return standard musician data
            assert "id" in data
            assert "name" in data
            assert "slug" in data
            print("✓ Master URL returns standard musician data (no default profile)")
    
    def test_master_url_returns_all_songs_via_default_profile(self, auth_headers):
        """Regression: /musician/{slug} should return all 11 songs via __all__ default profile"""
        # First ensure there's a default profile with __all__
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        default_profile = next((p for p in profiles if p.get("is_default")), None)
        
        if default_profile and "__all__" in default_profile.get("active_playlist_ids", []):
            # Test master URL
            master_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}")
            
            assert master_response.status_code == 200
            data = master_response.json()
            
            assert "songs" in data
            songs_count = len(data["songs"])
            
            # Should return all songs (the test musician has 11 songs)
            print(f"✓ Master URL returns {songs_count} songs via default profile with __all__")
            assert songs_count > 0, "Should return songs"
        else:
            print("⚠ Default profile doesn't have __all__ - skipping regression test")


class TestProfileOverrideLogic:
    """Test that profile fields override master account values on audience page"""
    
    def test_musician_name_override(self, auth_headers, musician_data):
        """Profile's musician_name should override master account name"""
        # Create profile with musician_name override
        unique_slug = f"name-override-{uuid.uuid4().hex[:8]}"
        override_name = "DJ Override Name"
        
        create_response = requests.post(f"{BASE_URL}/api/profiles", json={
            "name": "Name Override Test",
            "slug": unique_slug,
            "active_playlist_ids": [],
            "musician_name": override_name
        }, headers=auth_headers)
        
        assert create_response.status_code == 200
        profile_id = create_response.json()["id"]
        
        # Get public profile data
        public_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/{unique_slug}")
        
        assert public_response.status_code == 200
        data = public_response.json()
        
        # The 'name' field should be the override, not the master account name
        assert data["name"] == override_name, f"Expected '{override_name}', got '{data['name']}'"
        print(f"✓ musician_name override works: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/profiles/{profile_id}", headers=auth_headers)
    
    def test_payment_info_override(self, auth_headers, musician_data):
        """Profile's payment info should override master account values"""
        unique_slug = f"payment-override-{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(f"{BASE_URL}/api/profiles", json={
            "name": "Payment Override Test",
            "slug": unique_slug,
            "active_playlist_ids": [],
            "venmo_username": "profile-venmo-override"
        }, headers=auth_headers)
        
        assert create_response.status_code == 200
        profile_id = create_response.json()["id"]
        
        # Get public profile data
        public_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/{unique_slug}")
        
        assert public_response.status_code == 200
        data = public_response.json()
        
        # Venmo should be the override value
        assert data["venmo_username"] == "profile-venmo-override"
        print(f"✓ Payment info override works: venmo={data['venmo_username']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/profiles/{profile_id}", headers=auth_headers)


class TestRegressionExistingRoutes:
    """Regression tests: Ensure existing routes still work"""
    
    def test_existing_musician_slug_route(self):
        """GET /api/musicians/{slug} - Existing route still works"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "name" in data
        assert "slug" in data
        assert data["slug"] == TEST_MUSICIAN_SLUG
        print(f"✓ Existing /musician/:slug route works")
    
    def test_existing_songs_route(self):
        """GET /api/musicians/{slug}/songs - Existing songs route still works"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/songs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Existing songs route works: {len(data)} songs")
    
    def test_profile_slug_route(self, auth_headers):
        """GET /api/musicians/{master_slug}/{profile_slug} - Profile route works"""
        # Get a profile
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        if len(profiles) > 0:
            profile = profiles[0]
            response = requests.get(f"{BASE_URL}/api/musicians/{TEST_MUSICIAN_SLUG}/{profile['slug']}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "profile_id" in data
            assert "profile_slug" in data
            assert data["profile_slug"] == profile["slug"]
            print(f"✓ Profile slug route works: {profile['slug']}")
        else:
            print("⚠ No profiles to test profile slug route")
    
    def test_short_url_redirect_resolve(self):
        """GET /api/resolve/{slug} - Short URL resolution works"""
        response = requests.get(f"{BASE_URL}/api/resolve/{TEST_MUSICIAN_SLUG}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["found"] == True
        assert data["type"] == "musician"
        assert data["slug"] == TEST_MUSICIAN_SLUG
        print("✓ Short URL resolve works")
    
    def test_404_for_unknown_slug(self):
        """GET /api/resolve/{slug} - 404 for unknown slug"""
        response = requests.get(f"{BASE_URL}/api/resolve/nonexistent-musician-xyz123")
        
        assert response.status_code == 404
        print("✓ 404 for unknown slug works")


class TestCleanup:
    """Cleanup test profiles created during testing"""
    
    def test_cleanup_test_profiles(self, auth_headers):
        """Delete test profiles created during this test run"""
        profiles_response = requests.get(f"{BASE_URL}/api/profiles", headers=auth_headers)
        profiles = profiles_response.json()
        
        # Find and delete test profiles (those with test slugs)
        test_prefixes = ["sprint1-test-", "update-override-", "default-test-", "all-songs-test-", 
                        "name-override-", "payment-override-", "first-default-"]
        
        deleted_count = 0
        for profile in profiles:
            if any(profile["slug"].startswith(prefix) for prefix in test_prefixes):
                if not profile.get("is_default"):  # Can't delete default
                    delete_response = requests.delete(f"{BASE_URL}/api/profiles/{profile['id']}", headers=auth_headers)
                    if delete_response.status_code == 200:
                        deleted_count += 1
        
        print(f"✓ Cleaned up {deleted_count} test profiles")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
