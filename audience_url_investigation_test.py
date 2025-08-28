#!/usr/bin/env python3
"""
RequestWave Backend Testing Suite - Audience URL Domain Mismatch Investigation
Testing the audience URL domain mismatch issue as per review request.

INVESTIGATION REQUIREMENTS:
1. Test GET /api/profile endpoint to see what audience URL data it returns
2. Test GET /api/qr-code endpoint to see what audience_url it generates  
3. Check actual runtime environment variables (FRONTEND_URL, DB_NAME, etc.)
4. Verify backend hotfix logic is working correctly
5. Test if there's cached profile data causing the issue

CONTEXT: Frontend audience URL input field shows "https://livewave-music.emergent.host/musician/bryce-larsen" 
instead of "https://requestwave.app/musician/bryce-larsen". Backend .env shows FRONTEND_URL=https://requestwave.app 
but issue persists.

Test credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import uuid
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class AudienceURLInvestigator:
    def __init__(self):
        # Get backend URL from environment
        self.backend_url = os.getenv('REACT_APP_BACKEND_URL', 'https://stagepro-app.preview.emergentagent.com')
        self.api_url = f"{self.backend_url}/api" if not self.backend_url.endswith('/api') else self.backend_url
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'RequestWave-URL-Investigator/1.0'
        })
        
        # Test credentials as specified in review request
        self.test_credentials = {
            "email": "brycelarsenmusic@gmail.com",
            "password": "RequestWave2024!"
        }
        
        self.jwt_token = None
        self.musician_id = None
        self.musician_slug = None
        
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
        print(f"🔍 RequestWave Audience URL Domain Mismatch Investigation")
        print(f"📍 Backend URL: {self.backend_url}")
        print(f"📍 API URL: {self.api_url}")
        print(f"🕐 Investigation Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        
        print(result)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def authenticate(self) -> bool:
        """Authenticate with test credentials"""
        print("\n🔐 AUTHENTICATING: Logging in with test credentials")
        print("-" * 50)
        
        try:
            response = self.session.post(
                f"{self.api_url}/auth/login",
                json=self.test_credentials
            )
            
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("token")
                musician_data = data.get("musician", {})
                self.musician_id = musician_data.get("id")
                self.musician_slug = musician_data.get("slug")
                
                if self.jwt_token and self.musician_id:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.jwt_token}'
                    })
                    self.log_test("Authentication", True, f"Logged in as {self.test_credentials['email']}, slug: {self.musician_slug}")
                    return True
                else:
                    self.log_test("Authentication", False, "Missing token or musician_id in response")
                    return False
            else:
                self.log_test("Authentication", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Authentication", False, f"Exception: {str(e)}")
            return False

    def test_environment_variables(self) -> Dict[str, Any]:
        """Test 1: Check actual runtime environment variables"""
        print("\n🌍 TESTING: Runtime Environment Variables Check")
        print("-" * 50)
        
        results = {
            "test_name": "Environment Variables Check",
            "tests_passed": 0,
            "tests_total": 5,
            "issues": [],
            "env_vars": {}
        }
        
        try:
            # Test 1: Check if we can access environment info through a health endpoint
            print("🔍 Test 1: Backend environment configuration...")
            response = self.session.get(f"{self.api_url}/health")
            
            if response.status_code == 200:
                self.log_test("Backend Health Check", True, "Backend is accessible")
                results["tests_passed"] += 1
            else:
                self.log_test("Backend Health Check", False, f"HTTP {response.status_code}")
                results["issues"].append("Backend health check failed")
            
            # Test 2: Check FRONTEND_URL through profile endpoint behavior
            print("🔍 Test 2: FRONTEND_URL configuration check...")
            if self.jwt_token:
                profile_response = self.session.get(f"{self.api_url}/profile")
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    # Look for any URL fields that might reveal FRONTEND_URL
                    self.log_test("Profile Endpoint Access", True, "Can access profile endpoint")
                    results["tests_passed"] += 1
                    results["env_vars"]["profile_accessible"] = True
                else:
                    self.log_test("Profile Endpoint Access", False, f"HTTP {profile_response.status_code}")
                    results["issues"].append("Cannot access profile endpoint")
            else:
                self.log_test("Profile Endpoint Access", False, "No JWT token available")
                results["issues"].append("Authentication required for profile access")
            
            # Test 3: Check DB_NAME through database operations
            print("🔍 Test 3: Database configuration check...")
            if self.jwt_token:
                # Try to access songs endpoint to verify database connectivity
                songs_response = self.session.get(f"{self.api_url}/songs")
                if songs_response.status_code == 200:
                    songs_data = songs_response.json()
                    self.log_test("Database Connectivity", True, f"Database accessible, found {len(songs_data)} songs")
                    results["tests_passed"] += 1
                    results["env_vars"]["db_accessible"] = True
                else:
                    self.log_test("Database Connectivity", False, f"HTTP {songs_response.status_code}")
                    results["issues"].append("Database connectivity issue")
            else:
                self.log_test("Database Connectivity", False, "No JWT token for database test")
                results["issues"].append("Authentication required for database test")
            
            # Test 4: Check backend URL configuration
            print("🔍 Test 4: Backend URL configuration...")
            expected_backend = "https://stagepro-app.preview.emergentagent.com"
            if self.backend_url == expected_backend:
                self.log_test("Backend URL Config", True, f"Using expected backend URL: {self.backend_url}")
                results["tests_passed"] += 1
                results["env_vars"]["backend_url"] = self.backend_url
            else:
                self.log_test("Backend URL Config", False, f"Unexpected backend URL: {self.backend_url}")
                results["issues"].append(f"Backend URL mismatch: expected {expected_backend}, got {self.backend_url}")
            
            # Test 5: Log environment variables we can detect
            print("🔍 Test 5: Environment variables detection...")
            detected_vars = {
                "REACT_APP_BACKEND_URL": os.getenv('REACT_APP_BACKEND_URL'),
                "backend_url_used": self.backend_url,
                "api_url_used": self.api_url
            }
            
            self.log_test("Environment Variables Detection", True, f"Detected vars: {json.dumps(detected_vars, indent=2)}")
            results["tests_passed"] += 1
            results["env_vars"].update(detected_vars)
                
        except Exception as e:
            self.log_test("Environment Variables Exception", False, f"Exception: {str(e)}")
            results["issues"].append(f"Exception: {str(e)}")
        
        print(f"\n📊 Environment Variables Results: {results['tests_passed']}/{results['tests_total']} tests passed")
        return results

    def test_profile_endpoint(self) -> Dict[str, Any]:
        """Test 2: GET /api/profile endpoint to see what audience URL data it returns"""
        print("\n👤 TESTING: Profile Endpoint Audience URL Data")
        print("-" * 50)
        
        results = {
            "test_name": "Profile Endpoint Analysis",
            "tests_passed": 0,
            "tests_total": 4,
            "issues": [],
            "profile_data": {}
        }
        
        if not self.jwt_token:
            self.log_test("Profile Endpoint Test", False, "No JWT token available")
            results["issues"].append("Authentication required")
            return results
        
        try:
            # Test 1: Get profile data
            print("📋 Test 1: Retrieving profile data...")
            response = self.session.get(f"{self.api_url}/profile")
            
            if response.status_code == 200:
                profile_data = response.json()
                self.log_test("Profile Data Retrieval", True, "Successfully retrieved profile data")
                results["tests_passed"] += 1
                results["profile_data"] = profile_data
                
                # Log key profile fields
                key_fields = ["name", "email", "slug"]
                for field in key_fields:
                    if field in profile_data:
                        print(f"   • {field}: {profile_data[field]}")
            else:
                self.log_test("Profile Data Retrieval", False, f"HTTP {response.status_code}: {response.text}")
                results["issues"].append(f"Profile retrieval failed: {response.status_code}")
                return results
            
            # Test 2: Check for audience URL fields in profile
            print("🔍 Test 2: Checking for audience URL fields...")
            url_related_fields = []
            for key, value in profile_data.items():
                if any(url_term in key.lower() for url_term in ["url", "link", "domain", "frontend"]):
                    url_related_fields.append(f"{key}: {value}")
            
            if url_related_fields:
                self.log_test("Profile URL Fields", True, f"Found URL-related fields: {url_related_fields}")
                results["tests_passed"] += 1
            else:
                self.log_test("Profile URL Fields", True, "No explicit URL fields in profile (expected)")
                results["tests_passed"] += 1
            
            # Test 3: Check musician slug for audience URL construction
            print("🔍 Test 3: Musician slug analysis...")
            musician_slug = profile_data.get("slug")
            if musician_slug:
                # Construct expected audience URLs
                expected_requestwave_url = f"https://requestwave.app/musician/{musician_slug}"
                problematic_url = f"https://livewave-music.emergent.host/musician/{musician_slug}"
                
                self.log_test("Musician Slug Analysis", True, f"Slug: {musician_slug}")
                results["tests_passed"] += 1
                
                print(f"   • Expected URL: {expected_requestwave_url}")
                print(f"   • Problematic URL: {problematic_url}")
                
                results["profile_data"]["expected_audience_url"] = expected_requestwave_url
                results["profile_data"]["problematic_audience_url"] = problematic_url
            else:
                self.log_test("Musician Slug Analysis", False, "No slug found in profile")
                results["issues"].append("Missing musician slug")
            
            # Test 4: Check for any cached URL data
            print("🔍 Test 4: Checking for cached URL data...")
            cached_fields = []
            for key, value in profile_data.items():
                if isinstance(value, str) and ("livewave-music.emergent.host" in value or "requestwave.app" in value):
                    cached_fields.append(f"{key}: {value}")
            
            if cached_fields:
                self.log_test("Cached URL Data", False, f"Found cached URL data: {cached_fields}")
                results["issues"].append(f"Cached URL data found: {cached_fields}")
            else:
                self.log_test("Cached URL Data", True, "No cached URL data in profile")
                results["tests_passed"] += 1
                
        except Exception as e:
            self.log_test("Profile Endpoint Exception", False, f"Exception: {str(e)}")
            results["issues"].append(f"Exception: {str(e)}")
        
        print(f"\n📊 Profile Endpoint Results: {results['tests_passed']}/{results['tests_total']} tests passed")
        return results

    def test_qr_code_endpoint(self) -> Dict[str, Any]:
        """Test 3: GET /api/qr-code endpoint to see what audience_url it generates"""
        print("\n📱 TESTING: QR Code Endpoint Audience URL Generation")
        print("-" * 50)
        
        results = {
            "test_name": "QR Code Endpoint Analysis",
            "tests_passed": 0,
            "tests_total": 4,
            "issues": [],
            "qr_data": {}
        }
        
        if not self.jwt_token:
            self.log_test("QR Code Endpoint Test", False, "No JWT token available")
            results["issues"].append("Authentication required")
            return results
        
        try:
            # Test 1: Get QR code data
            print("📱 Test 1: Retrieving QR code data...")
            response = self.session.get(f"{self.api_url}/qr-code")
            
            if response.status_code == 200:
                qr_data = response.json()
                self.log_test("QR Code Data Retrieval", True, "Successfully retrieved QR code data")
                results["tests_passed"] += 1
                results["qr_data"] = qr_data
                
                # Log QR code response structure
                print(f"   • QR Response keys: {list(qr_data.keys())}")
            else:
                self.log_test("QR Code Data Retrieval", False, f"HTTP {response.status_code}: {response.text}")
                results["issues"].append(f"QR code retrieval failed: {response.status_code}")
                return results
            
            # Test 2: Check audience_url in QR code response
            print("🔍 Test 2: Analyzing audience_url in QR response...")
            audience_url = qr_data.get("audience_url")
            if audience_url:
                self.log_test("QR Audience URL Present", True, f"Found audience_url: {audience_url}")
                results["tests_passed"] += 1
                
                # Check if it's using the problematic domain
                if "livewave-music.emergent.host" in audience_url:
                    self.log_test("QR URL Domain Check", False, f"Using problematic domain: {audience_url}")
                    results["issues"].append(f"QR code uses wrong domain: {audience_url}")
                elif "requestwave.app" in audience_url:
                    self.log_test("QR URL Domain Check", True, f"Using correct domain: {audience_url}")
                    results["tests_passed"] += 1
                else:
                    self.log_test("QR URL Domain Check", False, f"Using unexpected domain: {audience_url}")
                    results["issues"].append(f"QR code uses unexpected domain: {audience_url}")
            else:
                self.log_test("QR Audience URL Present", False, "No audience_url found in QR response")
                results["issues"].append("Missing audience_url in QR response")
            
            # Test 3: Check QR code image generation
            print("🔍 Test 3: QR code image generation...")
            qr_code_image = qr_data.get("qr_code")
            if qr_code_image:
                self.log_test("QR Code Image Generation", True, "QR code image generated successfully")
                results["tests_passed"] += 1
            else:
                self.log_test("QR Code Image Generation", False, "No QR code image in response")
                results["issues"].append("Missing QR code image")
            
            # Test 4: Test with different QR parameters
            print("🔍 Test 4: Testing QR code with parameters...")
            param_response = self.session.post(
                f"{self.api_url}/qr-code",
                json={"format": "png", "size": 10}
            )
            
            if param_response.status_code == 200:
                param_data = param_response.json()
                param_audience_url = param_data.get("audience_url")
                
                if param_audience_url == audience_url:
                    self.log_test("QR Code Parameters Test", True, "Consistent audience_url with parameters")
                    results["tests_passed"] += 1
                else:
                    self.log_test("QR Code Parameters Test", False, f"Inconsistent URLs: {param_audience_url} vs {audience_url}")
                    results["issues"].append("Inconsistent audience URLs between requests")
            else:
                self.log_test("QR Code Parameters Test", False, f"Parameters test failed: {param_response.status_code}")
                results["issues"].append("QR code parameters test failed")
                
        except Exception as e:
            self.log_test("QR Code Endpoint Exception", False, f"Exception: {str(e)}")
            results["issues"].append(f"Exception: {str(e)}")
        
        print(f"\n📊 QR Code Endpoint Results: {results['tests_passed']}/{results['tests_total']} tests passed")
        return results

    def test_backend_hotfix_logic(self) -> Dict[str, Any]:
        """Test 4: Verify backend hotfix logic is working correctly"""
        print("\n🔧 TESTING: Backend Hotfix Logic Verification")
        print("-" * 50)
        
        results = {
            "test_name": "Backend Hotfix Logic",
            "tests_passed": 0,
            "tests_total": 4,
            "issues": [],
            "hotfix_data": {}
        }
        
        if not self.jwt_token or not self.musician_slug:
            self.log_test("Hotfix Logic Test", False, "No JWT token or musician slug available")
            results["issues"].append("Authentication or slug required")
            return results
        
        try:
            # Test 1: Check public musician endpoint (audience view)
            print("🌐 Test 1: Public musician endpoint check...")
            public_response = self.session.get(f"{self.api_url}/musicians/{self.musician_slug}")
            
            if public_response.status_code == 200:
                public_data = public_response.json()
                self.log_test("Public Musician Endpoint", True, f"Public endpoint accessible for slug: {self.musician_slug}")
                results["tests_passed"] += 1
                results["hotfix_data"]["public_musician"] = public_data
                
                # Check for any URL fields in public data
                url_fields = []
                for key, value in public_data.items():
                    if isinstance(value, str) and any(domain in value for domain in ["livewave-music.emergent.host", "requestwave.app"]):
                        url_fields.append(f"{key}: {value}")
                
                if url_fields:
                    print(f"   • URL fields in public data: {url_fields}")
            else:
                self.log_test("Public Musician Endpoint", False, f"HTTP {public_response.status_code}")
                results["issues"].append("Public musician endpoint failed")
            
            # Test 2: Check songs endpoint for audience
            print("🎵 Test 2: Public songs endpoint check...")
            songs_response = self.session.get(f"{self.api_url}/musicians/{self.musician_slug}/songs")
            
            if songs_response.status_code == 200:
                songs_data = songs_response.json()
                self.log_test("Public Songs Endpoint", True, f"Found {len(songs_data)} songs for audience")
                results["tests_passed"] += 1
                results["hotfix_data"]["public_songs_count"] = len(songs_data)
            else:
                self.log_test("Public Songs Endpoint", False, f"HTTP {songs_response.status_code}")
                results["issues"].append("Public songs endpoint failed")
            
            # Test 3: Test request creation (audience functionality)
            print("📝 Test 3: Request creation test...")
            if len(results["hotfix_data"].get("public_songs_count", 0)) > 0:
                # Get first song for testing
                songs_response = self.session.get(f"{self.api_url}/musicians/{self.musician_slug}/songs")
                if songs_response.status_code == 200:
                    songs = songs_response.json()
                    if songs:
                        test_song = songs[0]
                        request_data = {
                            "song_id": test_song["id"],
                            "requester_name": "URL Test User",
                            "requester_email": "urltest@requestwave.com",
                            "dedication": "Testing URL generation"
                        }
                        
                        # Remove auth header for audience request
                        temp_headers = self.session.headers.copy()
                        if 'Authorization' in self.session.headers:
                            del self.session.headers['Authorization']
                        
                        request_response = self.session.post(
                            f"{self.api_url}/requests",
                            json=request_data
                        )
                        
                        # Restore auth header
                        self.session.headers = temp_headers
                        
                        if request_response.status_code == 200:
                            request_result = request_response.json()
                            self.log_test("Request Creation Test", True, "Audience can create requests")
                            results["tests_passed"] += 1
                            
                            # Clean up test request
                            if "id" in request_result:
                                cleanup_response = self.session.delete(f"{self.api_url}/requests/{request_result['id']}")
                                if cleanup_response.status_code == 200:
                                    print("   • Test request cleaned up successfully")
                        else:
                            self.log_test("Request Creation Test", False, f"Request creation failed: {request_response.status_code}")
                            results["issues"].append("Audience request creation failed")
            else:
                self.log_test("Request Creation Test", False, "No songs available for request test")
                results["issues"].append("No songs available for testing")
            
            # Test 4: Check URL construction logic
            print("🔗 Test 4: URL construction logic verification...")
            # This tests if the backend is correctly constructing URLs
            expected_base = "https://requestwave.app"
            expected_audience_url = f"{expected_base}/musician/{self.musician_slug}"
            
            # Check if QR code endpoint returns correct URL
            qr_response = self.session.get(f"{self.api_url}/qr-code")
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                actual_url = qr_data.get("audience_url", "")
                
                if actual_url == expected_audience_url:
                    self.log_test("URL Construction Logic", True, f"Correct URL construction: {actual_url}")
                    results["tests_passed"] += 1
                elif "requestwave.app" in actual_url:
                    self.log_test("URL Construction Logic", True, f"Using requestwave.app domain: {actual_url}")
                    results["tests_passed"] += 1
                else:
                    self.log_test("URL Construction Logic", False, f"Incorrect URL: {actual_url}, expected: {expected_audience_url}")
                    results["issues"].append(f"URL construction issue: got {actual_url}, expected {expected_audience_url}")
            else:
                self.log_test("URL Construction Logic", False, "Cannot test URL construction - QR endpoint failed")
                results["issues"].append("QR endpoint failed for URL construction test")
                
        except Exception as e:
            self.log_test("Backend Hotfix Exception", False, f"Exception: {str(e)}")
            results["issues"].append(f"Exception: {str(e)}")
        
        print(f"\n📊 Backend Hotfix Results: {results['tests_passed']}/{results['tests_total']} tests passed")
        return results

    def test_cached_data_investigation(self) -> Dict[str, Any]:
        """Test 5: Test if there's cached profile data causing the issue"""
        print("\n💾 TESTING: Cached Data Investigation")
        print("-" * 50)
        
        results = {
            "test_name": "Cached Data Investigation",
            "tests_passed": 0,
            "tests_total": 4,
            "issues": [],
            "cache_data": {}
        }
        
        if not self.jwt_token:
            self.log_test("Cache Investigation Test", False, "No JWT token available")
            results["issues"].append("Authentication required")
            return results
        
        try:
            # Test 1: Multiple profile requests to check consistency
            print("🔄 Test 1: Multiple profile requests consistency...")
            profile_urls = []
            
            for i in range(3):
                response = self.session.get(f"{self.api_url}/profile")
                if response.status_code == 200:
                    profile_data = response.json()
                    # Look for any URL-related data
                    for key, value in profile_data.items():
                        if isinstance(value, str) and any(domain in value for domain in ["livewave-music.emergent.host", "requestwave.app"]):
                            profile_urls.append(f"Request {i+1} - {key}: {value}")
                time.sleep(0.5)  # Small delay between requests
            
            if profile_urls:
                self.log_test("Profile Consistency Check", False, f"Found URL data in profile: {profile_urls}")
                results["issues"].append(f"Profile contains URL data: {profile_urls}")
            else:
                self.log_test("Profile Consistency Check", True, "No URL data found in profile (consistent)")
                results["tests_passed"] += 1
            
            # Test 2: QR code consistency check
            print("🔄 Test 2: QR code consistency check...")
            qr_urls = []
            
            for i in range(3):
                response = self.session.get(f"{self.api_url}/qr-code")
                if response.status_code == 200:
                    qr_data = response.json()
                    audience_url = qr_data.get("audience_url")
                    if audience_url:
                        qr_urls.append(audience_url)
                time.sleep(0.5)
            
            if len(set(qr_urls)) == 1:
                self.log_test("QR Code Consistency", True, f"Consistent QR URLs: {qr_urls[0] if qr_urls else 'None'}")
                results["tests_passed"] += 1
                results["cache_data"]["qr_url"] = qr_urls[0] if qr_urls else None
            else:
                self.log_test("QR Code Consistency", False, f"Inconsistent QR URLs: {qr_urls}")
                results["issues"].append(f"Inconsistent QR URLs: {qr_urls}")
            
            # Test 3: Database direct check (through musician endpoint)
            print("🗄️  Test 3: Database data consistency...")
            if self.musician_slug:
                db_urls = []
                
                for i in range(2):
                    response = self.session.get(f"{self.api_url}/musicians/{self.musician_slug}")
                    if response.status_code == 200:
                        musician_data = response.json()
                        for key, value in musician_data.items():
                            if isinstance(value, str) and any(domain in value for domain in ["livewave-music.emergent.host", "requestwave.app"]):
                                db_urls.append(f"{key}: {value}")
                    time.sleep(0.5)
                
                if db_urls:
                    self.log_test("Database Consistency", False, f"Found URL data in database: {db_urls}")
                    results["issues"].append(f"Database contains URL data: {db_urls}")
                else:
                    self.log_test("Database Consistency", True, "No URL data in database (expected)")
                    results["tests_passed"] += 1
            else:
                self.log_test("Database Consistency", False, "No musician slug for database test")
                results["issues"].append("Missing musician slug")
            
            # Test 4: Cache invalidation test
            print("🔄 Test 4: Cache invalidation test...")
            # Update profile to trigger any cache refresh
            profile_update = {
                "bio": f"Cache test - {datetime.now().isoformat()}"
            }
            
            update_response = self.session.put(
                f"{self.api_url}/profile",
                json=profile_update
            )
            
            if update_response.status_code == 200:
                # Wait a moment then check QR code again
                time.sleep(1)
                post_update_response = self.session.get(f"{self.api_url}/qr-code")
                
                if post_update_response.status_code == 200:
                    post_update_data = post_update_response.json()
                    post_update_url = post_update_data.get("audience_url")
                    
                    if post_update_url == results["cache_data"].get("qr_url"):
                        self.log_test("Cache Invalidation Test", True, "URL consistent after profile update")
                        results["tests_passed"] += 1
                    else:
                        self.log_test("Cache Invalidation Test", False, f"URL changed after update: {post_update_url}")
                        results["issues"].append("URL inconsistency after profile update")
                else:
                    self.log_test("Cache Invalidation Test", False, "QR endpoint failed after profile update")
                    results["issues"].append("QR endpoint failed after profile update")
            else:
                self.log_test("Cache Invalidation Test", False, f"Profile update failed: {update_response.status_code}")
                results["issues"].append("Profile update failed for cache test")
                
        except Exception as e:
            self.log_test("Cache Investigation Exception", False, f"Exception: {str(e)}")
            results["issues"].append(f"Exception: {str(e)}")
        
        print(f"\n📊 Cache Investigation Results: {results['tests_passed']}/{results['tests_total']} tests passed")
        return results

    def run_investigation(self):
        """Run complete audience URL domain mismatch investigation"""
        print("🔍 STARTING: Audience URL Domain Mismatch Investigation")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ CRITICAL: Authentication failed - cannot proceed with investigation")
            return "AUTHENTICATION_FAILED", 0, []
        
        # Run all investigation tests
        env_results = self.test_environment_variables()
        profile_results = self.test_profile_endpoint()
        qr_results = self.test_qr_code_endpoint()
        hotfix_results = self.test_backend_hotfix_logic()
        cache_results = self.test_cached_data_investigation()
        
        # Calculate overall results
        all_results = [env_results, profile_results, qr_results, hotfix_results, cache_results]
        total_tests_passed = sum(r["tests_passed"] for r in all_results)
        total_tests_total = sum(r["tests_total"] for r in all_results)
        
        # Print comprehensive summary
        print("\n" + "=" * 80)
        print("🔍 AUDIENCE URL DOMAIN MISMATCH INVESTIGATION SUMMARY")
        print("=" * 80)
        
        success_rate = (total_tests_passed / total_tests_total * 100) if total_tests_total > 0 else 0
        
        print(f"Total Tests: {total_tests_total}")
        print(f"Passed: {total_tests_passed}")
        print(f"Failed: {total_tests_total - total_tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Investigation findings
        print("\n🔍 KEY INVESTIGATION FINDINGS:")
        
        # Environment variables
        if env_results["tests_passed"] >= 3:
            print("✅ Environment configuration appears correct")
        else:
            print("❌ Environment configuration issues detected")
        
        # Profile endpoint
        profile_audience_url = profile_results.get("profile_data", {}).get("expected_audience_url")
        if profile_audience_url and "requestwave.app" in profile_audience_url:
            print(f"✅ Profile generates correct audience URL: {profile_audience_url}")
        else:
            print("❌ Profile audience URL generation issue")
        
        # QR code endpoint
        qr_audience_url = qr_results.get("qr_data", {}).get("audience_url")
        if qr_audience_url:
            if "requestwave.app" in qr_audience_url:
                print(f"✅ QR code uses correct domain: {qr_audience_url}")
            elif "livewave-music.emergent.host" in qr_audience_url:
                print(f"❌ QR code uses problematic domain: {qr_audience_url}")
            else:
                print(f"⚠️  QR code uses unexpected domain: {qr_audience_url}")
        else:
            print("❌ QR code endpoint not returning audience_url")
        
        # Backend hotfix logic
        if hotfix_results["tests_passed"] >= 3:
            print("✅ Backend hotfix logic working correctly")
        else:
            print("❌ Backend hotfix logic issues detected")
        
        # Cache investigation
        if cache_results["tests_passed"] >= 3:
            print("✅ No cached data issues detected")
        else:
            print("❌ Potential cached data issues found")
        
        # Root cause analysis
        print("\n🎯 ROOT CAUSE ANALYSIS:")
        
        all_issues = []
        for result in all_results:
            all_issues.extend(result.get("issues", []))
        
        domain_issues = [issue for issue in all_issues if "livewave-music.emergent.host" in issue]
        if domain_issues:
            print("🚨 CRITICAL: Found references to problematic domain:")
            for issue in domain_issues:
                print(f"   • {issue}")
        
        url_construction_issues = [issue for issue in all_issues if "URL" in issue and "construction" in issue]
        if url_construction_issues:
            print("🔧 URL Construction Issues:")
            for issue in url_construction_issues:
                print(f"   • {issue}")
        
        cache_issues = [issue for issue in all_issues if "cache" in issue.lower() or "consistency" in issue.lower()]
        if cache_issues:
            print("💾 Cache/Consistency Issues:")
            for issue in cache_issues:
                print(f"   • {issue}")
        
        # Overall status
        if success_rate >= 85:
            print("\n🎉 INVESTIGATION STATUS: MOSTLY HEALTHY (minor issues)")
            overall_status = "MOSTLY_HEALTHY"
        elif success_rate >= 70:
            print("\n⚠️  INVESTIGATION STATUS: ISSUES DETECTED")
            overall_status = "ISSUES_DETECTED"
        else:
            print("\n❌ INVESTIGATION STATUS: CRITICAL ISSUES")
            overall_status = "CRITICAL_ISSUES"
        
        print("=" * 80)
        print(f"🏁 INVESTIGATION COMPLETE: {overall_status}")
        print("=" * 80)
        
        return overall_status, success_rate, all_results

def main():
    """Main investigation execution function"""
    investigator = AudienceURLInvestigator()
    
    try:
        overall_status, success_rate, results = investigator.run_investigation()
        
        # Return appropriate exit code
        if overall_status in ["MOSTLY_HEALTHY", "ISSUES_DETECTED"]:
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Investigation failed with exception: {str(e)}")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)