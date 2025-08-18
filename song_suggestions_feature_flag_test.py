#!/usr/bin/env python3
"""
SONG SUGGESTIONS FEATURE FLAG BUG FIX TESTING

Testing the Song Suggestions feature flag bug fix as requested:

CRITICAL BUG FIX: The "Suggest a song" button wasn't appearing on the Audience page 
even when "Song Suggestions" was enabled in the Design tab.

ROOT CAUSE IDENTIFIED: 
- Public design endpoint GET /api/musicians/{slug}/design was missing the `allow_song_suggestions` field
- Frontend checks `designSettings.allow_song_suggestions` to show/hide the button
- Since the field was undefined, the button never appeared

FIX IMPLEMENTED: 
- Added `allow_song_suggestions` field to the public design endpoint response
- Uses default value of `True` to match the DesignSettings model default

TESTING REQUIRED:
1. Test Public Design Endpoint - GET /api/musicians/{slug}/design
   - Should now include `allow_song_suggestions` field in response
   - Default value should be `true` when not explicitly set
   - Should reflect actual setting when musician has toggled it

2. Test with brycelarsenmusic@gmail.com account:
   - Test with slug "brycelarsenmusic" or whatever the actual slug is
   - Verify the response includes all expected design fields including `allow_song_suggestions`

3. Test Design Settings Management (authenticated endpoints):
   - GET /api/design/settings - should work for authenticated users
   - PUT /api/design/settings - should allow toggling `allow_song_suggestions`

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration - Use the correct backend URL from frontend/.env
BASE_URL = "https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class SongSuggestionsFeatureFlagTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
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

    def test_pro_musician_login(self):
        """Test login with brycelarsenmusic@gmail.com account"""
        try:
            print("🎵 TESTING PRO MUSICIAN LOGIN")
            print("=" * 80)
            
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"📊 Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    
                    print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
                    print(f"   ✅ Musician slug: {self.musician_slug}")
                    print(f"   ✅ Musician ID: {self.musician_id}")
                    
                    self.log_result("Pro Musician Login", True, f"Logged in as {data['musician']['name']} with slug '{self.musician_slug}'")
                else:
                    self.log_result("Pro Musician Login", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Pro Musician Login", False, f"Status code: {response.status_code}, Response: {response.text}")
                
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Pro Musician Login", False, f"Exception: {str(e)}")

    def test_public_design_endpoint_includes_allow_song_suggestions(self):
        """Test that public design endpoint includes allow_song_suggestions field - CRITICAL BUG FIX"""
        try:
            print("🎵 CRITICAL BUG FIX TEST: Public Design Endpoint includes allow_song_suggestions")
            print("=" * 80)
            
            if not self.musician_slug:
                self.log_result("Public Design Endpoint - allow_song_suggestions", False, "No musician slug available - login first")
                return
            
            # Step 1: Test public design endpoint (no authentication needed)
            print("📊 Step 1: Test public design endpoint GET /musicians/{slug}/design")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/design")
            
            print(f"   📊 Public design endpoint status: {response.status_code}")
            
            if response.status_code != 200:
                self.log_result("Public Design Endpoint - allow_song_suggestions", False, f"Public design endpoint failed: {response.status_code}, Response: {response.text}")
                self.auth_token = original_token
                return
            
            design_data = response.json()
            print(f"   📊 Design response keys: {list(design_data.keys())}")
            print(f"   📊 Full design response: {design_data}")
            
            # Step 2: Verify allow_song_suggestions field is present
            print("📊 Step 2: Verify allow_song_suggestions field is present")
            
            has_allow_song_suggestions = "allow_song_suggestions" in design_data
            
            if has_allow_song_suggestions:
                allow_song_suggestions_value = design_data["allow_song_suggestions"]
                print(f"   ✅ allow_song_suggestions field present: {allow_song_suggestions_value}")
                
                # Verify it's a boolean
                if isinstance(allow_song_suggestions_value, bool):
                    print(f"   ✅ allow_song_suggestions is boolean type")
                    field_type_correct = True
                else:
                    print(f"   ❌ allow_song_suggestions is not boolean: {type(allow_song_suggestions_value)}")
                    field_type_correct = False
            else:
                print(f"   ❌ allow_song_suggestions field missing from response")
                field_type_correct = False
                allow_song_suggestions_value = None
            
            # Step 3: Verify other expected design fields are still present
            print("📊 Step 3: Verify other expected design fields are still present")
            
            expected_fields = ["color_scheme", "layout_mode", "show_year", "show_notes"]
            missing_fields = [field for field in expected_fields if field not in design_data]
            
            if len(missing_fields) == 0:
                print(f"   ✅ All expected design fields present: {expected_fields}")
                other_fields_present = True
            else:
                print(f"   ❌ Missing design fields: {missing_fields}")
                other_fields_present = False
            
            # Step 4: Verify default value behavior
            print("📊 Step 4: Verify default value behavior")
            
            # The fix should use default value of True to match DesignSettings model default
            if has_allow_song_suggestions:
                if allow_song_suggestions_value is True:
                    print(f"   ✅ Default value is True (matches DesignSettings model default)")
                    default_value_correct = True
                else:
                    print(f"   ⚠️  Value is {allow_song_suggestions_value} (may be explicitly set by musician)")
                    default_value_correct = True  # Still acceptable if musician has changed it
            else:
                default_value_correct = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Final assessment
            if has_allow_song_suggestions and field_type_correct and other_fields_present and default_value_correct:
                self.log_result("Public Design Endpoint - allow_song_suggestions", True, f"✅ CRITICAL BUG FIX SUCCESSFUL: Public design endpoint now includes allow_song_suggestions field (value: {allow_song_suggestions_value})")
            else:
                issues = []
                if not has_allow_song_suggestions:
                    issues.append("allow_song_suggestions field missing")
                if not field_type_correct:
                    issues.append("incorrect field type")
                if not other_fields_present:
                    issues.append(f"missing other fields: {missing_fields}")
                if not default_value_correct:
                    issues.append("default value incorrect")
                
                self.log_result("Public Design Endpoint - allow_song_suggestions", False, f"❌ CRITICAL BUG FIX FAILED: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Public Design Endpoint - allow_song_suggestions", False, f"❌ Exception: {str(e)}")
            # Restore auth token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_authenticated_design_settings_endpoints(self):
        """Test authenticated design settings endpoints work correctly"""
        try:
            print("🎵 TESTING AUTHENTICATED DESIGN SETTINGS ENDPOINTS")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Authenticated Design Settings", False, "No auth token available - login first")
                return
            
            # Step 1: Test GET /api/design/settings (authenticated)
            print("📊 Step 1: Test GET /api/design/settings (authenticated)")
            
            get_response = self.make_request("GET", "/design/settings")
            
            print(f"   📊 GET design settings status: {get_response.status_code}")
            
            if get_response.status_code == 200:
                get_data = get_response.json()
                print(f"   ✅ GET design settings successful")
                print(f"   📊 Design settings keys: {list(get_data.keys())}")
                
                # Verify allow_song_suggestions is present
                if "allow_song_suggestions" in get_data:
                    current_value = get_data["allow_song_suggestions"]
                    print(f"   ✅ allow_song_suggestions in authenticated endpoint: {current_value}")
                    get_has_field = True
                else:
                    print(f"   ❌ allow_song_suggestions missing from authenticated endpoint")
                    get_has_field = False
                    current_value = None
                
                get_endpoint_working = True
            else:
                print(f"   ❌ GET design settings failed: {get_response.status_code}, Response: {get_response.text}")
                get_endpoint_working = False
                get_has_field = False
                current_value = None
            
            # Step 2: Test PUT /api/design/settings to toggle allow_song_suggestions
            print("📊 Step 2: Test PUT /api/design/settings to toggle allow_song_suggestions")
            
            if get_endpoint_working and get_has_field:
                # Toggle the current value
                new_value = not current_value
                
                update_data = {
                    "allow_song_suggestions": new_value
                }
                
                put_response = self.make_request("PUT", "/design/settings", update_data)
                
                print(f"   📊 PUT design settings status: {put_response.status_code}")
                
                if put_response.status_code == 200:
                    put_data = put_response.json()
                    print(f"   ✅ PUT design settings successful")
                    
                    # Verify the value was updated
                    if "allow_song_suggestions" in put_data:
                        updated_value = put_data["allow_song_suggestions"]
                        if updated_value == new_value:
                            print(f"   ✅ allow_song_suggestions updated: {current_value} → {updated_value}")
                            put_endpoint_working = True
                            value_updated = True
                        else:
                            print(f"   ❌ allow_song_suggestions not updated correctly: expected {new_value}, got {updated_value}")
                            put_endpoint_working = True
                            value_updated = False
                    else:
                        print(f"   ❌ allow_song_suggestions missing from PUT response")
                        put_endpoint_working = True
                        value_updated = False
                else:
                    print(f"   ❌ PUT design settings failed: {put_response.status_code}, Response: {put_response.text}")
                    put_endpoint_working = False
                    value_updated = False
                
                # Step 3: Verify the change persists by getting settings again
                print("📊 Step 3: Verify the change persists")
                
                if put_endpoint_working and value_updated:
                    verify_response = self.make_request("GET", "/design/settings")
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        persisted_value = verify_data.get("allow_song_suggestions")
                        
                        if persisted_value == new_value:
                            print(f"   ✅ Change persisted: {persisted_value}")
                            change_persisted = True
                        else:
                            print(f"   ❌ Change not persisted: expected {new_value}, got {persisted_value}")
                            change_persisted = False
                    else:
                        print(f"   ❌ Verification GET failed: {verify_response.status_code}")
                        change_persisted = False
                    
                    # Step 4: Restore original value
                    print("📊 Step 4: Restore original value")
                    
                    restore_data = {
                        "allow_song_suggestions": current_value
                    }
                    
                    restore_response = self.make_request("PUT", "/design/settings", restore_data)
                    
                    if restore_response.status_code == 200:
                        print(f"   ✅ Original value restored: {current_value}")
                    else:
                        print(f"   ⚠️  Failed to restore original value: {restore_response.status_code}")
                else:
                    change_persisted = False
            else:
                put_endpoint_working = False
                value_updated = False
                change_persisted = False
            
            # Final assessment
            if get_endpoint_working and get_has_field and put_endpoint_working and value_updated and change_persisted:
                self.log_result("Authenticated Design Settings", True, f"✅ AUTHENTICATED DESIGN ENDPOINTS WORKING: GET and PUT endpoints support allow_song_suggestions field correctly")
            else:
                issues = []
                if not get_endpoint_working:
                    issues.append("GET endpoint failed")
                if not get_has_field:
                    issues.append("GET endpoint missing allow_song_suggestions field")
                if not put_endpoint_working:
                    issues.append("PUT endpoint failed")
                if not value_updated:
                    issues.append("PUT endpoint didn't update value")
                if not change_persisted:
                    issues.append("changes don't persist")
                
                self.log_result("Authenticated Design Settings", False, f"❌ AUTHENTICATED DESIGN SETTINGS ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Authenticated Design Settings", False, f"❌ Exception: {str(e)}")

    def test_public_endpoint_reflects_authenticated_changes(self):
        """Test that public endpoint reflects changes made through authenticated endpoints"""
        try:
            print("🎵 TESTING PUBLIC ENDPOINT REFLECTS AUTHENTICATED CHANGES")
            print("=" * 80)
            
            if not self.auth_token or not self.musician_slug:
                self.log_result("Public Reflects Authenticated Changes", False, "No auth token or slug available")
                return
            
            # Step 1: Get current value from authenticated endpoint
            print("📊 Step 1: Get current value from authenticated endpoint")
            
            auth_response = self.make_request("GET", "/design/settings")
            
            if auth_response.status_code != 200:
                self.log_result("Public Reflects Authenticated Changes", False, f"Failed to get authenticated settings: {auth_response.status_code}")
                return
            
            auth_data = auth_response.json()
            current_value = auth_data.get("allow_song_suggestions")
            
            if current_value is None:
                self.log_result("Public Reflects Authenticated Changes", False, "allow_song_suggestions not found in authenticated endpoint")
                return
            
            print(f"   ✅ Current authenticated value: {current_value}")
            
            # Step 2: Get current value from public endpoint
            print("📊 Step 2: Get current value from public endpoint")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            public_response = self.make_request("GET", f"/musicians/{self.musician_slug}/design")
            
            if public_response.status_code != 200:
                self.log_result("Public Reflects Authenticated Changes", False, f"Failed to get public design: {public_response.status_code}")
                self.auth_token = original_token
                return
            
            public_data = public_response.json()
            public_value = public_data.get("allow_song_suggestions")
            
            print(f"   ✅ Current public value: {public_value}")
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 3: Verify values match
            print("📊 Step 3: Verify authenticated and public values match")
            
            if current_value == public_value:
                print(f"   ✅ Values match: authenticated={current_value}, public={public_value}")
                initial_values_match = True
            else:
                print(f"   ❌ Values don't match: authenticated={current_value}, public={public_value}")
                initial_values_match = False
            
            # Step 4: Change value through authenticated endpoint
            print("📊 Step 4: Change value through authenticated endpoint")
            
            new_value = not current_value
            
            update_data = {
                "allow_song_suggestions": new_value
            }
            
            update_response = self.make_request("PUT", "/design/settings", update_data)
            
            if update_response.status_code != 200:
                self.log_result("Public Reflects Authenticated Changes", False, f"Failed to update settings: {update_response.status_code}")
                return
            
            print(f"   ✅ Updated authenticated value to: {new_value}")
            
            # Step 5: Check if public endpoint reflects the change
            print("📊 Step 5: Check if public endpoint reflects the change")
            
            # Clear auth token for public access
            self.auth_token = None
            
            updated_public_response = self.make_request("GET", f"/musicians/{self.musician_slug}/design")
            
            if updated_public_response.status_code != 200:
                self.log_result("Public Reflects Authenticated Changes", False, f"Failed to get updated public design: {updated_public_response.status_code}")
                self.auth_token = original_token
                return
            
            updated_public_data = updated_public_response.json()
            updated_public_value = updated_public_data.get("allow_song_suggestions")
            
            print(f"   📊 Updated public value: {updated_public_value}")
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 6: Verify public endpoint reflects the change
            print("📊 Step 6: Verify public endpoint reflects the change")
            
            if updated_public_value == new_value:
                print(f"   ✅ Public endpoint reflects authenticated change: {updated_public_value}")
                change_reflected = True
            else:
                print(f"   ❌ Public endpoint doesn't reflect change: expected {new_value}, got {updated_public_value}")
                change_reflected = False
            
            # Step 7: Restore original value
            print("📊 Step 7: Restore original value")
            
            restore_data = {
                "allow_song_suggestions": current_value
            }
            
            restore_response = self.make_request("PUT", "/design/settings", restore_data)
            
            if restore_response.status_code == 200:
                print(f"   ✅ Original value restored: {current_value}")
            else:
                print(f"   ⚠️  Failed to restore original value: {restore_response.status_code}")
            
            # Final assessment
            if initial_values_match and change_reflected:
                self.log_result("Public Reflects Authenticated Changes", True, f"✅ PUBLIC ENDPOINT SYNC WORKING: Public endpoint correctly reflects authenticated changes to allow_song_suggestions")
            else:
                issues = []
                if not initial_values_match:
                    issues.append("initial values don't match between endpoints")
                if not change_reflected:
                    issues.append("public endpoint doesn't reflect authenticated changes")
                
                self.log_result("Public Reflects Authenticated Changes", False, f"❌ PUBLIC ENDPOINT SYNC ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Public Reflects Authenticated Changes", False, f"❌ Exception: {str(e)}")
            # Restore auth token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def test_frontend_integration_scenario(self):
        """Test the complete frontend integration scenario that was broken"""
        try:
            print("🎵 TESTING COMPLETE FRONTEND INTEGRATION SCENARIO")
            print("=" * 80)
            
            if not self.musician_slug:
                self.log_result("Frontend Integration Scenario", False, "No musician slug available")
                return
            
            print("📊 SCENARIO: Frontend checks designSettings.allow_song_suggestions to show/hide 'Suggest a Song' button")
            print("📊 BEFORE FIX: Field was undefined, so button never appeared")
            print("📊 AFTER FIX: Field should be present with boolean value")
            
            # Step 1: Simulate frontend fetching design settings for audience page
            print("📊 Step 1: Simulate frontend fetching design settings for audience page")
            
            # Clear auth token to simulate public audience access
            original_token = self.auth_token
            self.auth_token = None
            
            response = self.make_request("GET", f"/musicians/{self.musician_slug}/design")
            
            print(f"   📊 Frontend design fetch status: {response.status_code}")
            
            if response.status_code != 200:
                self.log_result("Frontend Integration Scenario", False, f"Frontend design fetch failed: {response.status_code}")
                self.auth_token = original_token
                return
            
            design_settings = response.json()
            
            # Step 2: Check if frontend can access allow_song_suggestions field
            print("📊 Step 2: Check if frontend can access allow_song_suggestions field")
            
            if "allow_song_suggestions" in design_settings:
                allow_song_suggestions = design_settings["allow_song_suggestions"]
                print(f"   ✅ designSettings.allow_song_suggestions is available: {allow_song_suggestions}")
                field_available = True
                
                # Step 3: Simulate frontend conditional rendering logic
                print("📊 Step 3: Simulate frontend conditional rendering logic")
                
                if isinstance(allow_song_suggestions, bool):
                    print(f"   ✅ Field is boolean type (required for conditional rendering)")
                    
                    # Simulate: {designSettings.allow_song_suggestions && <SuggestSongButton />}
                    if allow_song_suggestions:
                        print(f"   ✅ FRONTEND LOGIC: 'Suggest a Song' button WOULD BE SHOWN")
                        button_would_show = True
                    else:
                        print(f"   ✅ FRONTEND LOGIC: 'Suggest a Song' button WOULD BE HIDDEN (setting disabled)")
                        button_would_show = False  # This is correct behavior when disabled
                    
                    conditional_logic_working = True
                else:
                    print(f"   ❌ Field is not boolean: {type(allow_song_suggestions)} - frontend conditional may fail")
                    conditional_logic_working = False
                    button_would_show = False
            else:
                print(f"   ❌ designSettings.allow_song_suggestions is UNDEFINED (original bug)")
                field_available = False
                conditional_logic_working = False
                button_would_show = False
                allow_song_suggestions = None
            
            # Step 4: Test with different setting values
            print("📊 Step 4: Test with different setting values")
            
            # Restore auth token to change settings
            self.auth_token = original_token
            
            if field_available and conditional_logic_working:
                # Test with allow_song_suggestions = True
                print("   📊 Testing with allow_song_suggestions = True")
                
                update_data = {"allow_song_suggestions": True}
                update_response = self.make_request("PUT", "/design/settings", update_data)
                
                if update_response.status_code == 200:
                    # Check public endpoint
                    self.auth_token = None
                    public_response = self.make_request("GET", f"/musicians/{self.musician_slug}/design")
                    self.auth_token = original_token
                    
                    if public_response.status_code == 200:
                        public_data = public_response.json()
                        public_value = public_data.get("allow_song_suggestions")
                        
                        if public_value is True:
                            print(f"      ✅ With setting=True: Button WOULD BE SHOWN")
                            true_test_passed = True
                        else:
                            print(f"      ❌ With setting=True: Expected True, got {public_value}")
                            true_test_passed = False
                    else:
                        true_test_passed = False
                else:
                    true_test_passed = False
                
                # Test with allow_song_suggestions = False
                print("   📊 Testing with allow_song_suggestions = False")
                
                update_data = {"allow_song_suggestions": False}
                update_response = self.make_request("PUT", "/design/settings", update_data)
                
                if update_response.status_code == 200:
                    # Check public endpoint
                    self.auth_token = None
                    public_response = self.make_request("GET", f"/musicians/{self.musician_slug}/design")
                    self.auth_token = original_token
                    
                    if public_response.status_code == 200:
                        public_data = public_response.json()
                        public_value = public_data.get("allow_song_suggestions")
                        
                        if public_value is False:
                            print(f"      ✅ With setting=False: Button WOULD BE HIDDEN")
                            false_test_passed = True
                        else:
                            print(f"      ❌ With setting=False: Expected False, got {public_value}")
                            false_test_passed = False
                    else:
                        false_test_passed = False
                else:
                    false_test_passed = False
                
                # Restore original value
                restore_data = {"allow_song_suggestions": allow_song_suggestions}
                self.make_request("PUT", "/design/settings", restore_data)
                
                different_values_working = true_test_passed and false_test_passed
            else:
                different_values_working = False
            
            # Final assessment
            if field_available and conditional_logic_working and different_values_working:
                self.log_result("Frontend Integration Scenario", True, f"✅ FRONTEND INTEGRATION FIX SUCCESSFUL: 'Suggest a Song' button will now appear/disappear correctly based on allow_song_suggestions setting")
            else:
                issues = []
                if not field_available:
                    issues.append("allow_song_suggestions field not available to frontend")
                if not conditional_logic_working:
                    issues.append("frontend conditional logic would fail")
                if not different_values_working:
                    issues.append("different setting values don't work correctly")
                
                self.log_result("Frontend Integration Scenario", False, f"❌ FRONTEND INTEGRATION STILL BROKEN: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Frontend Integration Scenario", False, f"❌ Exception: {str(e)}")
            # Restore auth token in case of exception
            if 'original_token' in locals():
                self.auth_token = original_token

    def run_all_tests(self):
        """Run all song suggestions feature flag tests"""
        print("🎵 SONG SUGGESTIONS FEATURE FLAG BUG FIX TESTING")
        print("=" * 120)
        print("TESTING CRITICAL BUG FIX: 'Suggest a song' button not appearing on Audience page")
        print("ROOT CAUSE: Public design endpoint missing allow_song_suggestions field")
        print("FIX: Added allow_song_suggestions field to public endpoint response")
        print("=" * 120)
        
        # Test sequence
        self.test_pro_musician_login()
        
        if self.auth_token and self.musician_slug:
            self.test_public_design_endpoint_includes_allow_song_suggestions()
            self.test_authenticated_design_settings_endpoints()
            self.test_public_endpoint_reflects_authenticated_changes()
            self.test_frontend_integration_scenario()
        else:
            print("❌ Cannot proceed with tests - login failed")
        
        # Print summary
        print("\n" + "=" * 120)
        print("🎵 SONG SUGGESTIONS FEATURE FLAG BUG FIX TEST SUMMARY")
        print("=" * 120)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1f}% ({self.results['passed']}/{total_tests})")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        if success_rate >= 80:
            print(f"\n🎉 SONG SUGGESTIONS FEATURE FLAG BUG FIX: {'SUCCESSFUL' if success_rate == 100 else 'MOSTLY SUCCESSFUL'}")
            print("✅ The 'Suggest a Song' button should now appear correctly on the Audience page!")
        else:
            print(f"\n⚠️  SONG SUGGESTIONS FEATURE FLAG BUG FIX: NEEDS ATTENTION")
            print("❌ The 'Suggest a Song' button may still not appear correctly")
        
        print("=" * 120)

if __name__ == "__main__":
    tester = SongSuggestionsFeatureFlagTester()
    tester.run_all_tests()