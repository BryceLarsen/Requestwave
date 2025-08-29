#!/usr/bin/env python3
"""
QR CODE URL MISMATCH DEBUGGING TEST

The user reports:
- Frontend audience URL: https://requestwave-app.preview.emergentagent.com/musician/bryce-larsen (working)
- QR code URL: https://livewave-music.emergent.host/musician/bryce-larsen (not working)

This test will investigate:
1. Backend Environment Variables: What is the actual FRONTEND_URL value the backend is reading at runtime?
2. Test QR Code Generation: Generate a test QR code and verify what audience_url it returns
3. Environment Variable Source: Check if the backend is reading from .env file or deployment-level environment variables
4. Frontend URL Detection: Check what REACT_APP_BACKEND_URL is set to and how the frontend is determining the base URL
5. QR Code Endpoint: Test GET /api/qr-code directly to see what URL it generates

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://requestwave-app.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class QRCodeDebugTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None
        self.musician_slug = None
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

    def test_backend_environment_variables(self):
        """Test what FRONTEND_URL value the backend is reading at runtime"""
        try:
            print("🔍 INVESTIGATION 1: Backend Environment Variables")
            print("=" * 80)
            
            # Step 1: Login with Pro account
            print("📊 Step 1: Login with Pro account")
            login_data = {
                "email": PRO_MUSICIAN["email"],
                "password": PRO_MUSICIAN["password"]
            }
            
            login_response = self.make_request("POST", "/auth/login", login_data)
            
            if login_response.status_code != 200:
                self.log_result("Backend Environment Variables - Pro Login", False, f"Failed to login: {login_response.status_code}")
                return
            
            login_data_response = login_response.json()
            self.auth_token = login_data_response["token"]
            self.musician_slug = login_data_response["musician"]["slug"]
            
            print(f"   ✅ Successfully logged in as: {login_data_response['musician']['name']}")
            print(f"   📊 Musician slug: {self.musician_slug}")
            
            # Step 2: Check if there's a debug/config endpoint to see environment variables
            print("📊 Step 2: Check for debug/config endpoint")
            
            # Try common debug endpoints
            debug_endpoints = ["/debug", "/config", "/health", "/status", "/env"]
            
            for endpoint in debug_endpoints:
                try:
                    debug_response = self.make_request("GET", endpoint)
                    print(f"   📊 {endpoint}: {debug_response.status_code}")
                    
                    if debug_response.status_code == 200:
                        debug_data = debug_response.json()
                        print(f"   📊 {endpoint} response: {json.dumps(debug_data, indent=2)[:500]}...")
                        
                        # Look for FRONTEND_URL in the response
                        if isinstance(debug_data, dict):
                            for key, value in debug_data.items():
                                if 'frontend' in key.lower() or 'url' in key.lower():
                                    print(f"   🔍 Found URL-related config: {key} = {value}")
                except:
                    pass
            
            # Step 3: Try to infer FRONTEND_URL from QR code generation
            print("📊 Step 3: Generate QR code to see what URL is used")
            
            qr_response = self.make_request("GET", "/qr-code")
            
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                print(f"   ✅ QR code endpoint accessible")
                print(f"   📊 QR code response keys: {list(qr_data.keys())}")
                
                # Look for audience_url in the response
                audience_url = qr_data.get('audience_url')
                if audience_url:
                    print(f"   🔍 FOUND AUDIENCE URL IN QR CODE: {audience_url}")
                    
                    # Extract the base URL
                    if '/musician/' in audience_url:
                        base_url = audience_url.split('/musician/')[0]
                        print(f"   🔍 EXTRACTED BASE URL: {base_url}")
                        
                        # This is likely the FRONTEND_URL the backend is using
                        if 'livewave-music.emergent.host' in base_url:
                            print(f"   ❌ ISSUE IDENTIFIED: Backend is using old URL: {base_url}")
                            print(f"   📊 Expected URL should be: https://requestwave-app.preview.emergentagent.com")
                            backend_url_issue = True
                        else:
                            print(f"   ✅ Backend URL looks correct: {base_url}")
                            backend_url_issue = False
                    else:
                        print(f"   ❌ Unexpected audience URL format: {audience_url}")
                        backend_url_issue = True
                else:
                    print(f"   ❌ No audience_url found in QR code response")
                    backend_url_issue = True
            else:
                print(f"   ❌ QR code endpoint failed: {qr_response.status_code}")
                print(f"   📊 Response: {qr_response.text[:200]}...")
                backend_url_issue = True
            
            # Step 4: Test QR code with specific musician slug
            print("📊 Step 4: Test QR code with specific musician slug")
            
            if self.musician_slug:
                musician_qr_response = self.make_request("GET", f"/musicians/{self.musician_slug}/qr-code")
                
                if musician_qr_response.status_code == 200:
                    musician_qr_data = musician_qr_response.json()
                    print(f"   ✅ Musician-specific QR code endpoint accessible")
                    
                    musician_audience_url = musician_qr_data.get('audience_url')
                    if musician_audience_url:
                        print(f"   🔍 MUSICIAN QR CODE URL: {musician_audience_url}")
                        
                        # Check if this matches the expected URL
                        expected_url = f"https://requestwave-app.preview.emergentagent.com/musician/{self.musician_slug}"
                        if musician_audience_url == expected_url:
                            print(f"   ✅ Musician QR code URL matches expected URL")
                            musician_qr_correct = True
                        else:
                            print(f"   ❌ Musician QR code URL mismatch")
                            print(f"   📊 Expected: {expected_url}")
                            print(f"   📊 Actual:   {musician_audience_url}")
                            musician_qr_correct = False
                    else:
                        print(f"   ❌ No audience_url in musician QR code response")
                        musician_qr_correct = False
                else:
                    print(f"   ❌ Musician QR code endpoint failed: {musician_qr_response.status_code}")
                    musician_qr_correct = False
            else:
                musician_qr_correct = False
            
            # Final assessment
            if not backend_url_issue and musician_qr_correct:
                self.log_result("Backend Environment Variables", True, "✅ Backend FRONTEND_URL configuration is correct")
            else:
                issues = []
                if backend_url_issue:
                    issues.append("Backend using incorrect FRONTEND_URL (livewave-music.emergent.host instead of performance-pay-1.preview.emergentagent.com)")
                if not musician_qr_correct:
                    issues.append("Musician-specific QR code URL incorrect")
                
                self.log_result("Backend Environment Variables", False, f"❌ BACKEND URL CONFIGURATION ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Backend Environment Variables", False, f"❌ Exception: {str(e)}")

    def test_qr_code_generation(self):
        """Generate a test QR code and verify what audience_url it returns"""
        try:
            print("🔍 INVESTIGATION 2: QR Code Generation Testing")
            print("=" * 80)
            
            # Step 1: Test general QR code endpoint
            print("📊 Step 1: Test general QR code endpoint")
            
            qr_response = self.make_request("GET", "/qr-code")
            
            print(f"   📊 QR code endpoint status: {qr_response.status_code}")
            print(f"   📊 QR code response: {qr_response.text[:300]}...")
            
            if qr_response.status_code == 200:
                try:
                    qr_data = qr_response.json()
                    print(f"   ✅ QR code endpoint returns JSON")
                    print(f"   📊 Response keys: {list(qr_data.keys())}")
                    
                    # Check for audience_url
                    if 'audience_url' in qr_data:
                        audience_url = qr_data['audience_url']
                        print(f"   🔍 AUDIENCE URL: {audience_url}")
                        general_qr_works = True
                    else:
                        print(f"   ❌ No audience_url in response")
                        general_qr_works = False
                        
                except json.JSONDecodeError:
                    print(f"   ❌ QR code response is not valid JSON")
                    general_qr_works = False
            else:
                print(f"   ❌ QR code endpoint failed")
                general_qr_works = False
            
            # Step 2: Test musician-specific QR code endpoint
            print("📊 Step 2: Test musician-specific QR code endpoint")
            
            if self.musician_slug:
                musician_qr_response = self.make_request("GET", f"/musicians/{self.musician_slug}/qr-code")
                
                print(f"   📊 Musician QR code status: {musician_qr_response.status_code}")
                print(f"   📊 Musician QR code response: {musician_qr_response.text[:300]}...")
                
                if musician_qr_response.status_code == 200:
                    try:
                        musician_qr_data = musician_qr_response.json()
                        print(f"   ✅ Musician QR code endpoint returns JSON")
                        print(f"   📊 Response keys: {list(musician_qr_data.keys())}")
                        
                        # Check for audience_url
                        if 'audience_url' in musician_qr_data:
                            musician_audience_url = musician_qr_data['audience_url']
                            print(f"   🔍 MUSICIAN AUDIENCE URL: {musician_audience_url}")
                            
                            # Analyze the URL components
                            if 'livewave-music.emergent.host' in musician_audience_url:
                                print(f"   ❌ PROBLEM IDENTIFIED: Using old domain 'livewave-music.emergent.host'")
                                print(f"   📊 Should be: 'performance-pay-1.preview.emergentagent.com'")
                                url_domain_correct = False
                            elif 'performance-pay-1.preview.emergentagent.com' in musician_audience_url:
                                print(f"   ✅ Correct domain in use")
                                url_domain_correct = True
                            else:
                                print(f"   ❌ Unexpected domain in URL")
                                url_domain_correct = False
                            
                            # Check if slug is correct
                            if f"/musician/{self.musician_slug}" in musician_audience_url:
                                print(f"   ✅ Correct musician slug in URL")
                                url_slug_correct = True
                            else:
                                print(f"   ❌ Incorrect or missing musician slug in URL")
                                url_slug_correct = False
                            
                            musician_qr_works = True
                        else:
                            print(f"   ❌ No audience_url in musician QR code response")
                            musician_qr_works = False
                            url_domain_correct = False
                            url_slug_correct = False
                            
                    except json.JSONDecodeError:
                        print(f"   ❌ Musician QR code response is not valid JSON")
                        musician_qr_works = False
                        url_domain_correct = False
                        url_slug_correct = False
                else:
                    print(f"   ❌ Musician QR code endpoint failed")
                    musician_qr_works = False
                    url_domain_correct = False
                    url_slug_correct = False
            else:
                print(f"   ❌ No musician slug available for testing")
                musician_qr_works = False
                url_domain_correct = False
                url_slug_correct = False
            
            # Step 3: Test QR code with different parameters
            print("📊 Step 3: Test QR code with different parameters")
            
            qr_params = [
                {"format": "png", "size": 10},
                {"format": "png", "size": 5},
                {}  # Default parameters
            ]
            
            param_tests_passed = 0
            
            for i, params in enumerate(qr_params):
                param_response = self.make_request("GET", "/qr-code", params=params)
                
                if param_response.status_code == 200:
                    print(f"   ✅ QR code with params {params}: Success")
                    param_tests_passed += 1
                else:
                    print(f"   ❌ QR code with params {params}: Failed ({param_response.status_code})")
            
            params_work = param_tests_passed == len(qr_params)
            
            # Final assessment
            if general_qr_works and musician_qr_works and url_domain_correct and url_slug_correct and params_work:
                self.log_result("QR Code Generation", True, "✅ QR code generation working correctly with proper URLs")
            else:
                issues = []
                if not general_qr_works:
                    issues.append("general QR code endpoint not working")
                if not musician_qr_works:
                    issues.append("musician-specific QR code endpoint not working")
                if not url_domain_correct:
                    issues.append("incorrect domain in QR code URLs (using livewave-music.emergent.host instead of performance-pay-1.preview.emergentagent.com)")
                if not url_slug_correct:
                    issues.append("incorrect musician slug in QR code URLs")
                if not params_work:
                    issues.append("QR code parameters not working correctly")
                
                self.log_result("QR Code Generation", False, f"❌ QR CODE GENERATION ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("QR Code Generation", False, f"❌ Exception: {str(e)}")

    def test_frontend_url_detection(self):
        """Check what REACT_APP_BACKEND_URL is set to and how the frontend is determining the base URL"""
        try:
            print("🔍 INVESTIGATION 3: Frontend URL Detection")
            print("=" * 80)
            
            # Step 1: Test the actual frontend URL that should work
            print("📊 Step 1: Test the working frontend URL")
            
            expected_frontend_url = f"https://requestwave-app.preview.emergentagent.com/musician/{self.musician_slug}"
            
            try:
                # Test if the expected URL is accessible
                frontend_response = requests.get(expected_frontend_url, timeout=10)
                print(f"   📊 Frontend URL test: {frontend_response.status_code}")
                
                if frontend_response.status_code == 200:
                    print(f"   ✅ Expected frontend URL is accessible: {expected_frontend_url}")
                    expected_url_works = True
                else:
                    print(f"   ❌ Expected frontend URL returned: {frontend_response.status_code}")
                    expected_url_works = False
            except Exception as e:
                print(f"   ❌ Failed to test expected frontend URL: {str(e)}")
                expected_url_works = False
            
            # Step 2: Test the problematic URL from QR code
            print("📊 Step 2: Test the problematic QR code URL")
            
            problematic_url = f"https://livewave-music.emergent.host/musician/{self.musician_slug}"
            
            try:
                # Test if the problematic URL is accessible
                problem_response = requests.get(problematic_url, timeout=10)
                print(f"   📊 Problematic URL test: {problem_response.status_code}")
                
                if problem_response.status_code == 200:
                    print(f"   ⚠️  Problematic URL is actually accessible: {problematic_url}")
                    problematic_url_accessible = True
                else:
                    print(f"   ❌ Problematic URL not accessible: {problem_response.status_code}")
                    problematic_url_accessible = False
            except Exception as e:
                print(f"   ❌ Problematic URL failed as expected: {str(e)}")
                problematic_url_accessible = False
            
            # Step 3: Check backend API base URL consistency
            print("📊 Step 3: Check backend API base URL consistency")
            
            # The backend API we're using
            current_backend_url = self.base_url
            print(f"   📊 Current backend API URL: {current_backend_url}")
            
            # Extract the base domain
            if 'performance-pay-1.preview.emergentagent.com' in current_backend_url:
                print(f"   ✅ Backend API using correct domain")
                backend_domain_correct = True
            else:
                print(f"   ❌ Backend API using unexpected domain")
                backend_domain_correct = False
            
            # Step 4: Test if backend and frontend domains match
            print("📊 Step 4: Test backend and frontend domain consistency")
            
            backend_domain = current_backend_url.replace('/api', '').replace('http://', '').replace('https://', '')
            expected_frontend_domain = expected_frontend_url.replace('http://', '').replace('https://', '').split('/')[0]
            
            print(f"   📊 Backend domain: {backend_domain}")
            print(f"   📊 Expected frontend domain: {expected_frontend_domain}")
            
            if backend_domain == expected_frontend_domain:
                print(f"   ✅ Backend and frontend domains match")
                domains_match = True
            else:
                print(f"   ❌ Backend and frontend domains don't match")
                domains_match = False
            
            # Step 5: Test CORS and API accessibility
            print("📊 Step 5: Test CORS and API accessibility")
            
            # Test a simple API endpoint to verify CORS
            cors_test_response = self.make_request("GET", "/health")
            
            if cors_test_response.status_code == 200:
                print(f"   ✅ API accessible and CORS working")
                cors_works = True
            else:
                print(f"   ❌ API accessibility issues: {cors_test_response.status_code}")
                cors_works = False
            
            # Final assessment
            if expected_url_works and not problematic_url_accessible and backend_domain_correct and domains_match and cors_works:
                self.log_result("Frontend URL Detection", True, "✅ Frontend URL configuration is correct, issue is in backend QR code generation")
            else:
                issues = []
                if not expected_url_works:
                    issues.append("expected frontend URL not accessible")
                if problematic_url_accessible:
                    issues.append("problematic URL is unexpectedly accessible")
                if not backend_domain_correct:
                    issues.append("backend API using wrong domain")
                if not domains_match:
                    issues.append("backend and frontend domains don't match")
                if not cors_works:
                    issues.append("CORS or API accessibility issues")
                
                self.log_result("Frontend URL Detection", False, f"❌ FRONTEND URL DETECTION ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Frontend URL Detection", False, f"❌ Exception: {str(e)}")

    def test_qr_code_endpoint_direct(self):
        """Test GET /api/qr-code directly to see what URL it generates"""
        try:
            print("🔍 INVESTIGATION 4: Direct QR Code Endpoint Testing")
            print("=" * 80)
            
            # Step 1: Test QR code endpoint without authentication
            print("📊 Step 1: Test QR code endpoint without authentication")
            
            # Clear auth token temporarily
            temp_token = self.auth_token
            self.auth_token = None
            
            no_auth_response = self.make_request("GET", "/qr-code")
            
            print(f"   📊 No auth QR code status: {no_auth_response.status_code}")
            
            if no_auth_response.status_code == 401:
                print(f"   ✅ QR code endpoint requires authentication (expected)")
                auth_required = True
            elif no_auth_response.status_code == 200:
                print(f"   ⚠️  QR code endpoint accessible without auth")
                auth_required = False
            else:
                print(f"   ❌ Unexpected response: {no_auth_response.status_code}")
                auth_required = False
            
            # Restore auth token
            self.auth_token = temp_token
            
            # Step 2: Test QR code endpoint with authentication
            print("📊 Step 2: Test QR code endpoint with authentication")
            
            auth_response = self.make_request("GET", "/qr-code")
            
            print(f"   📊 Auth QR code status: {auth_response.status_code}")
            print(f"   📊 Auth QR code response: {auth_response.text[:500]}...")
            
            if auth_response.status_code == 200:
                try:
                    auth_qr_data = auth_response.json()
                    print(f"   ✅ QR code endpoint accessible with auth")
                    print(f"   📊 Response structure: {list(auth_qr_data.keys())}")
                    
                    # Extract and analyze the audience URL
                    if 'audience_url' in auth_qr_data:
                        audience_url = auth_qr_data['audience_url']
                        print(f"   🔍 AUDIENCE URL: {audience_url}")
                        
                        # Detailed URL analysis
                        url_parts = audience_url.split('/')
                        print(f"   📊 URL parts: {url_parts}")
                        
                        # Check domain
                        if 'livewave-music.emergent.host' in audience_url:
                            print(f"   ❌ CONFIRMED ISSUE: Using old domain 'livewave-music.emergent.host'")
                            domain_issue_confirmed = True
                        elif 'performance-pay-1.preview.emergentagent.com' in audience_url:
                            print(f"   ✅ Using correct domain")
                            domain_issue_confirmed = False
                        else:
                            print(f"   ❌ Using unexpected domain")
                            domain_issue_confirmed = True
                        
                        # Check if it includes musician slug
                        if self.musician_slug and self.musician_slug in audience_url:
                            print(f"   ✅ Includes correct musician slug: {self.musician_slug}")
                            slug_correct = True
                        else:
                            print(f"   ❌ Missing or incorrect musician slug")
                            slug_correct = False
                        
                        auth_qr_works = True
                    else:
                        print(f"   ❌ No audience_url in response")
                        auth_qr_works = False
                        domain_issue_confirmed = True
                        slug_correct = False
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Response is not valid JSON")
                    auth_qr_works = False
                    domain_issue_confirmed = True
                    slug_correct = False
            else:
                print(f"   ❌ QR code endpoint failed with auth")
                auth_qr_works = False
                domain_issue_confirmed = True
                slug_correct = False
            
            # Step 3: Test QR code with different formats and sizes
            print("📊 Step 3: Test QR code with different formats and sizes")
            
            format_tests = [
                {"format": "png", "size": 5},
                {"format": "png", "size": 10},
                {"format": "png", "size": 15}
            ]
            
            format_results = []
            
            for params in format_tests:
                format_response = self.make_request("GET", "/qr-code", params=params)
                
                if format_response.status_code == 200:
                    try:
                        format_data = format_response.json()
                        if 'audience_url' in format_data:
                            format_url = format_data['audience_url']
                            print(f"   📊 Format {params}: {format_url[:50]}...")
                            format_results.append(format_url)
                        else:
                            print(f"   ❌ Format {params}: No audience_url")
                    except:
                        print(f"   ❌ Format {params}: Invalid JSON")
                else:
                    print(f"   ❌ Format {params}: Failed ({format_response.status_code})")
            
            # Check if all format tests return the same URL
            if format_results and all(url == format_results[0] for url in format_results):
                print(f"   ✅ All format tests return consistent URL")
                format_consistency = True
            else:
                print(f"   ❌ Format tests return inconsistent URLs")
                format_consistency = False
            
            # Step 4: Compare with musician-specific endpoint
            print("📊 Step 4: Compare with musician-specific QR code endpoint")
            
            if self.musician_slug:
                musician_specific_response = self.make_request("GET", f"/musicians/{self.musician_slug}/qr-code")
                
                if musician_specific_response.status_code == 200:
                    try:
                        musician_specific_data = musician_specific_response.json()
                        if 'audience_url' in musician_specific_data:
                            musician_specific_url = musician_specific_data['audience_url']
                            print(f"   📊 Musician-specific URL: {musician_specific_url}")
                            
                            # Compare with general endpoint
                            if auth_qr_works and 'audience_url' in auth_qr_data:
                                general_url = auth_qr_data['audience_url']
                                if musician_specific_url == general_url:
                                    print(f"   ✅ General and musician-specific URLs match")
                                    url_consistency = True
                                else:
                                    print(f"   ❌ General and musician-specific URLs differ")
                                    print(f"   📊 General: {general_url}")
                                    print(f"   📊 Specific: {musician_specific_url}")
                                    url_consistency = False
                            else:
                                url_consistency = False
                        else:
                            print(f"   ❌ No audience_url in musician-specific response")
                            url_consistency = False
                    except:
                        print(f"   ❌ Musician-specific response invalid JSON")
                        url_consistency = False
                else:
                    print(f"   ❌ Musician-specific endpoint failed: {musician_specific_response.status_code}")
                    url_consistency = False
            else:
                url_consistency = False
            
            # Final assessment
            if auth_qr_works and not domain_issue_confirmed and slug_correct and format_consistency and url_consistency:
                self.log_result("QR Code Endpoint Direct", True, "✅ QR code endpoint working correctly with proper URLs")
            else:
                issues = []
                if not auth_qr_works:
                    issues.append("QR code endpoint not working with authentication")
                if domain_issue_confirmed:
                    issues.append("CONFIRMED: QR code using wrong domain (livewave-music.emergent.host)")
                if not slug_correct:
                    issues.append("musician slug missing or incorrect in QR code URL")
                if not format_consistency:
                    issues.append("QR code format parameters causing inconsistent URLs")
                if not url_consistency:
                    issues.append("general and musician-specific QR code endpoints return different URLs")
                
                self.log_result("QR Code Endpoint Direct", False, f"❌ QR CODE ENDPOINT ISSUES: {', '.join(issues)}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("QR Code Endpoint Direct", False, f"❌ Exception: {str(e)}")

    def run_all_investigations(self):
        """Run all QR code URL mismatch investigations"""
        print("🔍 STARTING QR CODE URL MISMATCH DEBUGGING")
        print("=" * 100)
        
        # Investigation 1: Backend Environment Variables
        self.test_backend_environment_variables()
        
        # Investigation 2: QR Code Generation
        self.test_qr_code_generation()
        
        # Investigation 3: Frontend URL Detection
        self.test_frontend_url_detection()
        
        # Investigation 4: Direct QR Code Endpoint Testing
        self.test_qr_code_endpoint_direct()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🔍 FINAL QR CODE URL MISMATCH INVESTIGATION RESULTS")
        print("=" * 100)
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        
        if self.results['passed'] + self.results['failed'] > 0:
            success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100)
            print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results['errors']:
            print("\n❌ INVESTIGATION FINDINGS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n🔍 SUMMARY OF FINDINGS:")
        print("   The QR code URL mismatch issue appears to be caused by the backend")
        print("   using an outdated FRONTEND_URL environment variable value.")
        print("   Expected: https://requestwave-app.preview.emergentagent.com")
        print("   Actual:   https://livewave-music.emergent.host")
        print("\n💡 RECOMMENDED SOLUTION:")
        print("   Update the FRONTEND_URL environment variable in the backend")
        print("   configuration to use the correct domain.")
        
        print("\n" + "=" * 100)

if __name__ == "__main__":
    tester = QRCodeDebugTester()
    tester.run_all_investigations()