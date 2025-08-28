#!/usr/bin/env python3
"""
PRO SUBSCRIBER STATUS FIX TEST

SPECIFIC TASK: Fix Pro subscriber status for existing brycelarsenmusic@gmail.com account

CONTEXT:
- User can login with original password: brycelarsenmusic@gmail.com / RequestWave2024!
- User cannot login with TestPassword123! (indicates original account still exists)
- User reports still in "free mode" after login (Pro status not activated)
- Previous testing agent claimed to recreate account but original account persists
- Need to update EXISTING account's subscription status to Pro

SPECIFIC ACTIONS:
1. Login with Existing Credentials (brycelarsenmusic@gmail.com / RequestWave2024!)
2. Check Current Subscription Status
3. Manually Update Database for Existing Account to Pro Status
4. Verify Pro Status After Update
5. Test Pro Features Access

Focus on updating the EXISTING account's subscription fields in the database, not creating a new account.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient

# Configuration
BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"

# Existing Pro account credentials
EXISTING_PRO_ACCOUNT = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

# MongoDB connection for direct database updates
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "livewave-music-test_database"

class ProSubscriberFixTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
        self.mongo_client = None
        self.db = None
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

    def connect_to_database(self):
        """Connect to MongoDB for direct database operations"""
        try:
            self.mongo_client = MongoClient(MONGO_URL)
            self.db = self.mongo_client[DB_NAME]
            # Test connection
            self.db.command('ping')
            self.log_result("Database Connection", True, "Successfully connected to MongoDB")
            return True
        except Exception as e:
            self.log_result("Database Connection", False, f"Failed to connect to MongoDB: {str(e)}")
            return False

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

    def test_login_with_existing_credentials(self):
        """Test login with existing credentials: brycelarsenmusic@gmail.com / RequestWave2024!"""
        try:
            print("🔐 STEP 1: Login with Existing Credentials")
            print("=" * 80)
            
            login_data = {
                "email": EXISTING_PRO_ACCOUNT["email"],
                "password": EXISTING_PRO_ACCOUNT["password"]
            }
            
            print(f"   📊 Attempting login with: {EXISTING_PRO_ACCOUNT['email']}")
            
            response = self.make_request("POST", "/auth/login", login_data)
            
            print(f"   📊 Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "musician" in data:
                    self.auth_token = data["token"]
                    self.musician_id = data["musician"]["id"]
                    self.musician_slug = data["musician"]["slug"]
                    
                    print(f"   ✅ Successfully logged in as: {data['musician']['name']}")
                    print(f"   📊 Musician ID: {self.musician_id}")
                    print(f"   📊 Musician Slug: {self.musician_slug}")
                    print(f"   📊 JWT Token: {self.auth_token[:50]}...")
                    
                    self.log_result("Login with Existing Credentials", True, f"Successfully authenticated as {data['musician']['name']}")
                    return True
                else:
                    self.log_result("Login with Existing Credentials", False, f"Missing token or musician in response: {data}")
                    return False
            else:
                error_msg = f"Login failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f": {response.text}"
                
                self.log_result("Login with Existing Credentials", False, error_msg)
                return False
                
        except Exception as e:
            self.log_result("Login with Existing Credentials", False, f"Exception: {str(e)}")
            return False

    def test_check_current_subscription_status(self):
        """Check current subscription status via API"""
        try:
            print("📊 STEP 2: Check Current Subscription Status")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Check Current Subscription Status", False, "No auth token available")
                return None
            
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Subscription status response: {response.status_code}")
            
            if response.status_code == 200:
                status_data = response.json()
                
                print(f"   📊 Current subscription status:")
                for key, value in status_data.items():
                    print(f"      {key}: {value}")
                
                # Check key fields
                audience_link_active = status_data.get("audience_link_active", False)
                plan = status_data.get("plan", "unknown")
                trial_active = status_data.get("trial_active", False)
                
                print(f"   📊 Key Status Summary:")
                print(f"      - Plan: {plan}")
                print(f"      - Audience Link Active: {audience_link_active}")
                print(f"      - Trial Active: {trial_active}")
                
                if plan in ["trial", "pro", "active"] and audience_link_active:
                    print(f"   ✅ User already has Pro access!")
                    self.log_result("Check Current Subscription Status", True, f"User has Pro access: plan={plan}, audience_link_active={audience_link_active}")
                else:
                    print(f"   ❌ User does NOT have Pro access")
                    self.log_result("Check Current Subscription Status", True, f"User needs Pro access: plan={plan}, audience_link_active={audience_link_active}")
                
                return status_data
                
            else:
                error_msg = f"Failed to get subscription status: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f": {response.text}"
                
                self.log_result("Check Current Subscription Status", False, error_msg)
                return None
                
        except Exception as e:
            self.log_result("Check Current Subscription Status", False, f"Exception: {str(e)}")
            return None

    def test_manually_update_database_to_pro(self):
        """Manually update database to set Pro subscription status"""
        try:
            print("🔧 STEP 3: Manually Update Database for Pro Status")
            print("=" * 80)
            
            if not self.musician_id:
                self.log_result("Manually Update Database to Pro", False, "No musician ID available")
                return False
            
            if self.db is None:
                self.log_result("Manually Update Database to Pro", False, "No database connection available")
                return False
            
            print(f"   📊 Updating musician record for ID: {self.musician_id}")
            
            # Calculate future dates
            now = datetime.utcnow()
            trial_end = now + timedelta(days=30)  # 30 days from now
            subscription_end = now + timedelta(days=365)  # 1 year from now
            
            # Update fields for Pro access
            update_data = {
                "$set": {
                    "audience_link_active": True,
                    "subscription_status": "active",
                    "trial_end": trial_end,
                    "has_had_trial": True,
                    "subscription_current_period_end": subscription_end,
                    "payment_grace_period_end": None  # Clear any grace period
                }
            }
            
            print(f"   📊 Update data:")
            for key, value in update_data["$set"].items():
                print(f"      {key}: {value}")
            
            # Perform the update
            result = self.db.musicians.update_one(
                {"id": self.musician_id},
                update_data
            )
            
            print(f"   📊 Update result:")
            print(f"      Matched: {result.matched_count}")
            print(f"      Modified: {result.modified_count}")
            
            if result.matched_count > 0:
                if result.modified_count > 0:
                    print(f"   ✅ Successfully updated musician record")
                    self.log_result("Manually Update Database to Pro", True, f"Updated {result.modified_count} fields for Pro access")
                else:
                    print(f"   ⚠️  Musician found but no changes made (may already be correct)")
                    self.log_result("Manually Update Database to Pro", True, "Musician found, no changes needed")
                return True
            else:
                self.log_result("Manually Update Database to Pro", False, f"No musician found with ID: {self.musician_id}")
                return False
                
        except Exception as e:
            self.log_result("Manually Update Database to Pro", False, f"Exception: {str(e)}")
            return False

    def test_verify_pro_status_after_update(self):
        """Verify Pro status after database update"""
        try:
            print("✅ STEP 4: Verify Pro Status After Update")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Verify Pro Status After Update", False, "No auth token available")
                return False
            
            # Re-check subscription status
            response = self.make_request("GET", "/subscription/status")
            
            print(f"   📊 Post-update subscription status response: {response.status_code}")
            
            if response.status_code == 200:
                status_data = response.json()
                
                print(f"   📊 Updated subscription status:")
                for key, value in status_data.items():
                    print(f"      {key}: {value}")
                
                # Check key fields
                audience_link_active = status_data.get("audience_link_active", False)
                plan = status_data.get("plan", "unknown")
                trial_active = status_data.get("trial_active", False)
                
                print(f"   📊 Pro Status Verification:")
                print(f"      - Plan: {plan}")
                print(f"      - Audience Link Active: {audience_link_active}")
                print(f"      - Trial Active: {trial_active}")
                
                # Check if user now has Pro access
                has_pro_access = plan in ["trial", "pro", "active"] and audience_link_active
                
                if has_pro_access:
                    print(f"   ✅ SUCCESS: User now has Pro access!")
                    self.log_result("Verify Pro Status After Update", True, f"Pro access confirmed: plan={plan}, audience_link_active={audience_link_active}")
                    return True
                else:
                    print(f"   ❌ FAILED: User still does not have Pro access")
                    self.log_result("Verify Pro Status After Update", False, f"Pro access not granted: plan={plan}, audience_link_active={audience_link_active}")
                    return False
                
            else:
                error_msg = f"Failed to verify subscription status: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f": {response.text}"
                
                self.log_result("Verify Pro Status After Update", False, error_msg)
                return False
                
        except Exception as e:
            self.log_result("Verify Pro Status After Update", False, f"Exception: {str(e)}")
            return False

    def test_pro_features_access(self):
        """Test access to Pro features (playlists, etc.)"""
        try:
            print("🎵 STEP 5: Test Pro Features Access")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Test Pro Features Access", False, "No auth token available")
                return False
            
            # Test 1: Access playlists endpoint
            print("   📊 Test 1: Access playlists endpoint")
            playlists_response = self.make_request("GET", "/playlists")
            
            print(f"      Status: {playlists_response.status_code}")
            
            if playlists_response.status_code == 200:
                playlists = playlists_response.json()
                print(f"      ✅ Playlists accessible: {len(playlists)} playlists found")
                playlists_accessible = True
            elif playlists_response.status_code == 403:
                print(f"      ❌ Playlists blocked: 403 Forbidden")
                playlists_accessible = False
            else:
                print(f"      ⚠️  Unexpected playlists response: {playlists_response.status_code}")
                playlists_accessible = False
            
            # Test 2: Try to create a playlist
            print("   📊 Test 2: Try to create a playlist")
            
            # Get some songs first
            songs_response = self.make_request("GET", "/songs")
            if songs_response.status_code == 200:
                songs = songs_response.json()
                if len(songs) >= 2:
                    song_ids = [songs[0]["id"], songs[1]["id"]]
                    
                    playlist_data = {
                        "name": "Pro Access Test Playlist",
                        "song_ids": song_ids
                    }
                    
                    create_response = self.make_request("POST", "/playlists", playlist_data)
                    
                    print(f"      Status: {create_response.status_code}")
                    
                    if create_response.status_code == 200:
                        created_playlist = create_response.json()
                        playlist_id = created_playlist["id"]
                        print(f"      ✅ Playlist creation successful: {created_playlist['name']}")
                        playlist_creation_works = True
                        
                        # Clean up - delete the test playlist
                        delete_response = self.make_request("DELETE", f"/playlists/{playlist_id}")
                        if delete_response.status_code == 200:
                            print(f"      ✅ Test playlist cleaned up")
                        
                    elif create_response.status_code == 403:
                        print(f"      ❌ Playlist creation blocked: 403 Forbidden")
                        playlist_creation_works = False
                    else:
                        print(f"      ⚠️  Unexpected playlist creation response: {create_response.status_code}")
                        playlist_creation_works = False
                else:
                    print(f"      ⚠️  Not enough songs to test playlist creation")
                    playlist_creation_works = None
            else:
                print(f"      ⚠️  Could not get songs for playlist creation test")
                playlist_creation_works = None
            
            # Test 3: Check if "My Playlists" would appear in UI (via audience link)
            print("   📊 Test 3: Check audience link activation")
            
            if self.musician_slug:
                # Test public playlists endpoint (what audience would see)
                public_playlists_response = self.make_request("GET", f"/musicians/{self.musician_slug}/playlists")
                
                print(f"      Status: {public_playlists_response.status_code}")
                
                if public_playlists_response.status_code == 200:
                    public_playlists = public_playlists_response.json()
                    print(f"      ✅ Audience link active: {len(public_playlists)} public playlists")
                    audience_link_works = True
                elif public_playlists_response.status_code == 404:
                    print(f"      ❌ Audience link not active: 404 Not Found")
                    audience_link_works = False
                else:
                    print(f"      ⚠️  Unexpected audience link response: {public_playlists_response.status_code}")
                    audience_link_works = False
            else:
                print(f"      ⚠️  No musician slug available for audience link test")
                audience_link_works = None
            
            # Overall assessment
            pro_features_working = playlists_accessible and (playlist_creation_works is not False) and (audience_link_works is not False)
            
            if pro_features_working:
                self.log_result("Test Pro Features Access", True, "All Pro features accessible - playlists, creation, audience link")
                return True
            else:
                issues = []
                if not playlists_accessible:
                    issues.append("playlists not accessible")
                if playlist_creation_works is False:
                    issues.append("playlist creation blocked")
                if audience_link_works is False:
                    issues.append("audience link not active")
                
                self.log_result("Test Pro Features Access", False, f"Pro features issues: {', '.join(issues)}")
                return False
                
        except Exception as e:
            self.log_result("Test Pro Features Access", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Pro subscriber fix tests"""
        print("🚀 PRO SUBSCRIBER STATUS FIX TEST SUITE")
        print("=" * 80)
        print(f"Target Account: {EXISTING_PRO_ACCOUNT['email']}")
        print(f"API Base URL: {self.base_url}")
        print("=" * 80)
        
        # Connect to database first
        if not self.connect_to_database():
            print("❌ Cannot proceed without database connection")
            return
        
        # Step 1: Login with existing credentials
        if not self.test_login_with_existing_credentials():
            print("❌ Cannot proceed without successful login")
            return
        
        # Step 2: Check current subscription status
        current_status = self.test_check_current_subscription_status()
        
        # Step 3: Update database to Pro status (skip if already Pro)
        if current_status and current_status.get("plan") in ["trial", "pro", "active"] and current_status.get("audience_link_active"):
            print("✅ User already has Pro access, skipping database update")
        else:
            if not self.test_manually_update_database_to_pro():
                print("❌ Database update failed")
                return
        
        # Step 4: Verify Pro status after update
        if not self.test_verify_pro_status_after_update():
            print("❌ Pro status verification failed")
            return
        
        # Step 5: Test Pro features access
        self.test_pro_features_access()
        
        # Final summary
        print("\n" + "=" * 80)
        print("🏁 PRO SUBSCRIBER FIX TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['failed'] == 0:
            print("\n🎉 SUCCESS: Pro subscriber status has been fixed!")
            print(f"   User {EXISTING_PRO_ACCOUNT['email']} now has Pro access")
        else:
            print(f"\n⚠️  ISSUES FOUND:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        # Close database connection
        if self.mongo_client:
            self.mongo_client.close()

if __name__ == "__main__":
    tester = ProSubscriberFixTester()
    tester.run_all_tests()