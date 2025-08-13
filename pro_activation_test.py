#!/usr/bin/env python3
"""
PRO SUBSCRIBER ACTIVATION TEST FOR BRYCELARSENMUSIC@GMAIL.COM

REVIEW REQUEST: Manually activate Pro subscriber status for brycelarsenmusic@gmail.com

CONTEXT:
- User experiencing deployment environment variable issues preventing subscription checkout
- Need to manually make brycelarsenmusic@gmail.com a Pro subscriber as workaround
- User needs audience link access to test functionality while deployment issues are resolved

SPECIFIC ACTIONS NEEDED:
1. Find User Record: Login with brycelarsenmusic@gmail.com / RequestWave2024!
2. Update Subscription Status: Set audience_link_active = true, subscription plan to "pro" or "trial", update trial_end to future date if needed, set has_had_trial = true if appropriate
3. Verify Pro Access: Test check_pro_access() function returns true for this user
4. Test Audience Link: Verify audience interface is accessible

This test will verify the current status and manually update the database if needed.
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pymongo
from pymongo import MongoClient

# Configuration
BASE_URL = "https://requestwave.app/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "requestwave_production"

# Target user credentials
TARGET_USER = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class ProActivationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.musician_data = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        # MongoDB connection
        try:
            self.mongo_client = MongoClient(MONGO_URL)
            self.db = self.mongo_client[DB_NAME]
            print(f"✅ Connected to MongoDB: {DB_NAME}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            self.mongo_client = None
            self.db = None

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

    def test_user_login(self):
        """Test login with target user credentials"""
        try:
            print("🔐 STEP 1: Testing User Login")
            print("=" * 60)
            
            login_data = {
                "email": TARGET_USER["email"],
                "password": TARGET_USER["password"]
            }
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"   📊 Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    self.musician_data = data["musician"]
                    
                    print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
                    print(f"   📊 Musician ID: {self.musician_id}")
                    print(f"   📊 Musician Slug: {self.musician_slug}")
                    print(f"   📊 Email: {data['musician']['email']}")
                    
                    self.log_result("User Login", True, f"Successfully authenticated {TARGET_USER['email']}")
                else:
                    self.log_result("User Login", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("User Login", False, f"Login failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("User Login", False, f"Exception during login: {str(e)}")

    def test_current_subscription_status(self):
        """Test current subscription status"""
        try:
            print("\n📊 STEP 2: Checking Current Subscription Status")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Current Subscription Status", False, "No auth token available")
                return
            
            # Test subscription status endpoint
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status response: {response.status_code}")
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"   📊 Subscription Status Response: {json.dumps(status_data, indent=2, default=str)}")
                
                # Extract key fields
                plan = status_data.get("plan", "unknown")
                audience_link_active = status_data.get("audience_link_active", False)
                trial_active = status_data.get("trial_active", False)
                trial_end = status_data.get("trial_end")
                
                print(f"   📊 Current Plan: {plan}")
                print(f"   📊 Audience Link Active: {audience_link_active}")
                print(f"   📊 Trial Active: {trial_active}")
                print(f"   📊 Trial End: {trial_end}")
                
                # Determine if user needs Pro activation
                needs_activation = not audience_link_active or plan not in ["trial", "pro", "active"]
                
                if needs_activation:
                    print(f"   ⚠️  USER NEEDS PRO ACTIVATION")
                    print(f"      - Audience Link Active: {audience_link_active}")
                    print(f"      - Plan: {plan} (needs to be 'trial', 'pro', or 'active')")
                else:
                    print(f"   ✅ USER ALREADY HAS PRO ACCESS")
                
                self.log_result("Current Subscription Status", True, f"Plan: {plan}, Audience Link: {audience_link_active}")
                return needs_activation
                
            else:
                self.log_result("Current Subscription Status", False, f"Status check failed: {response.status_code} - {response.text}")
                return True  # Assume needs activation if we can't check
                
        except Exception as e:
            self.log_result("Current Subscription Status", False, f"Exception: {str(e)}")
            return True  # Assume needs activation if error

    def test_current_pro_access(self):
        """Test current Pro access by trying to access Pro features"""
        try:
            print("\n🎵 STEP 3: Testing Current Pro Access")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Current Pro Access", False, "No auth token available")
                return False
            
            # Test playlist access (Pro feature)
            playlists_response = self.make_request("GET", "/playlists")
            
            print(f"   📊 Playlists endpoint response: {playlists_response.status_code}")
            
            if playlists_response.status_code == 200:
                playlists = playlists_response.json()
                print(f"   ✅ Pro access working - can access playlists ({len(playlists)} playlists)")
                
                # Test playlist creation
                test_playlist_data = {
                    "name": "Pro Access Test Playlist",
                    "song_ids": []
                }
                
                create_response = self.make_request("POST", "/playlists", test_playlist_data)
                
                if create_response.status_code == 200:
                    created_playlist = create_response.json()
                    playlist_id = created_playlist["id"]
                    print(f"   ✅ Pro access confirmed - can create playlists")
                    
                    # Clean up test playlist
                    delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
                    if delete_response.status_code == 200:
                        print(f"   ✅ Cleaned up test playlist")
                    
                    self.log_result("Current Pro Access", True, "User has working Pro access")
                    return True
                else:
                    print(f"   ❌ Cannot create playlists: {create_response.status_code}")
                    self.log_result("Current Pro Access", False, f"Cannot create playlists: {create_response.status_code}")
                    return False
                    
            elif playlists_response.status_code == 403:
                print(f"   ❌ Pro access denied - 403 Forbidden")
                self.log_result("Current Pro Access", False, "Pro access denied - 403 Forbidden")
                return False
            else:
                print(f"   ❌ Unexpected response: {playlists_response.status_code}")
                self.log_result("Current Pro Access", False, f"Unexpected response: {playlists_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Current Pro Access", False, f"Exception: {str(e)}")
            return False

    def manually_activate_pro_status(self):
        """Manually activate Pro status in the database"""
        try:
            print("\n🔧 STEP 4: Manually Activating Pro Status")
            print("=" * 60)
            
            if not self.db:
                self.log_result("Manual Pro Activation", False, "No database connection available")
                return False
            
            if not self.musician_id:
                self.log_result("Manual Pro Activation", False, "No musician ID available")
                return False
            
            # Calculate future trial end date (30 days from now)
            future_trial_end = datetime.utcnow() + timedelta(days=30)
            
            # Update musician record with Pro status
            update_data = {
                "$set": {
                    "audience_link_active": True,
                    "has_had_trial": True,
                    "trial_end": future_trial_end,
                    "subscription_status": "active",
                    "subscription_current_period_end": future_trial_end,
                    "updated_at": datetime.utcnow()
                }
            }
            
            print(f"   📊 Updating musician record with ID: {self.musician_id}")
            print(f"   📊 Setting audience_link_active: True")
            print(f"   📊 Setting trial_end: {future_trial_end}")
            print(f"   📊 Setting subscription_status: active")
            
            result = self.db.musicians.update_one(
                {"id": self.musician_id},
                update_data
            )
            
            if result.modified_count > 0:
                print(f"   ✅ Successfully updated musician record")
                self.log_result("Manual Pro Activation", True, "Database updated successfully")
                return True
            else:
                print(f"   ❌ No records were modified")
                self.log_result("Manual Pro Activation", False, "No records were modified")
                return False
                
        except Exception as e:
            self.log_result("Manual Pro Activation", False, f"Exception: {str(e)}")
            return False

    def verify_pro_activation(self):
        """Verify Pro activation was successful"""
        try:
            print("\n✅ STEP 5: Verifying Pro Activation")
            print("=" * 60)
            
            if not self.auth_token:
                self.log_result("Verify Pro Activation", False, "No auth token available")
                return False
            
            # Re-login to get fresh token with updated permissions
            print("   📊 Re-authenticating to get fresh token...")
            login_data = {
                "email": TARGET_USER["email"],
                "password": TARGET_USER["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code == 200:
                login_data_response = login_response.json()
                self.auth_token = login_data_response["token"]
                print(f"   ✅ Re-authenticated successfully")
            else:
                print(f"   ❌ Re-authentication failed: {login_response.status_code}")
                return False
            
            # Check subscription status again
            status_response = self.make_request("GET", "/subscription/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                plan = status_data.get("plan", "unknown")
                audience_link_active = status_data.get("audience_link_active", False)
                trial_active = status_data.get("trial_active", False)
                
                print(f"   📊 Updated Plan: {plan}")
                print(f"   📊 Updated Audience Link Active: {audience_link_active}")
                print(f"   📊 Updated Trial Active: {trial_active}")
                
                # Verify Pro access
                if audience_link_active and plan in ["trial", "pro", "active"]:
                    print(f"   ✅ Pro status successfully activated!")
                    
                    # Test playlist creation again
                    test_playlist_data = {
                        "name": "Pro Verification Test Playlist",
                        "song_ids": []
                    }
                    
                    create_response = self.make_request("POST", "/playlists", test_playlist_data)
                    
                    if create_response.status_code == 200:
                        created_playlist = create_response.json()
                        playlist_id = created_playlist["id"]
                        print(f"   ✅ Playlist creation working - Pro access confirmed")
                        
                        # Clean up
                        self.make_request("DELETE", f"/playlists/{playlist_id}")
                        
                        self.log_result("Verify Pro Activation", True, "Pro activation successful and verified")
                        return True
                    else:
                        print(f"   ❌ Playlist creation still failing: {create_response.status_code}")
                        self.log_result("Verify Pro Activation", False, f"Playlist creation still failing: {create_response.status_code}")
                        return False
                else:
                    print(f"   ❌ Pro status not properly activated")
                    self.log_result("Verify Pro Activation", False, f"Pro status not properly activated - Plan: {plan}, Audience Link: {audience_link_active}")
                    return False
            else:
                print(f"   ❌ Status check failed: {status_response.status_code}")
                self.log_result("Verify Pro Activation", False, f"Status check failed: {status_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Verify Pro Activation", False, f"Exception: {str(e)}")
            return False

    def test_audience_link_access(self):
        """Test audience link accessibility"""
        try:
            print("\n🌐 STEP 6: Testing Audience Link Access")
            print("=" * 60)
            
            if not self.musician_slug:
                self.log_result("Audience Link Access", False, "No musician slug available")
                return False
            
            # Test public audience endpoint (no auth needed)
            self.auth_token = None  # Clear auth for public access
            
            # Test musician public profile
            profile_response = self.make_request("GET", f"/musicians/{self.musician_slug}")
            
            print(f"   📊 Public profile response: {profile_response.status_code}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                print(f"   ✅ Public profile accessible: {profile_data.get('name', 'Unknown')}")
                
                # Test public songs endpoint
                songs_response = self.make_request("GET", f"/musicians/{self.musician_slug}/songs")
                
                print(f"   📊 Public songs response: {songs_response.status_code}")
                
                if songs_response.status_code == 200:
                    songs = songs_response.json()
                    print(f"   ✅ Public songs accessible: {len(songs)} songs available")
                    
                    # Test public playlists endpoint
                    playlists_response = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
                    
                    print(f"   📊 Public playlists response: {playlists_response.status_code}")
                    
                    if playlists_response.status_code == 200:
                        playlists = playlists_response.json()
                        print(f"   ✅ Public playlists accessible: {len(playlists)} playlists available")
                        
                        self.log_result("Audience Link Access", True, f"Audience interface fully accessible - {len(songs)} songs, {len(playlists)} playlists")
                        return True
                    else:
                        print(f"   ❌ Public playlists not accessible: {playlists_response.status_code}")
                        self.log_result("Audience Link Access", False, f"Public playlists not accessible: {playlists_response.status_code}")
                        return False
                else:
                    print(f"   ❌ Public songs not accessible: {songs_response.status_code}")
                    self.log_result("Audience Link Access", False, f"Public songs not accessible: {songs_response.status_code}")
                    return False
            else:
                print(f"   ❌ Public profile not accessible: {profile_response.status_code}")
                self.log_result("Audience Link Access", False, f"Public profile not accessible: {profile_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Audience Link Access", False, f"Exception: {str(e)}")
            return False

    def run_full_test_suite(self):
        """Run the complete Pro activation test suite"""
        print("🚀 STARTING PRO ACTIVATION TEST SUITE")
        print("=" * 80)
        print(f"Target User: {TARGET_USER['email']}")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Step 1: Login
        self.test_user_login()
        
        if not self.auth_token:
            print("\n❌ CRITICAL: Cannot proceed without authentication")
            return
        
        # Step 2: Check current status
        needs_activation = self.test_current_subscription_status()
        
        # Step 3: Test current Pro access
        has_pro_access = self.test_current_pro_access()
        
        # Step 4: Manually activate if needed
        if needs_activation or not has_pro_access:
            print(f"\n🔧 User needs Pro activation - proceeding with manual activation")
            activation_success = self.manually_activate_pro_status()
            
            if activation_success:
                # Step 5: Verify activation
                self.verify_pro_activation()
            else:
                print(f"\n❌ Manual activation failed - cannot proceed with verification")
        else:
            print(f"\n✅ User already has Pro access - skipping manual activation")
        
        # Step 6: Test audience link access
        self.test_audience_link_access()
        
        # Final summary
        print("\n" + "=" * 80)
        print("🏁 PRO ACTIVATION TEST SUITE COMPLETE")
        print("=" * 80)
        print(f"✅ Tests Passed: {self.results['passed']}")
        print(f"❌ Tests Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            print("\n❌ FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        if self.results['passed'] > 0 and self.results['failed'] == 0:
            print(f"\n🎉 SUCCESS: brycelarsenmusic@gmail.com now has full Pro subscriber access!")
            print(f"   ✅ Audience link is active and accessible")
            print(f"   ✅ Playlist functionality is available")
            print(f"   ✅ Pro features are working correctly")
        elif self.results['passed'] > self.results['failed']:
            print(f"\n⚠️  PARTIAL SUCCESS: Most functionality working, some minor issues")
        else:
            print(f"\n❌ FAILURE: Pro activation was not successful")
        
        print("=" * 80)

def main():
    """Main function to run the Pro activation test"""
    tester = ProActivationTester()
    tester.run_full_test_suite()

if __name__ == "__main__":
    main()