#!/usr/bin/env python3
"""
Comprehensive Freemium Model Backend Testing for RequestWave
Focus: Test all freemium model functionality as requested in the review

PRIORITY 1 - Subscription Management APIs:
- GET /api/subscription/status - Test subscription status retrieval for trial and non-trial users
- POST /api/subscription/checkout - Test Stripe checkout session creation with package_id (monthly_plan/annual_plan) and origin_url
- GET /api/subscription/checkout/status/{session_id} - Test payment status checking and subscription activation
- POST /api/subscription/cancel - Test subscription cancellation

PRIORITY 2 - Trial and Access Control:
- Test new user registration automatically starts 30-day trial (audience_link_active=true, trial_end set)
- GET /api/musicians/{slug}/access-check - Test audience link access verification
- Test access control on GET /api/musicians/{slug}/songs and POST /api/musicians/{slug}/requests (should return 402 when audience_link_active=false)

PRIORITY 3 - Account Management:
- DELETE /api/account/delete - Test account deletion with confirmation_text='DELETE'
- POST /api/webhook/stripe - Test Stripe webhook handling (may need mock webhook data)

PRIORITY 4 - Freemium Model Integration:
- Test that existing users are migrated properly (should have freemium fields added)
- Test subscription status calculation (trial vs active vs canceled vs free)
- Test payment transaction recording during checkout process
"""

import requests
import json
import os
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com/api"

# Test users for different scenarios
NEW_USER = {
    "name": "Freemium Test User",
    "email": f"freemium.test.{int(time.time())}@requestwave.com",
    "password": "FreemiumTest123!"
}

EXISTING_USER = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class FreemiumModelTester:
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
                response = requests.delete(url, headers=request_headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def test_new_user_registration_trial(self):
        """PRIORITY 2: Test new user registration automatically starts 30-day trial"""
        try:
            print("🔍 PRIORITY 2: Testing New User Registration Trial")
            print("=" * 80)
            
            # Step 1: Register new user
            print("📊 Step 1: Register new user")
            
            response = self.make_request("POST", "/auth/register", NEW_USER)
            
            if response.status_code != 200:
                self.log_result("New User Registration Trial", False, f"Registration failed: {response.status_code}, Response: {response.text}")
                return
            
            data = response.json()
            if "token" not in data or "musician" not in data:
                self.log_result("New User Registration Trial", False, f"Missing token or musician in response: {data}")
                return
            
            self.auth_token = data["token"]
            self.musician_id = data["musician"]["id"]
            self.musician_slug = data["musician"]["slug"]
            musician_data = data["musician"]
            
            print(f"   ✅ Successfully registered: {musician_data['name']}")
            print(f"   ✅ Musician ID: {self.musician_id}")
            print(f"   ✅ Musician slug: {self.musician_slug}")
            
            # Step 2: Verify trial fields are set correctly
            print("📊 Step 2: Verify trial fields are set correctly")
            
            # Check freemium model fields
            audience_link_active = musician_data.get("audience_link_active", False)
            has_had_trial = musician_data.get("has_had_trial", False)
            trial_end = musician_data.get("trial_end")
            
            print(f"   📊 audience_link_active: {audience_link_active}")
            print(f"   📊 has_had_trial: {has_had_trial}")
            print(f"   📊 trial_end: {trial_end}")
            
            # Verify trial is active
            trial_active = audience_link_active and has_had_trial and trial_end
            
            if trial_active:
                # Parse trial_end date and verify it's ~30 days from now
                if isinstance(trial_end, str):
                    try:
                        trial_end_dt = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
                        now = datetime.now(trial_end_dt.tzinfo)
                        days_remaining = (trial_end_dt - now).days
                        
                        print(f"   ✅ Trial end date: {trial_end_dt}")
                        print(f"   ✅ Days remaining: {days_remaining}")
                        
                        if 25 <= days_remaining <= 30:  # Allow some variance
                            trial_duration_correct = True
                            print(f"   ✅ Trial duration is correct (~30 days)")
                        else:
                            trial_duration_correct = False
                            print(f"   ❌ Trial duration incorrect: {days_remaining} days (expected ~30)")
                    except Exception as e:
                        trial_duration_correct = False
                        print(f"   ❌ Error parsing trial_end date: {e}")
                else:
                    trial_duration_correct = False
                    print(f"   ❌ trial_end is not a string: {type(trial_end)}")
            else:
                trial_duration_correct = False
                print(f"   ❌ Trial not properly activated")
            
            # Step 3: Test subscription status endpoint
            print("📊 Step 3: Test subscription status endpoint")
            
            status_response = self.make_request("GET", "/subscription/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 Subscription status: {json.dumps(status_data, indent=2)}")
                
                # Verify trial status
                plan = status_data.get("plan")
                trial_active_status = status_data.get("trial_active", False)
                audience_link_active_status = status_data.get("audience_link_active", False)
                
                if plan == "trial" and trial_active_status and audience_link_active_status:
                    status_endpoint_correct = True
                    print(f"   ✅ Subscription status endpoint shows correct trial status")
                else:
                    status_endpoint_correct = False
                    print(f"   ❌ Subscription status incorrect: plan={plan}, trial_active={trial_active_status}, audience_link_active={audience_link_active_status}")
            else:
                status_endpoint_correct = False
                print(f"   ❌ Subscription status endpoint failed: {status_response.status_code}, Response: {status_response.text}")
            
            # Final assessment
            if trial_active and trial_duration_correct and status_endpoint_correct:
                self.log_result("New User Registration Trial", True, f"✅ New user registration correctly starts 30-day trial with audience_link_active=true")
            else:
                issues = []
                if not trial_active:
                    issues.append("trial not activated")
                if not trial_duration_correct:
                    issues.append("trial duration incorrect")
                if not status_endpoint_correct:
                    issues.append("status endpoint incorrect")
                
                self.log_result("New User Registration Trial", False, f"❌ Trial setup issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("New User Registration Trial", False, f"❌ Exception: {str(e)}")

    def test_subscription_status_endpoint(self):
        """PRIORITY 1: Test GET /api/subscription/status for different user types"""
        try:
            print("🔍 PRIORITY 1: Testing Subscription Status Endpoint")
            print("=" * 80)
            
            # Test with existing user (Pro account)
            print("📊 Step 1: Test with existing Pro user")
            
            login_data = {
                "email": EXISTING_USER["email"],
                "password": EXISTING_USER["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Subscription Status Endpoint", False, f"Failed to login existing user: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            original_token = self.auth_token
            self.auth_token = login_data_response["token"]
            
            print(f"   ✅ Logged in as: {login_data_response['musician']['name']}")
            
            # Test subscription status
            status_response = self.make_request("GET", "/subscription/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 Existing user status: {json.dumps(status_data, indent=2)}")
                
                # Verify required fields are present
                required_fields = ["plan", "audience_link_active", "trial_active"]
                missing_fields = [field for field in required_fields if field not in status_data]
                
                if len(missing_fields) == 0:
                    existing_user_status_valid = True
                    print(f"   ✅ All required fields present: {required_fields}")
                else:
                    existing_user_status_valid = False
                    print(f"   ❌ Missing fields: {missing_fields}")
            else:
                existing_user_status_valid = False
                print(f"   ❌ Status endpoint failed for existing user: {status_response.status_code}, Response: {status_response.text}")
            
            # Test with new trial user (if we have one from previous test)
            print("📊 Step 2: Test with new trial user")
            
            if hasattr(self, 'musician_id') and self.musician_id:
                # We have a trial user from previous test
                # Switch back to trial user token
                self.auth_token = original_token  # This should be the trial user token
                
                trial_status_response = self.make_request("GET", "/subscription/status")
                
                if trial_status_response.status_code == 200:
                    trial_status_data = trial_status_response.json()
                    print(f"   📊 Trial user status: {json.dumps(trial_status_data, indent=2)}")
                    
                    # Verify trial status
                    plan = trial_status_data.get("plan")
                    trial_active = trial_status_data.get("trial_active", False)
                    audience_link_active = trial_status_data.get("audience_link_active", False)
                    
                    if plan == "trial" and trial_active and audience_link_active:
                        trial_user_status_valid = True
                        print(f"   ✅ Trial user status correct")
                    else:
                        trial_user_status_valid = False
                        print(f"   ❌ Trial user status incorrect: plan={plan}, trial_active={trial_active}, audience_link_active={audience_link_active}")
                else:
                    trial_user_status_valid = False
                    print(f"   ❌ Status endpoint failed for trial user: {trial_status_response.status_code}")
            else:
                trial_user_status_valid = True  # Skip if no trial user available
                print(f"   ℹ️  No trial user available from previous test")
            
            # Final assessment
            if existing_user_status_valid and trial_user_status_valid:
                self.log_result("Subscription Status Endpoint", True, f"✅ Subscription status endpoint works correctly for both existing and trial users")
            else:
                issues = []
                if not existing_user_status_valid:
                    issues.append("existing user status invalid")
                if not trial_user_status_valid:
                    issues.append("trial user status invalid")
                
                self.log_result("Subscription Status Endpoint", False, f"❌ Status endpoint issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Status Endpoint", False, f"❌ Exception: {str(e)}")

    def test_stripe_checkout_creation(self):
        """PRIORITY 1: Test POST /api/subscription/checkout with package_id and origin_url"""
        try:
            print("🔍 PRIORITY 1: Testing Stripe Checkout Creation")
            print("=" * 80)
            
            # Use existing user for checkout test
            print("📊 Step 1: Login with existing user")
            
            login_data = {
                "email": EXISTING_USER["email"],
                "password": EXISTING_USER["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Stripe Checkout Creation", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            
            print(f"   ✅ Logged in as: {login_data_response['musician']['name']}")
            
            # Step 2: Test monthly plan checkout
            print("📊 Step 2: Test monthly plan checkout creation")
            
            monthly_checkout_data = {
                "package_id": "monthly_plan",
                "origin_url": "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com"
            }
            
            monthly_response = self.make_request("POST", "/subscription/checkout", monthly_checkout_data)
            
            print(f"   📊 Monthly checkout status: {monthly_response.status_code}")
            print(f"   📊 Monthly checkout response: {monthly_response.text}")
            
            if monthly_response.status_code == 200:
                monthly_data = monthly_response.json()
                
                # Verify response structure
                if "url" in monthly_data and "session_id" in monthly_data:
                    monthly_checkout_valid = True
                    print(f"   ✅ Monthly checkout created successfully")
                    print(f"   ✅ Checkout URL: {monthly_data['url'][:100]}...")
                    print(f"   ✅ Session ID: {monthly_data['session_id']}")
                    
                    # Verify URL is a Stripe checkout URL
                    if "checkout.stripe.com" in monthly_data['url']:
                        stripe_url_valid = True
                        print(f"   ✅ Valid Stripe checkout URL")
                    else:
                        stripe_url_valid = False
                        print(f"   ❌ Invalid checkout URL format")
                else:
                    monthly_checkout_valid = False
                    stripe_url_valid = False
                    print(f"   ❌ Missing url or session_id in response: {monthly_data}")
            else:
                monthly_checkout_valid = False
                stripe_url_valid = False
                print(f"   ❌ Monthly checkout failed: {monthly_response.status_code}")
            
            # Step 3: Test annual plan checkout
            print("📊 Step 3: Test annual plan checkout creation")
            
            annual_checkout_data = {
                "package_id": "annual_plan",
                "origin_url": "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com"
            }
            
            annual_response = self.make_request("POST", "/subscription/checkout", annual_checkout_data)
            
            print(f"   📊 Annual checkout status: {annual_response.status_code}")
            
            if annual_response.status_code == 200:
                annual_data = annual_response.json()
                
                if "url" in annual_data and "session_id" in annual_data:
                    annual_checkout_valid = True
                    print(f"   ✅ Annual checkout created successfully")
                    print(f"   ✅ Session ID: {annual_data['session_id']}")
                else:
                    annual_checkout_valid = False
                    print(f"   ❌ Missing url or session_id in annual response: {annual_data}")
            else:
                annual_checkout_valid = False
                print(f"   ❌ Annual checkout failed: {annual_response.status_code}")
            
            # Step 4: Test invalid package_id
            print("📊 Step 4: Test invalid package_id handling")
            
            invalid_checkout_data = {
                "package_id": "invalid_plan",
                "origin_url": "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com"
            }
            
            invalid_response = self.make_request("POST", "/subscription/checkout", invalid_checkout_data)
            
            if invalid_response.status_code in [400, 422]:
                invalid_handling_correct = True
                print(f"   ✅ Invalid package_id correctly rejected: {invalid_response.status_code}")
            else:
                invalid_handling_correct = False
                print(f"   ❌ Invalid package_id not properly handled: {invalid_response.status_code}")
            
            # Final assessment
            if monthly_checkout_valid and annual_checkout_valid and stripe_url_valid and invalid_handling_correct:
                self.log_result("Stripe Checkout Creation", True, f"✅ Stripe checkout creation works correctly for both monthly and annual plans")
            else:
                issues = []
                if not monthly_checkout_valid:
                    issues.append("monthly checkout failed")
                if not annual_checkout_valid:
                    issues.append("annual checkout failed")
                if not stripe_url_valid:
                    issues.append("invalid Stripe URL")
                if not invalid_handling_correct:
                    issues.append("invalid package_id not handled")
                
                self.log_result("Stripe Checkout Creation", False, f"❌ Checkout creation issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Stripe Checkout Creation", False, f"❌ Exception: {str(e)}")

    def test_audience_access_control(self):
        """PRIORITY 2: Test audience link access control"""
        try:
            print("🔍 PRIORITY 2: Testing Audience Access Control")
            print("=" * 80)
            
            # Use existing user for access control test
            print("📊 Step 1: Login with existing user")
            
            login_data = {
                "email": EXISTING_USER["email"],
                "password": EXISTING_USER["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Audience Access Control", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Logged in as: {login_data_response['musician']['name']}")
            print(f"   ✅ Musician slug: {musician_slug}")
            
            # Step 2: Test access check endpoint
            print("📊 Step 2: Test GET /api/musicians/{slug}/access-check")
            
            # Clear auth token for public access check
            self.auth_token = None
            
            access_check_response = self.make_request("GET", f"/musicians/{musician_slug}/access-check")
            
            print(f"   📊 Access check status: {access_check_response.status_code}")
            print(f"   📊 Access check response: {access_check_response.text}")
            
            if access_check_response.status_code == 200:
                access_data = access_check_response.json()
                access_allowed = access_data.get("access_allowed", False)
                
                print(f"   📊 Access allowed: {access_allowed}")
                access_check_working = True
            else:
                access_check_working = False
                access_allowed = False
                print(f"   ❌ Access check endpoint failed: {access_check_response.status_code}")
            
            # Step 3: Test audience songs access
            print("📊 Step 3: Test GET /api/musicians/{slug}/songs access control")
            
            songs_response = self.make_request("GET", f"/musicians/{musician_slug}/songs")
            
            print(f"   📊 Songs access status: {songs_response.status_code}")
            
            if access_allowed:
                # Should allow access
                if songs_response.status_code == 200:
                    songs_access_correct = True
                    songs_data = songs_response.json()
                    print(f"   ✅ Songs access allowed: {len(songs_data)} songs available")
                else:
                    songs_access_correct = False
                    print(f"   ❌ Songs access denied when should be allowed: {songs_response.status_code}")
            else:
                # Should deny access with 402
                if songs_response.status_code == 402:
                    songs_access_correct = True
                    print(f"   ✅ Songs access correctly denied with 402")
                else:
                    songs_access_correct = False
                    print(f"   ❌ Songs access not properly denied: {songs_response.status_code} (expected 402)")
            
            # Step 4: Test audience request submission access
            print("📊 Step 4: Test POST /api/musicians/{slug}/requests access control")
            
            # First get a song ID for the request (if access is allowed)
            if access_allowed and songs_response.status_code == 200:
                songs_data = songs_response.json()
                if len(songs_data) > 0:
                    test_song_id = songs_data[0]["id"]
                    
                    request_data = {
                        "song_id": test_song_id,
                        "requester_name": "Access Control Test User",
                        "requester_email": "access.test@requestwave.com",
                        "dedication": "Testing access control"
                    }
                    
                    request_response = self.make_request("POST", f"/musicians/{musician_slug}/requests", request_data)
                    
                    print(f"   📊 Request submission status: {request_response.status_code}")
                    
                    if request_response.status_code == 200:
                        request_access_correct = True
                        print(f"   ✅ Request submission allowed")
                    else:
                        request_access_correct = False
                        print(f"   ❌ Request submission denied when should be allowed: {request_response.status_code}")
                else:
                    request_access_correct = True  # Skip if no songs available
                    print(f"   ℹ️  No songs available for request test")
            else:
                # Access should be denied - try to submit a request anyway
                request_data = {
                    "song_id": "dummy-song-id",
                    "requester_name": "Access Control Test User",
                    "requester_email": "access.test@requestwave.com",
                    "dedication": "Testing access control"
                }
                
                request_response = self.make_request("POST", f"/musicians/{musician_slug}/requests", request_data)
                
                print(f"   📊 Request submission status: {request_response.status_code}")
                
                if request_response.status_code == 402:
                    request_access_correct = True
                    print(f"   ✅ Request submission correctly denied with 402")
                else:
                    request_access_correct = False
                    print(f"   ❌ Request submission not properly denied: {request_response.status_code} (expected 402)")
            
            # Final assessment
            if access_check_working and songs_access_correct and request_access_correct:
                self.log_result("Audience Access Control", True, f"✅ Audience access control working correctly - access_allowed={access_allowed}")
            else:
                issues = []
                if not access_check_working:
                    issues.append("access check endpoint failed")
                if not songs_access_correct:
                    issues.append("songs access control incorrect")
                if not request_access_correct:
                    issues.append("request access control incorrect")
                
                self.log_result("Audience Access Control", False, f"❌ Access control issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Audience Access Control", False, f"❌ Exception: {str(e)}")

    def test_account_deletion(self):
        """PRIORITY 3: Test DELETE /api/account/delete with confirmation"""
        try:
            print("🔍 PRIORITY 3: Testing Account Deletion")
            print("=" * 80)
            
            # Create a test user specifically for deletion
            print("📊 Step 1: Create test user for deletion")
            
            deletion_test_user = {
                "name": "Account Deletion Test User",
                "email": f"deletion.test.{int(time.time())}@requestwave.com",
                "password": "DeletionTest123!"
            }
            
            register_response = self.make_request("POST", "/auth/register", deletion_test_user)
            
            if register_response.status_code != 200:
                self.log_result("Account Deletion", False, f"Failed to create test user: {register_response.status_code}")
                return
            
            register_data = register_response.json()
            deletion_token = register_data["token"]
            deletion_musician_id = register_data["musician"]["id"]
            
            print(f"   ✅ Created test user: {register_data['musician']['name']}")
            print(f"   ✅ User ID: {deletion_musician_id}")
            
            # Step 2: Test deletion without proper confirmation
            print("📊 Step 2: Test deletion without proper confirmation")
            
            # Save current token and switch to deletion user
            original_token = self.auth_token
            self.auth_token = deletion_token
            
            # Try deletion with wrong confirmation text
            wrong_confirmation = {"confirmation_text": "delete"}  # Should be "DELETE"
            
            wrong_response = self.make_request("DELETE", "/account/delete", wrong_confirmation)
            
            print(f"   📊 Wrong confirmation status: {wrong_response.status_code}")
            
            if wrong_response.status_code in [400, 422]:
                wrong_confirmation_handled = True
                print(f"   ✅ Wrong confirmation text correctly rejected")
            else:
                wrong_confirmation_handled = False
                print(f"   ❌ Wrong confirmation not properly handled: {wrong_response.status_code}")
            
            # Step 3: Test deletion with correct confirmation
            print("📊 Step 3: Test deletion with correct confirmation")
            
            correct_confirmation = {"confirmation_text": "DELETE"}
            
            delete_response = self.make_request("DELETE", "/account/delete", correct_confirmation)
            
            print(f"   📊 Deletion status: {delete_response.status_code}")
            print(f"   📊 Deletion response: {delete_response.text}")
            
            if delete_response.status_code == 200:
                deletion_successful = True
                print(f"   ✅ Account deletion successful")
                
                # Verify deletion response
                try:
                    delete_data = delete_response.json()
                    if "success" in delete_data and delete_data["success"]:
                        deletion_response_valid = True
                        print(f"   ✅ Deletion response valid")
                    else:
                        deletion_response_valid = False
                        print(f"   ❌ Deletion response invalid: {delete_data}")
                except:
                    deletion_response_valid = False
                    print(f"   ❌ Deletion response not JSON")
            else:
                deletion_successful = False
                deletion_response_valid = False
                print(f"   ❌ Account deletion failed: {delete_response.status_code}")
            
            # Step 4: Verify account is actually deleted
            print("📊 Step 4: Verify account is actually deleted")
            
            if deletion_successful:
                # Try to access protected endpoint with deleted user's token
                profile_response = self.make_request("GET", "/profile")
                
                if profile_response.status_code == 401:
                    account_actually_deleted = True
                    print(f"   ✅ Account actually deleted - token no longer valid")
                else:
                    account_actually_deleted = False
                    print(f"   ❌ Account not actually deleted - token still valid: {profile_response.status_code}")
                
                # Try to login with deleted user credentials
                login_attempt = self.make_request("POST", "/auth/login", {
                    "email": deletion_test_user["email"],
                    "password": deletion_test_user["password"]
                })
                
                if login_attempt.status_code == 401:
                    login_blocked = True
                    print(f"   ✅ Login blocked for deleted account")
                else:
                    login_blocked = False
                    print(f"   ❌ Login still possible for deleted account: {login_attempt.status_code}")
            else:
                account_actually_deleted = True  # Skip if deletion failed
                login_blocked = True
            
            # Restore original token
            self.auth_token = original_token
            
            # Final assessment
            if wrong_confirmation_handled and deletion_successful and deletion_response_valid and account_actually_deleted and login_blocked:
                self.log_result("Account Deletion", True, f"✅ Account deletion works correctly with proper confirmation and cleanup")
            else:
                issues = []
                if not wrong_confirmation_handled:
                    issues.append("wrong confirmation not handled")
                if not deletion_successful:
                    issues.append("deletion failed")
                if not deletion_response_valid:
                    issues.append("deletion response invalid")
                if not account_actually_deleted:
                    issues.append("account not actually deleted")
                if not login_blocked:
                    issues.append("login not blocked")
                
                self.log_result("Account Deletion", False, f"❌ Account deletion issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Account Deletion", False, f"❌ Exception: {str(e)}")

    def test_stripe_webhook_handling(self):
        """PRIORITY 3: Test POST /api/webhook/stripe"""
        try:
            print("🔍 PRIORITY 3: Testing Stripe Webhook Handling")
            print("=" * 80)
            
            # Step 1: Test webhook endpoint accessibility
            print("📊 Step 1: Test webhook endpoint accessibility")
            
            # Webhooks should not require authentication
            original_token = self.auth_token
            self.auth_token = None
            
            # Test with mock webhook data
            mock_webhook_data = {
                "id": "evt_test_webhook",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_test_session_id",
                        "customer": "cus_test_customer",
                        "subscription": "sub_test_subscription",
                        "payment_status": "paid",
                        "metadata": {
                            "musician_id": "test_musician_id"
                        }
                    }
                }
            }
            
            webhook_response = self.make_request("POST", "/webhook/stripe", mock_webhook_data)
            
            print(f"   📊 Webhook status: {webhook_response.status_code}")
            print(f"   📊 Webhook response: {webhook_response.text}")
            
            if webhook_response.status_code == 200:
                webhook_accessible = True
                print(f"   ✅ Webhook endpoint accessible")
                
                # Check response format
                try:
                    webhook_data = webhook_response.json()
                    if "status" in webhook_data:
                        webhook_response_valid = True
                        print(f"   ✅ Webhook response format valid")
                    else:
                        webhook_response_valid = False
                        print(f"   ❌ Webhook response missing status: {webhook_data}")
                except:
                    webhook_response_valid = False
                    print(f"   ❌ Webhook response not JSON")
            else:
                webhook_accessible = False
                webhook_response_valid = False
                print(f"   ❌ Webhook endpoint not accessible: {webhook_response.status_code}")
            
            # Step 2: Test different webhook event types
            print("📊 Step 2: Test different webhook event types")
            
            webhook_events = [
                "checkout.session.completed",
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
                "invoice.payment_succeeded",
                "invoice.payment_failed"
            ]
            
            event_handling_results = {}
            
            for event_type in webhook_events:
                mock_event = {
                    "id": f"evt_test_{event_type.replace('.', '_')}",
                    "object": "event",
                    "type": event_type,
                    "data": {
                        "object": {
                            "id": f"test_{event_type.replace('.', '_')}_id",
                            "customer": "cus_test_customer",
                            "metadata": {
                                "musician_id": "test_musician_id"
                            }
                        }
                    }
                }
                
                event_response = self.make_request("POST", "/webhook/stripe", mock_event)
                event_handling_results[event_type] = event_response.status_code == 200
                
                print(f"   📊 {event_type}: {event_response.status_code}")
            
            successful_events = sum(1 for success in event_handling_results.values() if success)
            event_handling_working = successful_events >= len(webhook_events) * 0.8  # Allow some failures
            
            if event_handling_working:
                print(f"   ✅ Event handling working: {successful_events}/{len(webhook_events)} events handled")
            else:
                print(f"   ❌ Event handling issues: only {successful_events}/{len(webhook_events)} events handled")
            
            # Step 3: Test webhook with invalid data
            print("📊 Step 3: Test webhook with invalid data")
            
            invalid_webhook_data = {"invalid": "data"}
            
            invalid_response = self.make_request("POST", "/webhook/stripe", invalid_webhook_data)
            
            # Should handle gracefully (either 200 with error message or 400)
            if invalid_response.status_code in [200, 400]:
                invalid_handling_correct = True
                print(f"   ✅ Invalid webhook data handled gracefully: {invalid_response.status_code}")
            else:
                invalid_handling_correct = False
                print(f"   ❌ Invalid webhook data not handled properly: {invalid_response.status_code}")
            
            # Restore original token
            self.auth_token = original_token
            
            # Final assessment
            if webhook_accessible and webhook_response_valid and event_handling_working and invalid_handling_correct:
                self.log_result("Stripe Webhook Handling", True, f"✅ Stripe webhook handling works correctly for various event types")
            else:
                issues = []
                if not webhook_accessible:
                    issues.append("webhook not accessible")
                if not webhook_response_valid:
                    issues.append("webhook response invalid")
                if not event_handling_working:
                    issues.append("event handling issues")
                if not invalid_handling_correct:
                    issues.append("invalid data not handled")
                
                self.log_result("Stripe Webhook Handling", False, f"❌ Webhook handling issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Stripe Webhook Handling", False, f"❌ Exception: {str(e)}")

    def test_payment_transaction_recording(self):
        """PRIORITY 4: Test payment transaction recording during checkout"""
        try:
            print("🔍 PRIORITY 4: Testing Payment Transaction Recording")
            print("=" * 80)
            
            # Use existing user for transaction test
            print("📊 Step 1: Login with existing user")
            
            login_data = {
                "email": EXISTING_USER["email"],
                "password": EXISTING_USER["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Payment Transaction Recording", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            musician_id = login_data_response["musician"]["id"]
            
            print(f"   ✅ Logged in as: {login_data_response['musician']['name']}")
            
            # Step 2: Create checkout session and verify transaction recording
            print("📊 Step 2: Create checkout session and verify transaction recording")
            
            checkout_data = {
                "package_id": "monthly_plan",
                "origin_url": "https://02097561-4318-47d1-b18b-ed57f34042df.preview.emergentagent.com"
            }
            
            checkout_response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            if checkout_response.status_code != 200:
                self.log_result("Payment Transaction Recording", False, f"Checkout creation failed: {checkout_response.status_code}")
                return
            
            checkout_data_response = checkout_response.json()
            session_id = checkout_data_response.get("session_id")
            
            print(f"   ✅ Checkout session created: {session_id}")
            
            # Step 3: Check if transaction was recorded (this might require database access or a specific endpoint)
            print("📊 Step 3: Verify transaction recording")
            
            # Since we don't have direct database access, we'll test the checkout status endpoint
            # which should show the transaction
            if session_id:
                status_response = self.make_request("GET", f"/subscription/checkout/status/{session_id}")
                
                print(f"   📊 Checkout status endpoint: {status_response.status_code}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   📊 Checkout status data: {json.dumps(status_data, indent=2)}")
                    
                    # Look for transaction-related fields
                    transaction_fields = ["payment_status", "session_id", "amount"]
                    transaction_data_present = any(field in status_data for field in transaction_fields)
                    
                    if transaction_data_present:
                        transaction_recording_working = True
                        print(f"   ✅ Transaction data present in status response")
                    else:
                        transaction_recording_working = False
                        print(f"   ❌ No transaction data in status response")
                else:
                    transaction_recording_working = False
                    print(f"   ❌ Checkout status endpoint failed: {status_response.status_code}")
            else:
                transaction_recording_working = False
                print(f"   ❌ No session_id returned from checkout")
            
            # Step 4: Test subscription status includes payment information
            print("📊 Step 4: Verify subscription status includes payment information")
            
            subscription_status_response = self.make_request("GET", "/subscription/status")
            
            if subscription_status_response.status_code == 200:
                subscription_data = subscription_status_response.json()
                
                # Look for payment-related fields
                payment_fields = ["subscription_ends_at", "can_reactivate", "grace_period_active"]
                payment_info_present = any(field in subscription_data for field in payment_fields)
                
                if payment_info_present:
                    payment_info_working = True
                    print(f"   ✅ Payment information present in subscription status")
                else:
                    payment_info_working = False
                    print(f"   ❌ No payment information in subscription status")
            else:
                payment_info_working = False
                print(f"   ❌ Subscription status failed: {subscription_status_response.status_code}")
            
            # Final assessment
            if transaction_recording_working and payment_info_working:
                self.log_result("Payment Transaction Recording", True, f"✅ Payment transaction recording works correctly")
            else:
                issues = []
                if not transaction_recording_working:
                    issues.append("transaction recording not working")
                if not payment_info_working:
                    issues.append("payment info not in subscription status")
                
                self.log_result("Payment Transaction Recording", False, f"❌ Transaction recording issues: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Payment Transaction Recording", False, f"❌ Exception: {str(e)}")

    def run_all_tests(self):
        """Run all freemium model tests"""
        print("🚀 Starting Comprehensive Freemium Model Backend Testing")
        print("=" * 100)
        
        # PRIORITY 2 - Trial and Access Control
        self.test_new_user_registration_trial()
        self.test_audience_access_control()
        
        # PRIORITY 1 - Subscription Management APIs
        self.test_subscription_status_endpoint()
        self.test_stripe_checkout_creation()
        
        # PRIORITY 3 - Account Management
        self.test_account_deletion()
        self.test_stripe_webhook_handling()
        
        # PRIORITY 4 - Freemium Model Integration
        self.test_payment_transaction_recording()
        
        # Print final results
        print("=" * 100)
        print("🏁 FREEMIUM MODEL TESTING COMPLETE")
        print("=" * 100)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        return self.results

if __name__ == "__main__":
    tester = FreemiumModelTester()
    results = tester.run_all_tests()