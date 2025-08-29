#!/usr/bin/env python3
"""
Deployment Readiness Test Suite for RequestWave
Testing the deployment fixes that were just implemented:
1. Environment Variable Configuration Test
2. URL Generation Consistency Test  
3. CORS Configuration Test
4. Production Deployment Readiness
5. Integration Health Check
"""

import requests
import json
import sys
import os
from datetime import datetime
import time

# Configuration
BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"
TEST_EMAIL = "brycelarsenmusic@gmail.com"
TEST_PASSWORD = "RequestWave2024!"

class DeploymentReadinessTester:
    def __init__(self):
        self.token = None
        self.musician_id = None
        self.test_song_ids = []
        self.test_request_ids = []
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
            print(f"   Details: {details}")
    
    def authenticate(self):
        """Authenticate and get JWT token"""
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.musician_id = data.get("musician", {}).get("id")
                self.log_result("Authentication", True, f"Successfully authenticated as {TEST_EMAIL}")
                return True
            else:
                self.log_result("Authentication", False, f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def get_headers(self):
        """Get headers with authentication"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_environment_variable_configuration(self):
        """Test 1: Environment Variable Configuration Test"""
        print("\n=== Testing Environment Variable Configuration ===")
        
        try:
            # Test QR code generation to see if it uses environment-based URL
            response = requests.get(
                f"{BASE_URL}/qr-code",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                audience_url = data.get("audience_url", "")
                qr_code_data = data.get("qr_code", "")
                
                # Check if audience URL uses the correct domain
                expected_domains = ["requestwave.app", "livewave"]
                domain_found = any(domain in audience_url for domain in expected_domains)
                
                if domain_found and qr_code_data:
                    self.log_result("Environment Variable - QR Code URL", True, 
                                  f"QR code uses environment-based URL: {audience_url}", {
                                      "audience_url": audience_url,
                                      "has_qr_code": bool(qr_code_data)
                                  })
                else:
                    self.log_result("Environment Variable - QR Code URL", False, 
                                  f"QR code URL may not use environment variable: {audience_url}", {
                                      "audience_url": audience_url,
                                      "expected_domains": expected_domains
                                  })
            else:
                self.log_result("Environment Variable - QR Code URL", False, 
                              f"Failed to get QR code: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("Environment Variable - QR Code URL", False, f"Environment variable test error: {str(e)}")

    def test_url_generation_consistency(self):
        """Test 2: URL Generation Consistency Test"""
        print("\n=== Testing URL Generation Consistency ===")
        
        try:
            # Test QR code endpoint multiple times to ensure consistency
            urls_generated = []
            
            for i in range(3):
                response = requests.get(
                    f"{BASE_URL}/qr-code",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    audience_url = data.get("audience_url", "")
                    urls_generated.append(audience_url)
                    time.sleep(0.5)  # Small delay between requests
                else:
                    self.log_result("URL Generation Consistency", False, 
                                  f"QR code request {i+1} failed: {response.status_code}")
                    return
            
            # Check if all URLs are identical
            if len(set(urls_generated)) == 1 and urls_generated[0]:
                self.log_result("URL Generation Consistency", True, 
                              "QR code endpoint generates consistent URLs", {
                                  "url": urls_generated[0],
                                  "requests_tested": len(urls_generated)
                              })
            else:
                self.log_result("URL Generation Consistency", False, 
                              "QR code endpoint generates inconsistent URLs", {
                                  "urls_generated": urls_generated
                              })
            
            # Test audience URL generation across different endpoints
            profile_response = requests.get(f"{BASE_URL}/profile", headers=self.get_headers())
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                musician_slug = profile_data.get("slug", "")
                
                if musician_slug:
                    # Check if the audience URL pattern is consistent
                    expected_url_pattern = f"/musician/{musician_slug}"
                    if expected_url_pattern in urls_generated[0]:
                        self.log_result("URL Generation - Pattern Consistency", True, 
                                      "Audience URL follows expected pattern", {
                                          "pattern": expected_url_pattern,
                                          "full_url": urls_generated[0]
                                      })
                    else:
                        self.log_result("URL Generation - Pattern Consistency", False, 
                                      "Audience URL doesn't follow expected pattern", {
                                          "expected_pattern": expected_url_pattern,
                                          "actual_url": urls_generated[0]
                                      })
                
        except Exception as e:
            self.log_result("URL Generation Consistency", False, f"URL consistency test error: {str(e)}")

    def test_cors_configuration(self):
        """Test 3: CORS Configuration Test"""
        print("\n=== Testing CORS Configuration ===")
        
        try:
            # Test CORS headers on various endpoints
            test_endpoints = [
                "/auth/login",
                "/profile", 
                "/qr-code",
                "/songs"
            ]
            
            cors_results = []
            
            for endpoint in test_endpoints:
                # Make OPTIONS request to check CORS preflight
                try:
                    options_response = requests.options(
                        f"{BASE_URL}{endpoint}",
                        headers={
                            "Origin": "https://requestwave.app",
                            "Access-Control-Request-Method": "GET",
                            "Access-Control-Request-Headers": "authorization,content-type"
                        }
                    )
                    
                    cors_headers = {
                        "access-control-allow-origin": options_response.headers.get("Access-Control-Allow-Origin"),
                        "access-control-allow-methods": options_response.headers.get("Access-Control-Allow-Methods"),
                        "access-control-allow-headers": options_response.headers.get("Access-Control-Allow-Headers")
                    }
                    
                    cors_results.append({
                        "endpoint": endpoint,
                        "status": options_response.status_code,
                        "cors_headers": cors_headers
                    })
                    
                except Exception as e:
                    cors_results.append({
                        "endpoint": endpoint,
                        "error": str(e)
                    })
            
            # Check if CORS is properly configured
            successful_cors = [r for r in cors_results if r.get("status") in [200, 204]]
            
            if len(successful_cors) >= len(test_endpoints) // 2:
                self.log_result("CORS Configuration", True, 
                              f"CORS properly configured for {len(successful_cors)}/{len(test_endpoints)} endpoints", {
                                  "cors_results": cors_results
                              })
            else:
                self.log_result("CORS Configuration", False, 
                              f"CORS issues found on multiple endpoints", {
                                  "cors_results": cors_results
                              })
                
        except Exception as e:
            self.log_result("CORS Configuration", False, f"CORS test error: {str(e)}")

    def test_production_deployment_readiness(self):
        """Test 4: Production Deployment Readiness"""
        print("\n=== Testing Production Deployment Readiness ===")
        
        try:
            # Test for hardcoded URLs in critical endpoints
            critical_endpoints = [
                ("/qr-code", "QR Code Generation"),
                ("/profile", "Profile Data"),
            ]
            
            hardcoded_url_issues = []
            
            for endpoint, description in critical_endpoints:
                response = requests.get(f"{BASE_URL}{endpoint}", headers=self.get_headers())
                
                if response.status_code == 200:
                    response_text = response.text.lower()
                    
                    # Check for hardcoded development URLs
                    problematic_patterns = [
                        "localhost",
                        "127.0.0.1",
                        "livewave-music.emergent.host",
                        "http://",  # Should be https in production
                    ]
                    
                    found_issues = []
                    for pattern in problematic_patterns:
                        if pattern in response_text and pattern != "http://" or (pattern == "http://" and "https://" not in response_text):
                            found_issues.append(pattern)
                    
                    if found_issues:
                        hardcoded_url_issues.append({
                            "endpoint": endpoint,
                            "description": description,
                            "issues": found_issues
                        })
            
            if not hardcoded_url_issues:
                self.log_result("Production Deployment - No Hardcoded URLs", True, 
                              "No hardcoded development URLs found in critical endpoints")
            else:
                self.log_result("Production Deployment - No Hardcoded URLs", False, 
                              "Found hardcoded URLs in critical endpoints", {
                                  "issues": hardcoded_url_issues
                              })
            
            # Test environment variable fallback logic
            qr_response = requests.get(f"{BASE_URL}/qr-code", headers=self.get_headers())
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                audience_url = qr_data.get("audience_url", "")
                
                # Check if URL uses production domain
                production_domains = ["requestwave.app"]
                uses_production_domain = any(domain in audience_url for domain in production_domains)
                
                if uses_production_domain:
                    self.log_result("Production Deployment - Domain Override", True, 
                                  "QR code uses production domain", {
                                      "audience_url": audience_url
                                  })
                else:
                    self.log_result("Production Deployment - Domain Override", False, 
                                  "QR code may not use production domain", {
                                      "audience_url": audience_url,
                                      "expected_domains": production_domains
                                  })
                
        except Exception as e:
            self.log_result("Production Deployment Readiness", False, f"Production readiness test error: {str(e)}")

    def test_mongodb_atlas_compatibility(self):
        """Test MongoDB Atlas compatibility using environment variables only"""
        print("\n=== Testing MongoDB Atlas Compatibility ===")
        
        try:
            # Test basic database operations to ensure MongoDB connection works
            # This indirectly tests that MONGO_URL environment variable is working
            
            # Test 1: Profile retrieval (requires DB connection)
            profile_response = requests.get(f"{BASE_URL}/profile", headers=self.get_headers())
            
            if profile_response.status_code == 200:
                self.log_result("MongoDB Atlas - Profile Retrieval", True, 
                              "Successfully retrieved profile data from database")
            else:
                self.log_result("MongoDB Atlas - Profile Retrieval", False, 
                              f"Failed to retrieve profile: {profile_response.status_code}")
                return
            
            # Test 2: Songs retrieval (requires DB connection)
            songs_response = requests.get(f"{BASE_URL}/songs", headers=self.get_headers())
            
            if songs_response.status_code == 200:
                songs_data = songs_response.json()
                self.log_result("MongoDB Atlas - Songs Retrieval", True, 
                              f"Successfully retrieved {len(songs_data)} songs from database")
            else:
                self.log_result("MongoDB Atlas - Songs Retrieval", False, 
                              f"Failed to retrieve songs: {songs_response.status_code}")
            
            # Test 3: Write operation (create a test song)
            test_song_data = {
                "title": "Deployment Test Song",
                "artist": "Test Artist",
                "genres": ["Pop"],
                "moods": ["Feel Good"],
                "year": 2024,
                "notes": "Test song for deployment readiness"
            }
            
            create_response = requests.post(
                f"{BASE_URL}/songs",
                json=test_song_data,
                headers=self.get_headers()
            )
            
            if create_response.status_code == 200:
                song_data = create_response.json()
                song_id = song_data.get("id")
                self.test_song_ids.append(song_id)
                
                self.log_result("MongoDB Atlas - Write Operation", True, 
                              "Successfully created test song in database", {
                                  "song_id": song_id
                              })
                
                # Test 4: Update operation
                update_response = requests.put(
                    f"{BASE_URL}/songs/{song_id}",
                    json={"notes": "Updated notes for deployment test"},
                    headers=self.get_headers()
                )
                
                if update_response.status_code == 200:
                    self.log_result("MongoDB Atlas - Update Operation", True, 
                                  "Successfully updated test song in database")
                else:
                    self.log_result("MongoDB Atlas - Update Operation", False, 
                                  f"Failed to update song: {update_response.status_code}")
                
            else:
                self.log_result("MongoDB Atlas - Write Operation", False, 
                              f"Failed to create test song: {create_response.status_code}")
                
        except Exception as e:
            self.log_result("MongoDB Atlas Compatibility", False, f"MongoDB compatibility test error: {str(e)}")

    def test_integration_health_check(self):
        """Test 5: Integration Health Check"""
        print("\n=== Testing Integration Health Check ===")
        
        try:
            # Test core functionality still works after deployment fixes
            
            # Test 1: Authentication system
            auth_response = requests.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            
            if auth_response.status_code == 200:
                self.log_result("Integration Health - Authentication", True, 
                              "Authentication system working correctly")
            else:
                self.log_result("Integration Health - Authentication", False, 
                              f"Authentication failed: {auth_response.status_code}")
                return
            
            # Test 2: Song management
            songs_response = requests.get(f"{BASE_URL}/songs", headers=self.get_headers())
            
            if songs_response.status_code == 200:
                songs = songs_response.json()
                self.log_result("Integration Health - Song Management", True, 
                              f"Song management working - {len(songs)} songs available")
            else:
                self.log_result("Integration Health - Song Management", False, 
                              f"Song management failed: {songs_response.status_code}")
            
            # Test 3: Request handling (if we have songs)
            if songs_response.status_code == 200:
                songs = songs_response.json()
                if songs:
                    test_request_data = {
                        "song_id": songs[0]["id"],
                        "requester_name": "Deployment Test User",
                        "requester_email": "deploymenttest@example.com",
                        "dedication": "Testing deployment readiness"
                    }
                    
                    request_response = requests.post(
                        f"{BASE_URL}/requests",
                        json=test_request_data,
                        headers=self.get_headers()
                    )
                    
                    if request_response.status_code == 200:
                        request_data = request_response.json()
                        request_id = request_data.get("id")
                        self.test_request_ids.append(request_id)
                        
                        self.log_result("Integration Health - Request Handling", True, 
                                      "Request handling working correctly", {
                                          "request_id": request_id
                                      })
                    else:
                        self.log_result("Integration Health - Request Handling", False, 
                                      f"Request creation failed: {request_response.status_code}")
            
            # Test 4: QR code generation (critical for audience access)
            qr_response = requests.get(f"{BASE_URL}/qr-code", headers=self.get_headers())
            
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                if qr_data.get("qr_code") and qr_data.get("audience_url"):
                    self.log_result("Integration Health - QR Code Generation", True, 
                                  "QR code generation working correctly", {
                                      "audience_url": qr_data.get("audience_url")
                                  })
                else:
                    self.log_result("Integration Health - QR Code Generation", False, 
                                  "QR code generation incomplete", qr_data)
            else:
                self.log_result("Integration Health - QR Code Generation", False, 
                              f"QR code generation failed: {qr_response.status_code}")
            
            # Test 5: Profile management
            profile_response = requests.get(f"{BASE_URL}/profile", headers=self.get_headers())
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                if profile_data.get("name") and profile_data.get("email"):
                    self.log_result("Integration Health - Profile Management", True, 
                                  "Profile management working correctly")
                else:
                    self.log_result("Integration Health - Profile Management", False, 
                                  "Profile data incomplete", profile_data)
            else:
                self.log_result("Integration Health - Profile Management", False, 
                              f"Profile retrieval failed: {profile_response.status_code}")
                
        except Exception as e:
            self.log_result("Integration Health Check", False, f"Integration health check error: {str(e)}")

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== Cleaning Up Test Data ===")
        
        # Delete test songs
        for song_id in self.test_song_ids:
            try:
                response = requests.delete(
                    f"{BASE_URL}/songs/{song_id}",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    print(f"✅ Deleted test song {song_id}")
                else:
                    print(f"⚠️ Failed to delete test song {song_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error deleting test song {song_id}: {str(e)}")
        
        # Delete test requests
        for request_id in self.test_request_ids:
            try:
                response = requests.delete(
                    f"{BASE_URL}/requests/{request_id}",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    print(f"✅ Deleted test request {request_id}")
                else:
                    print(f"⚠️ Failed to delete test request {request_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error deleting test request {request_id}: {str(e)}")

    def run_all_tests(self):
        """Run all deployment readiness tests"""
        print("🚀 Starting Deployment Readiness Tests")
        print(f"Testing against: {BASE_URL}")
        print(f"Test user: {TEST_EMAIL}")
        print("=" * 60)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Run all deployment readiness tests
        self.test_environment_variable_configuration()
        self.test_url_generation_consistency()
        self.test_cors_configuration()
        self.test_production_deployment_readiness()
        self.test_mongodb_atlas_compatibility()
        self.test_integration_health_check()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 DEPLOYMENT READINESS TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎯 DEPLOYMENT READINESS TEST COMPLETE")
        return failed_tests == 0

if __name__ == "__main__":
    tester = DeploymentReadinessTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)