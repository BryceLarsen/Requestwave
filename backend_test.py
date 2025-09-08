#!/usr/bin/env python3
"""
Backend Test Suite for RequestWave Musician Profile and Audience Interface
Testing musician profile routing issue with /musician/bryce-larsen endpoint
Focus: Musician profile existence, audience endpoints, and routing functionality
"""

import requests
import json
import sys
from datetime import datetime
import time

# Configuration
INTERNAL_BASE_URL = "http://localhost:8001/api"
EXTERNAL_BASE_URL = "https://music-flow-update.preview.emergentagent.com/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"
TARGET_SLUG = "bryce-larsen"

class MusicianProfileTester:
    def __init__(self):
        self.internal_token = None
        self.external_token = None
        self.musician_id = None
        self.musician_slug = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def authenticate(self):
        """Authenticate with both internal and external APIs"""
        print("\n=== Authentication Setup ===")
        
        # Try internal authentication first
        try:
            response = requests.post(f"{INTERNAL_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.internal_token = data.get("token")
                musician_data = data.get("musician", {})
                self.musician_id = musician_data.get("id")
                self.musician_slug = musician_data.get("slug")
                
                self.log_result("Internal Authentication", True, f"Successfully authenticated {TEST_EMAIL}", {
                    "musician_id": self.musician_id,
                    "musician_slug": self.musician_slug,
                    "musician_name": musician_data.get("name")
                })
            else:
                self.log_result("Internal Authentication", False, f"Internal login failed: {response.status_code}")
                
        except Exception as e:
            self.log_result("Internal Authentication", False, f"Internal auth error: {str(e)}")
        
        # Try external authentication
        try:
            response = requests.post(f"{EXTERNAL_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.external_token = data.get("token")
                self.log_result("External Authentication", True, f"Successfully authenticated on external API")
            else:
                self.log_result("External Authentication", False, f"External login failed: {response.status_code}")
                
        except Exception as e:
            self.log_result("External Authentication", False, f"External auth error: {str(e)}")
    
    def test_musician_profile_exists(self):
        """Test if musician with slug 'bryce-larsen' exists in database"""
        print(f"\n=== Testing Musician Profile Existence (slug: {TARGET_SLUG}) ===")
        
        if not self.internal_token:
            self.log_result("Musician Profile Existence", False, "No authentication token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.internal_token}"}
            
            # First, get the current user's profile to see their slug
            profile_response = requests.get(f"{INTERNAL_BASE_URL}/profile", headers=headers, timeout=10)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                current_slug = profile_data.get("slug")
                
                self.log_result("Current User Profile", True, f"Retrieved current user profile", {
                    "current_slug": current_slug,
                    "name": profile_data.get("name"),
                    "email": profile_data.get("email"),
                    "audience_link_active": profile_data.get("audience_link_active")
                })
                
                # Check if current user has the target slug
                if current_slug == TARGET_SLUG:
                    self.log_result("Target Slug Match", True, f"Current user has target slug '{TARGET_SLUG}'")
                    return True
                else:
                    self.log_result("Target Slug Match", False, f"Current user slug '{current_slug}' != target '{TARGET_SLUG}'")
            else:
                self.log_result("Current User Profile", False, f"Failed to get profile: {profile_response.status_code}")
            
            # Try to access the target musician profile directly (if it exists)
            try:
                musician_response = requests.get(f"{INTERNAL_BASE_URL}/musicians/{TARGET_SLUG}", timeout=10)
                
                if musician_response.status_code == 200:
                    musician_data = musician_response.json()
                    self.log_result("Target Musician Profile", True, f"Found musician with slug '{TARGET_SLUG}'", {
                        "musician_id": musician_data.get("id"),
                        "name": musician_data.get("name"),
                        "slug": musician_data.get("slug"),
                        "tips_enabled": musician_data.get("tips_enabled"),
                        "requests_enabled": musician_data.get("requests_enabled")
                    })
                    return True
                elif musician_response.status_code == 404:
                    self.log_result("Target Musician Profile", False, f"Musician with slug '{TARGET_SLUG}' not found (404)")
                else:
                    self.log_result("Target Musician Profile", False, f"Error accessing musician profile: {musician_response.status_code}")
                    
            except Exception as e:
                self.log_result("Target Musician Profile", False, f"Error testing musician profile: {str(e)}")
            
            return False
                
        except Exception as e:
            self.log_result("Musician Profile Existence", False, f"Profile existence test error: {str(e)}")
            return False
    
    def test_audience_endpoint(self):
        """Test GET /api/musicians/bryce-larsen endpoint"""
        print(f"\n=== Testing Audience Endpoint: GET /musicians/{TARGET_SLUG} ===")
        
        # Test both internal and external APIs
        for api_name, base_url in [("Internal", INTERNAL_BASE_URL), ("External", EXTERNAL_BASE_URL)]:
            try:
                response = requests.get(f"{base_url}/musicians/{TARGET_SLUG}", timeout=30)
                
                if response.status_code == 200:
                    musician_data = response.json()
                    
                    # Verify required fields for audience interface
                    required_fields = ["id", "name", "slug"]
                    optional_fields = ["tips_enabled", "requests_enabled", "paypal_username", "venmo_username"]
                    
                    missing_required = [field for field in required_fields if field not in musician_data]
                    present_optional = [field for field in optional_fields if field in musician_data]
                    
                    if not missing_required:
                        self.log_result(f"Audience Endpoint - {api_name}", True, f"Successfully retrieved musician profile", {
                            "musician_id": musician_data.get("id"),
                            "name": musician_data.get("name"),
                            "slug": musician_data.get("slug"),
                            "tips_enabled": musician_data.get("tips_enabled"),
                            "requests_enabled": musician_data.get("requests_enabled"),
                            "required_fields_present": len(required_fields),
                            "optional_fields_present": len(present_optional),
                            "total_fields": len(musician_data)
                        })
                    else:
                        self.log_result(f"Audience Endpoint - {api_name}", False, f"Missing required fields: {missing_required}")
                        
                elif response.status_code == 404:
                    self.log_result(f"Audience Endpoint - {api_name}", False, f"Musician '{TARGET_SLUG}' not found (404)")
                else:
                    self.log_result(f"Audience Endpoint - {api_name}", False, f"Endpoint failed: {response.status_code} - {response.text[:200]}")
                    
            except Exception as e:
                self.log_result(f"Audience Endpoint - {api_name}", False, f"Error testing audience endpoint: {str(e)}")
    
    def test_songs_endpoint(self):
        """Test GET /api/musicians/bryce-larsen/songs endpoint"""
        print(f"\n=== Testing Songs Endpoint: GET /musicians/{TARGET_SLUG}/songs ===")
        
        # Test both internal and external APIs
        for api_name, base_url in [("Internal", INTERNAL_BASE_URL), ("External", EXTERNAL_BASE_URL)]:
            try:
                response = requests.get(f"{base_url}/musicians/{TARGET_SLUG}/songs", timeout=30)
                
                if response.status_code == 200:
                    songs_data = response.json()
                    
                    if isinstance(songs_data, list):
                        self.log_result(f"Songs Endpoint - {api_name}", True, f"Successfully retrieved songs list", {
                            "songs_count": len(songs_data),
                            "has_songs": len(songs_data) > 0,
                            "first_song": songs_data[0] if songs_data else None
                        })
                        
                        # If we have songs, verify their structure
                        if songs_data:
                            first_song = songs_data[0]
                            required_song_fields = ["id", "title", "artist"]
                            missing_song_fields = [field for field in required_song_fields if field not in first_song]
                            
                            if not missing_song_fields:
                                self.log_result(f"Songs Structure - {api_name}", True, "Songs have correct structure", {
                                    "sample_song": {
                                        "title": first_song.get("title"),
                                        "artist": first_song.get("artist"),
                                        "genres": first_song.get("genres", []),
                                        "moods": first_song.get("moods", [])
                                    }
                                })
                            else:
                                self.log_result(f"Songs Structure - {api_name}", False, f"Songs missing required fields: {missing_song_fields}")
                    else:
                        self.log_result(f"Songs Endpoint - {api_name}", False, f"Songs endpoint returned non-list: {type(songs_data)}")
                        
                elif response.status_code == 404:
                    self.log_result(f"Songs Endpoint - {api_name}", False, f"Songs endpoint not found for '{TARGET_SLUG}' (404)")
                else:
                    self.log_result(f"Songs Endpoint - {api_name}", False, f"Songs endpoint failed: {response.status_code} - {response.text[:200]}")
                    
            except Exception as e:
                self.log_result(f"Songs Endpoint - {api_name}", False, f"Error testing songs endpoint: {str(e)}")
    
    def test_all_musicians_list(self):
        """Check all musicians to see what slugs actually exist"""
        print("\n=== Testing All Musicians List ===")
        
        if not self.internal_token:
            self.log_result("All Musicians List", False, "No authentication token available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.internal_token}"}
            
            # Try to get all musicians (this might not be a public endpoint)
            # Let's try a few possible endpoints
            possible_endpoints = [
                "/musicians",
                "/admin/musicians", 
                "/profile/all"
            ]
            
            found_musicians = False
            
            for endpoint in possible_endpoints:
                try:
                    response = requests.get(f"{INTERNAL_BASE_URL}{endpoint}", headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        musicians_data = response.json()
                        
                        if isinstance(musicians_data, list) and musicians_data:
                            found_musicians = True
                            slugs = [m.get("slug") for m in musicians_data if m.get("slug")]
                            
                            self.log_result("All Musicians List", True, f"Found {len(musicians_data)} musicians", {
                                "endpoint_used": endpoint,
                                "total_musicians": len(musicians_data),
                                "available_slugs": slugs[:10],  # Show first 10 slugs
                                "target_slug_exists": TARGET_SLUG in slugs
                            })
                            break
                            
                except Exception as e:
                    continue
            
            if not found_musicians:
                self.log_result("All Musicians List", False, "Could not find endpoint to list all musicians")
                
        except Exception as e:
            self.log_result("All Musicians List", False, f"Error testing musicians list: {str(e)}")
    
    def test_create_test_musician(self):
        """Create a test musician with bryce-larsen slug if needed"""
        print(f"\n=== Testing Creation of Test Musician (slug: {TARGET_SLUG}) ===")
        
        if not self.internal_token:
            self.log_result("Create Test Musician", False, "No authentication token available")
            return
        
        # First check if we can update the current user's slug
        try:
            headers = {"Authorization": f"Bearer {self.internal_token}"}
            
            # Get current profile
            profile_response = requests.get(f"{INTERNAL_BASE_URL}/profile", headers=headers, timeout=10)
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                current_slug = profile_data.get("slug")
                
                if current_slug != TARGET_SLUG:
                    # Try to update the slug to the target slug
                    update_data = {"slug": TARGET_SLUG}  # This might not be allowed
                    
                    # Note: Most systems don't allow slug updates, but let's try
                    self.log_result("Create Test Musician", False, f"Current user slug is '{current_slug}', target is '{TARGET_SLUG}'. Manual slug update may be required.", {
                        "current_slug": current_slug,
                        "target_slug": TARGET_SLUG,
                        "suggestion": f"Consider using existing slug '{current_slug}' for testing or manually update database"
                    })
                else:
                    self.log_result("Create Test Musician", True, f"Current user already has target slug '{TARGET_SLUG}'")
            else:
                self.log_result("Create Test Musician", False, f"Could not get current profile: {profile_response.status_code}")
                
        except Exception as e:
            self.log_result("Create Test Musician", False, f"Error in test musician creation: {str(e)}")
    
    def test_routing_functionality(self):
        """Test various routing scenarios to identify the issue"""
        print("\n=== Testing Routing Functionality ===")
        
        # Test different URL patterns that might be causing issues
        test_patterns = [
            f"/musicians/{TARGET_SLUG}",
            f"/musicians/{TARGET_SLUG}/",
            f"/musician/{TARGET_SLUG}",  # Note: singular vs plural
            f"/musician/{TARGET_SLUG}/",
            f"/api/musicians/{TARGET_SLUG}",
            f"/api/musician/{TARGET_SLUG}"
        ]
        
        for pattern in test_patterns:
            for api_name, base_url in [("Internal", INTERNAL_BASE_URL), ("External", EXTERNAL_BASE_URL)]:
                try:
                    # Remove /api prefix if it's already in the base URL
                    test_url = pattern
                    if pattern.startswith("/api/") and "/api" in base_url:
                        test_url = pattern[4:]  # Remove /api/ prefix
                    
                    full_url = f"{base_url}{test_url}"
                    response = requests.get(full_url, timeout=30)
                    
                    self.log_result(f"Routing Test - {api_name}", response.status_code in [200, 404], f"Pattern '{pattern}' -> {response.status_code}", {
                        "pattern": pattern,
                        "full_url": full_url,
                        "status_code": response.status_code,
                        "response_size": len(response.text) if response.text else 0
                    })
                    
                except Exception as e:
                    self.log_result(f"Routing Test - {api_name}", False, f"Error testing pattern '{pattern}': {str(e)}")
    
    def run_all_tests(self):
        """Run all musician profile and audience interface tests"""
        print("🚀 Starting Musician Profile and Audience Interface Backend Tests")
        print(f"Internal API: {INTERNAL_BASE_URL}")
        print(f"External API: {EXTERNAL_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print(f"Target slug: {TARGET_SLUG}")
        print("=" * 80)
        
        # Run all tests in order
        self.authenticate()
        self.test_musician_profile_exists()
        self.test_audience_endpoint()
        self.test_songs_endpoint()
        self.test_all_musicians_list()
        self.test_create_test_musician()
        self.test_routing_functionality()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 MUSICIAN PROFILE ROUTING TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results
        critical_failures = []
        minor_failures = []
        
        for result in self.results:
            if not result["success"]:
                if any(keyword in result["test"].lower() for keyword in ["audience endpoint", "songs endpoint", "musician profile"]):
                    critical_failures.append(result)
                else:
                    minor_failures.append(result)
        
        if critical_failures:
            print("\n❌ CRITICAL FAILURES:")
            for result in critical_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        if minor_failures:
            print("\n⚠️ MINOR FAILURES:")
            for result in minor_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        
        # Check if target musician exists
        target_exists = any(r["success"] and "target musician profile" in r["test"].lower() for r in self.results)
        if target_exists:
            print(f"✅ Musician with slug '{TARGET_SLUG}' exists in database")
        else:
            print(f"❌ Musician with slug '{TARGET_SLUG}' NOT found in database")
        
        # Check audience endpoint status
        audience_working = any(r["success"] and "audience endpoint" in r["test"].lower() for r in self.results)
        if audience_working:
            print(f"✅ Audience endpoint /musicians/{TARGET_SLUG} is working")
        else:
            print(f"❌ Audience endpoint /musicians/{TARGET_SLUG} is NOT working")
        
        # Check songs endpoint status
        songs_working = any(r["success"] and "songs endpoint" in r["test"].lower() for r in self.results)
        if songs_working:
            print(f"✅ Songs endpoint /musicians/{TARGET_SLUG}/songs is working")
        else:
            print(f"❌ Songs endpoint /musicians/{TARGET_SLUG}/songs is NOT working")
        
        print("\n🎯 MUSICIAN PROFILE ROUTING TEST COMPLETE")
        
        # Provide recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not target_exists:
            print(f"1. Create musician profile with slug '{TARGET_SLUG}' or use existing user's slug")
        if not audience_working:
            print("2. Check API routing configuration for /musicians/:slug endpoint")
        if not songs_working:
            print("3. Verify songs endpoint routing and data availability")
        
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = MusicianProfileTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)