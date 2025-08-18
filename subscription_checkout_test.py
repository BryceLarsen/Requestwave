#!/usr/bin/env python3
"""
COMPREHENSIVE SUBSCRIPTION CHECKOUT BACKEND TESTING

Testing the comprehensive production subscription checkout fixes as requested:

CRITICAL TEST AREAS:
1. POST /api/subscription/checkout with brycelarsenmusic@gmail.com
2. Test both monthly and annual plans
3. Test validation errors (missing plan, invalid plan, missing URLs)
4. Verify proper 422 responses with error_id for validation failures
5. Test response format should return { url: "stripe_checkout_url" } on success
6. Test environment configuration error messages
7. Test webhook endpoint POST /api/stripe/webhook

Test Credentials: brycelarsenmusic@gmail.com / RequestWave2024!

Expected: Enhanced error handling, validation logic, structured logging, and proper Stripe integration.
"""

import requests
import json
import os
import time
import uuid
from typing import Dict, Any, Optional

# Configuration - Use environment variable from frontend/.env
FRONTEND_ENV_URL = "https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com"
BASE_URL = f"{FRONTEND_ENV_URL}/api"

# Test credentials as specified
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class SubscriptionCheckoutTester:
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

    def test_authentication_setup(self):
        """Test authentication with specified credentials"""
        try:
            print("🔐 AUTHENTICATION SETUP")
            print("=" * 80)
            
            print("📊 Step 1: Login with brycelarsenmusic@gmail.com")
            
            login_data = {
                "email": TEST_CREDENTIALS["email"],
                "password": TEST_CREDENTIALS["password"]
            }
            
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
                    
                    self.log_result("Authentication Setup", True, f"Successfully authenticated as {data['musician']['name']}")
                else:
                    self.log_result("Authentication Setup", False, f"Missing token or musician in response: {data}")
            else:
                self.log_result("Authentication Setup", False, f"Login failed with status {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception: {str(e)}")

    def test_subscription_checkout_monthly_plan(self):
        """Test POST /api/subscription/checkout with monthly plan"""
        try:
            print("💳 SUBSCRIPTION CHECKOUT - MONTHLY PLAN")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Checkout Monthly", False, "No authentication token available")
                return
            
            print("📊 Step 1: Test monthly plan checkout with valid data")
            
            checkout_data = {
                "plan": "monthly",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Checkout response status: {response.status_code}")
            print(f"   📊 Checkout response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response data keys: {list(data.keys())}")
                    
                    # Check for expected response format: { url: "stripe_checkout_url" }
                    if "url" in data:
                        checkout_url = data["url"]
                        print(f"   ✅ Checkout URL returned: {checkout_url[:100]}...")
                        
                        # Verify it's a Stripe checkout URL
                        if "stripe.com" in checkout_url or "checkout.stripe.com" in checkout_url:
                            print(f"   ✅ Valid Stripe checkout URL format")
                            self.log_result("Subscription Checkout Monthly - Valid Response", True, "Monthly checkout returns valid Stripe URL")
                        else:
                            print(f"   ⚠️  URL doesn't appear to be Stripe checkout URL")
                            self.log_result("Subscription Checkout Monthly - URL Format", False, f"URL doesn't appear to be Stripe: {checkout_url}")
                    else:
                        print(f"   ❌ Missing 'url' field in response")
                        self.log_result("Subscription Checkout Monthly - Missing URL", False, f"Response missing 'url' field: {data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Response is not valid JSON: {response.text}")
                    self.log_result("Subscription Checkout Monthly - Invalid JSON", False, f"Non-JSON response: {response.text}")
                    
            elif response.status_code == 400:
                # Check if it's a configuration error (expected in test environment)
                try:
                    error_data = response.json()
                    print(f"   📊 Error response: {error_data}")
                    
                    if "error_id" in error_data:
                        print(f"   ✅ Error response includes error_id: {error_data['error_id']}")
                        
                        # Check for configuration-related error messages
                        error_message = error_data.get("message", "").lower()
                        if any(keyword in error_message for keyword in ["stripe", "api key", "configuration", "not configured"]):
                            print(f"   ✅ Helpful configuration error message: {error_data['message']}")
                            self.log_result("Subscription Checkout Monthly - Config Error", True, "Returns helpful configuration error with error_id")
                        else:
                            print(f"   ❌ Generic error message: {error_data['message']}")
                            self.log_result("Subscription Checkout Monthly - Error Message", False, f"Generic error: {error_data['message']}")
                    else:
                        print(f"   ❌ Error response missing error_id")
                        self.log_result("Subscription Checkout Monthly - Missing Error ID", False, f"Error response missing error_id: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Error response is not valid JSON: {response.text}")
                    self.log_result("Subscription Checkout Monthly - Invalid Error JSON", False, f"Non-JSON error response: {response.text}")
                    
            elif response.status_code == 422:
                # This would be validation errors - should not happen with valid data
                try:
                    error_data = response.json()
                    print(f"   ❌ Unexpected validation error: {error_data}")
                    self.log_result("Subscription Checkout Monthly - Unexpected Validation", False, f"Unexpected 422 with valid data: {error_data}")
                except:
                    self.log_result("Subscription Checkout Monthly - 422 Error", False, f"422 status with non-JSON response: {response.text}")
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                self.log_result("Subscription Checkout Monthly - Unexpected Status", False, f"Status {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Checkout Monthly", False, f"Exception: {str(e)}")

    def test_subscription_checkout_annual_plan(self):
        """Test POST /api/subscription/checkout with annual plan"""
        try:
            print("💳 SUBSCRIPTION CHECKOUT - ANNUAL PLAN")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Checkout Annual", False, "No authentication token available")
                return
            
            print("📊 Step 1: Test annual plan checkout with valid data")
            
            checkout_data = {
                "plan": "annual",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Checkout response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response data keys: {list(data.keys())}")
                    
                    # Check for expected response format: { url: "stripe_checkout_url" }
                    if "url" in data:
                        checkout_url = data["url"]
                        print(f"   ✅ Checkout URL returned: {checkout_url[:100]}...")
                        
                        # Verify it's a Stripe checkout URL
                        if "stripe.com" in checkout_url or "checkout.stripe.com" in checkout_url:
                            print(f"   ✅ Valid Stripe checkout URL format")
                            self.log_result("Subscription Checkout Annual - Valid Response", True, "Annual checkout returns valid Stripe URL")
                        else:
                            print(f"   ⚠️  URL doesn't appear to be Stripe checkout URL")
                            self.log_result("Subscription Checkout Annual - URL Format", False, f"URL doesn't appear to be Stripe: {checkout_url}")
                    else:
                        print(f"   ❌ Missing 'url' field in response")
                        self.log_result("Subscription Checkout Annual - Missing URL", False, f"Response missing 'url' field: {data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Response is not valid JSON: {response.text}")
                    self.log_result("Subscription Checkout Annual - Invalid JSON", False, f"Non-JSON response: {response.text}")
                    
            elif response.status_code == 400:
                # Check if it's a configuration error (expected in test environment)
                try:
                    error_data = response.json()
                    print(f"   📊 Error response: {error_data}")
                    
                    if "error_id" in error_data:
                        print(f"   ✅ Error response includes error_id: {error_data['error_id']}")
                        
                        # Check for configuration-related error messages
                        error_message = error_data.get("message", "").lower()
                        if any(keyword in error_message for keyword in ["stripe", "api key", "configuration", "not configured"]):
                            print(f"   ✅ Helpful configuration error message: {error_data['message']}")
                            self.log_result("Subscription Checkout Annual - Config Error", True, "Returns helpful configuration error with error_id")
                        else:
                            print(f"   ❌ Generic error message: {error_data['message']}")
                            self.log_result("Subscription Checkout Annual - Error Message", False, f"Generic error: {error_data['message']}")
                    else:
                        print(f"   ❌ Error response missing error_id")
                        self.log_result("Subscription Checkout Annual - Missing Error ID", False, f"Error response missing error_id: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Error response is not valid JSON: {response.text}")
                    self.log_result("Subscription Checkout Annual - Invalid Error JSON", False, f"Non-JSON error response: {response.text}")
                    
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                self.log_result("Subscription Checkout Annual - Unexpected Status", False, f"Status {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Checkout Annual", False, f"Exception: {str(e)}")

    def test_subscription_checkout_validation_errors(self):
        """Test validation errors for subscription checkout"""
        try:
            print("🔍 SUBSCRIPTION CHECKOUT - VALIDATION ERRORS")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Subscription Checkout Validation", False, "No authentication token available")
                return
            
            # Test 1: Missing plan
            print("📊 Test 1: Missing plan field")
            
            missing_plan_data = {
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", missing_plan_data)
            
            print(f"   📊 Missing plan response status: {response.status_code}")
            
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    print(f"   ✅ Proper 422 validation error for missing plan")
                    
                    if "error_id" in error_data:
                        print(f"   ✅ Error includes error_id: {error_data['error_id']}")
                        self.log_result("Validation - Missing Plan", True, "Returns 422 with error_id for missing plan")
                    else:
                        print(f"   ❌ Missing error_id in validation response")
                        self.log_result("Validation - Missing Plan Error ID", False, f"422 response missing error_id: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ 422 response is not valid JSON: {response.text}")
                    self.log_result("Validation - Missing Plan JSON", False, f"Non-JSON 422 response: {response.text}")
            else:
                print(f"   ❌ Expected 422, got {response.status_code}")
                self.log_result("Validation - Missing Plan Status", False, f"Expected 422, got {response.status_code}: {response.text}")
            
            # Test 2: Invalid plan
            print("📊 Test 2: Invalid plan value")
            
            invalid_plan_data = {
                "plan": "invalid_plan",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", invalid_plan_data)
            
            print(f"   📊 Invalid plan response status: {response.status_code}")
            
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    print(f"   ✅ Proper 422 validation error for invalid plan")
                    
                    if "error_id" in error_data:
                        print(f"   ✅ Error includes error_id: {error_data['error_id']}")
                        self.log_result("Validation - Invalid Plan", True, "Returns 422 with error_id for invalid plan")
                    else:
                        print(f"   ❌ Missing error_id in validation response")
                        self.log_result("Validation - Invalid Plan Error ID", False, f"422 response missing error_id: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ 422 response is not valid JSON: {response.text}")
                    self.log_result("Validation - Invalid Plan JSON", False, f"Non-JSON 422 response: {response.text}")
            else:
                print(f"   ❌ Expected 422, got {response.status_code}")
                self.log_result("Validation - Invalid Plan Status", False, f"Expected 422, got {response.status_code}: {response.text}")
            
            # Test 3: Missing success_url
            print("📊 Test 3: Missing success_url")
            
            missing_success_url_data = {
                "plan": "monthly",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", missing_success_url_data)
            
            print(f"   📊 Missing success_url response status: {response.status_code}")
            
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    print(f"   ✅ Proper 422 validation error for missing success_url")
                    
                    if "error_id" in error_data:
                        print(f"   ✅ Error includes error_id: {error_data['error_id']}")
                        self.log_result("Validation - Missing Success URL", True, "Returns 422 with error_id for missing success_url")
                    else:
                        print(f"   ❌ Missing error_id in validation response")
                        self.log_result("Validation - Missing Success URL Error ID", False, f"422 response missing error_id: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ 422 response is not valid JSON: {response.text}")
                    self.log_result("Validation - Missing Success URL JSON", False, f"Non-JSON 422 response: {response.text}")
            else:
                print(f"   ❌ Expected 422, got {response.status_code}")
                self.log_result("Validation - Missing Success URL Status", False, f"Expected 422, got {response.status_code}: {response.text}")
            
            # Test 4: Missing cancel_url
            print("📊 Test 4: Missing cancel_url")
            
            missing_cancel_url_data = {
                "plan": "monthly",
                "success_url": "https://example.com/success"
            }
            
            response = self.make_request("POST", "/subscription/checkout", missing_cancel_url_data)
            
            print(f"   📊 Missing cancel_url response status: {response.status_code}")
            
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    print(f"   ✅ Proper 422 validation error for missing cancel_url")
                    
                    if "error_id" in error_data:
                        print(f"   ✅ Error includes error_id: {error_data['error_id']}")
                        self.log_result("Validation - Missing Cancel URL", True, "Returns 422 with error_id for missing cancel_url")
                    else:
                        print(f"   ❌ Missing error_id in validation response")
                        self.log_result("Validation - Missing Cancel URL Error ID", False, f"422 response missing error_id: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ 422 response is not valid JSON: {response.text}")
                    self.log_result("Validation - Missing Cancel URL JSON", False, f"Non-JSON 422 response: {response.text}")
            else:
                print(f"   ❌ Expected 422, got {response.status_code}")
                self.log_result("Validation - Missing Cancel URL Status", False, f"Expected 422, got {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Subscription Checkout Validation", False, f"Exception: {str(e)}")

    def test_webhook_endpoint(self):
        """Test POST /api/stripe/webhook endpoint"""
        try:
            print("🔗 STRIPE WEBHOOK ENDPOINT")
            print("=" * 80)
            
            print("📊 Step 1: Test webhook endpoint accessibility")
            
            # Test webhook endpoint without signature (should fail with proper error)
            webhook_data = {
                "id": "evt_test_webhook",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_test_session",
                        "object": "checkout.session"
                    }
                }
            }
            
            # Don't include auth token for webhook - webhooks are authenticated via Stripe signature
            original_token = self.auth_token
            self.auth_token = None
            
            response = self.make_request("POST", "/stripe/webhook", webhook_data)
            
            print(f"   📊 Webhook response status: {response.status_code}")
            print(f"   📊 Webhook response: {response.text[:200]}...")
            
            # Restore auth token
            self.auth_token = original_token
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", "").lower()
                    
                    if "signature" in error_message or "missing signature" in error_message:
                        print(f"   ✅ Webhook properly validates signatures: {error_data.get('message', '')}")
                        self.log_result("Webhook Endpoint - Signature Validation", True, "Webhook properly requires Stripe signature")
                    else:
                        print(f"   ⚠️  Webhook error but not signature-related: {error_data}")
                        self.log_result("Webhook Endpoint - Error Type", False, f"Unexpected webhook error: {error_data}")
                        
                except json.JSONDecodeError:
                    if "missing signature" in response.text.lower() or "signature" in response.text.lower():
                        print(f"   ✅ Webhook properly validates signatures (text response)")
                        self.log_result("Webhook Endpoint - Signature Validation Text", True, "Webhook requires signature (text response)")
                    else:
                        print(f"   ❌ Webhook error response not JSON: {response.text}")
                        self.log_result("Webhook Endpoint - Non-JSON Error", False, f"Non-JSON webhook error: {response.text}")
                        
            elif response.status_code == 422:
                # This might indicate routing issues (webhook being routed to wrong endpoint)
                try:
                    error_data = response.json()
                    print(f"   ❌ Webhook returns 422 validation error - possible routing issue: {error_data}")
                    self.log_result("Webhook Endpoint - Routing Issue", False, f"Webhook returns 422 - possible routing conflict: {error_data}")
                except:
                    print(f"   ❌ Webhook returns 422 - possible routing issue: {response.text}")
                    self.log_result("Webhook Endpoint - Routing Issue Text", False, f"Webhook returns 422: {response.text}")
                    
            elif response.status_code == 200:
                print(f"   ⚠️  Webhook accepts unsigned request - security concern")
                self.log_result("Webhook Endpoint - Security Issue", False, "Webhook accepts unsigned requests")
                
            else:
                print(f"   ❌ Unexpected webhook response: {response.status_code}")
                self.log_result("Webhook Endpoint - Unexpected Response", False, f"Unexpected status {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Webhook Endpoint", False, f"Exception: {str(e)}")

    def test_environment_configuration_checks(self):
        """Test environment configuration validation"""
        try:
            print("⚙️  ENVIRONMENT CONFIGURATION CHECKS")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Environment Configuration", False, "No authentication token available")
                return
            
            print("📊 Step 1: Test checkout with likely placeholder configuration")
            
            # Try a checkout request to see what configuration errors we get
            checkout_data = {
                "plan": "monthly",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", checkout_data)
            
            print(f"   📊 Configuration test response status: {response.status_code}")
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", "")
                    
                    print(f"   📊 Configuration error message: {error_message}")
                    
                    # Check for helpful configuration error messages
                    helpful_keywords = [
                        "stripe api key",
                        "not configured",
                        "configuration",
                        "environment",
                        "setup",
                        "contact support",
                        "placeholder"
                    ]
                    
                    if any(keyword in error_message.lower() for keyword in helpful_keywords):
                        print(f"   ✅ Helpful configuration error message provided")
                        self.log_result("Environment Configuration - Helpful Errors", True, "Provides helpful configuration error messages")
                    else:
                        print(f"   ❌ Generic or unhelpful error message")
                        self.log_result("Environment Configuration - Error Quality", False, f"Unhelpful error message: {error_message}")
                    
                    # Check for error_id in configuration errors
                    if "error_id" in error_data:
                        print(f"   ✅ Configuration error includes error_id for tracking: {error_data['error_id']}")
                        self.log_result("Environment Configuration - Error ID", True, "Configuration errors include error_id")
                    else:
                        print(f"   ❌ Configuration error missing error_id")
                        self.log_result("Environment Configuration - Missing Error ID", False, "Configuration errors missing error_id")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Configuration error response not JSON: {response.text}")
                    self.log_result("Environment Configuration - Non-JSON Error", False, f"Non-JSON configuration error: {response.text}")
                    
            elif response.status_code == 200:
                print(f"   ⚠️  Checkout succeeded - configuration might be working")
                try:
                    data = response.json()
                    if "url" in data:
                        print(f"   ✅ Configuration appears to be working - got checkout URL")
                        self.log_result("Environment Configuration - Working", True, "Stripe configuration appears to be working")
                    else:
                        print(f"   ❌ Success response but missing URL")
                        self.log_result("Environment Configuration - Invalid Success", False, f"Success response missing URL: {data}")
                except:
                    print(f"   ❌ Success response not JSON: {response.text}")
                    self.log_result("Environment Configuration - Invalid Success JSON", False, f"Non-JSON success: {response.text}")
                    
            else:
                print(f"   ❌ Unexpected configuration test response: {response.status_code}")
                self.log_result("Environment Configuration - Unexpected Response", False, f"Unexpected status {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Environment Configuration", False, f"Exception: {str(e)}")

    def test_structured_logging_and_error_ids(self):
        """Test that responses include structured logging elements like error_id"""
        try:
            print("📋 STRUCTURED LOGGING AND ERROR IDS")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Structured Logging", False, "No authentication token available")
                return
            
            print("📊 Step 1: Test that error responses include error_id for tracking")
            
            # Generate a request that should fail to test error_id generation
            invalid_data = {
                "plan": "invalid_plan_type",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.make_request("POST", "/subscription/checkout", invalid_data)
            
            print(f"   📊 Error response status: {response.status_code}")
            
            if response.status_code in [400, 422]:
                try:
                    error_data = response.json()
                    print(f"   📊 Error response structure: {list(error_data.keys())}")
                    
                    # Check for error_id
                    if "error_id" in error_data:
                        error_id = error_data["error_id"]
                        print(f"   ✅ Error response includes error_id: {error_id}")
                        
                        # Verify error_id format (should be unique identifier)
                        if len(error_id) > 5 and error_id.replace('-', '').replace('_', '').isalnum():
                            print(f"   ✅ Error ID has valid format for tracking")
                            self.log_result("Structured Logging - Error ID Format", True, f"Error ID has valid format: {error_id}")
                        else:
                            print(f"   ❌ Error ID format seems invalid: {error_id}")
                            self.log_result("Structured Logging - Error ID Format", False, f"Invalid error ID format: {error_id}")
                    else:
                        print(f"   ❌ Error response missing error_id field")
                        self.log_result("Structured Logging - Missing Error ID", False, f"Error response missing error_id: {error_data}")
                    
                    # Check for descriptive error message
                    if "message" in error_data:
                        message = error_data["message"]
                        print(f"   ✅ Error includes descriptive message: {message[:100]}...")
                        self.log_result("Structured Logging - Error Message", True, "Error includes descriptive message")
                    else:
                        print(f"   ❌ Error response missing message field")
                        self.log_result("Structured Logging - Missing Message", False, f"Error response missing message: {error_data}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Error response is not valid JSON: {response.text}")
                    self.log_result("Structured Logging - Invalid JSON", False, f"Non-JSON error response: {response.text}")
                    
            else:
                print(f"   ⚠️  Expected error response, got {response.status_code}")
                # This might mean the validation is working differently than expected
                if response.status_code == 200:
                    print(f"   ⚠️  Request succeeded unexpectedly - might indicate different validation logic")
                    self.log_result("Structured Logging - Unexpected Success", False, "Expected validation error but got success")
                else:
                    print(f"   ❌ Unexpected status code: {response.status_code}")
                    self.log_result("Structured Logging - Unexpected Status", False, f"Unexpected status {response.status_code}: {response.text}")
            
            print("=" * 80)
            
        except Exception as e:
            self.log_result("Structured Logging", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all subscription checkout tests"""
        print("🚀 COMPREHENSIVE SUBSCRIPTION CHECKOUT TESTING")
        print("=" * 100)
        print(f"Testing against: {self.base_url}")
        print(f"Test credentials: {TEST_CREDENTIALS['email']}")
        print("=" * 100)
        
        # Run all tests in order
        self.test_authentication_setup()
        self.test_subscription_checkout_monthly_plan()
        self.test_subscription_checkout_annual_plan()
        self.test_subscription_checkout_validation_errors()
        self.test_webhook_endpoint()
        self.test_environment_configuration_checks()
        self.test_structured_logging_and_error_ids()
        
        # Print final results
        print("\n" + "=" * 100)
        print("🏁 FINAL TEST RESULTS")
        print("=" * 100)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ PASSED: {self.results['passed']}")
        print(f"❌ FAILED: {self.results['failed']}")
        print(f"📊 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print(f"\n❌ FAILED TESTS:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        print("=" * 100)
        
        return self.results

if __name__ == "__main__":
    tester = SubscriptionCheckoutTester()
    results = tester.run_all_tests()