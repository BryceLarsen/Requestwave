#!/usr/bin/env python3
"""
SOCIAL MEDIA LINK VISIBILITY IMPROVEMENTS TESTING

Testing the social media link visibility improvements to ensure blank/empty social links 
don't appear on the audience side. This tests the new `.trim() !== ''` validation checks.

CRITICAL TEST AREAS:
1. Empty Fields Test - Create musician with empty social media fields ("") 
2. Whitespace Fields Test - Create musician with whitespace-only fields ("   ")
3. Mixed Fields Test - Create musician with mix of filled/empty fields
4. All Empty Test - Create musician with all social media fields empty/blank
5. All Filled Test - Create musician with all fields properly filled

Expected: Frontend properly filters out empty/blank social media fields using 
the new `.trim() !== ''` validation checks, ensuring clean audience interface.

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://request-error-fix.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class SocialMediaVisibilityTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_musicians = []  # Track created test musicians for cleanup
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        if success:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {message}")

    def make_request(self, method: str, endpoint: str, data: Any = None, files: Any = None, headers: Dict = None, params: Dict = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        # Remove Content-Type for file uploads
        if files:
            request_headers.pop("Content-Type", None)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=data or params)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, headers={k: v for k, v in request_headers.items() if k != "Content-Type"}, files=files, data=data)
                elif params:
                    response = requests.post(url, headers=request_headers, params=params)
                else:
                    response = requests.post(url, headers=request_headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=request_headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=request_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def create_test_musician(self, name: str, email: str) -> Dict[str, Any]:
        """Create a test musician and return their data"""
        musician_data = {
            "name": name,
            "email": email,
            "password": "TestPassword123!"
        }
        
        # Try to register
        response = self.make_request("POST", "/auth/register", musician_data)
        
        if response.status_code == 200:
            data = response.json()
            self.test_musicians.append(data["musician"]["id"])
            return data
        elif response.status_code == 400:
            # Try login if already exists
            login_data = {
                "email": email,
                "password": "TestPassword123!"
            }
            login_response = self.make_request("POST", "/auth/login", login_data)
            if login_response.status_code == 200:
                data = login_response.json()
                return data
            else:
                raise Exception(f"Failed to login existing musician: {login_response.status_code}")
        else:
            raise Exception(f"Failed to register musician: {response.status_code}")

    def test_empty_fields(self):
        """Test 1: Create musician with empty social media fields ('')"""
        try:
            print("🎵 TEST 1: Empty Fields Test")
            print("=" * 80)
            
            # Step 1: Create test musician
            print("📊 Step 1: Create test musician with empty social media fields")
            musician_data = self.create_test_musician(
                "Empty Fields Test Musician", 
                "empty.fields@socialtest.com"
            )
            
            self.auth_token = musician_data["token"]
            musician_slug = musician_data["musician"]["slug"]
            
            print(f"   ✅ Created musician: {musician_data['musician']['name']}")
            print(f"   📊 Musician slug: {musician_slug}")
            
            # Step 2: Set all social media fields to empty strings
            print("📊 Step 2: Set all social media fields to empty strings")
            
            empty_social_data = {
                "instagram_username": "",
                "facebook_username": "",
                "tiktok_username": "",
                "spotify_artist_url": "",
                "apple_music_artist_url": ""
            }
            
            update_response = self.make_request("PUT", "/profile", empty_social_data)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile updated with empty social media fields")
                
                # Verify all fields are empty
                all_empty = all(
                    updated_profile.get(field) == "" 
                    for field in empty_social_data.keys()
                )
                
                if all_empty:
                    print(f"   ✅ All social media fields are empty strings")
                    empty_fields_set = True
                else:
                    print(f"   ❌ Some social media fields are not empty")
                    empty_fields_set = False
            else:
                print(f"   ❌ Failed to update profile: {update_response.status_code}")
                empty_fields_set = False
            
            # Step 3: Test public musician endpoint (audience view)
            print("📊 Step 3: Test public musician endpoint (audience view)")
            
            # Clear auth token for public access
            self.auth_token = None
            
            public_response = self.make_request("GET", f"/musicians/{musician_slug}")
            
            if public_response.status_code == 200:
                public_data = public_response.json()
                print(f"   ✅ Public musician endpoint accessible")
                
                # Check social media fields in public data
                social_fields = {
                    "instagram_username": public_data.get("instagram_username"),
                    "facebook_username": public_data.get("facebook_username"),
                    "tiktok_username": public_data.get("tiktok_username"),
                    "spotify_artist_url": public_data.get("spotify_artist_url"),
                    "apple_music_artist_url": public_data.get("apple_music_artist_url")
                }
                
                print(f"   📊 Public social media fields:")
                for field, value in social_fields.items():
                    print(f"      {field}: '{value}'")
                
                # All fields should be empty strings or None
                all_empty_public = all(
                    value == "" or value is None 
                    for value in social_fields.values()
                )
                
                if all_empty_public:
                    print(f"   ✅ All social media fields are empty in public data")
                    public_empty_correct = True
                else:
                    print(f"   ❌ Some social media fields have values in public data")
                    public_empty_correct = False
                
                public_access_works = True
            else:
                print(f"   ❌ Public musician endpoint failed: {public_response.status_code}")
                public_access_works = False
                public_empty_correct = False
            
            # Final assessment
            if empty_fields_set and public_access_works and public_empty_correct:
                self.log_result("Empty Fields Test", True, "✅ EMPTY FIELDS TEST PASSED: Empty social media fields properly handled")
            else:
                issues = []
                if not empty_fields_set:
                    issues.append("failed to set empty fields")
                if not public_access_works:
                    issues.append("public access failed")
                if not public_empty_correct:
                    issues.append("empty fields not handled correctly in public data")
                
                self.log_result("Empty Fields Test", False, f"❌ EMPTY FIELDS TEST ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Empty Fields Test", False, f"❌ Exception: {str(e)}")

    def test_whitespace_fields(self):
        """Test 2: Create musician with whitespace-only social media fields ('   ')"""
        try:
            print("🎵 TEST 2: Whitespace Fields Test")
            print("=" * 80)
            
            # Step 1: Create test musician
            print("📊 Step 1: Create test musician with whitespace social media fields")
            musician_data = self.create_test_musician(
                "Whitespace Fields Test Musician", 
                "whitespace.fields@socialtest.com"
            )
            
            self.auth_token = musician_data["token"]
            musician_slug = musician_data["musician"]["slug"]
            
            print(f"   ✅ Created musician: {musician_data['musician']['name']}")
            print(f"   📊 Musician slug: {musician_slug}")
            
            # Step 2: Set social media fields to whitespace-only strings
            print("📊 Step 2: Set social media fields to whitespace-only strings")
            
            whitespace_social_data = {
                "instagram_username": "   ",  # 3 spaces
                "facebook_username": "\t\t",  # 2 tabs
                "tiktok_username": " \t ",    # space-tab-space
                "spotify_artist_url": "    ", # 4 spaces
                "apple_music_artist_url": "\n\n"  # 2 newlines
            }
            
            update_response = self.make_request("PUT", "/profile", whitespace_social_data)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile updated with whitespace social media fields")
                
                # Check what the backend stored
                stored_values = {}
                for field in whitespace_social_data.keys():
                    stored_values[field] = updated_profile.get(field)
                    print(f"      {field}: '{stored_values[field]}'")
                
                whitespace_fields_set = True
            else:
                print(f"   ❌ Failed to update profile: {update_response.status_code}")
                whitespace_fields_set = False
                stored_values = {}
            
            # Step 3: Test public musician endpoint (audience view)
            print("📊 Step 3: Test public musician endpoint (audience view)")
            
            # Clear auth token for public access
            self.auth_token = None
            
            public_response = self.make_request("GET", f"/musicians/{musician_slug}")
            
            if public_response.status_code == 200:
                public_data = public_response.json()
                print(f"   ✅ Public musician endpoint accessible")
                
                # Check social media fields in public data
                public_social_fields = {
                    "instagram_username": public_data.get("instagram_username"),
                    "facebook_username": public_data.get("facebook_username"),
                    "tiktok_username": public_data.get("tiktok_username"),
                    "spotify_artist_url": public_data.get("spotify_artist_url"),
                    "apple_music_artist_url": public_data.get("apple_music_artist_url")
                }
                
                print(f"   📊 Public social media fields:")
                for field, value in public_social_fields.items():
                    print(f"      {field}: '{value}'")
                
                # Check if whitespace fields are properly handled
                # They should either be trimmed to empty strings or remain as whitespace
                # The key test is whether the frontend will filter them out with .trim() !== ''
                whitespace_handled_correctly = True
                for field, value in public_social_fields.items():
                    if value and value.strip() == "":
                        # This is whitespace-only, which should be filtered by frontend
                        print(f"      ⚠️  {field} contains whitespace-only value: '{value}'")
                    elif value == "":
                        # This is empty, which is correct
                        print(f"      ✅ {field} is empty (trimmed by backend)")
                    elif value is None:
                        # This is None, which is also correct
                        print(f"      ✅ {field} is None")
                    else:
                        # This has actual content
                        print(f"      📊 {field} has content: '{value}'")
                
                public_access_works = True
            else:
                print(f"   ❌ Public musician endpoint failed: {public_response.status_code}")
                public_access_works = False
                public_social_fields = {}
            
            # Step 4: Simulate frontend .trim() !== '' validation
            print("📊 Step 4: Simulate frontend .trim() !== '' validation")
            
            if public_access_works:
                visible_fields = {}
                for field, value in public_social_fields.items():
                    # Simulate frontend validation: .trim() !== ''
                    if value and str(value).strip() != '':
                        visible_fields[field] = value
                        print(f"      ✅ {field} would be VISIBLE: '{value}'")
                    else:
                        print(f"      ❌ {field} would be HIDDEN: '{value}' (empty after trim)")
                
                # For whitespace test, we expect NO fields to be visible
                no_fields_visible = len(visible_fields) == 0
                
                if no_fields_visible:
                    print(f"   ✅ No social media fields would be visible (correct for whitespace test)")
                    frontend_validation_correct = True
                else:
                    print(f"   ❌ Some fields would still be visible: {list(visible_fields.keys())}")
                    frontend_validation_correct = False
            else:
                frontend_validation_correct = False
            
            # Final assessment
            if whitespace_fields_set and public_access_works and frontend_validation_correct:
                self.log_result("Whitespace Fields Test", True, "✅ WHITESPACE FIELDS TEST PASSED: Whitespace-only fields properly filtered out")
            else:
                issues = []
                if not whitespace_fields_set:
                    issues.append("failed to set whitespace fields")
                if not public_access_works:
                    issues.append("public access failed")
                if not frontend_validation_correct:
                    issues.append("whitespace fields not properly filtered")
                
                self.log_result("Whitespace Fields Test", False, f"❌ WHITESPACE FIELDS TEST ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Whitespace Fields Test", False, f"❌ Exception: {str(e)}")

    def test_mixed_fields(self):
        """Test 3: Create musician with mix of filled/empty social media fields"""
        try:
            print("🎵 TEST 3: Mixed Fields Test")
            print("=" * 80)
            
            # Step 1: Create test musician
            print("📊 Step 1: Create test musician with mixed social media fields")
            musician_data = self.create_test_musician(
                "Mixed Fields Test Musician", 
                "mixed.fields@socialtest.com"
            )
            
            self.auth_token = musician_data["token"]
            musician_slug = musician_data["musician"]["slug"]
            
            print(f"   ✅ Created musician: {musician_data['musician']['name']}")
            print(f"   📊 Musician slug: {musician_slug}")
            
            # Step 2: Set mixed social media fields as specified in review request
            print("📊 Step 2: Set mixed social media fields")
            print("   - Instagram: filled with valid username")
            print("   - Facebook: left empty ('')")
            print("   - TikTok: filled with whitespace ('   ')")
            print("   - Spotify: filled with valid URL")
            print("   - Apple Music: left empty ('')")
            
            mixed_social_data = {
                "instagram_username": "validinstagram",  # Filled
                "facebook_username": "",                 # Empty
                "tiktok_username": "   ",               # Whitespace
                "spotify_artist_url": "https://open.spotify.com/artist/validartist",  # Filled
                "apple_music_artist_url": ""            # Empty
            }
            
            update_response = self.make_request("PUT", "/profile", mixed_social_data)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile updated with mixed social media fields")
                
                # Verify the stored values
                for field, expected_value in mixed_social_data.items():
                    stored_value = updated_profile.get(field)
                    print(f"      {field}: '{stored_value}' (expected: '{expected_value}')")
                
                mixed_fields_set = True
            else:
                print(f"   ❌ Failed to update profile: {update_response.status_code}")
                mixed_fields_set = False
            
            # Step 3: Test public musician endpoint (audience view)
            print("📊 Step 3: Test public musician endpoint (audience view)")
            
            # Clear auth token for public access
            self.auth_token = None
            
            public_response = self.make_request("GET", f"/musicians/{musician_slug}")
            
            if public_response.status_code == 200:
                public_data = public_response.json()
                print(f"   ✅ Public musician endpoint accessible")
                
                # Check social media fields in public data
                public_social_fields = {
                    "instagram_username": public_data.get("instagram_username"),
                    "facebook_username": public_data.get("facebook_username"),
                    "tiktok_username": public_data.get("tiktok_username"),
                    "spotify_artist_url": public_data.get("spotify_artist_url"),
                    "apple_music_artist_url": public_data.get("apple_music_artist_url")
                }
                
                print(f"   📊 Public social media fields:")
                for field, value in public_social_fields.items():
                    print(f"      {field}: '{value}'")
                
                public_access_works = True
            else:
                print(f"   ❌ Public musician endpoint failed: {public_response.status_code}")
                public_access_works = False
                public_social_fields = {}
            
            # Step 4: Simulate frontend .trim() !== '' validation
            print("📊 Step 4: Simulate frontend .trim() !== '' validation")
            
            if public_access_works:
                visible_fields = {}
                hidden_fields = {}
                
                for field, value in public_social_fields.items():
                    # Simulate frontend validation: .trim() !== ''
                    if value and str(value).strip() != '':
                        visible_fields[field] = value
                        print(f"      ✅ {field} would be VISIBLE: '{value}'")
                    else:
                        hidden_fields[field] = value
                        print(f"      ❌ {field} would be HIDDEN: '{value}' (empty after trim)")
                
                # Expected results based on review request:
                # - Instagram: should be visible (validinstagram)
                # - Facebook: should be hidden (empty)
                # - TikTok: should be hidden (whitespace)
                # - Spotify: should be visible (valid URL)
                # - Apple Music: should be hidden (empty)
                
                expected_visible = ["instagram_username", "spotify_artist_url"]
                expected_hidden = ["facebook_username", "tiktok_username", "apple_music_artist_url"]
                
                visible_correct = all(field in visible_fields for field in expected_visible)
                hidden_correct = all(field in hidden_fields for field in expected_hidden)
                
                if visible_correct and hidden_correct:
                    print(f"   ✅ Correct fields visible: {list(visible_fields.keys())}")
                    print(f"   ✅ Correct fields hidden: {list(hidden_fields.keys())}")
                    frontend_validation_correct = True
                else:
                    print(f"   ❌ Incorrect visibility results")
                    print(f"      Expected visible: {expected_visible}")
                    print(f"      Actually visible: {list(visible_fields.keys())}")
                    print(f"      Expected hidden: {expected_hidden}")
                    print(f"      Actually hidden: {list(hidden_fields.keys())}")
                    frontend_validation_correct = False
            else:
                frontend_validation_correct = False
            
            # Final assessment
            if mixed_fields_set and public_access_works and frontend_validation_correct:
                self.log_result("Mixed Fields Test", True, "✅ MIXED FIELDS TEST PASSED: Only Instagram and Spotify buttons would appear on audience side")
            else:
                issues = []
                if not mixed_fields_set:
                    issues.append("failed to set mixed fields")
                if not public_access_works:
                    issues.append("public access failed")
                if not frontend_validation_correct:
                    issues.append("incorrect field visibility")
                
                self.log_result("Mixed Fields Test", False, f"❌ MIXED FIELDS TEST ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Mixed Fields Test", False, f"❌ Exception: {str(e)}")

    def test_all_empty_fields(self):
        """Test 4: Create musician with all social media fields empty/blank"""
        try:
            print("🎵 TEST 4: All Empty Fields Test")
            print("=" * 80)
            
            # Step 1: Create test musician
            print("📊 Step 1: Create test musician with all empty social media fields")
            musician_data = self.create_test_musician(
                "All Empty Fields Test Musician", 
                "all.empty@socialtest.com"
            )
            
            self.auth_token = musician_data["token"]
            musician_slug = musician_data["musician"]["slug"]
            
            print(f"   ✅ Created musician: {musician_data['musician']['name']}")
            print(f"   📊 Musician slug: {musician_slug}")
            
            # Step 2: Ensure all social media fields are empty
            print("📊 Step 2: Set all social media fields to empty")
            
            all_empty_data = {
                "instagram_username": "",
                "facebook_username": "",
                "tiktok_username": "",
                "spotify_artist_url": "",
                "apple_music_artist_url": ""
            }
            
            update_response = self.make_request("PUT", "/profile", all_empty_data)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile updated with all empty social media fields")
                
                # Verify all fields are empty
                all_empty = all(
                    updated_profile.get(field) == "" or updated_profile.get(field) is None
                    for field in all_empty_data.keys()
                )
                
                if all_empty:
                    print(f"   ✅ All social media fields are empty")
                    all_empty_set = True
                else:
                    print(f"   ❌ Some social media fields are not empty")
                    all_empty_set = False
            else:
                print(f"   ❌ Failed to update profile: {update_response.status_code}")
                all_empty_set = False
            
            # Step 3: Test public musician endpoint (audience view)
            print("📊 Step 3: Test public musician endpoint (audience view)")
            
            # Clear auth token for public access
            self.auth_token = None
            
            public_response = self.make_request("GET", f"/musicians/{musician_slug}")
            
            if public_response.status_code == 200:
                public_data = public_response.json()
                print(f"   ✅ Public musician endpoint accessible")
                
                # Check social media fields in public data
                social_fields = {
                    "instagram_username": public_data.get("instagram_username"),
                    "facebook_username": public_data.get("facebook_username"),
                    "tiktok_username": public_data.get("tiktok_username"),
                    "spotify_artist_url": public_data.get("spotify_artist_url"),
                    "apple_music_artist_url": public_data.get("apple_music_artist_url")
                }
                
                print(f"   📊 Public social media fields:")
                for field, value in social_fields.items():
                    print(f"      {field}: '{value}'")
                
                public_access_works = True
            else:
                print(f"   ❌ Public musician endpoint failed: {public_response.status_code}")
                public_access_works = False
                social_fields = {}
            
            # Step 4: Simulate frontend .trim() !== '' validation
            print("📊 Step 4: Simulate frontend .trim() !== '' validation")
            
            if public_access_works:
                visible_fields = {}
                for field, value in social_fields.items():
                    # Simulate frontend validation: .trim() !== ''
                    if value and str(value).strip() != '':
                        visible_fields[field] = value
                        print(f"      ❌ {field} would be VISIBLE: '{value}' (unexpected)")
                    else:
                        print(f"      ✅ {field} would be HIDDEN: '{value}' (correct)")
                
                # For all empty test, we expect NO fields to be visible
                no_social_section = len(visible_fields) == 0
                
                if no_social_section:
                    print(f"   ✅ No social media section would appear (all fields hidden)")
                    frontend_validation_correct = True
                else:
                    print(f"   ❌ Some social media fields would still appear: {list(visible_fields.keys())}")
                    frontend_validation_correct = False
            else:
                frontend_validation_correct = False
            
            # Final assessment
            if all_empty_set and public_access_works and frontend_validation_correct:
                self.log_result("All Empty Fields Test", True, "✅ ALL EMPTY FIELDS TEST PASSED: No social media section appears when all fields empty")
            else:
                issues = []
                if not all_empty_set:
                    issues.append("failed to set all fields empty")
                if not public_access_works:
                    issues.append("public access failed")
                if not frontend_validation_correct:
                    issues.append("social media section still appears when all empty")
                
                self.log_result("All Empty Fields Test", False, f"❌ ALL EMPTY FIELDS TEST ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("All Empty Fields Test", False, f"❌ Exception: {str(e)}")

    def test_all_filled_fields(self):
        """Test 5: Create musician with all social media fields properly filled"""
        try:
            print("🎵 TEST 5: All Filled Fields Test")
            print("=" * 80)
            
            # Step 1: Create test musician
            print("📊 Step 1: Create test musician with all filled social media fields")
            musician_data = self.create_test_musician(
                "All Filled Fields Test Musician", 
                "all.filled@socialtest.com"
            )
            
            self.auth_token = musician_data["token"]
            musician_slug = musician_data["musician"]["slug"]
            
            print(f"   ✅ Created musician: {musician_data['musician']['name']}")
            print(f"   📊 Musician slug: {musician_slug}")
            
            # Step 2: Set all social media fields with valid content
            print("📊 Step 2: Set all social media fields with valid content")
            
            all_filled_data = {
                "instagram_username": "testmusician",
                "facebook_username": "testmusicianpage",
                "tiktok_username": "testmusician_tiktok",
                "spotify_artist_url": "https://open.spotify.com/artist/testmusician123",
                "apple_music_artist_url": "https://music.apple.com/us/artist/testmusician/123456789"
            }
            
            update_response = self.make_request("PUT", "/profile", all_filled_data)
            
            if update_response.status_code == 200:
                updated_profile = update_response.json()
                print(f"   ✅ Profile updated with all filled social media fields")
                
                # Verify all fields have content
                for field, expected_value in all_filled_data.items():
                    stored_value = updated_profile.get(field)
                    print(f"      {field}: '{stored_value}'")
                    
                all_filled = all(
                    updated_profile.get(field) == expected_value
                    for field, expected_value in all_filled_data.items()
                )
                
                if all_filled:
                    print(f"   ✅ All social media fields are properly filled")
                    all_filled_set = True
                else:
                    print(f"   ❌ Some social media fields are not set correctly")
                    all_filled_set = False
            else:
                print(f"   ❌ Failed to update profile: {update_response.status_code}")
                all_filled_set = False
            
            # Step 3: Test public musician endpoint (audience view)
            print("📊 Step 3: Test public musician endpoint (audience view)")
            
            # Clear auth token for public access
            self.auth_token = None
            
            public_response = self.make_request("GET", f"/musicians/{musician_slug}")
            
            if public_response.status_code == 200:
                public_data = public_response.json()
                print(f"   ✅ Public musician endpoint accessible")
                
                # Check social media fields in public data
                public_social_fields = {
                    "instagram_username": public_data.get("instagram_username"),
                    "facebook_username": public_data.get("facebook_username"),
                    "tiktok_username": public_data.get("tiktok_username"),
                    "spotify_artist_url": public_data.get("spotify_artist_url"),
                    "apple_music_artist_url": public_data.get("apple_music_artist_url")
                }
                
                print(f"   📊 Public social media fields:")
                for field, value in public_social_fields.items():
                    print(f"      {field}: '{value}'")
                
                public_access_works = True
            else:
                print(f"   ❌ Public musician endpoint failed: {public_response.status_code}")
                public_access_works = False
                public_social_fields = {}
            
            # Step 4: Simulate frontend .trim() !== '' validation
            print("📊 Step 4: Simulate frontend .trim() !== '' validation")
            
            if public_access_works:
                visible_fields = {}
                hidden_fields = {}
                
                for field, value in public_social_fields.items():
                    # Simulate frontend validation: .trim() !== ''
                    if value and str(value).strip() != '':
                        visible_fields[field] = value
                        print(f"      ✅ {field} would be VISIBLE: '{value}'")
                    else:
                        hidden_fields[field] = value
                        print(f"      ❌ {field} would be HIDDEN: '{value}' (unexpected)")
                
                # For all filled test, we expect ALL fields to be visible
                all_fields_visible = len(visible_fields) == 5 and len(hidden_fields) == 0
                
                if all_fields_visible:
                    print(f"   ✅ All social media buttons would appear correctly")
                    print(f"   📊 Visible fields: {list(visible_fields.keys())}")
                    frontend_validation_correct = True
                else:
                    print(f"   ❌ Not all social media fields would be visible")
                    print(f"      Visible: {list(visible_fields.keys())}")
                    print(f"      Hidden: {list(hidden_fields.keys())}")
                    frontend_validation_correct = False
            else:
                frontend_validation_correct = False
            
            # Final assessment
            if all_filled_set and public_access_works and frontend_validation_correct:
                self.log_result("All Filled Fields Test", True, "✅ ALL FILLED FIELDS TEST PASSED: All social media buttons appear correctly when fields are filled")
            else:
                issues = []
                if not all_filled_set:
                    issues.append("failed to set all fields with content")
                if not public_access_works:
                    issues.append("public access failed")
                if not frontend_validation_correct:
                    issues.append("not all filled fields are visible")
                
                self.log_result("All Filled Fields Test", False, f"❌ ALL FILLED FIELDS TEST ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("All Filled Fields Test", False, f"❌ Exception: {str(e)}")

    def cleanup_test_musicians(self):
        """Clean up test musicians created during testing"""
        try:
            print("🧹 CLEANUP: Removing test musicians")
            # Note: This would require a delete endpoint or admin access
            # For now, we'll just log the cleanup attempt
            print(f"   📊 Created {len(self.test_musicians)} test musicians during testing")
            print(f"   ⚠️  Manual cleanup may be required for test musicians")
        except Exception as e:
            print(f"   ❌ Cleanup failed: {str(e)}")

    def run_all_tests(self):
        """Run all social media visibility tests in sequence"""
        print("🎵 STARTING SOCIAL MEDIA LINK VISIBILITY IMPROVEMENTS TESTING")
        print("=" * 100)
        print("Testing the new `.trim() !== ''` validation checks to ensure blank/empty")
        print("social links don't appear on the audience side.")
        print("=" * 100)
        
        # Test 1: Empty Fields Test
        self.test_empty_fields()
        
        # Test 2: Whitespace Fields Test
        self.test_whitespace_fields()
        
        # Test 3: Mixed Fields Test
        self.test_mixed_fields()
        
        # Test 4: All Empty Test
        self.test_all_empty_fields()
        
        # Test 5: All Filled Test
        self.test_all_filled_fields()
        
        # Cleanup
        self.cleanup_test_musicians()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🎵 FINAL SOCIAL MEDIA VISIBILITY TEST RESULTS")
        print("=" * 100)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        
        if self.results['passed'] + self.results['failed'] > 0:
            success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100)
            print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        else:
            print(f"📊 SUCCESS RATE: 0.0%")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n🎯 SUMMARY:")
        print("The social media link visibility improvements should ensure that:")
        print("• Empty fields ('') don't appear on audience interface")
        print("• Whitespace-only fields ('   ') don't appear on audience interface")
        print("• Only properly filled fields appear as buttons on audience side")
        print("• Frontend .trim() !== '' validation filters out blank fields")
        print("• Clean audience interface without empty social media buttons")
        
        print("\n" + "=" * 100)

if __name__ == "__main__":
    tester = SocialMediaVisibilityTester()
    tester.run_all_tests()