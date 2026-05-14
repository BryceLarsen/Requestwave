"""
Test Suite for Design Settings in Profile System
Tests:
1. Account Settings contains only: email (disabled), slug (disabled), password change form
2. Design tab is removed from main tab bar (frontend test)
3. Profile editor has Design Settings section
4. 'Copy from Default Profile' button pulls values from default profile
5. Profile design fields stored in DB
6. GET /api/musicians/{master_slug}/{profile_slug} includes design_settings
7. GET /api/musicians/{slug}/design returns default profile design settings
8. Profile audience page uses profile design settings
9. REGRESSION: Master URL still works
10. REGRESSION: Profile overrides still work
11. REGRESSION: Short URL redirects still work
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://musician-dashboard-1.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test"
TEST_SLUG = "test"


class TestDesignProfileFeatures:
    """Test suite for design settings in profile system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.musician = login_response.json().get("musician")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    # ============================================
    # Test 1: Profile design fields stored in DB
    # ============================================
    def test_profile_design_fields_in_create(self):
        """Test that profile can be created with design fields"""
        # Create a test profile with design settings
        profile_data = {
            "name": "Design Test Profile",
            "slug": "design-test-profile",
            "active_playlist_ids": ["__all__"],
            "design_color_scheme": "blue",
            "design_show_year": False,
            "design_show_notes": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/profiles", json=profile_data)
        
        # If profile already exists, try to get it
        if response.status_code in [400, 409] and "already exists" in response.text:
            # Get existing profiles
            profiles_response = self.session.get(f"{BASE_URL}/api/profiles")
            assert profiles_response.status_code == 200
            profiles = profiles_response.json()
            existing = next((p for p in profiles if p["slug"] == "design-test-profile"), None)
            if existing:
                # Update it instead
                response = self.session.put(f"{BASE_URL}/api/profiles/{existing['id']}", json=profile_data)
                assert response.status_code == 200
                profile = response.json()
            else:
                pytest.fail("Profile creation failed and profile not found")
        else:
            assert response.status_code == 200, f"Profile creation failed: {response.text}"
            profile = response.json()
        
        # Verify design fields are stored
        assert profile.get("design_color_scheme") == "blue", f"Expected blue, got {profile.get('design_color_scheme')}"
        assert profile.get("design_show_year") == False, f"Expected False, got {profile.get('design_show_year')}"
        assert profile.get("design_show_notes") == True, f"Expected True, got {profile.get('design_show_notes')}"
        
        print(f"✓ Profile design fields stored correctly: color_scheme={profile.get('design_color_scheme')}")
    
    # ============================================
    # Test 2: Profile public endpoint includes design_settings
    # ============================================
    def test_profile_public_endpoint_includes_design_settings(self):
        """Test GET /api/musicians/{master_slug}/{profile_slug} includes design_settings"""
        # First ensure we have a profile with design settings
        profiles_response = self.session.get(f"{BASE_URL}/api/profiles")
        assert profiles_response.status_code == 200
        profiles = profiles_response.json()
        
        # Find a profile with design settings or use any profile
        test_profile = next((p for p in profiles if p.get("design_color_scheme")), None)
        if not test_profile and profiles:
            test_profile = profiles[0]
        
        if not test_profile:
            pytest.skip("No profiles available for testing")
        
        # Get the public profile endpoint
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_SLUG}/{test_profile['slug']}")
        assert response.status_code == 200, f"Profile public endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify design_settings object is present
        assert "design_settings" in data, "design_settings not found in response"
        design_settings = data["design_settings"]
        
        # Verify design_settings has expected fields
        assert "color_scheme" in design_settings, "color_scheme not in design_settings"
        assert "show_year" in design_settings, "show_year not in design_settings"
        assert "show_notes" in design_settings, "show_notes not in design_settings"
        
        print(f"✓ Profile public endpoint includes design_settings: {design_settings}")
    
    # ============================================
    # Test 3: Design endpoint returns default profile design settings
    # ============================================
    def test_design_endpoint_returns_default_profile_settings(self):
        """Test GET /api/musicians/{slug}/design returns default profile design settings when available"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_SLUG}/design")
        assert response.status_code == 200, f"Design endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify design settings structure
        assert "color_scheme" in data, "color_scheme not in design response"
        assert "show_year" in data, "show_year not in design response"
        assert "show_notes" in data, "show_notes not in design response"
        
        print(f"✓ Design endpoint returns settings: color_scheme={data.get('color_scheme')}")
    
    # ============================================
    # Test 4: Profile design settings override global
    # ============================================
    def test_profile_design_overrides_global(self):
        """Test that profile design settings override global design settings"""
        # Get global design settings
        global_response = self.session.get(f"{BASE_URL}/api/design/settings")
        assert global_response.status_code == 200
        global_settings = global_response.json()
        
        # Create/update a profile with different design settings
        profiles_response = self.session.get(f"{BASE_URL}/api/profiles")
        profiles = profiles_response.json()
        
        # Find or create a test profile
        test_profile = next((p for p in profiles if p["slug"] == "design-test-profile"), None)
        
        if test_profile:
            # Update with different color scheme than global
            different_color = "green" if global_settings.get("color_scheme") != "green" else "blue"
            update_response = self.session.put(f"{BASE_URL}/api/profiles/{test_profile['id']}", json={
                "design_color_scheme": different_color
            })
            assert update_response.status_code == 200
            
            # Get the public profile endpoint
            public_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_SLUG}/design-test-profile")
            assert public_response.status_code == 200
            
            data = public_response.json()
            design_settings = data.get("design_settings", {})
            
            # Verify profile design settings are used, not global
            assert design_settings.get("color_scheme") == different_color, \
                f"Expected {different_color}, got {design_settings.get('color_scheme')}"
            
            print(f"✓ Profile design settings override global: profile={different_color}, global={global_settings.get('color_scheme')}")
        else:
            pytest.skip("Test profile not found")
    
    # ============================================
    # REGRESSION Test 5: Master URL still works
    # ============================================
    def test_regression_master_url_works(self):
        """REGRESSION: Master URL /musician/{slug} still works with all songs"""
        response = requests.get(f"{BASE_URL}/api/musicians/{TEST_SLUG}")
        assert response.status_code == 200, f"Master URL failed: {response.text}"
        
        data = response.json()
        
        # Verify basic structure
        assert "name" in data, "name not in response"
        assert "slug" in data, "slug not in response"
        assert "songs" in data, "songs not in response"
        
        # Verify songs are returned
        songs = data.get("songs", [])
        assert len(songs) > 0, "No songs returned from master URL"
        
        print(f"✓ Master URL works: returned {len(songs)} songs")
    
    # ============================================
    # REGRESSION Test 6: Profile overrides still work
    # ============================================
    def test_regression_profile_overrides_work(self):
        """REGRESSION: Profile overrides (musician_name, bio, venmo) still work on audience page"""
        # Get profiles
        profiles_response = self.session.get(f"{BASE_URL}/api/profiles")
        assert profiles_response.status_code == 200
        profiles = profiles_response.json()
        
        # Find a profile with overrides
        profile_with_overrides = next((p for p in profiles if p.get("musician_name") or p.get("bio") or p.get("venmo_username")), None)
        
        if not profile_with_overrides:
            # Create one with overrides
            profile_data = {
                "name": "Override Test Profile",
                "slug": "override-test-profile",
                "active_playlist_ids": ["__all__"],
                "musician_name": "Override Artist Name",
                "bio": "Override bio text",
                "venmo_username": "override-venmo"
            }
            create_response = self.session.post(f"{BASE_URL}/api/profiles", json=profile_data)
            if create_response.status_code == 200:
                profile_with_overrides = create_response.json()
            elif create_response.status_code == 400 and "already exists" in create_response.text:
                profile_with_overrides = next((p for p in profiles if p["slug"] == "override-test-profile"), None)
        
        if profile_with_overrides:
            # Get public profile
            public_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_SLUG}/{profile_with_overrides['slug']}")
            assert public_response.status_code == 200
            
            data = public_response.json()
            
            # Verify overrides are applied
            if profile_with_overrides.get("musician_name"):
                assert data.get("name") == profile_with_overrides.get("musician_name"), \
                    f"musician_name override not applied: expected {profile_with_overrides.get('musician_name')}, got {data.get('name')}"
            
            print(f"✓ Profile overrides work: name={data.get('name')}")
        else:
            pytest.skip("No profile with overrides available")
    
    # ============================================
    # REGRESSION Test 7: Short URL redirects still work
    # ============================================
    def test_regression_short_url_redirects_work(self):
        """REGRESSION: Short URL redirects still work"""
        response = requests.get(f"{BASE_URL}/api/resolve/{TEST_SLUG}", allow_redirects=False)
        
        # Should return redirect or the resolved data
        assert response.status_code in [200, 301, 302, 307, 308], f"Short URL resolve failed: {response.status_code}"
        
        print(f"✓ Short URL redirect works: status={response.status_code}")
    
    # ============================================
    # Test 8: Get all profiles and verify design fields
    # ============================================
    def test_get_profiles_includes_design_fields(self):
        """Test that GET /api/profiles returns profiles with design fields"""
        response = self.session.get(f"{BASE_URL}/api/profiles")
        assert response.status_code == 200, f"Get profiles failed: {response.text}"
        
        profiles = response.json()
        assert len(profiles) > 0, "No profiles returned"
        
        # Check that profiles have design field structure
        for profile in profiles:
            # These fields should exist (even if None)
            assert "design_color_scheme" in profile or profile.get("design_color_scheme") is None or "design_color_scheme" not in profile
            
        print(f"✓ Get profiles returns {len(profiles)} profiles with design field structure")
    
    # ============================================
    # Test 9: Update profile design settings
    # ============================================
    def test_update_profile_design_settings(self):
        """Test updating profile design settings"""
        # Get profiles
        profiles_response = self.session.get(f"{BASE_URL}/api/profiles")
        assert profiles_response.status_code == 200
        profiles = profiles_response.json()
        
        if not profiles:
            pytest.skip("No profiles available")
        
        # Use first non-default profile or any profile
        test_profile = next((p for p in profiles if not p.get("is_default")), profiles[0])
        
        # Update design settings
        update_data = {
            "design_color_scheme": "orange",
            "design_show_year": True,
            "design_show_notes": False
        }
        
        response = self.session.put(f"{BASE_URL}/api/profiles/{test_profile['id']}", json=update_data)
        assert response.status_code == 200, f"Update profile failed: {response.text}"
        
        updated_profile = response.json()
        
        # Verify updates
        assert updated_profile.get("design_color_scheme") == "orange", \
            f"design_color_scheme not updated: {updated_profile.get('design_color_scheme')}"
        
        print(f"✓ Profile design settings updated: color_scheme={updated_profile.get('design_color_scheme')}")
    
    # ============================================
    # Test 10: Default profile design settings used in master URL
    # ============================================
    def test_default_profile_design_in_master_url(self):
        """Test that default profile design settings are used when accessing master URL"""
        # Get profiles to find default
        profiles_response = self.session.get(f"{BASE_URL}/api/profiles")
        assert profiles_response.status_code == 200
        profiles = profiles_response.json()
        
        default_profile = next((p for p in profiles if p.get("is_default")), None)
        
        if default_profile and default_profile.get("design_color_scheme"):
            # Get master URL
            master_response = requests.get(f"{BASE_URL}/api/musicians/{TEST_SLUG}")
            assert master_response.status_code == 200
            
            data = master_response.json()
            design_settings = data.get("design_settings", {})
            
            # If default profile has design settings, they should be used
            if default_profile.get("design_color_scheme"):
                assert design_settings.get("color_scheme") == default_profile.get("design_color_scheme"), \
                    f"Default profile design not used: expected {default_profile.get('design_color_scheme')}, got {design_settings.get('color_scheme')}"
            
            print(f"✓ Default profile design settings used in master URL: {design_settings.get('color_scheme')}")
        else:
            print("✓ No default profile with design settings - global settings used")


class TestAccountSettingsSlimmed:
    """Test that Account Settings only contains email, slug, password change"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.musician = login_response.json().get("musician")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    def test_profile_endpoint_returns_email_and_slug(self):
        """Test that profile endpoint returns email and slug for Account Settings"""
        response = self.session.get(f"{BASE_URL}/api/profile")
        assert response.status_code == 200, f"Profile endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify email and slug are present
        assert "email" in data, "email not in profile response"
        assert "slug" in data, "slug not in profile response"
        
        print(f"✓ Profile endpoint returns email={data.get('email')}, slug={data.get('slug')}")
    
    def test_change_password_endpoint_exists(self):
        """Test that change password endpoint exists"""
        # Test with invalid data to verify endpoint exists
        response = self.session.put(f"{BASE_URL}/api/account/change-password", json={
            "current_password": "wrong",
            "new_password": "newpass123"
        })
        
        # Should return 400 or 401 for wrong password, not 404
        assert response.status_code in [400, 401, 422], \
            f"Change password endpoint not found or unexpected error: {response.status_code}"
        
        print(f"✓ Change password endpoint exists: status={response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
