#!/usr/bin/env python3
"""
Production Bug Investigation Test Suite for RequestWave
Testing request management and tip functionality on deployed RequestWave app

BUG REPORTS TO INVESTIGATE:
1. Bug #1 - Request Visibility: New requests are not showing up in the On Stage tab or Songs tab
2. Bug #2 - Tip Button Error: Send tip button returning error when making request from audience link

TESTING PRIORITY:
- Request Management Testing: GET /api/requests endpoints, POST /api/requests, request storage, status updates
- Tip Functionality Testing: tip link generation, tip recording, payment usernames, tip integration

Environment: Production deployment at https://requestwave.app/api
Account: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import sys
from datetime import datetime
import time
import uuid

# Configuration
PRODUCTION_BASE_URL = "https://requestwave.app/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class ProductionBugTester:
    def __init__(self):
        self.token = None
        self.musician_id = None
        self.musician_slug = None
        self.results = []
        self.test_request_ids = []  # Track created test requests for cleanup
        
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
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
    def authenticate(self):
        """Authenticate with production API"""
        print("\n=== Authenticating with Production API ===")
        
        try:
            response = requests.post(f"{PRODUCTION_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                musician_data = data.get("musician", {})
                self.musician_id = musician_data.get("id")
                self.musician_slug = musician_data.get("slug")
                
                if self.token and self.musician_id:
                    self.log_result("Production Authentication", True, f"Successfully authenticated {TEST_EMAIL}", {
                        "musician_id": self.musician_id,
                        "musician_slug": self.musician_slug,
                        "musician_name": musician_data.get("name"),
                        "token_length": len(self.token)
                    })
                    return True
                else:
                    self.log_result("Production Authentication", False, "Missing token or musician_id in response", {
                        "response_data": data
                    })
                    return False
            else:
                self.log_result("Production Authentication", False, f"Login failed: {response.status_code} - {response.text}", {
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers)
                })
                return False
                
        except Exception as e:
            self.log_result("Production Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def get_headers(self):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_request_management_endpoints(self):
        """Test request management endpoints for Bug #1 - Request Visibility"""
        print("\n=== Testing Request Management Endpoints (Bug #1) ===")
        
        if not self.token:
            self.log_result("Request Management", False, "No authentication token available")
            return False
        
        headers = self.get_headers()
        
        # Test 1: GET /api/requests/musician/{id} - Musician's requests
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/requests/musician/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                requests_data = response.json()
                self.log_result("GET Musician Requests", True, f"Successfully retrieved musician requests", {
                    "endpoint": f"/requests/musician/{self.musician_id}",
                    "requests_count": len(requests_data),
                    "request_statuses": [req.get("status") for req in requests_data[:5]],  # First 5 statuses
                    "recent_requests": [{"id": req.get("id"), "song_title": req.get("song_title"), 
                                       "status": req.get("status"), "created_at": req.get("created_at")} 
                                      for req in requests_data[:3]]  # First 3 requests
                })
            else:
                self.log_result("GET Musician Requests", False, f"Failed to get musician requests: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("GET Musician Requests", False, f"Error getting musician requests: {str(e)}")
        
        # Test 2: GET /api/requests/updates/{id} - Real-time updates endpoint
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/requests/updates/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                updates_data = response.json()
                
                # Check if response is dict with 'requests' key or direct array
                if isinstance(updates_data, dict) and 'requests' in updates_data:
                    requests_list = updates_data['requests']
                    total_requests = updates_data.get('total_requests', len(requests_list))
                    last_updated = updates_data.get('last_updated')
                    
                    self.log_result("GET Request Updates", True, f"Successfully retrieved request updates (dict format)", {
                        "endpoint": f"/requests/updates/{self.musician_id}",
                        "response_format": "dict_with_requests_key",
                        "requests_count": len(requests_list),
                        "total_requests": total_requests,
                        "last_updated": last_updated,
                        "response_keys": list(updates_data.keys())
                    })
                elif isinstance(updates_data, list):
                    self.log_result("GET Request Updates", True, f"Successfully retrieved request updates (array format)", {
                        "endpoint": f"/requests/updates/{self.musician_id}",
                        "response_format": "direct_array",
                        "requests_count": len(updates_data)
                    })
                else:
                    self.log_result("GET Request Updates", False, f"Unexpected response format", {
                        "response_type": type(updates_data).__name__,
                        "response_data": updates_data
                    })
            else:
                self.log_result("GET Request Updates", False, f"Failed to get request updates: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("GET Request Updates", False, f"Error getting request updates: {str(e)}")
    
    def test_request_creation_from_audience(self):
        """Test request creation from audience perspective for Bug #1"""
        print("\n=== Testing Request Creation from Audience (Bug #1) ===")
        
        if not self.musician_slug:
            self.log_result("Audience Request Creation", False, "No musician slug available for testing")
            return False
        
        # First, get musician's songs to create a valid request
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/musicians/{self.musician_slug}/songs", timeout=30)
            
            if response.status_code == 200:
                songs_data = response.json()
                if not songs_data:
                    self.log_result("Get Musician Songs", False, "No songs available for request creation")
                    return False
                
                # Use the first song for testing
                test_song = songs_data[0]
                song_id = test_song.get("id")
                
                self.log_result("Get Musician Songs", True, f"Retrieved songs for request creation", {
                    "songs_count": len(songs_data),
                    "test_song": {
                        "id": song_id,
                        "title": test_song.get("title"),
                        "artist": test_song.get("artist")
                    }
                })
                
                # Now create a test request from audience perspective (no auth required)
                request_data = {
                    "song_id": song_id,
                    "requester_name": "Production Test User",
                    "requester_email": "test@requestwave.com",
                    "dedication": "Testing request visibility bug - please ignore",
                    "tip_amount": 0.0  # Include required field
                }
                
                response = requests.post(f"{PRODUCTION_BASE_URL}/requests", json=request_data, timeout=30)
                
                if response.status_code == 200:
                    request_response = response.json()
                    request_id = request_response.get("id")
                    self.test_request_ids.append(request_id)  # Track for cleanup
                    
                    self.log_result("Create Audience Request", True, f"Successfully created request from audience", {
                        "request_id": request_id,
                        "song_title": request_response.get("song_title"),
                        "song_artist": request_response.get("song_artist"),
                        "status": request_response.get("status"),
                        "created_at": request_response.get("created_at")
                    })
                    
                    # Wait a moment for the request to be processed
                    time.sleep(2)
                    
                    # Verify the request appears in musician's request list
                    self.verify_request_visibility(request_id)
                    
                else:
                    self.log_result("Create Audience Request", False, f"Failed to create request: {response.status_code} - {response.text}")
                    
            else:
                self.log_result("Get Musician Songs", False, f"Failed to get musician songs: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Audience Request Creation", False, f"Error in audience request creation: {str(e)}")
    
    def verify_request_visibility(self, request_id):
        """Verify that the created request is visible in musician's request endpoints"""
        print(f"\n=== Verifying Request Visibility for {request_id} ===")
        
        headers = self.get_headers()
        
        # Check if request appears in musician requests
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/requests/musician/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                requests_data = response.json()
                found_request = None
                
                for req in requests_data:
                    if req.get("id") == request_id:
                        found_request = req
                        break
                
                if found_request:
                    self.log_result("Request Visibility - Musician Endpoint", True, f"Request found in musician requests", {
                        "request_id": request_id,
                        "status": found_request.get("status"),
                        "song_title": found_request.get("song_title"),
                        "requester_name": found_request.get("requester_name")
                    })
                else:
                    self.log_result("Request Visibility - Musician Endpoint", False, f"Request NOT found in musician requests", {
                        "request_id": request_id,
                        "total_requests": len(requests_data),
                        "request_ids_found": [req.get("id") for req in requests_data[:5]]
                    })
            else:
                self.log_result("Request Visibility - Musician Endpoint", False, f"Failed to check musician requests: {response.status_code}")
                
        except Exception as e:
            self.log_result("Request Visibility - Musician Endpoint", False, f"Error checking request visibility: {str(e)}")
        
        # Check if request appears in updates endpoint
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/requests/updates/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                updates_data = response.json()
                
                # Handle both dict and array response formats
                requests_list = updates_data.get('requests', []) if isinstance(updates_data, dict) else updates_data
                
                found_request = None
                for req in requests_list:
                    if req.get("id") == request_id:
                        found_request = req
                        break
                
                if found_request:
                    self.log_result("Request Visibility - Updates Endpoint", True, f"Request found in updates endpoint", {
                        "request_id": request_id,
                        "status": found_request.get("status")
                    })
                else:
                    self.log_result("Request Visibility - Updates Endpoint", False, f"Request NOT found in updates endpoint", {
                        "request_id": request_id,
                        "total_requests": len(requests_list)
                    })
            else:
                self.log_result("Request Visibility - Updates Endpoint", False, f"Failed to check updates endpoint: {response.status_code}")
                
        except Exception as e:
            self.log_result("Request Visibility - Updates Endpoint", False, f"Error checking updates endpoint: {str(e)}")
    
    def test_request_status_updates(self):
        """Test request status updates functionality"""
        print("\n=== Testing Request Status Updates ===")
        
        if not self.test_request_ids:
            self.log_result("Request Status Updates", False, "No test requests available for status updates")
            return False
        
        headers = self.get_headers()
        test_request_id = self.test_request_ids[0]
        
        # Test updating request status to 'up_next'
        try:
            response = requests.put(f"{PRODUCTION_BASE_URL}/requests/{test_request_id}/status", 
                                  json={"status": "up_next"}, headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.log_result("Update Request Status - up_next", True, f"Successfully updated request status to up_next", {
                    "request_id": test_request_id,
                    "new_status": "up_next"
                })
                
                # Verify the status was updated
                time.sleep(1)
                self.verify_status_update(test_request_id, "up_next")
                
            else:
                self.log_result("Update Request Status - up_next", False, f"Failed to update status: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Update Request Status - up_next", False, f"Error updating request status: {str(e)}")
    
    def verify_status_update(self, request_id, expected_status):
        """Verify that request status was updated correctly"""
        headers = self.get_headers()
        
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/requests/musician/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                requests_data = response.json()
                found_request = None
                
                for req in requests_data:
                    if req.get("id") == request_id:
                        found_request = req
                        break
                
                if found_request:
                    actual_status = found_request.get("status")
                    if actual_status == expected_status:
                        self.log_result("Verify Status Update", True, f"Status correctly updated", {
                            "request_id": request_id,
                            "expected_status": expected_status,
                            "actual_status": actual_status
                        })
                    else:
                        self.log_result("Verify Status Update", False, f"Status not updated correctly", {
                            "request_id": request_id,
                            "expected_status": expected_status,
                            "actual_status": actual_status
                        })
                else:
                    self.log_result("Verify Status Update", False, f"Request not found for status verification")
            else:
                self.log_result("Verify Status Update", False, f"Failed to verify status update: {response.status_code}")
                
        except Exception as e:
            self.log_result("Verify Status Update", False, f"Error verifying status update: {str(e)}")
    
    def test_tip_functionality(self):
        """Test tip functionality for Bug #2 - Tip Button Error"""
        print("\n=== Testing Tip Functionality (Bug #2) ===")
        
        if not self.token:
            self.log_result("Tip Functionality", False, "No authentication token available")
            return False
        
        headers = self.get_headers()
        
        # Test 1: Check musician profile has payment usernames configured
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/profile", headers=headers, timeout=30)
            
            if response.status_code == 200:
                profile_data = response.json()
                
                paypal_username = profile_data.get("paypal_username")
                venmo_username = profile_data.get("venmo_username")
                zelle_email = profile_data.get("zelle_email")
                
                payment_methods = []
                if paypal_username:
                    payment_methods.append(f"PayPal: {paypal_username}")
                if venmo_username:
                    payment_methods.append(f"Venmo: {venmo_username}")
                if zelle_email:
                    payment_methods.append(f"Zelle: {zelle_email}")
                
                if payment_methods:
                    self.log_result("Payment Profile Configuration", True, f"Payment methods configured", {
                        "payment_methods": payment_methods,
                        "paypal_username": paypal_username,
                        "venmo_username": venmo_username,
                        "zelle_email": zelle_email
                    })
                else:
                    self.log_result("Payment Profile Configuration", False, "No payment methods configured in profile", {
                        "profile_fields": list(profile_data.keys())
                    })
                    
            else:
                self.log_result("Payment Profile Configuration", False, f"Failed to get profile: {response.status_code}")
                
        except Exception as e:
            self.log_result("Payment Profile Configuration", False, f"Error checking payment profile: {str(e)}")
        
        # Test 2: Test tip link generation endpoints (correct endpoint format)
        test_amounts = [5.00, 10.00, 20.00]
        
        for amount in test_amounts:
            try:
                response = requests.get(f"{PRODUCTION_BASE_URL}/musicians/{self.musician_slug}/tip-links", 
                                      params={"amount": amount, "message": "Test tip"}, 
                                      timeout=30)
                
                if response.status_code == 200:
                    tip_data = response.json()
                    paypal_link = tip_data.get("paypal_link")
                    venmo_link = tip_data.get("venmo_link")
                    
                    if paypal_link or venmo_link:
                        self.log_result(f"Tip Link Generation - Amount ${amount}", True, f"Successfully generated tip links", {
                            "amount": amount,
                            "paypal_link": paypal_link,
                            "venmo_link": venmo_link,
                            "paypal_valid": "paypal.me/" in (paypal_link or "") if paypal_link else False,
                            "venmo_valid": "venmo.com/" in (venmo_link or "") if venmo_link else False
                        })
                    else:
                        self.log_result(f"Tip Link Generation - Amount ${amount}", False, f"No tip links in response", {
                            "response_data": tip_data
                        })
                else:
                    self.log_result(f"Tip Link Generation - Amount ${amount}", False, f"Failed to generate tip links: {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.log_result(f"Tip Link Generation - Amount ${amount}", False, f"Error generating tip links: {str(e)}")
        
        # Test 3: Test tip recording functionality (correct endpoint format)
        try:
            tip_record_data = {
                "amount": 5.00,
                "platform": "paypal",
                "tipper_name": "Test Tipper",
                "message": "Test tip recording"
            }
            
            response = requests.post(f"{PRODUCTION_BASE_URL}/musicians/{self.musician_slug}/tips", 
                                   json=tip_record_data, timeout=30)
            
            if response.status_code == 200:
                tip_response = response.json()
                self.log_result("Tip Recording", True, f"Successfully recorded tip", {
                    "tip_id": tip_response.get("id"),
                    "amount": tip_response.get("amount"),
                    "platform": tip_response.get("platform")
                })
            else:
                self.log_result("Tip Recording", False, f"Failed to record tip: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Tip Recording", False, f"Error recording tip: {str(e)}")
    
    def test_tip_integration_with_requests(self):
        """Test tip integration with request creation flow"""
        print("\n=== Testing Tip Integration with Request Flow ===")
        
        if not self.musician_slug:
            self.log_result("Tip Integration", False, "No musician slug available")
            return False
        
        # Get musician's public profile to check tip settings
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}/musicians/{self.musician_slug}", timeout=30)
            
            if response.status_code == 200:
                musician_data = response.json()
                tips_enabled = musician_data.get("tips_enabled", True)
                
                self.log_result("Musician Public Profile - Tips", True, f"Retrieved musician public profile", {
                    "tips_enabled": tips_enabled,
                    "paypal_username": musician_data.get("paypal_username"),
                    "venmo_username": musician_data.get("venmo_username"),
                    "profile_fields": list(musician_data.keys())
                })
                
                if not tips_enabled:
                    self.log_result("Tips Enabled Check", False, "Tips are disabled for this musician")
                    return False
                    
            else:
                self.log_result("Musician Public Profile - Tips", False, f"Failed to get public profile: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Musician Public Profile - Tips", False, f"Error getting public profile: {str(e)}")
            return False
        
        # Test creating a request with tip integration
        try:
            # Get a song for the request
            response = requests.get(f"{PRODUCTION_BASE_URL}/musicians/{self.musician_slug}/songs", timeout=30)
            
            if response.status_code == 200:
                songs_data = response.json()
                if songs_data:
                    test_song = songs_data[0]
                    
                    # Create request with tip integration test
                    request_data = {
                        "song_id": test_song.get("id"),
                        "requester_name": "Tip Integration Test",
                        "requester_email": "tiptest@requestwave.com",
                        "dedication": "Testing tip integration - please ignore",
                        "tip_amount": 0.0  # Include required field
                    }
                    
                    response = requests.post(f"{PRODUCTION_BASE_URL}/requests", json=request_data, timeout=30)
                    
                    if response.status_code == 200:
                        request_response = response.json()
                        request_id = request_response.get("id")
                        self.test_request_ids.append(request_id)
                        
                        # Check if request has tip-related fields
                        tip_clicked = request_response.get("tip_clicked", False)
                        social_clicks = request_response.get("social_clicks", [])
                        
                        self.log_result("Request with Tip Integration", True, f"Successfully created request with tip fields", {
                            "request_id": request_id,
                            "tip_clicked": tip_clicked,
                            "social_clicks": social_clicks,
                            "has_tip_fields": "tip_clicked" in request_response
                        })
                        
                        # Test tip click tracking
                        self.test_tip_click_tracking(request_id)
                        
                    else:
                        self.log_result("Request with Tip Integration", False, f"Failed to create request: {response.status_code}")
                        
        except Exception as e:
            self.log_result("Request with Tip Integration", False, f"Error testing tip integration: {str(e)}")
    
    def test_tip_click_tracking(self, request_id):
        """Test tip click tracking functionality"""
        print(f"\n=== Testing Tip Click Tracking for {request_id} ===")
        
        platforms = ["paypal", "venmo"]
        
        for platform in platforms:
            try:
                response = requests.post(f"{PRODUCTION_BASE_URL}/requests/{request_id}/track-click", 
                                       json={"platform": platform}, timeout=30)
                
                if response.status_code == 200:
                    self.log_result(f"Tip Click Tracking - {platform.title()}", True, f"Successfully tracked {platform} tip click", {
                        "request_id": request_id,
                        "platform": platform
                    })
                else:
                    self.log_result(f"Tip Click Tracking - {platform.title()}", False, f"Failed to track {platform} click: {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.log_result(f"Tip Click Tracking - {platform.title()}", False, f"Error tracking {platform} click: {str(e)}")
    
    def cleanup_test_requests(self):
        """Clean up test requests created during testing"""
        print("\n=== Cleaning Up Test Requests ===")
        
        if not self.test_request_ids:
            print("No test requests to clean up")
            return
        
        headers = self.get_headers()
        cleaned_count = 0
        
        for request_id in self.test_request_ids:
            try:
                response = requests.delete(f"{PRODUCTION_BASE_URL}/requests/{request_id}", 
                                         headers=headers, timeout=30)
                
                if response.status_code == 200:
                    cleaned_count += 1
                    print(f"✅ Cleaned up test request: {request_id}")
                else:
                    print(f"❌ Failed to clean up request {request_id}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error cleaning up request {request_id}: {str(e)}")
        
        print(f"Cleaned up {cleaned_count}/{len(self.test_request_ids)} test requests")
    
    def run_all_tests(self):
        """Run all production bug investigation tests"""
        print("🚀 Starting Production Bug Investigation Tests")
        print(f"Production API: {PRODUCTION_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        try:
            # Bug #1 - Request Visibility Testing
            print("\n🐛 BUG #1 INVESTIGATION: Request Visibility Issues")
            print("Testing: New requests not showing up in On Stage tab or Songs tab")
            self.test_request_management_endpoints()
            self.test_request_creation_from_audience()
            self.test_request_status_updates()
            
            # Bug #2 - Tip Button Error Testing
            print("\n🐛 BUG #2 INVESTIGATION: Tip Button Error")
            print("Testing: Send tip button returning error when making request from audience link")
            self.test_tip_functionality()
            self.test_tip_integration_with_requests()
            
        finally:
            # Always clean up test data
            self.cleanup_test_requests()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 PRODUCTION BUG INVESTIGATION SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results by bug
        bug1_results = [r for r in self.results if any(keyword in r["test"].lower() 
                       for keyword in ["request", "visibility", "status", "musician", "audience"])]
        bug2_results = [r for r in self.results if any(keyword in r["test"].lower() 
                       for keyword in ["tip", "payment", "link", "click"])]
        
        print(f"\n🐛 BUG #1 - REQUEST VISIBILITY:")
        bug1_passed = len([r for r in bug1_results if r["success"]])
        bug1_total = len(bug1_results)
        print(f"   Tests: {bug1_passed}/{bug1_total} passed")
        
        bug1_failures = [r for r in bug1_results if not r["success"]]
        if bug1_failures:
            print("   ❌ FAILURES:")
            for result in bug1_failures:
                print(f"      - {result['test']}: {result['message']}")
        
        print(f"\n🐛 BUG #2 - TIP BUTTON ERROR:")
        bug2_passed = len([r for r in bug2_results if r["success"]])
        bug2_total = len(bug2_results)
        print(f"   Tests: {bug2_passed}/{bug2_total} passed")
        
        bug2_failures = [r for r in bug2_results if not r["success"]]
        if bug2_failures:
            print("   ❌ FAILURES:")
            for result in bug2_failures:
                print(f"      - {result['test']}: {result['message']}")
        
        # Root cause analysis
        print(f"\n🔍 ROOT CAUSE ANALYSIS:")
        
        critical_failures = [r for r in self.results if not r["success"] and 
                           any(keyword in r["test"].lower() for keyword in 
                               ["visibility", "creation", "tip link", "authentication"])]
        
        if critical_failures:
            print("❌ CRITICAL ISSUES IDENTIFIED:")
            for result in critical_failures:
                print(f"   - {result['test']}: {result['message']}")
        else:
            print("✅ No critical issues found - bugs may be frontend-related or intermittent")
        
        print("\n🎯 PRODUCTION BUG INVESTIGATION COMPLETE")
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = ProductionBugTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)