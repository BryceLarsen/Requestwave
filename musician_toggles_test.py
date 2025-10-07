#!/usr/bin/env python3
"""
COMPREHENSIVE TESTING FOR MUSICIAN CONTROL TOGGLES

Testing the new musician control toggles backend functionality for RequestWave:

CRITICAL TEST AREAS:
1. Profile Update Testing - PUT /api/profile endpoint with tips_enabled and requests_enabled fields
2. Musician Profile Retrieval - GET /api/profile and GET /api/musicians/{slug} endpoints returning these fields  
3. Field Validation - boolean fields accepting true/false values and handling null/undefined gracefully
4. Audience Endpoint - GET /api/musicians/{slug} includes fields for audience UI to respect settings
5. Integration Testing - end-to-end testing of toggle settings persistence and retrieval

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: Complete musician control toggles system functional for frontend toggles implementation.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://request-error-fix.preview.emergentagent.com/api"
TEST_MUSICIAN = {
    "name": "Toggle Test Musician",
    "email": "toggle.test@requestwave.com", 
    "password": "SecurePassword123!"
}

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class MusicianTogglesTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.test_song_id = None
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

    def test_profile_update_toggles(self):
        """Test that PUT /api/profile endpoint correctly handles and persists tips_enabled and requests_enabled fields"""
        try:
            print("🎵 PRIORITY 1: Testing Profile Update with Toggle Fields")
            print("=" * 80)
            
            # Step 1: Login with Pro account
            print("📊 Step 1: Login with Pro account")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Profile Update Toggles - Pro Login", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            self.musician_id = login_data_response["musician"]["id"]
            self.musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            print(f"   📊 Musician slug: {self.musician_slug}")
            
            # Step 2: Get current profile to check toggle field structure
            print("📊 Step 2: Get current profile structure")
            profile_response = self.make_request("GET", "/profile")
            
            if profile_response.status_code != 200:
                self.log_result("Profile Update Toggles - Get Profile", False, f"Failed to get profile: {profile_response.status_code}")
                return
            
            profile_data = profile_response.json()
            print(f"   📊 Profile fields: {list(profile_data.keys())}")
            
            # Step 3: Check if toggle fields are present with default values
            print("📊 Step 3: Check toggle field presence and defaults")
            has_tips_enabled = "tips_enabled" in profile_data
            has_requests_enabled = "requests_enabled" in profile_data
            
            if has_tips_enabled:
                tips_default = profile_data.get('tips_enabled')
                print(f"   ✅ tips_enabled field present with default: {tips_default}")
                tips_enabled_present = True
            else:
                print(f"   ❌ tips_enabled field missing")
                tips_enabled_present = False
                tips_default = None
            
            if has_requests_enabled:
                requests_default = profile_data.get('requests_enabled')
                print(f"   ✅ requests_enabled field present with default: {requests_default}")
                requests_enabled_present = True
            else:
                print(f"   ❌ requests_enabled field missing")
                requests_enabled_present = False
                requests_default = None
            
            # Step 4: Test individual field updates
            print("📊 Step 4: Test individual toggle field updates")
            
            # Update only tips_enabled to false
            tips_update = {"tips_enabled": False}
            tips_response = self.make_request("PUT", "/profile", tips_update)
            
            if tips_response.status_code == 200:
                tips_profile = tips_response.json()
                if tips_profile.get('tips_enabled') == False:
                    print(f"   ✅ tips_enabled individual update to False works")
                    tips_individual_works = True
                else:
                    print(f"   ❌ tips_enabled individual update failed: got {tips_profile.get('tips_enabled')}")
                    tips_individual_works = False
            else:
                print(f"   ❌ tips_enabled update failed: {tips_response.status_code}")
                tips_individual_works = False
            
            # Update only requests_enabled to false
            requests_update = {"requests_enabled": False}
            requests_response = self.make_request("PUT", "/profile", requests_update)
            
            if requests_response.status_code == 200:
                requests_profile = requests_response.json()
                if requests_profile.get('requests_enabled') == False:
                    print(f"   ✅ requests_enabled individual update to False works")
                    requests_individual_works = True
                else:
                    print(f"   ❌ requests_enabled individual update failed: got {requests_profile.get('requests_enabled')}")
                    requests_individual_works = False
            else:
                print(f"   ❌ requests_enabled update failed: {requests_response.status_code}")
                requests_individual_works = False
            
            # Step 5: Test combined field updates
            print("📊 Step 5: Test combined toggle field updates")
            
            combined_update = {
                "tips_enabled": True,
                "requests_enabled": True
            }
            
            combined_response = self.make_request("PUT", "/profile", combined_update)
            
            if combined_response.status_code == 200:
                combined_profile = combined_response.json()
                tips_combined = combined_profile.get('tips_enabled') == True
                requests_combined = combined_profile.get('requests_enabled') == True
                
                if tips_combined and requests_combined:
                    print(f"   ✅ Combined toggle update to True works")
                    combined_update_works = True
                else:
                    print(f"   ❌ Combined toggle update failed: tips={combined_profile.get('tips_enabled')}, requests={combined_profile.get('requests_enabled')}")
                    combined_update_works = False
            else:
                print(f"   ❌ Combined toggle update failed: {combined_response.status_code}")
                combined_update_works = False
            
            # Step 6: Test mixed boolean values
            print("📊 Step 6: Test mixed boolean values")
            
            mixed_update = {
                "tips_enabled": False,
                "requests_enabled": True
            }
            
            mixed_response = self.make_request("PUT", "/profile", mixed_update)
            
            if mixed_response.status_code == 200:
                mixed_profile = mixed_response.json()
                tips_mixed = mixed_profile.get('tips_enabled') == False
                requests_mixed = mixed_profile.get('requests_enabled') == True
                
                if tips_mixed and requests_mixed:
                    print(f"   ✅ Mixed boolean values work (tips=False, requests=True)")
                    mixed_values_work = True
                else:
                    print(f"   ❌ Mixed boolean values failed: tips={mixed_profile.get('tips_enabled')}, requests={mixed_profile.get('requests_enabled')}")
                    mixed_values_work = False
            else:
                print(f"   ❌ Mixed boolean values update failed: {mixed_response.status_code}")
                mixed_values_work = False
            
            # Final assessment
            if tips_enabled_present and requests_enabled_present and tips_individual_works and requests_individual_works and combined_update_works and mixed_values_work:
                self.log_result("Profile Update Toggles", True, "✅ PROFILE UPDATE TOGGLES WORKING: Both tips_enabled and requests_enabled fields correctly handled in PUT /api/profile")
            else:
                issues = []
                if not tips_enabled_present:
                    issues.append("tips_enabled field missing")
                if not requests_enabled_present:
                    issues.append("requests_enabled field missing")
                if not tips_individual_works:
                    issues.append("tips_enabled individual update not working")
                if not requests_individual_works:
                    issues.append("requests_enabled individual update not working")
                if not combined_update_works:
                    issues.append("combined toggle update not working")
                if not mixed_values_work:
                    issues.append("mixed boolean values not working")
                
                self.log_result("Profile Update Toggles", False, f"❌ PROFILE UPDATE TOGGLES ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Profile Update Toggles", False, f"❌ Exception: {str(e)}")

    def test_profile_retrieval_toggles(self):
        """Test that GET /api/profile returns tips_enabled and requests_enabled fields with correct values"""
        try:
            print("🎵 PRIORITY 2: Testing Profile Retrieval with Toggle Fields")
            print("=" * 80)
            
            # Step 1: Ensure we're logged in (from previous test)
            if not self.auth_token:
                print("📊 Step 1: Login with Pro account")
                login_data = {
                    "email": PRO_MUSICIAN["email"],
                    "password": PRO_MUSICIAN["password"]
                }
                
                login_response = self.make_request("POST", "/auth/login", login_data)
                
                if login_response.status_code != 200:
                    self.log_result("Profile Retrieval Toggles - Pro Login", False, f"Failed to login: {login_response.status_code}")
                    return
                
                login_data_response = login_response.json()
                self.auth_token = login_data_response["token"]
                self.musician_slug = login_data_response["musician"]["slug"]
                
                print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            
            # Step 2: Set known toggle values
            print("📊 Step 2: Set known toggle values for testing")
            
            known_values = {
                "tips_enabled": True,
                "requests_enabled": False
            }
            
            set_response = self.make_request("PUT", "/profile", known_values)
            
            if set_response.status_code == 200:
                print(f"   ✅ Set known values: tips_enabled=True, requests_enabled=False")
                values_set = True
            else:
                print(f"   ❌ Failed to set known values: {set_response.status_code}")
                values_set = False
            
            # Step 3: Test GET /api/profile returns correct toggle values
            print("📊 Step 3: Test GET /api/profile returns correct toggle values")
            
            get_response = self.make_request("GET", "/profile")
            
            if get_response.status_code == 200:
                get_profile = get_response.json()
                
                tips_retrieved = get_profile.get('tips_enabled')
                requests_retrieved = get_profile.get('requests_enabled')
                
                print(f"   📊 Retrieved tips_enabled: {tips_retrieved}")
                print(f"   📊 Retrieved requests_enabled: {requests_retrieved}")
                
                tips_correct = tips_retrieved == True
                requests_correct = requests_retrieved == False
                
                if tips_correct and requests_correct:
                    print(f"   ✅ GET /api/profile returns correct toggle values")
                    get_profile_works = True
                else:
                    print(f"   ❌ GET /api/profile returns incorrect toggle values")
                    get_profile_works = False
            else:
                print(f"   ❌ GET /api/profile failed: {get_response.status_code}")
                get_profile_works = False
            
            # Step 4: Test different combinations of toggle values
            print("📊 Step 4: Test different combinations of toggle values")
            
            test_combinations = [
                {"tips_enabled": False, "requests_enabled": False},
                {"tips_enabled": True, "requests_enabled": True},
                {"tips_enabled": False, "requests_enabled": True}
            ]
            
            combination_results = []
            
            for i, combo in enumerate(test_combinations):
                print(f"   📊 Testing combination {i+1}: {combo}")
                
                # Set the combination
                set_combo_response = self.make_request("PUT", "/profile", combo)
                
                if set_combo_response.status_code == 200:
                    # Retrieve and verify
                    get_combo_response = self.make_request("GET", "/profile")
                    
                    if get_combo_response.status_code == 200:
                        combo_profile = get_combo_response.json()
                        
                        tips_match = combo_profile.get('tips_enabled') == combo['tips_enabled']
                        requests_match = combo_profile.get('requests_enabled') == combo['requests_enabled']
                        
                        if tips_match and requests_match:
                            print(f"     ✅ Combination {i+1} works correctly")
                            combination_results.append(True)
                        else:
                            print(f"     ❌ Combination {i+1} failed: got tips={combo_profile.get('tips_enabled')}, requests={combo_profile.get('requests_enabled')}")
                            combination_results.append(False)
                    else:
                        print(f"     ❌ Combination {i+1} GET failed: {get_combo_response.status_code}")
                        combination_results.append(False)
                else:
                    print(f"     ❌ Combination {i+1} SET failed: {set_combo_response.status_code}")
                    combination_results.append(False)
            
            all_combinations_work = all(combination_results)
            
            # Step 5: Test field persistence across sessions
            print("📊 Step 5: Test field persistence across sessions")
            
            # Set specific values
            persistence_values = {
                "tips_enabled": True,
                "requests_enabled": False
            }
            
            persist_set_response = self.make_request("PUT", "/profile", persistence_values)
            
            if persist_set_response.status_code == 200:
                # Simulate new session by clearing and re-setting auth token
                old_token = self.auth_token
                self.auth_token = None
                
                # Re-login
                login_data = {
                    "email": PRO_MUSICIAN["email"],
                    "password": PRO_MUSICIAN["password"]
                }
                
                relogin_response = self.make_request("POST", "/auth/login", login_data)
                
                if relogin_response.status_code == 200:
                    relogin_data = relogin_response.json()
                    self.auth_token = relogin_data["token"]
                    
                    # Check if values persisted
                    persist_get_response = self.make_request("GET", "/profile")
                    
                    if persist_get_response.status_code == 200:
                        persist_profile = persist_get_response.json()
                        
                        tips_persisted = persist_profile.get('tips_enabled') == True
                        requests_persisted = persist_profile.get('requests_enabled') == False
                        
                        if tips_persisted and requests_persisted:
                            print(f"   ✅ Toggle values persist across sessions")
                            persistence_works = True
                        else:
                            print(f"   ❌ Toggle values don't persist: tips={persist_profile.get('tips_enabled')}, requests={persist_profile.get('requests_enabled')}")
                            persistence_works = False
                    else:
                        print(f"   ❌ Failed to get profile after re-login: {persist_get_response.status_code}")
                        persistence_works = False
                else:
                    print(f"   ❌ Failed to re-login: {relogin_response.status_code}")
                    persistence_works = False
            else:
                print(f"   ❌ Failed to set persistence values: {persist_set_response.status_code}")
                persistence_works = False
            
            # Final assessment
            if values_set and get_profile_works and all_combinations_work and persistence_works:
                self.log_result("Profile Retrieval Toggles", True, "✅ PROFILE RETRIEVAL TOGGLES WORKING: GET /api/profile correctly returns tips_enabled and requests_enabled with proper persistence")
            else:
                issues = []
                if not values_set:
                    issues.append("failed to set known values")
                if not get_profile_works:
                    issues.append("GET /api/profile doesn't return correct values")
                if not all_combinations_work:
                    issues.append("not all toggle combinations work")
                if not persistence_works:
                    issues.append("toggle values don't persist across sessions")
                
                self.log_result("Profile Retrieval Toggles", False, f"❌ PROFILE RETRIEVAL TOGGLES ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Profile Retrieval Toggles", False, f"❌ Exception: {str(e)}")

    def test_field_validation(self):
        """Test that boolean fields accept true/false values and handle null/undefined gracefully"""
        try:
            print("🎵 PRIORITY 3: Testing Toggle Field Validation")
            print("=" * 80)
            
            # Step 1: Ensure we're logged in
            if not self.auth_token:
                print("📊 Step 1: Login with Pro account")
                login_data = {
                    "email": PRO_MUSICIAN["email"],
                    "password": PRO_MUSICIAN["password"]
                }
                
                login_response = self.make_request("POST", "/auth/login", login_data)
                
                if login_response.status_code != 200:
                    self.log_result("Field Validation - Pro Login", False, f"Failed to login: {login_response.status_code}")
                    return
                
                login_data_response = login_response.json()
                self.auth_token = login_data_response["token"]
                
                print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            
            # Step 2: Test explicit boolean values
            print("📊 Step 2: Test explicit boolean values")
            
            boolean_tests = [
                {"tips_enabled": True, "requests_enabled": True},
                {"tips_enabled": False, "requests_enabled": False},
                {"tips_enabled": True, "requests_enabled": False},
                {"tips_enabled": False, "requests_enabled": True}
            ]
            
            boolean_results = []
            
            for i, test_data in enumerate(boolean_tests):
                print(f"   📊 Testing boolean combination {i+1}: {test_data}")
                
                bool_response = self.make_request("PUT", "/profile", test_data)
                
                if bool_response.status_code == 200:
                    bool_profile = bool_response.json()
                    
                    tips_match = bool_profile.get('tips_enabled') == test_data['tips_enabled']
                    requests_match = bool_profile.get('requests_enabled') == test_data['requests_enabled']
                    
                    if tips_match and requests_match:
                        print(f"     ✅ Boolean combination {i+1} accepted correctly")
                        boolean_results.append(True)
                    else:
                        print(f"     ❌ Boolean combination {i+1} not handled correctly")
                        boolean_results.append(False)
                else:
                    print(f"     ❌ Boolean combination {i+1} rejected: {bool_response.status_code}")
                    boolean_results.append(False)
            
            explicit_booleans_work = all(boolean_results)
            
            # Step 3: Test null/undefined handling (omitted fields)
            print("📊 Step 3: Test null/undefined handling (omitted fields)")
            
            # First set known values
            known_values = {
                "tips_enabled": True,
                "requests_enabled": False
            }
            
            set_known_response = self.make_request("PUT", "/profile", known_values)
            
            if set_known_response.status_code == 200:
                print(f"   ✅ Set known values: tips_enabled=True, requests_enabled=False")
                
                # Now update profile without toggle fields
                other_update = {
                    "name": "Updated Test Name"
                    # Omit tips_enabled and requests_enabled
                }
                
                omit_response = self.make_request("PUT", "/profile", other_update)
                
                if omit_response.status_code == 200:
                    omit_profile = omit_response.json()
                    
                    # Check if toggle values were preserved
                    tips_preserved = omit_profile.get('tips_enabled') == True
                    requests_preserved = omit_profile.get('requests_enabled') == False
                    
                    if tips_preserved and requests_preserved:
                        print(f"   ✅ Omitted toggle fields preserved existing values")
                        null_handling_works = True
                    else:
                        print(f"   ❌ Omitted toggle fields not preserved: tips={omit_profile.get('tips_enabled')}, requests={omit_profile.get('requests_enabled')}")
                        null_handling_works = False
                else:
                    print(f"   ❌ Profile update with omitted fields failed: {omit_response.status_code}")
                    null_handling_works = False
            else:
                print(f"   ❌ Failed to set known values: {set_known_response.status_code}")
                null_handling_works = False
            
            # Step 4: Test explicit null values (if API accepts them)
            print("📊 Step 4: Test explicit null values")
            
            # Note: JSON null values might be handled differently than omitted fields
            null_test_data = {
                "tips_enabled": None,
                "requests_enabled": None
            }
            
            null_response = self.make_request("PUT", "/profile", null_test_data)
            
            print(f"   📊 Null values response status: {null_response.status_code}")
            
            if null_response.status_code == 200:
                null_profile = null_response.json()
                
                # Check how null values are handled
                tips_null_handled = 'tips_enabled' in null_profile
                requests_null_handled = 'requests_enabled' in null_profile
                
                if tips_null_handled and requests_null_handled:
                    print(f"   ✅ Explicit null values handled gracefully")
                    print(f"     📊 tips_enabled after null: {null_profile.get('tips_enabled')}")
                    print(f"     📊 requests_enabled after null: {null_profile.get('requests_enabled')}")
                    explicit_null_works = True
                else:
                    print(f"   ❌ Explicit null values not handled correctly")
                    explicit_null_works = False
            elif null_response.status_code == 422:
                print(f"   ⚠️  Explicit null values rejected with validation error (acceptable)")
                explicit_null_works = True  # Rejection is acceptable behavior
            else:
                print(f"   ❌ Explicit null values caused unexpected error: {null_response.status_code}")
                explicit_null_works = False
            
            # Step 5: Test invalid values
            print("📊 Step 5: Test invalid values")
            
            invalid_tests = [
                {"tips_enabled": "true", "requests_enabled": False},  # String instead of boolean
                {"tips_enabled": 1, "requests_enabled": 0},          # Numbers instead of booleans
                {"tips_enabled": True, "requests_enabled": "invalid"} # Invalid string
            ]
            
            invalid_results = []
            
            for i, invalid_data in enumerate(invalid_tests):
                print(f"   📊 Testing invalid data {i+1}: {invalid_data}")
                
                invalid_response = self.make_request("PUT", "/profile", invalid_data)
                
                # Invalid data should be rejected (400/422) or converted gracefully
                if invalid_response.status_code in [400, 422]:
                    print(f"     ✅ Invalid data {i+1} properly rejected")
                    invalid_results.append(True)
                elif invalid_response.status_code == 200:
                    # Check if values were converted gracefully
                    invalid_profile = invalid_response.json()
                    print(f"     ⚠️  Invalid data {i+1} accepted and converted: tips={invalid_profile.get('tips_enabled')}, requests={invalid_profile.get('requests_enabled')}")
                    invalid_results.append(True)  # Graceful conversion is acceptable
                else:
                    print(f"     ❌ Invalid data {i+1} caused unexpected error: {invalid_response.status_code}")
                    invalid_results.append(False)
            
            invalid_handling_works = all(invalid_results)
            
            # Final assessment
            if explicit_booleans_work and null_handling_works and explicit_null_works and invalid_handling_works:
                self.log_result("Field Validation", True, "✅ FIELD VALIDATION WORKING: Boolean fields accept true/false values and handle null/undefined gracefully")
            else:
                issues = []
                if not explicit_booleans_work:
                    issues.append("explicit boolean values not working")
                if not null_handling_works:
                    issues.append("null/undefined handling not working")
                if not explicit_null_works:
                    issues.append("explicit null values not handled")
                if not invalid_handling_works:
                    issues.append("invalid values not handled properly")
                
                self.log_result("Field Validation", False, f"❌ FIELD VALIDATION ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Field Validation", False, f"❌ Exception: {str(e)}")

    def test_audience_endpoint_toggles(self):
        """Test that GET /api/musicians/{slug} includes tips_enabled and requests_enabled for audience UI"""
        try:
            print("🎵 PRIORITY 4: Testing Audience Endpoint Toggle Fields")
            print("=" * 80)
            
            # Step 1: Ensure we're logged in and set up toggle values
            if not self.auth_token:
                print("📊 Step 1: Login with Pro account")
                login_data = {
                    "email": PRO_MUSICIAN["email"],
                    "password": PRO_MUSICIAN["password"]
                }
                
                login_response = self.make_request("POST", "/auth/login", login_data)
                
                if login_response.status_code != 200:
                    self.log_result("Audience Endpoint Toggles - Pro Login", False, f"Failed to login: {login_response.status_code}")
                    return
                
                login_data_response = login_response.json()
                self.auth_token = login_data_response["token"]
                self.musician_slug = login_data_response["musician"]["slug"]
                
                print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            
            # Step 2: Set specific toggle values for testing
            print("📊 Step 2: Set specific toggle values for audience testing")
            
            audience_test_values = {
                "tips_enabled": True,
                "requests_enabled": False
            }
            
            set_audience_response = self.make_request("PUT", "/profile", audience_test_values)
            
            if set_audience_response.status_code == 200:
                print(f"   ✅ Set audience test values: tips_enabled=True, requests_enabled=False")
                values_set_for_audience = True
            else:
                print(f"   ❌ Failed to set audience test values: {set_audience_response.status_code}")
                values_set_for_audience = False
            
            # Step 3: Test public audience endpoint (no authentication)
            print("📊 Step 3: Test public audience endpoint access")
            
            # Clear auth token for public access
            original_token = self.auth_token
            self.auth_token = None
            
            audience_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if audience_response.status_code == 200:
                audience_data = audience_response.json()
                print(f"   ✅ Public audience endpoint accessible")
                print(f"   📊 Audience endpoint fields: {list(audience_data.keys())}")
                
                # Check if toggle fields are included
                has_tips_enabled = "tips_enabled" in audience_data
                has_requests_enabled = "requests_enabled" in audience_data
                
                if has_tips_enabled:
                    audience_tips = audience_data.get('tips_enabled')
                    print(f"   ✅ tips_enabled included in audience data: {audience_tips}")
                    tips_in_audience = True
                else:
                    print(f"   ❌ tips_enabled missing from audience data")
                    tips_in_audience = False
                    audience_tips = None
                
                if has_requests_enabled:
                    audience_requests = audience_data.get('requests_enabled')
                    print(f"   ✅ requests_enabled included in audience data: {audience_requests}")
                    requests_in_audience = True
                else:
                    print(f"   ❌ requests_enabled missing from audience data")
                    requests_in_audience = False
                    audience_requests = None
                
                # Verify values match what we set
                tips_value_correct = audience_tips == True
                requests_value_correct = audience_requests == False
                
                if tips_value_correct:
                    print(f"   ✅ tips_enabled value correct in audience data")
                else:
                    print(f"   ❌ tips_enabled value incorrect: expected True, got {audience_tips}")
                
                if requests_value_correct:
                    print(f"   ✅ requests_enabled value correct in audience data")
                else:
                    print(f"   ❌ requests_enabled value incorrect: expected False, got {audience_requests}")
                
                audience_endpoint_works = True
            else:
                print(f"   ❌ Public audience endpoint failed: {audience_response.status_code}")
                audience_endpoint_works = False
                tips_in_audience = False
                requests_in_audience = False
                tips_value_correct = False
                requests_value_correct = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Step 4: Test different toggle combinations in audience endpoint
            print("📊 Step 4: Test different toggle combinations in audience endpoint")
            
            test_combinations = [
                {"tips_enabled": False, "requests_enabled": False},
                {"tips_enabled": True, "requests_enabled": True},
                {"tips_enabled": False, "requests_enabled": True}
            ]
            
            combination_results = []
            
            for i, combo in enumerate(test_combinations):
                print(f"   📊 Testing audience combination {i+1}: {combo}")
                
                # Set the combination (with auth)
                set_combo_response = self.make_request("PUT", "/profile", combo)
                
                if set_combo_response.status_code == 200:
                    # Test audience endpoint (without auth)
                    self.auth_token = None
                    
                    combo_audience_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
                    
                    if combo_audience_response.status_code == 200:
                        combo_audience_data = combo_audience_response.json()
                        
                        tips_match = combo_audience_data.get('tips_enabled') == combo['tips_enabled']
                        requests_match = combo_audience_data.get('requests_enabled') == combo['requests_enabled']
                        
                        if tips_match and requests_match:
                            print(f"     ✅ Audience combination {i+1} works correctly")
                            combination_results.append(True)
                        else:
                            print(f"     ❌ Audience combination {i+1} failed: got tips={combo_audience_data.get('tips_enabled')}, requests={combo_audience_data.get('requests_enabled')}")
                            combination_results.append(False)
                    else:
                        print(f"     ❌ Audience combination {i+1} GET failed: {combo_audience_response.status_code}")
                        combination_results.append(False)
                    
                    # Restore auth token
                    self.auth_token = original_token
                else:
                    print(f"     ❌ Audience combination {i+1} SET failed: {set_combo_response.status_code}")
                    combination_results.append(False)
            
            all_audience_combinations_work = all(combination_results)
            
            # Step 5: Verify other essential audience fields are still present
            print("📊 Step 5: Verify other essential audience fields are present")
            
            # Clear auth for final public check
            self.auth_token = None
            
            final_audience_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            if final_audience_response.status_code == 200:
                final_audience_data = final_audience_response.json()
                
                essential_fields = ['id', 'name', 'slug']
                payment_fields = ['paypal_username', 'venmo_username']
                
                essential_present = all(field in final_audience_data for field in essential_fields)
                payment_present = any(field in final_audience_data for field in payment_fields)
                
                if essential_present:
                    print(f"   ✅ Essential audience fields present: {essential_fields}")
                else:
                    print(f"   ❌ Some essential audience fields missing")
                
                if payment_present:
                    print(f"   ✅ Payment fields present for tip functionality")
                else:
                    print(f"   ❌ Payment fields missing")
                
                other_fields_present = essential_present and payment_present
            else:
                print(f"   ❌ Final audience check failed: {final_audience_response.status_code}")
                other_fields_present = False
            
            # Restore auth token
            self.auth_token = original_token
            
            # Final assessment
            if values_set_for_audience and audience_endpoint_works and tips_in_audience and requests_in_audience and tips_value_correct and requests_value_correct and all_audience_combinations_work and other_fields_present:
                self.log_result("Audience Endpoint Toggles", True, "✅ AUDIENCE ENDPOINT TOGGLES WORKING: GET /api/musicians/{slug} includes tips_enabled and requests_enabled for audience UI")
            else:
                issues = []
                if not values_set_for_audience:
                    issues.append("failed to set test values")
                if not audience_endpoint_works:
                    issues.append("audience endpoint not accessible")
                if not tips_in_audience:
                    issues.append("tips_enabled missing from audience data")
                if not requests_in_audience:
                    issues.append("requests_enabled missing from audience data")
                if not tips_value_correct:
                    issues.append("tips_enabled value incorrect in audience data")
                if not requests_value_correct:
                    issues.append("requests_enabled value incorrect in audience data")
                if not all_audience_combinations_work:
                    issues.append("not all toggle combinations work in audience endpoint")
                if not other_fields_present:
                    issues.append("other essential audience fields missing")
                
                self.log_result("Audience Endpoint Toggles", False, f"❌ AUDIENCE ENDPOINT TOGGLES ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Audience Endpoint Toggles", False, f"❌ Exception: {str(e)}")

    def test_integration_end_to_end(self):
        """Test complete end-to-end integration of toggle settings"""
        try:
            print("🎵 PRIORITY 5: Testing End-to-End Integration")
            print("=" * 80)
            
            # Step 1: Create a new test musician for clean integration test
            print("📊 Step 1: Create new test musician for integration test")
            
            integration_musician = {
                "name": "Integration Test Musician",
                "email": "integration.test@requestwave.com",
                "password": "SecurePassword123!"
            }
            
            register_response = self.make_request("POST", "/auth/register", integration_musician)
            
            if register_response.status_code == 200:
                register_data = register_response.json()
                self.auth_token = register_data["token"]
                integration_slug = register_data["musician"]["slug"]
                print(f"   ✅ Registered integration test musician: {register_data['musician']['name']}")
            elif register_response.status_code == 400:
                # Try login if already exists
                login_data = {
                    "email": integration_musician["email"],
                    "password": integration_musician["password"]
                }
                login_response = self.make_request("POST", "/auth/login", login_data)
                if login_response.status_code == 200:
                    register_data = login_response.json()
                    self.auth_token = register_data["token"]
                    integration_slug = register_data["musician"]["slug"]
                    print(f"   ✅ Logged in existing integration test musician: {register_data['musician']['name']}")
                else:
                    self.log_result("Integration End-to-End - Authentication", False, f"Failed to login: {login_response.status_code}")
                    return
            else:
                self.log_result("Integration End-to-End - Registration", False, f"Failed to register: {register_response.status_code}")
                return
            
            # Step 2: Check default toggle values for new musician
            print("📊 Step 2: Check default toggle values for new musician")
            
            default_profile_response = self.make_request("GET", "/profile")
            
            if default_profile_response.status_code == 200:
                default_profile = default_profile_response.json()
                
                default_tips = default_profile.get('tips_enabled')
                default_requests = default_profile.get('requests_enabled')
                
                print(f"   📊 Default tips_enabled: {default_tips}")
                print(f"   📊 Default requests_enabled: {default_requests}")
                
                # Defaults should be True according to the model
                defaults_correct = default_tips == True and default_requests == True
                
                if defaults_correct:
                    print(f"   ✅ Default toggle values are correct (both True)")
                    defaults_work = True
                else:
                    print(f"   ❌ Default toggle values incorrect")
                    defaults_work = False
            else:
                print(f"   ❌ Failed to get default profile: {default_profile_response.status_code}")
                defaults_work = False
            
            # Step 3: Test complete workflow - musician disables tips
            print("📊 Step 3: Test complete workflow - musician disables tips")
            
            # Musician disables tips via profile update
            disable_tips = {"tips_enabled": False}
            
            disable_response = self.make_request("PUT", "/profile", disable_tips)
            
            if disable_response.status_code == 200:
                print(f"   ✅ Musician successfully disabled tips")
                
                # Verify in private profile
                private_check = self.make_request("GET", "/profile")
                
                if private_check.status_code == 200:
                    private_data = private_check.json()
                    private_tips_disabled = private_data.get('tips_enabled') == False
                    
                    if private_tips_disabled:
                        print(f"   ✅ Tips disabled confirmed in private profile")
                        private_update_works = True
                    else:
                        print(f"   ❌ Tips not disabled in private profile")
                        private_update_works = False
                else:
                    print(f"   ❌ Failed to check private profile: {private_check.status_code}")
                    private_update_works = False
                
                # Verify in public audience endpoint
                self.auth_token = None  # Clear auth for public access
                
                public_check = self.make_request("GET", f"/musicians/{integration_slug}")
                
                if public_check.status_code == 200:
                    public_data = public_check.json()
                    public_tips_disabled = public_data.get('tips_enabled') == False
                    
                    if public_tips_disabled:
                        print(f"   ✅ Tips disabled visible to audience")
                        public_update_works = True
                    else:
                        print(f"   ❌ Tips disabled not visible to audience: {public_data.get('tips_enabled')}")
                        public_update_works = False
                else:
                    print(f"   ❌ Failed to check public endpoint: {public_check.status_code}")
                    public_update_works = False
                
                # Restore auth
                login_data = {
                    "email": integration_musician["email"],
                    "password": integration_musician["password"]
                }
                relogin_response = self.make_request("POST", "/auth/login", login_data)
                if relogin_response.status_code == 200:
                    self.auth_token = relogin_response.json()["token"]
                
                tips_workflow_works = private_update_works and public_update_works
            else:
                print(f"   ❌ Failed to disable tips: {disable_response.status_code}")
                tips_workflow_works = False
            
            # Step 4: Test complete workflow - musician disables requests
            print("📊 Step 4: Test complete workflow - musician disables requests")
            
            # Musician disables requests via profile update
            disable_requests = {"requests_enabled": False}
            
            disable_req_response = self.make_request("PUT", "/profile", disable_requests)
            
            if disable_req_response.status_code == 200:
                print(f"   ✅ Musician successfully disabled requests")
                
                # Verify in private profile
                private_req_check = self.make_request("GET", "/profile")
                
                if private_req_check.status_code == 200:
                    private_req_data = private_req_check.json()
                    private_requests_disabled = private_req_data.get('requests_enabled') == False
                    
                    if private_requests_disabled:
                        print(f"   ✅ Requests disabled confirmed in private profile")
                        private_req_works = True
                    else:
                        print(f"   ❌ Requests not disabled in private profile")
                        private_req_works = False
                else:
                    print(f"   ❌ Failed to check private profile for requests: {private_req_check.status_code}")
                    private_req_works = False
                
                # Verify in public audience endpoint
                self.auth_token = None  # Clear auth for public access
                
                public_req_check = self.make_request("GET", f"/musicians/{integration_slug}")
                
                if public_req_check.status_code == 200:
                    public_req_data = public_req_check.json()
                    public_requests_disabled = public_req_data.get('requests_enabled') == False
                    
                    if public_requests_disabled:
                        print(f"   ✅ Requests disabled visible to audience")
                        public_req_works = True
                    else:
                        print(f"   ❌ Requests disabled not visible to audience: {public_req_data.get('requests_enabled')}")
                        public_req_works = False
                else:
                    print(f"   ❌ Failed to check public endpoint for requests: {public_req_check.status_code}")
                    public_req_works = False
                
                # Restore auth
                relogin_response = self.make_request("POST", "/auth/login", login_data)
                if relogin_response.status_code == 200:
                    self.auth_token = relogin_response.json()["token"]
                
                requests_workflow_works = private_req_works and public_req_works
            else:
                print(f"   ❌ Failed to disable requests: {disable_req_response.status_code}")
                requests_workflow_works = False
            
            # Step 5: Test re-enabling both toggles
            print("📊 Step 5: Test re-enabling both toggles")
            
            re_enable_both = {
                "tips_enabled": True,
                "requests_enabled": True
            }
            
            re_enable_response = self.make_request("PUT", "/profile", re_enable_both)
            
            if re_enable_response.status_code == 200:
                print(f"   ✅ Musician successfully re-enabled both toggles")
                
                # Verify both are enabled in public endpoint
                self.auth_token = None
                
                final_check = self.make_request("GET", f"/musicians/{integration_slug}")
                
                if final_check.status_code == 200:
                    final_data = final_check.json()
                    
                    final_tips_enabled = final_data.get('tips_enabled') == True
                    final_requests_enabled = final_data.get('requests_enabled') == True
                    
                    if final_tips_enabled and final_requests_enabled:
                        print(f"   ✅ Both toggles re-enabled and visible to audience")
                        re_enable_works = True
                    else:
                        print(f"   ❌ Re-enabling failed: tips={final_data.get('tips_enabled')}, requests={final_data.get('requests_enabled')}")
                        re_enable_works = False
                else:
                    print(f"   ❌ Failed final check: {final_check.status_code}")
                    re_enable_works = False
            else:
                print(f"   ❌ Failed to re-enable toggles: {re_enable_response.status_code}")
                re_enable_works = False
            
            # Final assessment
            if defaults_work and tips_workflow_works and requests_workflow_works and re_enable_works:
                self.log_result("Integration End-to-End", True, "✅ INTEGRATION END-TO-END WORKING: Complete toggle workflow functional from musician profile to audience visibility")
            else:
                issues = []
                if not defaults_work:
                    issues.append("default toggle values incorrect")
                if not tips_workflow_works:
                    issues.append("tips disable workflow not working")
                if not requests_workflow_works:
                    issues.append("requests disable workflow not working")
                if not re_enable_works:
                    issues.append("re-enabling toggles not working")
                
                self.log_result("Integration End-to-End", False, f"❌ INTEGRATION END-TO-END ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Integration End-to-End", False, f"❌ Exception: {str(e)}")

    def run_all_tests(self):
        """Run all musician control toggles tests in sequence"""
        print("🎵 STARTING COMPREHENSIVE MUSICIAN CONTROL TOGGLES TESTING")
        print("=" * 100)
        
        # Test 1: Profile Update Testing
        self.test_profile_update_toggles()
        
        # Test 2: Profile Retrieval Testing
        self.test_profile_retrieval_toggles()
        
        # Test 3: Field Validation Testing
        self.test_field_validation()
        
        # Test 4: Audience Endpoint Testing
        self.test_audience_endpoint_toggles()
        
        # Test 5: Integration End-to-End Testing
        self.test_integration_end_to_end()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🎵 FINAL MUSICIAN CONTROL TOGGLES TEST RESULTS")
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
        
        print("\n" + "=" * 100)

if __name__ == "__main__":
    tester = MusicianTogglesTester()
    tester.run_all_tests()