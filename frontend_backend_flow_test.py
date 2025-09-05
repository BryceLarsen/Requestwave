#!/usr/bin/env python3
"""
Frontend-Backend Request Flow Debugging Test Suite
Testing the exact request creation flow from audience interface to identify
why frontend shows "error creating request" despite backend working in isolation.

Focus Areas:
1. Frontend Request Flow Testing - Test exact request creation from audience interface
2. Audience Interface API Testing - Test POST /api/requests from audience perspective
3. Frontend Environment Detection - Verify frontend calls correct preview backend
4. Analytics Endpoint Testing - Test analytics endpoints causing infinite loading
5. Error Response Analysis - Capture actual backend responses vs frontend errors
"""

import requests
import json
import sys
from datetime import datetime
import time
import uuid

# Configuration - Using preview environment URLs from .env files
PREVIEW_BACKEND_URL = "https://requestwave-app.preview.emergentagent.com/api"
PREVIEW_FRONTEND_URL = "https://requestwave-app.preview.emergentagent.com"
INTERNAL_BACKEND_URL = "http://localhost:8001/api"

# Test musician data (Bryce Larsen)
TEST_MUSICIAN_SLUG = "bryce-larsen"
TEST_MUSICIAN_EMAIL = "brycelarsenmusic@gmail.com"
TEST_MUSICIAN_PASSWORD = "RequestWave2024!"

class FrontendBackendFlowTester:
    def __init__(self):
        self.musician_token = None
        self.musician_id = None
        self.musician_data = None
        self.test_song_id = None
        self.test_request_id = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details and isinstance(details, dict):
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def setup_test_environment(self):
        """Setup test environment by authenticating and getting musician data"""
        print("\n=== Setting Up Test Environment ===")
        
        # First try to authenticate with preview backend
        try:
            response = requests.post(f"{PREVIEW_BACKEND_URL}/auth/login", json={
                "email": TEST_MUSICIAN_EMAIL,
                "password": TEST_MUSICIAN_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.musician_token = data.get("token")
                self.musician_data = data.get("musician", {})
                self.musician_id = self.musician_data.get("id")
                
                self.log_result("Environment Setup - Authentication", True, 
                              f"Successfully authenticated {TEST_MUSICIAN_EMAIL}", {
                    "musician_id": self.musician_id,
                    "musician_name": self.musician_data.get("name"),
                    "backend_url": PREVIEW_BACKEND_URL
                })
                return True
            else:
                self.log_result("Environment Setup - Authentication", False, 
                              f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Environment Setup - Authentication", False, 
                          f"Authentication error: {str(e)}")
            return False
    
    def test_audience_musician_profile_access(self):
        """Test audience access to musician profile (no auth required)"""
        print("\n=== Testing Audience Musician Profile Access ===")
        
        try:
            # Test preview backend
            response = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}", timeout=30)
            
            if response.status_code == 200:
                profile_data = response.json()
                
                # Check required fields for audience interface
                required_fields = ["id", "name", "slug", "requests_enabled", "tips_enabled"]
                missing_fields = [field for field in required_fields if field not in profile_data]
                
                if not missing_fields:
                    self.log_result("Audience Profile Access", True, 
                                  f"Successfully retrieved musician profile for audience", {
                        "musician_name": profile_data.get("name"),
                        "requests_enabled": profile_data.get("requests_enabled"),
                        "tips_enabled": profile_data.get("tips_enabled"),
                        "profile_fields": list(profile_data.keys())
                    })
                    return profile_data
                else:
                    self.log_result("Audience Profile Access", False, 
                                  f"Profile missing required fields: {missing_fields}")
                    return None
            else:
                self.log_result("Audience Profile Access", False, 
                              f"Failed to get musician profile: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Audience Profile Access", False, 
                          f"Profile access error: {str(e)}")
            return None
    
    def test_audience_songs_access(self):
        """Test audience access to musician's songs (no auth required)"""
        print("\n=== Testing Audience Songs Access ===")
        
        try:
            response = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/songs", timeout=30)
            
            if response.status_code == 200:
                songs_data = response.json()
                
                if isinstance(songs_data, list) and len(songs_data) > 0:
                    # Get first song for testing request creation
                    test_song = songs_data[0]
                    self.test_song_id = test_song.get("id")
                    
                    self.log_result("Audience Songs Access", True, 
                                  f"Successfully retrieved {len(songs_data)} songs for audience", {
                        "songs_count": len(songs_data),
                        "test_song_title": test_song.get("title"),
                        "test_song_artist": test_song.get("artist"),
                        "test_song_id": self.test_song_id
                    })
                    return songs_data
                else:
                    self.log_result("Audience Songs Access", False, 
                                  f"No songs found or invalid response format")
                    return None
            else:
                self.log_result("Audience Songs Access", False, 
                              f"Failed to get songs: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Audience Songs Access", False, 
                          f"Songs access error: {str(e)}")
            return None
    
    def test_audience_request_creation_preview_backend(self):
        """Test request creation from audience perspective using preview backend"""
        print("\n=== Testing Audience Request Creation (Preview Backend) ===")
        
        if not self.test_song_id:
            self.log_result("Audience Request Creation - Preview", False, 
                          "No test song ID available")
            return False
        
        try:
            # Create request as audience member (no authentication)
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Test Audience Member",
                "requester_email": "testaudience@example.com",
                "dedication": "Testing frontend-backend flow"
            }
            
            response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                   json=request_data, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                self.test_request_id = response_data.get("id")
                
                # Verify response structure
                required_fields = ["id", "musician_id", "song_id", "song_title", "song_artist", 
                                 "requester_name", "requester_email", "status", "created_at"]
                missing_fields = [field for field in required_fields if field not in response_data]
                
                if not missing_fields:
                    self.log_result("Audience Request Creation - Preview", True, 
                                  "Successfully created request from audience perspective", {
                        "request_id": self.test_request_id,
                        "song_title": response_data.get("song_title"),
                        "song_artist": response_data.get("song_artist"),
                        "status": response_data.get("status"),
                        "response_fields": list(response_data.keys())
                    })
                    return True
                else:
                    self.log_result("Audience Request Creation - Preview", False, 
                                  f"Response missing required fields: {missing_fields}", {
                        "response_data": response_data
                    })
                    return False
            else:
                self.log_result("Audience Request Creation - Preview", False, 
                              f"Request creation failed: {response.status_code} - {response.text}", {
                    "request_payload": request_data,
                    "response_headers": dict(response.headers)
                })
                return False
                
        except Exception as e:
            self.log_result("Audience Request Creation - Preview", False, 
                          f"Request creation error: {str(e)}")
            return False
    
    def test_audience_request_creation_internal_backend(self):
        """Test request creation using internal backend for comparison"""
        print("\n=== Testing Audience Request Creation (Internal Backend) ===")
        
        if not self.test_song_id:
            self.log_result("Audience Request Creation - Internal", False, 
                          "No test song ID available")
            return False
        
        try:
            # Create request as audience member (no authentication)
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Test Audience Member Internal",
                "requester_email": "testinternal@example.com",
                "dedication": "Testing internal backend flow"
            }
            
            response = requests.post(f"{INTERNAL_BACKEND_URL}/requests", 
                                   json=request_data, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                
                self.log_result("Audience Request Creation - Internal", True, 
                              "Successfully created request via internal backend", {
                    "request_id": response_data.get("id"),
                    "song_title": response_data.get("song_title"),
                    "song_artist": response_data.get("song_artist"),
                    "status": response_data.get("status")
                })
                return True
            else:
                self.log_result("Audience Request Creation - Internal", False, 
                              f"Internal request creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Audience Request Creation - Internal", False, 
                          f"Internal request creation error: {str(e)}")
            return False
    
    def test_musician_specific_request_endpoint(self):
        """Test the musician-specific request endpoint POST /musicians/{slug}/requests"""
        print("\n=== Testing Musician-Specific Request Endpoint ===")
        
        if not self.test_song_id:
            self.log_result("Musician Request Endpoint", False, 
                          "No test song ID available")
            return False
        
        try:
            # Test the musician-specific endpoint
            request_data = {
                "song_id": self.test_song_id,
                "requester_name": "Test Musician Endpoint",
                "requester_email": "testmusicianendpoint@example.com",
                "dedication": "Testing musician-specific endpoint"
            }
            
            response = requests.post(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/requests", 
                                   json=request_data, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                self.log_result("Musician Request Endpoint", True, 
                              "Successfully created request via musician-specific endpoint", {
                    "request_id": response_data.get("id"),
                    "endpoint": f"/musicians/{TEST_MUSICIAN_SLUG}/requests",
                    "song_title": response_data.get("song_title"),
                    "status": response_data.get("status")
                })
                return True
            else:
                self.log_result("Musician Request Endpoint", False, 
                              f"Musician endpoint failed: {response.status_code} - {response.text}", {
                    "endpoint": f"/musicians/{TEST_MUSICIAN_SLUG}/requests",
                    "request_payload": request_data
                })
                return False
                
        except Exception as e:
            self.log_result("Musician Request Endpoint", False, 
                          f"Musician endpoint error: {str(e)}")
            return False
    
    def test_analytics_endpoints(self):
        """Test analytics endpoints that were causing infinite loading"""
        print("\n=== Testing Analytics Endpoints ===")
        
        if not self.musician_token:
            self.log_result("Analytics Endpoints", False, 
                          "No musician token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.musician_token}",
            "Content-Type": "application/json"
        }
        
        analytics_endpoints = [
            ("/analytics/requesters", "Requester Analytics"),
            ("/analytics/daily", "Daily Analytics"),
            ("/analytics/export-requesters", "CSV Export"),
            ("/requests/grouped", "Grouped Requests")
        ]
        
        for endpoint, description in analytics_endpoints:
            try:
                response = requests.get(f"{PREVIEW_BACKEND_URL}{endpoint}", 
                                      headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(f"Analytics - {description}", True, 
                                  f"Successfully retrieved {description.lower()}", {
                        "endpoint": endpoint,
                        "response_type": type(data).__name__,
                        "data_size": len(str(data))
                    })
                else:
                    self.log_result(f"Analytics - {description}", False, 
                                  f"Analytics endpoint failed: {response.status_code} - {response.text}", {
                        "endpoint": endpoint
                    })
                    
            except requests.exceptions.Timeout:
                self.log_result(f"Analytics - {description}", False, 
                              f"Analytics endpoint timed out (30s)", {
                    "endpoint": endpoint,
                    "issue": "timeout"
                })
            except Exception as e:
                self.log_result(f"Analytics - {description}", False, 
                              f"Analytics endpoint error: {str(e)}", {
                    "endpoint": endpoint
                })
    
    def test_frontend_environment_variables(self):
        """Test if frontend environment variables are correctly configured"""
        print("\n=== Testing Frontend Environment Configuration ===")
        
        # Check if the frontend is calling the correct backend URL
        expected_backend_url = "https://requestwave-app.preview.emergentagent.com"
        
        # Test a simple endpoint to verify the backend URL is accessible
        try:
            response = requests.get(f"{expected_backend_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                self.log_result("Frontend Environment - Backend URL", True, 
                              "Frontend backend URL is accessible", {
                    "backend_url": expected_backend_url,
                    "health_check": "passed"
                })
            else:
                self.log_result("Frontend Environment - Backend URL", False, 
                              f"Backend URL health check failed: {response.status_code}")
                
        except Exception as e:
            self.log_result("Frontend Environment - Backend URL", False, 
                          f"Backend URL accessibility error: {str(e)}")
        
        # Test CORS headers
        try:
            response = requests.options(f"{PREVIEW_BACKEND_URL}/requests", 
                                      headers={"Origin": PREVIEW_FRONTEND_URL}, timeout=10)
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
            }
            
            self.log_result("Frontend Environment - CORS", True, 
                          "CORS preflight check completed", {
                "cors_headers": cors_headers,
                "origin": PREVIEW_FRONTEND_URL
            })
            
        except Exception as e:
            self.log_result("Frontend Environment - CORS", False, 
                          f"CORS check error: {str(e)}")
    
    def test_error_response_analysis(self):
        """Test error responses to understand what frontend might be receiving"""
        print("\n=== Testing Error Response Analysis ===")
        
        # Test invalid request data to see error format
        try:
            invalid_request_data = {
                "song_id": "invalid-song-id",
                "requester_name": "",  # Empty name
                "requester_email": "invalid-email",  # Invalid email
                "dedication": "Testing error responses"
            }
            
            response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                   json=invalid_request_data, timeout=30)
            
            self.log_result("Error Response Analysis - Invalid Data", True, 
                          f"Got error response for invalid data: {response.status_code}", {
                "status_code": response.status_code,
                "error_response": response.text[:500],  # First 500 chars
                "content_type": response.headers.get("Content-Type")
            })
            
        except Exception as e:
            self.log_result("Error Response Analysis - Invalid Data", False, 
                          f"Error response test failed: {str(e)}")
        
        # Test missing required fields
        try:
            incomplete_request_data = {
                "requester_name": "Test User"
                # Missing song_id, requester_email
            }
            
            response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                   json=incomplete_request_data, timeout=30)
            
            self.log_result("Error Response Analysis - Missing Fields", True, 
                          f"Got error response for missing fields: {response.status_code}", {
                "status_code": response.status_code,
                "error_response": response.text[:500],
                "content_type": response.headers.get("Content-Type")
            })
            
        except Exception as e:
            self.log_result("Error Response Analysis - Missing Fields", False, 
                          f"Missing fields test failed: {str(e)}")
    
    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n=== Cleaning Up Test Data ===")
        
        if not self.musician_token or not self.test_request_id:
            self.log_result("Cleanup", True, "No test data to clean up")
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.musician_token}",
                "Content-Type": "application/json"
            }
            
            # Delete test request
            response = requests.delete(f"{PREVIEW_BACKEND_URL}/requests/{self.test_request_id}", 
                                     headers=headers, timeout=10)
            
            if response.status_code in [200, 204, 404]:  # 404 is OK if already deleted
                self.log_result("Cleanup", True, "Successfully cleaned up test data", {
                    "deleted_request_id": self.test_request_id
                })
            else:
                self.log_result("Cleanup", False, 
                              f"Failed to delete test request: {response.status_code}")
                
        except Exception as e:
            self.log_result("Cleanup", False, f"Cleanup error: {str(e)}")
    
    def run_all_tests(self):
        """Run all frontend-backend flow tests"""
        print("🚀 Starting Frontend-Backend Request Flow Debugging Tests")
        print(f"Preview Backend: {PREVIEW_BACKEND_URL}")
        print(f"Preview Frontend: {PREVIEW_FRONTEND_URL}")
        print(f"Internal Backend: {INTERNAL_BACKEND_URL}")
        print(f"Test Musician: {TEST_MUSICIAN_SLUG}")
        print("=" * 80)
        
        # Setup
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment. Aborting tests.")
            return False
        
        # Run core tests
        self.test_audience_musician_profile_access()
        self.test_audience_songs_access()
        self.test_audience_request_creation_preview_backend()
        self.test_audience_request_creation_internal_backend()
        self.test_musician_specific_request_endpoint()
        self.test_analytics_endpoints()
        self.test_frontend_environment_variables()
        self.test_error_response_analysis()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 FRONTEND-BACKEND FLOW TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize failures
        critical_failures = []
        minor_failures = []
        
        for result in self.results:
            if not result["success"]:
                if any(keyword in result["test"].lower() for keyword in 
                      ["request creation", "audience", "environment", "analytics"]):
                    critical_failures.append(result)
                else:
                    minor_failures.append(result)
        
        if critical_failures:
            print("\n❌ CRITICAL ISSUES FOUND:")
            for result in critical_failures:
                print(f"  - {result['test']}: {result['message']}")
                if result.get('details'):
                    for key, value in result['details'].items():
                        print(f"    {key}: {value}")
        
        if minor_failures:
            print("\n⚠️ MINOR ISSUES:")
            for result in minor_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        
        # Check request creation results
        preview_request_success = any(r["success"] for r in self.results 
                                    if "Audience Request Creation - Preview" in r["test"])
        internal_request_success = any(r["success"] for r in self.results 
                                     if "Audience Request Creation - Internal" in r["test"])
        
        if preview_request_success and internal_request_success:
            print("✅ Both preview and internal backends can create requests successfully")
        elif internal_request_success and not preview_request_success:
            print("❌ CRITICAL: Internal backend works but preview backend fails for requests")
        elif preview_request_success and not internal_request_success:
            print("⚠️ Preview backend works but internal backend has issues")
        else:
            print("❌ CRITICAL: Both backends failing for request creation")
        
        # Check analytics
        analytics_failures = [r for r in self.results if not r["success"] and "Analytics" in r["test"]]
        if analytics_failures:
            print(f"❌ Analytics endpoints have {len(analytics_failures)} issues")
        else:
            print("✅ Analytics endpoints working correctly")
        
        print("\n🎯 FRONTEND-BACKEND FLOW TEST COMPLETE")
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = FrontendBackendFlowTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)