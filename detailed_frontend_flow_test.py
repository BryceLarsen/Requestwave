#!/usr/bin/env python3
"""
Detailed Frontend Request Flow Simulation
Simulating the exact request flow that the frontend would make to identify
why users see "error creating request" despite backend working correctly.
"""

import requests
import json
import sys
from datetime import datetime
import time

# Configuration
PREVIEW_BACKEND_URL = "https://request-error-fix.preview.emergentagent.com/api"
PREVIEW_FRONTEND_URL = "https://request-error-fix.preview.emergentagent.com"
TEST_MUSICIAN_SLUG = "bryce-larsen"

class DetailedFrontendFlowTester:
    def __init__(self):
        self.results = []
        self.test_song_id = None
        
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
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def test_exact_frontend_headers(self):
        """Test with exact headers that frontend would send"""
        print("\n=== Testing Exact Frontend Headers ===")
        
        # Headers that a React frontend would typically send
        frontend_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": PREVIEW_FRONTEND_URL,
            "Referer": f"{PREVIEW_FRONTEND_URL}/musician/{TEST_MUSICIAN_SLUG}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            # First get a song to test with
            response = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/songs", 
                                  headers=frontend_headers, timeout=30)
            
            if response.status_code == 200:
                songs = response.json()
                if songs:
                    self.test_song_id = songs[0]["id"]
                    self.log_result("Frontend Headers - Songs Fetch", True, 
                                  f"Successfully fetched songs with frontend headers", {
                        "songs_count": len(songs),
                        "test_song": f"{songs[0]['title']} by {songs[0]['artist']}"
                    })
                else:
                    self.log_result("Frontend Headers - Songs Fetch", False, "No songs found")
                    return False
            else:
                self.log_result("Frontend Headers - Songs Fetch", False, 
                              f"Failed to fetch songs: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Frontend Headers - Songs Fetch", False, f"Error: {str(e)}")
            return False
        
        return True
    
    def test_request_creation_with_frontend_simulation(self):
        """Test request creation exactly as frontend would do it"""
        print("\n=== Testing Request Creation with Frontend Simulation ===")
        
        if not self.test_song_id:
            self.log_result("Frontend Request Creation", False, "No test song available")
            return False
        
        # Exact headers frontend would send
        frontend_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": PREVIEW_FRONTEND_URL,
            "Referer": f"{PREVIEW_FRONTEND_URL}/musician/{TEST_MUSICIAN_SLUG}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Exact payload frontend would send
        request_payload = {
            "song_id": self.test_song_id,
            "requester_name": "John Doe",
            "requester_email": "john.doe@example.com",
            "dedication": "This is my favorite song!"
        }
        
        try:
            # Test the main request endpoint
            response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                   json=request_payload, 
                                   headers=frontend_headers, 
                                   timeout=30)
            
            self.log_result("Frontend Request Creation - Main Endpoint", 
                          response.status_code == 200,
                          f"Request to /requests: {response.status_code}", {
                "response_text": response.text[:500],
                "response_headers": dict(response.headers),
                "request_payload": request_payload
            })
            
            # Test the musician-specific endpoint (alternative route)
            response2 = requests.post(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/requests", 
                                    json=request_payload, 
                                    headers=frontend_headers, 
                                    timeout=30)
            
            self.log_result("Frontend Request Creation - Musician Endpoint", 
                          response2.status_code == 200,
                          f"Request to /musicians/{TEST_MUSICIAN_SLUG}/requests: {response2.status_code}", {
                "response_text": response2.text[:500],
                "response_headers": dict(response2.headers)
            })
            
            return response.status_code == 200 or response2.status_code == 200
            
        except Exception as e:
            self.log_result("Frontend Request Creation", False, f"Error: {str(e)}")
            return False
    
    def test_different_request_formats(self):
        """Test different request payload formats that frontend might send"""
        print("\n=== Testing Different Request Formats ===")
        
        if not self.test_song_id:
            self.log_result("Request Formats", False, "No test song available")
            return
        
        frontend_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": PREVIEW_FRONTEND_URL
        }
        
        # Test different payload variations
        test_payloads = [
            {
                "name": "Standard Format",
                "payload": {
                    "song_id": self.test_song_id,
                    "requester_name": "Test User 1",
                    "requester_email": "test1@example.com",
                    "dedication": "Test dedication"
                }
            },
            {
                "name": "With Empty Dedication",
                "payload": {
                    "song_id": self.test_song_id,
                    "requester_name": "Test User 2",
                    "requester_email": "test2@example.com",
                    "dedication": ""
                }
            },
            {
                "name": "With Null Dedication",
                "payload": {
                    "song_id": self.test_song_id,
                    "requester_name": "Test User 3",
                    "requester_email": "test3@example.com",
                    "dedication": None
                }
            },
            {
                "name": "With Extra Fields",
                "payload": {
                    "song_id": self.test_song_id,
                    "requester_name": "Test User 4",
                    "requester_email": "test4@example.com",
                    "dedication": "Test",
                    "tip_amount": 0.0,
                    "extra_field": "should be ignored"
                }
            }
        ]
        
        for test_case in test_payloads:
            try:
                response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                       json=test_case["payload"], 
                                       headers=frontend_headers, 
                                       timeout=30)
                
                self.log_result(f"Request Format - {test_case['name']}", 
                              response.status_code == 200,
                              f"Status: {response.status_code}", {
                    "payload": test_case["payload"],
                    "response": response.text[:200] if response.status_code != 200 else "Success"
                })
                
            except Exception as e:
                self.log_result(f"Request Format - {test_case['name']}", False, f"Error: {str(e)}")
    
    def test_network_timing_and_timeouts(self):
        """Test network timing issues that might cause frontend errors"""
        print("\n=== Testing Network Timing and Timeouts ===")
        
        if not self.test_song_id:
            self.log_result("Network Timing", False, "No test song available")
            return
        
        frontend_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": PREVIEW_FRONTEND_URL
        }
        
        request_payload = {
            "song_id": self.test_song_id,
            "requester_name": "Timing Test User",
            "requester_email": "timing@example.com",
            "dedication": "Testing network timing"
        }
        
        # Test with different timeout values
        timeout_tests = [
            ("Short Timeout (5s)", 5),
            ("Medium Timeout (15s)", 15),
            ("Long Timeout (30s)", 30)
        ]
        
        for test_name, timeout_value in timeout_tests:
            try:
                start_time = time.time()
                response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                       json=request_payload, 
                                       headers=frontend_headers, 
                                       timeout=timeout_value)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                self.log_result(f"Network Timing - {test_name}", 
                              response.status_code == 200,
                              f"Response time: {response_time:.0f}ms, Status: {response.status_code}", {
                    "timeout_setting": f"{timeout_value}s",
                    "actual_response_time": f"{response_time:.0f}ms",
                    "status_code": response.status_code
                })
                
            except requests.exceptions.Timeout:
                self.log_result(f"Network Timing - {test_name}", False, 
                              f"Request timed out after {timeout_value}s")
            except Exception as e:
                self.log_result(f"Network Timing - {test_name}", False, f"Error: {str(e)}")
    
    def test_concurrent_requests(self):
        """Test multiple concurrent requests to check for race conditions"""
        print("\n=== Testing Concurrent Requests ===")
        
        if not self.test_song_id:
            self.log_result("Concurrent Requests", False, "No test song available")
            return
        
        import threading
        import queue
        
        frontend_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": PREVIEW_FRONTEND_URL
        }
        
        results_queue = queue.Queue()
        
        def make_request(request_id):
            try:
                request_payload = {
                    "song_id": self.test_song_id,
                    "requester_name": f"Concurrent User {request_id}",
                    "requester_email": f"concurrent{request_id}@example.com",
                    "dedication": f"Concurrent request {request_id}"
                }
                
                start_time = time.time()
                response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                       json=request_payload, 
                                       headers=frontend_headers, 
                                       timeout=30)
                end_time = time.time()
                
                results_queue.put({
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": (end_time - start_time) * 1000,
                    "success": response.status_code == 200
                })
                
            except Exception as e:
                results_queue.put({
                    "request_id": request_id,
                    "error": str(e),
                    "success": False
                })
        
        # Launch 5 concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i+1,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        concurrent_results = []
        while not results_queue.empty():
            concurrent_results.append(results_queue.get())
        
        successful_requests = len([r for r in concurrent_results if r.get("success", False)])
        total_requests = len(concurrent_results)
        
        self.log_result("Concurrent Requests", 
                      successful_requests == total_requests,
                      f"Successful: {successful_requests}/{total_requests}", {
            "success_rate": f"{(successful_requests/total_requests)*100:.1f}%",
            "results": concurrent_results
        })
    
    def test_specific_user_flow_simulation(self):
        """Simulate the exact user flow from the reported issue"""
        print("\n=== Testing Specific User Flow Simulation ===")
        
        # Simulate the exact flow: user visits musician page, selects song, submits request
        try:
            # Step 1: User visits musician page (GET musician profile)
            response1 = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}", timeout=30)
            
            if response1.status_code != 200:
                self.log_result("User Flow - Step 1 (Profile)", False, 
                              f"Failed to get musician profile: {response1.status_code}")
                return False
            
            # Step 2: User loads songs list
            response2 = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/songs", timeout=30)
            
            if response2.status_code != 200:
                self.log_result("User Flow - Step 2 (Songs)", False, 
                              f"Failed to get songs: {response2.status_code}")
                return False
            
            songs = response2.json()
            if not songs:
                self.log_result("User Flow - Step 2 (Songs)", False, "No songs available")
                return False
            
            # Step 3: User selects a song and submits request
            selected_song = songs[0]  # First song
            
            # Simulate exact frontend request
            frontend_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Origin": PREVIEW_FRONTEND_URL,
                "Referer": f"{PREVIEW_FRONTEND_URL}/musician/{TEST_MUSICIAN_SLUG}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            request_payload = {
                "song_id": selected_song["id"],
                "requester_name": "Real User Test",
                "requester_email": "realuser@example.com",
                "dedication": "Please play this song!"
            }
            
            response3 = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                    json=request_payload, 
                                    headers=frontend_headers, 
                                    timeout=30)
            
            if response3.status_code == 200:
                request_data = response3.json()
                self.log_result("User Flow - Complete", True, 
                              "Successfully completed full user flow", {
                    "selected_song": f"{selected_song['title']} by {selected_song['artist']}",
                    "request_id": request_data.get("id"),
                    "request_status": request_data.get("status")
                })
                return True
            else:
                self.log_result("User Flow - Step 3 (Request)", False, 
                              f"Request creation failed: {response3.status_code} - {response3.text}", {
                    "request_payload": request_payload,
                    "response_headers": dict(response3.headers)
                })
                return False
                
        except Exception as e:
            self.log_result("User Flow - Complete", False, f"Error in user flow: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all detailed frontend flow tests"""
        print("🔍 Starting Detailed Frontend Request Flow Simulation")
        print(f"Preview Backend: {PREVIEW_BACKEND_URL}")
        print(f"Preview Frontend: {PREVIEW_FRONTEND_URL}")
        print(f"Test Musician: {TEST_MUSICIAN_SLUG}")
        print("=" * 80)
        
        # Run tests
        if not self.test_exact_frontend_headers():
            print("❌ Failed to setup test environment. Aborting detailed tests.")
            return False
        
        self.test_request_creation_with_frontend_simulation()
        self.test_different_request_formats()
        self.test_network_timing_and_timeouts()
        self.test_concurrent_requests()
        self.test_specific_user_flow_simulation()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 DETAILED FRONTEND FLOW TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Show failures
        failures = [r for r in self.results if not r["success"]]
        if failures:
            print("\n❌ FAILED TESTS:")
            for result in failures:
                print(f"  - {result['test']}: {result['message']}")
                if result.get('details'):
                    for key, value in result['details'].items():
                        if isinstance(value, (dict, list)):
                            print(f"    {key}: {json.dumps(value, indent=2)[:200]}...")
                        else:
                            print(f"    {key}: {value}")
        
        print("\n🎯 DETAILED FRONTEND FLOW TEST COMPLETE")
        return len(failures) == 0

if __name__ == "__main__":
    tester = DetailedFrontendFlowTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)