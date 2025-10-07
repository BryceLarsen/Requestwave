#!/usr/bin/env python3
"""
Analytics Endpoints Test Suite for RequestWave
Testing analytics endpoints specifically to identify the issue with "Loading analytics..." in the frontend
Focus: GET /api/analytics/daily?days=7 and GET /api/analytics/requesters endpoints
"""

import requests
import json
import sys
from datetime import datetime
import time

# Configuration
INTERNAL_BASE_URL = "http://localhost:8001/api"
EXTERNAL_BASE_URL = "https://request-error-fix.preview.emergentagent.com/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class AnalyticsEndpointsTester:
    def __init__(self):
        self.internal_token = None
        self.external_token = None
        self.musician_id = None
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
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
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
                
                self.log_result("Internal Authentication", True, f"Successfully authenticated {TEST_EMAIL}", {
                    "musician_id": self.musician_id,
                    "musician_name": musician_data.get("name"),
                    "token_length": len(self.internal_token) if self.internal_token else 0
                })
            else:
                self.log_result("Internal Authentication", False, f"Login failed: {response.status_code} - {response.text}")
                
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
                self.log_result("External Authentication", True, f"Successfully authenticated {TEST_EMAIL} on external API")
            else:
                self.log_result("External Authentication", False, f"External login failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("External Authentication", False, f"External auth error: {str(e)}")
    
    def test_analytics_daily_endpoint(self, base_url, token, api_type):
        """Test GET /api/analytics/daily?days=7 endpoint"""
        print(f"\n=== Testing Analytics Daily Endpoint ({api_type}) ===")
        
        if not token:
            self.log_result(f"Analytics Daily - {api_type}", False, f"No {api_type} token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Test different day parameters
        day_params = [7, 30, 365]
        
        for days in day_params:
            try:
                response = requests.get(f"{base_url}/analytics/daily?days={days}", headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verify response structure
                    expected_fields = ["daily_stats", "top_songs", "top_requesters", "totals"]
                    missing_fields = [field for field in expected_fields if field not in data]
                    
                    if not missing_fields:
                        self.log_result(f"Analytics Daily {days}d - {api_type}", True, f"Successfully retrieved daily analytics for {days} days", {
                            "response_fields": list(data.keys()),
                            "daily_stats_count": len(data.get("daily_stats", [])),
                            "top_songs_count": len(data.get("top_songs", [])),
                            "top_requesters_count": len(data.get("top_requesters", [])),
                            "totals": data.get("totals", {})
                        })
                    else:
                        self.log_result(f"Analytics Daily {days}d - {api_type}", False, f"Response missing required fields: {missing_fields}", {
                            "response_data": data
                        })
                elif response.status_code == 401:
                    self.log_result(f"Analytics Daily {days}d - {api_type}", False, "Authentication failed - token may be invalid or expired")
                elif response.status_code == 403:
                    self.log_result(f"Analytics Daily {days}d - {api_type}", False, "Access forbidden - user may not have required permissions")
                else:
                    self.log_result(f"Analytics Daily {days}d - {api_type}", False, f"Request failed: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                self.log_result(f"Analytics Daily {days}d - {api_type}", False, f"Request timeout after 30 seconds")
            except Exception as e:
                self.log_result(f"Analytics Daily {days}d - {api_type}", False, f"Request error: {str(e)}")
    
    def test_analytics_requesters_endpoint(self, base_url, token, api_type):
        """Test GET /api/analytics/requesters endpoint"""
        print(f"\n=== Testing Analytics Requesters Endpoint ({api_type}) ===")
        
        if not token:
            self.log_result(f"Analytics Requesters - {api_type}", False, f"No {api_type} token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(f"{base_url}/analytics/requesters", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                if "requesters" in data:
                    requesters = data["requesters"]
                    
                    # Check structure of requester objects
                    if requesters and len(requesters) > 0:
                        first_requester = requesters[0]
                        expected_requester_fields = ["name", "email", "request_count", "total_tips", "latest_request"]
                        missing_requester_fields = [field for field in expected_requester_fields if field not in first_requester]
                        
                        if not missing_requester_fields:
                            self.log_result(f"Analytics Requesters - {api_type}", True, f"Successfully retrieved requesters analytics", {
                                "requesters_count": len(requesters),
                                "sample_requester": first_requester,
                                "response_structure": "Valid"
                            })
                        else:
                            self.log_result(f"Analytics Requesters - {api_type}", False, f"Requester objects missing fields: {missing_requester_fields}", {
                                "sample_requester": first_requester
                            })
                    else:
                        self.log_result(f"Analytics Requesters - {api_type}", True, f"Successfully retrieved requesters analytics (empty list)", {
                            "requesters_count": 0,
                            "message": "No requesters found - this is valid if user has no requests"
                        })
                else:
                    self.log_result(f"Analytics Requesters - {api_type}", False, "Response missing 'requesters' field", {
                        "response_data": data
                    })
            elif response.status_code == 401:
                self.log_result(f"Analytics Requesters - {api_type}", False, "Authentication failed - token may be invalid or expired")
            elif response.status_code == 403:
                self.log_result(f"Analytics Requesters - {api_type}", False, "Access forbidden - user may not have required permissions")
            else:
                self.log_result(f"Analytics Requesters - {api_type}", False, f"Request failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            self.log_result(f"Analytics Requesters - {api_type}", False, f"Request timeout after 30 seconds")
        except Exception as e:
            self.log_result(f"Analytics Requesters - {api_type}", False, f"Request error: {str(e)}")
    
    def test_analytics_export_endpoint(self, base_url, token, api_type):
        """Test GET /api/analytics/export-requesters endpoint"""
        print(f"\n=== Testing Analytics Export Endpoint ({api_type}) ===")
        
        if not token:
            self.log_result(f"Analytics Export - {api_type}", False, f"No {api_type} token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(f"{base_url}/analytics/export-requesters", headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Check if response is CSV format
                content_type = response.headers.get('content-type', '')
                content_disposition = response.headers.get('content-disposition', '')
                
                if 'text/csv' in content_type or 'csv' in content_disposition:
                    csv_content = response.text
                    lines = csv_content.strip().split('\n')
                    
                    self.log_result(f"Analytics Export - {api_type}", True, f"Successfully retrieved CSV export", {
                        "content_type": content_type,
                        "content_disposition": content_disposition,
                        "csv_lines": len(lines),
                        "csv_header": lines[0] if lines else "No header",
                        "csv_sample": lines[1] if len(lines) > 1 else "No data rows"
                    })
                else:
                    self.log_result(f"Analytics Export - {api_type}", False, f"Response not in CSV format", {
                        "content_type": content_type,
                        "response_preview": response.text[:200]
                    })
            elif response.status_code == 401:
                self.log_result(f"Analytics Export - {api_type}", False, "Authentication failed - token may be invalid or expired")
            elif response.status_code == 403:
                self.log_result(f"Analytics Export - {api_type}", False, "Access forbidden - user may not have required permissions")
            else:
                self.log_result(f"Analytics Export - {api_type}", False, f"Request failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            self.log_result(f"Analytics Export - {api_type}", False, f"Request timeout after 30 seconds")
        except Exception as e:
            self.log_result(f"Analytics Export - {api_type}", False, f"Request error: {str(e)}")
    
    def test_user_data_availability(self):
        """Test if user has any data that would show up in analytics"""
        print(f"\n=== Testing User Data Availability ===")
        
        if not self.internal_token:
            self.log_result("User Data Check", False, "No internal token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Check requests
            response = requests.get(f"{INTERNAL_BASE_URL}/requests/musician/{self.musician_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                requests_data = response.json()
                requests_count = len(requests_data) if isinstance(requests_data, list) else 0
                
                self.log_result("User Data - Requests", True, f"Found {requests_count} requests", {
                    "requests_count": requests_count,
                    "sample_request": requests_data[0] if requests_count > 0 else None
                })
            else:
                self.log_result("User Data - Requests", False, f"Failed to get requests: {response.status_code}")
            
            # Check songs
            response = requests.get(f"{INTERNAL_BASE_URL}/songs", headers=headers, timeout=10)
            
            if response.status_code == 200:
                songs_data = response.json()
                songs_count = len(songs_data) if isinstance(songs_data, list) else 0
                
                self.log_result("User Data - Songs", True, f"Found {songs_count} songs", {
                    "songs_count": songs_count
                })
            else:
                self.log_result("User Data - Songs", False, f"Failed to get songs: {response.status_code}")
                
        except Exception as e:
            self.log_result("User Data Check", False, f"Data check error: {str(e)}")
    
    def test_authentication_headers(self):
        """Test different authentication header formats"""
        print(f"\n=== Testing Authentication Header Formats ===")
        
        if not self.internal_token:
            self.log_result("Auth Headers Test", False, "No internal token available")
            return False
        
        # Test different header formats
        header_formats = [
            {"Authorization": f"Bearer {self.internal_token}"},
            {"Authorization": f"bearer {self.internal_token}"},  # lowercase
            {"authorization": f"Bearer {self.internal_token}"},  # lowercase header
        ]
        
        for i, headers in enumerate(header_formats):
            try:
                response = requests.get(f"{INTERNAL_BASE_URL}/analytics/daily?days=7", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    self.log_result(f"Auth Headers Format {i+1}", True, f"Header format accepted", {
                        "headers": headers,
                        "status_code": response.status_code
                    })
                else:
                    self.log_result(f"Auth Headers Format {i+1}", False, f"Header format rejected: {response.status_code}", {
                        "headers": headers
                    })
                    
            except Exception as e:
                self.log_result(f"Auth Headers Format {i+1}", False, f"Header test error: {str(e)}")
    
    def run_all_tests(self):
        """Run all analytics endpoint tests"""
        print("🚀 Starting Analytics Endpoints Backend Tests")
        print(f"Internal API: {INTERNAL_BASE_URL}")
        print(f"External API: {EXTERNAL_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print("Focus: Analytics endpoints issue investigation")
        print("=" * 80)
        
        # Authenticate first
        self.authenticate()
        
        # Test authentication headers
        self.test_authentication_headers()
        
        # Test user data availability
        self.test_user_data_availability()
        
        # Test analytics endpoints on both APIs
        if self.internal_token:
            self.test_analytics_daily_endpoint(INTERNAL_BASE_URL, self.internal_token, "Internal")
            self.test_analytics_requesters_endpoint(INTERNAL_BASE_URL, self.internal_token, "Internal")
            self.test_analytics_export_endpoint(INTERNAL_BASE_URL, self.internal_token, "Internal")
        
        if self.external_token:
            self.test_analytics_daily_endpoint(EXTERNAL_BASE_URL, self.external_token, "External")
            self.test_analytics_requesters_endpoint(EXTERNAL_BASE_URL, self.external_token, "External")
            self.test_analytics_export_endpoint(EXTERNAL_BASE_URL, self.external_token, "External")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 ANALYTICS ENDPOINTS TEST SUMMARY")
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
                if any(keyword in result["test"].lower() for keyword in ["analytics daily", "analytics requesters", "authentication"]):
                    critical_failures.append(result)
                else:
                    minor_failures.append(result)
        
        if critical_failures:
            print("\n❌ CRITICAL FAILURES (Analytics Issues):")
            for result in critical_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        if minor_failures:
            print("\n⚠️ MINOR FAILURES:")
            for result in minor_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        # Key findings for analytics issue
        print("\n🔍 ANALYTICS ISSUE INVESTIGATION FINDINGS:")
        
        analytics_tests = [r for r in self.results if "analytics" in r["test"].lower()]
        working_analytics = [r for r in analytics_tests if r["success"]]
        failing_analytics = [r for r in analytics_tests if not r["success"]]
        
        if working_analytics:
            print(f"✅ Working Analytics Endpoints: {len(working_analytics)}")
            for test in working_analytics:
                print(f"   - {test['test']}")
        
        if failing_analytics:
            print(f"❌ Failing Analytics Endpoints: {len(failing_analytics)}")
            for test in failing_analytics:
                print(f"   - {test['test']}: {test['message']}")
        
        # Root cause analysis
        print("\n🎯 ROOT CAUSE ANALYSIS:")
        if not self.internal_token and not self.external_token:
            print("❌ AUTHENTICATION FAILURE: Cannot authenticate with either API")
        elif failing_analytics:
            print("❌ ANALYTICS ENDPOINTS FAILING: Specific issues with analytics endpoints")
        elif not working_analytics:
            print("❌ NO ANALYTICS DATA: Endpoints working but returning no data")
        else:
            print("✅ ANALYTICS ENDPOINTS WORKING: Issue may be frontend-related")
        
        print("\n🎯 ANALYTICS ENDPOINTS TEST COMPLETE")
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = AnalyticsEndpointsTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)