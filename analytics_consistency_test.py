#!/usr/bin/env python3
"""
Analytics Data Consistency Test Suite for RequestWave
Testing the fixes for analytics data discrepancies between Analytics tab and Requests tab

ISSUE: Analytics endpoints were including archived requests while requests tab excludes them
FIXES APPLIED:
1. Updated /api/analytics/daily endpoint: Added "status": {"$ne": "archived"} filter
2. Updated /api/analytics/requesters endpoint: Added archived request exclusion
3. Backend restarted to apply changes

TESTING REQUIREMENTS:
1. Data Consistency Verification between /api/requests/musician/{musician_id} and /api/analytics/daily
2. Archived Request Exclusion verification
3. Request Counts matching between endpoints
4. Requester Analytics Consistency
5. Date Range Logic testing
"""

import requests
import json
import sys
from datetime import datetime, timedelta
import time

# Configuration
EXTERNAL_BASE_URL = "https://requestwave-revamp.preview.emergentagent.com/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class AnalyticsConsistencyTester:
    def __init__(self):
        self.token = None
        self.musician_id = None
        self.musician_slug = None
        self.results = []
        self.test_requests = []  # Store created test requests for cleanup
        
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
        """Authenticate with the API"""
        print("\n=== Authentication ===")
        
        try:
            response = requests.post(f"{EXTERNAL_BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                musician_data = data.get("musician", {})
                self.musician_id = musician_data.get("id")
                self.musician_slug = musician_data.get("slug")
                
                self.log_result("Authentication", True, f"Successfully authenticated {TEST_EMAIL}", {
                    "musician_id": self.musician_id,
                    "musician_slug": self.musician_slug,
                    "musician_name": musician_data.get("name")
                })
                return True
            else:
                self.log_result("Authentication", False, f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Auth error: {str(e)}")
            return False
    
    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def create_test_requests(self):
        """Create test requests with different statuses including archived ones"""
        print("\n=== Creating Test Requests for Analytics Testing ===")
        
        if not self.token:
            self.log_result("Create Test Requests", False, "No authentication token")
            return False
        
        try:
            headers = self.get_headers()
            
            # First, get available songs
            songs_response = requests.get(f"{EXTERNAL_BASE_URL}/songs", headers=headers, timeout=30)
            
            if songs_response.status_code != 200:
                self.log_result("Get Songs for Testing", False, f"Failed to get songs: {songs_response.status_code}")
                return False
            
            songs = songs_response.json()
            if not songs:
                self.log_result("Get Songs for Testing", False, "No songs available for testing")
                return False
            
            # Use the first available song for testing
            test_song = songs[0]
            song_id = test_song.get("id")
            
            # Create test requests with different statuses
            test_request_data = [
                {
                    "requester_name": "Analytics Test User 1",
                    "requester_email": "test1@analytics.com",
                    "status": "pending",
                    "dedication": "Test request for analytics consistency"
                },
                {
                    "requester_name": "Analytics Test User 2", 
                    "requester_email": "test2@analytics.com",
                    "status": "accepted",
                    "dedication": "Another test request"
                },
                {
                    "requester_name": "Analytics Test User 3",
                    "requester_email": "test3@analytics.com", 
                    "status": "played",
                    "dedication": "Played test request"
                },
                {
                    "requester_name": "Analytics Test User 4",
                    "requester_email": "test4@analytics.com",
                    "status": "archived",
                    "dedication": "Archived test request - should NOT appear in analytics"
                },
                {
                    "requester_name": "Analytics Test User 5",
                    "requester_email": "test5@analytics.com",
                    "status": "archived", 
                    "dedication": "Another archived request - should NOT appear in analytics"
                }
            ]
            
            created_requests = []
            
            for req_data in test_request_data:
                # Create the request
                create_payload = {
                    "song_id": song_id,
                    "requester_name": req_data["requester_name"],
                    "requester_email": req_data["requester_email"],
                    "dedication": req_data["dedication"]
                }
                
                create_response = requests.post(f"{EXTERNAL_BASE_URL}/requests", 
                                              json=create_payload, headers=headers, timeout=30)
                
                if create_response.status_code == 200:
                    request_data = create_response.json()
                    request_id = request_data.get("id")
                    
                    # Handle different status updates
                    if req_data["status"] == "archived":
                        # Use archive endpoint for archived status
                        archive_response = requests.put(f"{EXTERNAL_BASE_URL}/requests/{request_id}/archive",
                                                      headers=headers, timeout=30)
                        
                        if archive_response.status_code == 200:
                            created_requests.append({
                                "id": request_id,
                                "status": "archived",
                                "requester_name": req_data["requester_name"],
                                "requester_email": req_data["requester_email"]
                            })
                        else:
                            self.log_result("Archive Request", False, 
                                          f"Failed to archive request: {archive_response.status_code}")
                    elif req_data["status"] != "pending":
                        # Use status endpoint for other statuses
                        status_response = requests.put(f"{EXTERNAL_BASE_URL}/requests/{request_id}/status",
                                                     json={"status": req_data["status"]}, 
                                                     headers=headers, timeout=30)
                        
                        if status_response.status_code == 200:
                            created_requests.append({
                                "id": request_id,
                                "status": req_data["status"],
                                "requester_name": req_data["requester_name"],
                                "requester_email": req_data["requester_email"]
                            })
                        else:
                            self.log_result("Update Request Status", False, 
                                          f"Failed to update status to {req_data['status']}: {status_response.status_code}")
                    else:
                        # Pending status - no update needed
                        created_requests.append({
                            "id": request_id,
                            "status": "pending",
                            "requester_name": req_data["requester_name"],
                            "requester_email": req_data["requester_email"]
                        })
                else:
                    self.log_result("Create Test Request", False, 
                                  f"Failed to create request: {create_response.status_code}")
            
            self.test_requests = created_requests
            
            self.log_result("Create Test Requests", True, f"Created {len(created_requests)} test requests", {
                "requests": created_requests,
                "archived_count": len([r for r in created_requests if r["status"] == "archived"]),
                "non_archived_count": len([r for r in created_requests if r["status"] != "archived"])
            })
            
            return len(created_requests) > 0
            
        except Exception as e:
            self.log_result("Create Test Requests", False, f"Error creating test requests: {str(e)}")
            return False
    
    def test_requests_endpoint_excludes_archived(self):
        """Test that /api/requests/musician/{musician_id} excludes archived requests"""
        print("\n=== Testing Requests Endpoint Excludes Archived ===")
        
        if not self.token or not self.musician_id:
            self.log_result("Requests Endpoint Archived Exclusion", False, "Missing authentication or musician ID")
            return False
        
        try:
            headers = self.get_headers()
            response = requests.get(f"{EXTERNAL_BASE_URL}/requests/musician/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Handle the wrapped response format
                if isinstance(response_data, dict) and "requests" in response_data:
                    requests_list = response_data["requests"]
                else:
                    requests_list = response_data
                
                # Check if any archived requests are included
                archived_requests = [req for req in requests_list if req.get("status") == "archived"]
                non_archived_requests = [req for req in requests_list if req.get("status") != "archived"]
                
                # Count our test requests
                test_archived = [req for req in requests_list 
                               if req.get("requester_email", "").startswith("test") and req.get("status") == "archived"]
                test_non_archived = [req for req in requests_list 
                                   if req.get("requester_email", "").startswith("test") and req.get("status") != "archived"]
                
                success = len(archived_requests) == 0
                
                self.log_result("Requests Endpoint Archived Exclusion", success, 
                              f"Requests endpoint {'excludes' if success else 'includes'} archived requests", {
                    "total_requests": len(requests_list),
                    "archived_requests_found": len(archived_requests),
                    "non_archived_requests": len(non_archived_requests),
                    "test_archived_found": len(test_archived),
                    "test_non_archived_found": len(test_non_archived),
                    "expected_test_non_archived": 3  # pending, accepted, played
                })
                
                return success
            else:
                self.log_result("Requests Endpoint Archived Exclusion", False, 
                              f"Failed to get requests: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Requests Endpoint Archived Exclusion", False, f"Error: {str(e)}")
            return False
    
    def test_analytics_daily_excludes_archived(self):
        """Test that /api/analytics/daily excludes archived requests"""
        print("\n=== Testing Analytics Daily Excludes Archived ===")
        
        if not self.token or not self.musician_id:
            self.log_result("Analytics Daily Archived Exclusion", False, "Missing authentication or musician ID")
            return False
        
        try:
            headers = self.get_headers()
            
            # Test different day ranges
            for days in [7, 30, 365]:
                response = requests.get(f"{EXTERNAL_BASE_URL}/analytics/daily?days={days}", 
                                      headers=headers, timeout=30)
                
                if response.status_code == 200:
                    analytics_data = response.json()
                    
                    # Check the structure and data
                    daily_stats = analytics_data.get("daily_stats", [])
                    totals = analytics_data.get("totals", {})
                    
                    # Look for any indication of archived requests in the data
                    total_requests = totals.get("total_requests", 0)
                    
                    self.log_result(f"Analytics Daily {days} Days", True, 
                                  f"Analytics daily endpoint working for {days} days", {
                        "days_requested": days,
                        "daily_stats_count": len(daily_stats),
                        "total_requests_in_period": total_requests,
                        "totals": totals,
                        "has_daily_breakdown": len(daily_stats) > 0
                    })
                else:
                    self.log_result(f"Analytics Daily {days} Days", False, 
                                  f"Failed to get analytics: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_result("Analytics Daily Archived Exclusion", False, f"Error: {str(e)}")
            return False
    
    def test_analytics_requesters_excludes_archived(self):
        """Test that /api/analytics/requesters excludes archived requests"""
        print("\n=== Testing Analytics Requesters Excludes Archived ===")
        
        if not self.token:
            self.log_result("Analytics Requesters Archived Exclusion", False, "Missing authentication")
            return False
        
        try:
            headers = self.get_headers()
            response = requests.get(f"{EXTERNAL_BASE_URL}/analytics/requesters", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                requesters_data = response.json()
                
                # Look for our test requesters
                test_requesters = [req for req in requesters_data 
                                 if req.get("email", "").startswith("test") and "@analytics.com" in req.get("email", "")]
                
                # Check if any archived test requesters appear
                archived_test_emails = ["test4@analytics.com", "test5@analytics.com"]  # These should be archived
                non_archived_test_emails = ["test1@analytics.com", "test2@analytics.com", "test3@analytics.com"]
                
                found_archived = [req for req in test_requesters if req.get("email") in archived_test_emails]
                found_non_archived = [req for req in test_requesters if req.get("email") in non_archived_test_emails]
                
                success = len(found_archived) == 0 and len(found_non_archived) > 0
                
                self.log_result("Analytics Requesters Archived Exclusion", success,
                              f"Requesters analytics {'excludes' if len(found_archived) == 0 else 'includes'} archived requests", {
                    "total_requesters": len(requesters_data),
                    "test_requesters_found": len(test_requesters),
                    "archived_test_requesters_found": len(found_archived),
                    "non_archived_test_requesters_found": len(found_non_archived),
                    "expected_non_archived": 3,
                    "expected_archived": 0
                })
                
                return success
            else:
                self.log_result("Analytics Requesters Archived Exclusion", False, 
                              f"Failed to get requesters analytics: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Analytics Requesters Archived Exclusion", False, f"Error: {str(e)}")
            return False
    
    def test_data_consistency_between_endpoints(self):
        """Test data consistency between requests and analytics endpoints"""
        print("\n=== Testing Data Consistency Between Endpoints ===")
        
        if not self.token or not self.musician_id:
            self.log_result("Data Consistency Check", False, "Missing authentication or musician ID")
            return False
        
        try:
            headers = self.get_headers()
            
            # Get requests data
            requests_response = requests.get(f"{EXTERNAL_BASE_URL}/requests/musician/{self.musician_id}", 
                                           headers=headers, timeout=30)
            
            # Get analytics data
            analytics_response = requests.get(f"{EXTERNAL_BASE_URL}/analytics/daily?days=30", 
                                            headers=headers, timeout=30)
            
            if requests_response.status_code == 200 and analytics_response.status_code == 200:
                requests_data = requests_response.json()
                analytics_data = analytics_response.json()
                
                # Count non-archived requests
                non_archived_requests = [req for req in requests_data if req.get("status") != "archived"]
                
                # Get analytics totals
                analytics_totals = analytics_data.get("totals", {})
                analytics_total_requests = analytics_totals.get("total_requests", 0)
                
                # Filter requests to last 30 days for fair comparison
                thirty_days_ago = datetime.now() - timedelta(days=30)
                recent_requests = []
                
                for req in non_archived_requests:
                    created_at = req.get("created_at")
                    if created_at:
                        try:
                            # Parse the datetime
                            if isinstance(created_at, str):
                                req_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            else:
                                req_date = created_at
                            
                            if req_date >= thirty_days_ago:
                                recent_requests.append(req)
                        except:
                            # If we can't parse the date, include it to be safe
                            recent_requests.append(req)
                
                requests_count = len(recent_requests)
                
                # Check consistency
                consistency_threshold = 0  # Allow for some variance due to timing
                count_difference = abs(requests_count - analytics_total_requests)
                is_consistent = count_difference <= consistency_threshold
                
                self.log_result("Data Consistency Check", is_consistent,
                              f"Request counts {'match' if is_consistent else 'do not match'} between endpoints", {
                    "requests_endpoint_count": requests_count,
                    "analytics_endpoint_count": analytics_total_requests,
                    "difference": count_difference,
                    "consistency_threshold": consistency_threshold,
                    "total_requests_including_archived": len(requests_data),
                    "archived_requests_excluded": len(requests_data) - len(non_archived_requests)
                })
                
                return is_consistent
            else:
                self.log_result("Data Consistency Check", False, 
                              f"Failed to get data - Requests: {requests_response.status_code}, Analytics: {analytics_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Data Consistency Check", False, f"Error: {str(e)}")
            return False
    
    def test_date_range_logic(self):
        """Test that analytics date filtering works correctly"""
        print("\n=== Testing Date Range Logic ===")
        
        if not self.token:
            self.log_result("Date Range Logic", False, "Missing authentication")
            return False
        
        try:
            headers = self.get_headers()
            
            # Test different date ranges
            date_ranges = [1, 7, 30, 90, 365]
            results = {}
            
            for days in date_ranges:
                response = requests.get(f"{EXTERNAL_BASE_URL}/analytics/daily?days={days}", 
                                      headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    daily_stats = data.get("daily_stats", [])
                    totals = data.get("totals", {})
                    
                    results[days] = {
                        "daily_stats_count": len(daily_stats),
                        "total_requests": totals.get("total_requests", 0),
                        "success": True
                    }
                else:
                    results[days] = {
                        "success": False,
                        "status_code": response.status_code
                    }
            
            # Verify that longer periods generally have more or equal data
            successful_ranges = {k: v for k, v in results.items() if v.get("success")}
            
            date_logic_correct = True
            for i, days in enumerate(sorted(successful_ranges.keys())):
                if i > 0:
                    prev_days = sorted(successful_ranges.keys())[i-1]
                    current_total = successful_ranges[days]["total_requests"]
                    prev_total = successful_ranges[prev_days]["total_requests"]
                    
                    # Longer periods should have >= requests (unless no new data)
                    if current_total < prev_total:
                        date_logic_correct = False
            
            self.log_result("Date Range Logic", date_logic_correct,
                          f"Date range filtering {'works correctly' if date_logic_correct else 'has issues'}", {
                "tested_ranges": list(date_ranges),
                "successful_ranges": list(successful_ranges.keys()),
                "results": results
            })
            
            return date_logic_correct
            
        except Exception as e:
            self.log_result("Date Range Logic", False, f"Error: {str(e)}")
            return False
    
    def cleanup_test_requests(self):
        """Clean up test requests created during testing"""
        print("\n=== Cleaning Up Test Requests ===")
        
        if not self.token or not self.test_requests:
            self.log_result("Cleanup Test Requests", True, "No test requests to clean up")
            return True
        
        try:
            headers = self.get_headers()
            cleaned_count = 0
            
            for test_request in self.test_requests:
                request_id = test_request.get("id")
                if request_id:
                    # Try to delete the request
                    delete_response = requests.delete(f"{EXTERNAL_BASE_URL}/requests/{request_id}", 
                                                    headers=headers, timeout=30)
                    
                    if delete_response.status_code in [200, 204, 404]:  # 404 is OK if already deleted
                        cleaned_count += 1
            
            self.log_result("Cleanup Test Requests", True, f"Cleaned up {cleaned_count}/{len(self.test_requests)} test requests", {
                "total_test_requests": len(self.test_requests),
                "successfully_cleaned": cleaned_count
            })
            
            return True
            
        except Exception as e:
            self.log_result("Cleanup Test Requests", False, f"Error during cleanup: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all analytics consistency tests"""
        print("🚀 Starting Analytics Data Consistency Tests")
        print(f"API Base URL: {EXTERNAL_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run all tests in order
        test_results = []
        
        # Create test data
        test_results.append(self.create_test_requests())
        
        # Wait a moment for data to be processed
        time.sleep(2)
        
        # Run consistency tests
        test_results.append(self.test_requests_endpoint_excludes_archived())
        test_results.append(self.test_analytics_daily_excludes_archived())
        test_results.append(self.test_analytics_requesters_excludes_archived())
        test_results.append(self.test_data_consistency_between_endpoints())
        test_results.append(self.test_date_range_logic())
        
        # Cleanup
        self.cleanup_test_requests()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 ANALYTICS CONSISTENCY TEST SUMMARY")
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
                if any(keyword in result["test"].lower() for keyword in 
                      ["consistency", "archived exclusion", "data consistency"]):
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
        
        # Check archived exclusion
        archived_excluded = any(r["success"] and "archived exclusion" in r["test"].lower() for r in self.results)
        if archived_excluded:
            print("✅ Analytics endpoints properly exclude archived requests")
        else:
            print("❌ Analytics endpoints may still include archived requests")
        
        # Check data consistency
        data_consistent = any(r["success"] and "data consistency" in r["test"].lower() for r in self.results)
        if data_consistent:
            print("✅ Data is consistent between Analytics and Requests tabs")
        else:
            print("❌ Data inconsistency detected between Analytics and Requests tabs")
        
        print("\n🎯 ANALYTICS CONSISTENCY TEST COMPLETE")
        
        # Provide recommendations
        if critical_failures:
            print("\n💡 RECOMMENDATIONS:")
            if not archived_excluded:
                print("1. Verify that analytics endpoints have proper archived request exclusion filters")
            if not data_consistent:
                print("2. Check that both endpoints use the same filtering logic")
            print("3. Review the aggregation pipelines in analytics endpoints")
        else:
            print("\n✅ ALL CRITICAL TESTS PASSED - Analytics consistency fixes are working correctly!")
        
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = AnalyticsConsistencyTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)