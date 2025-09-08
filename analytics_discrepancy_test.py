#!/usr/bin/env python3
"""
Analytics Data Count Discrepancy Investigation
CRITICAL ISSUE: User reports Analytics shows only 2 requests vs 46 in Requests tab

This test will:
1. Authenticate with real user credentials (brycelarsenmusic@gmail.com)
2. Test actual endpoints with user's real data
3. Compare request counts between endpoints
4. Identify exact root cause of discrepancy

Focus Areas:
- /api/requests/musician/{musician_id} - should return 46 requests
- /api/analytics/daily (no days param) - should return same 46 requests for all-time
- /api/analytics/daily?days=7 - should return requests from last 7 days
- /api/analytics/daily?days=30 - should return requests from last 30 days
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

class AnalyticsDiscrepancyTester:
    def __init__(self):
        self.token = None
        self.musician_id = None
        self.musician_slug = None
        self.results = []
        self.requests_data = []
        self.analytics_data = {}
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
    def authenticate(self):
        """Authenticate with real user credentials"""
        print("\n=== AUTHENTICATION ===")
        
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
                    "musician_name": musician_data.get("name"),
                    "token_length": len(self.token) if self.token else 0
                })
                return True
            else:
                self.log_result("Authentication", False, f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def test_requests_endpoint(self):
        """Test GET /api/requests/musician/{musician_id} - should return 46 requests"""
        print(f"\n=== TESTING REQUESTS ENDPOINT ===")
        
        if not self.token or not self.musician_id:
            self.log_result("Requests Endpoint", False, "No authentication token or musician ID available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{EXTERNAL_BASE_URL}/requests/musician/{self.musician_id}", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.requests_data = response.json()
                request_count = len(self.requests_data)
                
                # Analyze request data
                statuses = {}
                dates = []
                for req in self.requests_data:
                    status = req.get('status', 'unknown')
                    statuses[status] = statuses.get(status, 0) + 1
                    
                    created_at = req.get('created_at')
                    if created_at:
                        dates.append(created_at)
                
                # Sort dates to find range
                dates.sort()
                date_range = f"{dates[0]} to {dates[-1]}" if dates else "No dates"
                
                self.log_result("Requests Endpoint", True, f"Retrieved {request_count} requests", {
                    "total_requests": request_count,
                    "status_breakdown": statuses,
                    "date_range": date_range,
                    "first_request": self.requests_data[0] if self.requests_data else None,
                    "last_request": self.requests_data[-1] if self.requests_data else None
                })
                
                # Check if we have the expected 46 requests
                if request_count == 46:
                    self.log_result("Expected Request Count", True, "Found expected 46 requests")
                else:
                    self.log_result("Expected Request Count", False, f"Expected 46 requests, found {request_count}")
                
            else:
                self.log_result("Requests Endpoint", False, f"Failed to get requests: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Requests Endpoint", False, f"Error testing requests endpoint: {str(e)}")
    
    def test_analytics_daily_all_time(self):
        """Test GET /api/analytics/daily (no days param) - should return all-time data"""
        print(f"\n=== TESTING ANALYTICS DAILY (ALL TIME) ===")
        
        if not self.token:
            self.log_result("Analytics Daily All Time", False, "No authentication token available")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{EXTERNAL_BASE_URL}/analytics/daily", 
                                  headers=headers, timeout=30)
            
            if response.status_code == 200:
                analytics_data = response.json()
                self.analytics_data['all_time'] = analytics_data
                
                # Extract key metrics
                totals = analytics_data.get('totals', {})
                total_requests = totals.get('total_requests', 0)
                daily_stats = analytics_data.get('daily_stats', [])
                
                # Calculate total from daily stats as verification
                daily_total = sum(day.get('requests', 0) for day in daily_stats)
                
                self.log_result("Analytics Daily All Time", True, f"Retrieved all-time analytics", {
                    "totals_total_requests": total_requests,
                    "daily_stats_count": len(daily_stats),
                    "daily_stats_total": daily_total,
                    "top_songs_count": len(analytics_data.get('top_songs', [])),
                    "top_requesters_count": len(analytics_data.get('top_requesters', [])),
                    "response_structure": list(analytics_data.keys())
                })
                
                # Check if analytics matches requests endpoint
                requests_count = len(self.requests_data) if self.requests_data else 0
                if total_requests == requests_count:
                    self.log_result("Analytics vs Requests Match", True, f"Analytics total ({total_requests}) matches requests count ({requests_count})")
                else:
                    self.log_result("Analytics vs Requests Match", False, f"DISCREPANCY: Analytics total ({total_requests}) != requests count ({requests_count})")
                
                # Check if we have the problematic "only 2 requests" issue
                if total_requests == 2:
                    self.log_result("Analytics Capped at 2", True, "CONFIRMED: Analytics shows only 2 requests (user's reported issue)")
                else:
                    self.log_result("Analytics Capped at 2", False, f"Analytics shows {total_requests} requests, not the reported 2")
                
            else:
                self.log_result("Analytics Daily All Time", False, f"Failed to get analytics: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Analytics Daily All Time", False, f"Error testing analytics all time: {str(e)}")
    
    def test_analytics_daily_with_days(self):
        """Test analytics with different day parameters"""
        print(f"\n=== TESTING ANALYTICS DAILY WITH DAYS PARAMETERS ===")
        
        if not self.token:
            self.log_result("Analytics Daily with Days", False, "No authentication token available")
            return
        
        day_periods = [7, 30, 365]
        
        for days in day_periods:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.get(f"{EXTERNAL_BASE_URL}/analytics/daily?days={days}", 
                                      headers=headers, timeout=30)
                
                if response.status_code == 200:
                    analytics_data = response.json()
                    self.analytics_data[f'days_{days}'] = analytics_data
                    
                    totals = analytics_data.get('totals', {})
                    total_requests = totals.get('total_requests', 0)
                    daily_stats = analytics_data.get('daily_stats', [])
                    
                    self.log_result(f"Analytics Daily {days} Days", True, f"Retrieved {days}-day analytics", {
                        "days_parameter": days,
                        "total_requests": total_requests,
                        "daily_stats_count": len(daily_stats),
                        "date_range": f"{daily_stats[0].get('date') if daily_stats else 'N/A'} to {daily_stats[-1].get('date') if daily_stats else 'N/A'}"
                    })
                    
                else:
                    self.log_result(f"Analytics Daily {days} Days", False, f"Failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.log_result(f"Analytics Daily {days} Days", False, f"Error: {str(e)}")
    
    def analyze_database_queries(self):
        """Analyze potential database query differences"""
        print(f"\n=== ANALYZING DATABASE QUERY DIFFERENCES ===")
        
        if not self.requests_data or not self.analytics_data.get('all_time'):
            self.log_result("Database Query Analysis", False, "Missing requests or analytics data for comparison")
            return
        
        try:
            # Analyze request data structure
            requests_count = len(self.requests_data)
            
            # Check for archived requests
            archived_count = len([r for r in self.requests_data if r.get('status') == 'archived'])
            non_archived_count = requests_count - archived_count
            
            # Check date ranges
            request_dates = [r.get('created_at') for r in self.requests_data if r.get('created_at')]
            request_dates.sort()
            
            # Analyze analytics data
            analytics_total = self.analytics_data['all_time'].get('totals', {}).get('total_requests', 0)
            daily_stats = self.analytics_data['all_time'].get('daily_stats', [])
            
            self.log_result("Database Query Analysis", True, "Completed query analysis", {
                "requests_endpoint": {
                    "total_requests": requests_count,
                    "archived_requests": archived_count,
                    "non_archived_requests": non_archived_count,
                    "date_range": f"{request_dates[0]} to {request_dates[-1]}" if request_dates else "No dates"
                },
                "analytics_endpoint": {
                    "total_requests": analytics_total,
                    "daily_stats_entries": len(daily_stats),
                    "daily_stats_sum": sum(day.get('requests', 0) for day in daily_stats)
                },
                "potential_issues": {
                    "archived_filtering": archived_count > 0,
                    "count_mismatch": requests_count != analytics_total,
                    "daily_stats_mismatch": analytics_total != sum(day.get('requests', 0) for day in daily_stats)
                }
            })
            
            # Identify specific discrepancy patterns
            if analytics_total == 2 and requests_count > 2:
                self.log_result("Root Cause Analysis", True, "IDENTIFIED: Analytics query likely has LIMIT 2 or similar restriction", {
                    "evidence": f"Analytics returns exactly 2 while requests endpoint returns {requests_count}",
                    "likely_cause": "Database query in analytics endpoint has incorrect LIMIT clause or aggregation issue"
                })
            
        except Exception as e:
            self.log_result("Database Query Analysis", False, f"Error in analysis: {str(e)}")
    
    def test_response_structure_verification(self):
        """Verify response structures match expected format"""
        print(f"\n=== VERIFYING RESPONSE STRUCTURES ===")
        
        if not self.analytics_data.get('all_time'):
            self.log_result("Response Structure Verification", False, "No analytics data available")
            return
        
        try:
            analytics_data = self.analytics_data['all_time']
            
            # Expected structure for analytics response
            expected_keys = ['daily_stats', 'totals', 'top_songs', 'top_requesters']
            missing_keys = [key for key in expected_keys if key not in analytics_data]
            
            # Check totals structure
            totals = analytics_data.get('totals', {})
            expected_total_keys = ['total_requests', 'unique_requesters']
            missing_total_keys = [key for key in expected_total_keys if key not in totals]
            
            # Check daily_stats structure
            daily_stats = analytics_data.get('daily_stats', [])
            if daily_stats:
                first_day = daily_stats[0]
                expected_day_keys = ['date', 'requests']
                missing_day_keys = [key for key in expected_day_keys if key not in first_day]
            else:
                missing_day_keys = ['No daily stats available']
            
            self.log_result("Response Structure Verification", len(missing_keys) == 0, "Verified analytics response structure", {
                "missing_root_keys": missing_keys,
                "missing_totals_keys": missing_total_keys,
                "missing_daily_keys": missing_day_keys,
                "totals_field": totals,
                "daily_stats_count": len(daily_stats),
                "structure_valid": len(missing_keys) == 0 and len(missing_total_keys) == 0
            })
            
        except Exception as e:
            self.log_result("Response Structure Verification", False, f"Error verifying structure: {str(e)}")
    
    def run_comprehensive_investigation(self):
        """Run complete analytics discrepancy investigation"""
        print("🔍 STARTING ANALYTICS DATA COUNT DISCREPANCY INVESTIGATION")
        print(f"External API: {EXTERNAL_BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print(f"Expected: Requests tab shows 46, Analytics shows only 2")
        print("=" * 80)
        
        # Run investigation steps
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with investigation")
            return False
        
        self.test_requests_endpoint()
        self.test_analytics_daily_all_time()
        self.test_analytics_daily_with_days()
        self.analyze_database_queries()
        self.test_response_structure_verification()
        
        # Generate comprehensive summary
        print("\n" + "=" * 80)
        print("📊 ANALYTICS DISCREPANCY INVESTIGATION SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        
        requests_count = len(self.requests_data) if self.requests_data else 0
        analytics_total = self.analytics_data.get('all_time', {}).get('totals', {}).get('total_requests', 0) if self.analytics_data.get('all_time') else 0
        
        print(f"📋 Requests Endpoint: {requests_count} requests")
        print(f"📊 Analytics Endpoint: {analytics_total} requests")
        
        if requests_count > 0 and analytics_total > 0:
            if requests_count == analytics_total:
                print("✅ NO DISCREPANCY: Request counts match between endpoints")
            else:
                print(f"❌ DISCREPANCY CONFIRMED: {requests_count - analytics_total} request difference")
                
                if analytics_total == 2:
                    print("🚨 CRITICAL: Analytics capped at exactly 2 requests (matches user report)")
                    print("💡 LIKELY CAUSE: Database query in analytics endpoint has LIMIT 2 or aggregation issue")
        
        # Critical failures
        critical_failures = [r for r in self.results if not r["success"] and 
                           any(keyword in r["test"].lower() for keyword in ["requests endpoint", "analytics", "discrepancy"])]
        
        if critical_failures:
            print("\n❌ CRITICAL FAILURES:")
            for result in critical_failures:
                print(f"  - {result['test']}: {result['message']}")
        
        # Root cause analysis
        print("\n🎯 ROOT CAUSE ANALYSIS:")
        
        if requests_count == 46 and analytics_total == 2:
            print("✅ USER ISSUE CONFIRMED: Analytics shows 2 requests instead of 46")
            print("🔧 REQUIRED FIX: Check analytics database query for:")
            print("   - Incorrect LIMIT clause")
            print("   - Aggregation pipeline issues")
            print("   - Date filtering problems")
            print("   - Archived request filtering differences")
        elif requests_count != 46:
            print(f"⚠️ UNEXPECTED: Requests endpoint shows {requests_count} instead of expected 46")
        elif analytics_total != 2:
            print(f"⚠️ UNEXPECTED: Analytics shows {analytics_total} instead of reported 2")
        else:
            print("✅ Issue may have been resolved or test environment differs from production")
        
        print("\n🎯 ANALYTICS DISCREPANCY INVESTIGATION COMPLETE")
        
        return requests_count == analytics_total

if __name__ == "__main__":
    tester = AnalyticsDiscrepancyTester()
    success = tester.run_comprehensive_investigation()
    sys.exit(0 if success else 1)