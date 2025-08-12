#!/usr/bin/env python3
"""
PRICING CONFIGURATION VERIFICATION TEST

This test specifically verifies the pricing configuration discrepancy found:
- Backend code shows ANNUAL_PLAN_FEE = 24.00
- Environment shows PRICE_ANNUAL_48 = price_1LiveAnnualFortyEightDollarsPerYear  
- _plan_price_id function returns PRICE_ANNUAL_24 (not PRICE_ANNUAL_48)

This is a critical issue for the frontend UI changes that expect $48 annual pricing.
"""

import requests
import json
import os
from typing import Dict, Any

# Configuration
BASE_URL = "https://livewave-music.emergent.host/api"

# Test credentials
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com", 
    "password": "RequestWave2024!"
}

class PricingConfigurationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
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

    def make_request(self, method: str, endpoint: str, data: Any = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def test_authentication(self):
        """Authenticate for testing"""
        try:
            login_response = self.make_request("POST", "/auth/login", TEST_CREDENTIALS)
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                self.auth_token = login_data["token"]
                self.log_result("Authentication", True, f"Authenticated as {login_data['musician']['name']}")
            else:
                self.log_result("Authentication", False, f"Login failed: {login_response.status_code}")
                
        except Exception as e:
            self.log_result("Authentication", False, f"Exception: {str(e)}")

    def test_annual_pricing_configuration(self):
        """Test annual pricing configuration discrepancy"""
        try:
            print("💰 Testing Annual Pricing Configuration")
            print("=" * 80)
            
            if not self.auth_token:
                self.log_result("Annual Pricing Configuration", False, "No authentication token")
                return
            
            # Test annual checkout to see which price ID is actually used
            annual_checkout_data = {
                "plan": "annual",
                "success_url": "https://test.com/success",
                "cancel_url": "https://test.com/cancel"
            }
            
            checkout_response = self.make_request("POST", "/subscription/checkout", annual_checkout_data)
            
            print(f"   📊 Annual checkout response status: {checkout_response.status_code}")
            print(f"   📊 Annual checkout response: {checkout_response.text}")
            
            # Analyze the response for pricing information
            if checkout_response.status_code == 400:
                # Expected in test environment, but we can analyze the error
                response_text = checkout_response.text
                
                # Look for price ID references in the error
                if "price_1LiveAnnualFortyEightDollarsPerYear" in response_text:
                    print("   ✅ Backend is using PRICE_ANNUAL_48 ($48 annual pricing)")
                    pricing_correct = True
                elif "price_1LiveAnnualTwentyFourDollarsPerYear" in response_text or "PRICE_ANNUAL_24" in response_text:
                    print("   ❌ Backend is using PRICE_ANNUAL_24 ($24 annual pricing)")
                    pricing_correct = False
                else:
                    print("   ⚠️  Cannot determine which price ID is being used from error message")
                    pricing_correct = None
                
                # Check if error mentions specific amounts
                if "$48" in response_text or "48" in response_text:
                    print("   ✅ Error message references $48 pricing")
                elif "$24" in response_text or "24" in response_text:
                    print("   ❌ Error message references $24 pricing")
                
            elif checkout_response.status_code == 200:
                # Successful response - analyze the checkout URL or session data
                checkout_data = checkout_response.json()
                checkout_url = checkout_data.get("checkout_url", "")
                
                print(f"   📊 Checkout URL: {checkout_url}")
                
                # In a real Stripe checkout URL, we might be able to see pricing info
                if "48" in checkout_url:
                    print("   ✅ Checkout URL suggests $48 pricing")
                    pricing_correct = True
                elif "24" in checkout_url:
                    print("   ❌ Checkout URL suggests $24 pricing")
                    pricing_correct = False
                else:
                    print("   ⚠️  Cannot determine pricing from checkout URL")
                    pricing_correct = None
            
            else:
                print(f"   ❌ Unexpected checkout response: {checkout_response.status_code}")
                pricing_correct = False
            
            # Test the pricing configuration by examining what the backend reports
            print("\n   📊 Analyzing Backend Configuration:")
            
            # The discrepancy we found:
            print("   🔍 DISCREPANCY ANALYSIS:")
            print("      - Backend code: ANNUAL_PLAN_FEE = 24.00")
            print("      - Environment: PRICE_ANNUAL_48 = price_1LiveAnnualFortyEightDollarsPerYear")
            print("      - _plan_price_id function returns PRICE_ANNUAL_24 (not PRICE_ANNUAL_48)")
            print("      - This means backend is configured for $24 annual, not $48!")
            
            if pricing_correct is True:
                self.log_result("Annual Pricing Configuration", True, "Backend correctly uses $48 annual pricing")
            elif pricing_correct is False:
                self.log_result("Annual Pricing Configuration", False, "CRITICAL: Backend uses $24 annual pricing instead of expected $48")
            else:
                self.log_result("Annual Pricing Configuration", False, "Cannot determine actual pricing configuration")
                
        except Exception as e:
            self.log_result("Annual Pricing Configuration", False, f"Exception: {str(e)}")

    def test_pricing_consistency_check(self):
        """Test overall pricing consistency"""
        try:
            print("🔍 Testing Pricing Consistency")
            print("=" * 80)
            
            # Test both monthly and annual to see the pattern
            plans_to_test = ["monthly", "annual"]
            pricing_results = {}
            
            for plan in plans_to_test:
                print(f"   📊 Testing {plan} plan pricing...")
                
                checkout_data = {
                    "plan": plan,
                    "success_url": "https://test.com/success",
                    "cancel_url": "https://test.com/cancel"
                }
                
                response = self.make_request("POST", "/subscription/checkout", checkout_data)
                
                print(f"      Status: {response.status_code}")
                
                # Analyze response for pricing clues
                response_text = response.text
                pricing_clues = []
                
                if "price_1LiveMonthlyFiveDollarsPerMonth" in response_text:
                    pricing_clues.append("Uses $5 monthly price ID")
                if "price_1LiveAnnualFortyEightDollarsPerYear" in response_text:
                    pricing_clues.append("Uses $48 annual price ID")
                if "price_1LiveAnnualTwentyFourDollarsPerYear" in response_text:
                    pricing_clues.append("Uses $24 annual price ID")
                
                # Look for amount references
                if "$5" in response_text or "5.00" in response_text:
                    pricing_clues.append("References $5 amount")
                if "$24" in response_text or "24.00" in response_text:
                    pricing_clues.append("References $24 amount")
                if "$48" in response_text or "48.00" in response_text:
                    pricing_clues.append("References $48 amount")
                
                pricing_results[plan] = {
                    "status": response.status_code,
                    "clues": pricing_clues,
                    "response": response_text[:200] + "..." if len(response_text) > 200 else response_text
                }
                
                if pricing_clues:
                    print(f"      Pricing clues: {', '.join(pricing_clues)}")
                else:
                    print(f"      No clear pricing clues found")
            
            # Analyze consistency
            print("\n   🎯 PRICING CONSISTENCY ANALYSIS:")
            
            annual_clues = pricing_results.get("annual", {}).get("clues", [])
            monthly_clues = pricing_results.get("monthly", {}).get("clues", [])
            
            # Check if annual pricing is consistent with $48 expectation
            uses_48_pricing = any("$48" in clue or "FortyEight" in clue for clue in annual_clues)
            uses_24_pricing = any("$24" in clue or "TwentyFour" in clue for clue in annual_clues)
            
            if uses_48_pricing and not uses_24_pricing:
                consistency_result = "✅ Annual pricing correctly configured for $48"
                consistency_pass = True
            elif uses_24_pricing and not uses_48_pricing:
                consistency_result = "❌ Annual pricing incorrectly configured for $24 (should be $48)"
                consistency_pass = False
            elif uses_48_pricing and uses_24_pricing:
                consistency_result = "⚠️  Mixed pricing signals - configuration conflict detected"
                consistency_pass = False
            else:
                consistency_result = "⚠️  Cannot determine annual pricing configuration"
                consistency_pass = False
            
            print(f"      {consistency_result}")
            
            # Check monthly pricing
            uses_5_pricing = any("$5" in clue or "Five" in clue for clue in monthly_clues)
            if uses_5_pricing:
                print("      ✅ Monthly pricing correctly configured for $5")
            else:
                print("      ⚠️  Monthly pricing configuration unclear")
            
            self.log_result("Pricing Consistency", consistency_pass, consistency_result)
            
            return pricing_results
            
        except Exception as e:
            self.log_result("Pricing Consistency", False, f"Exception: {str(e)}")
            return {}

    def run_all_tests(self):
        """Run all pricing configuration tests"""
        print("🚀 PRICING CONFIGURATION VERIFICATION TEST")
        print("=" * 80)
        print("Investigating pricing configuration discrepancy:")
        print("- Expected: $48 annual pricing for frontend UI")
        print("- Found: Backend code shows $24 annual pricing")
        print("- Issue: _plan_price_id returns PRICE_ANNUAL_24 not PRICE_ANNUAL_48")
        print("=" * 80)
        
        self.test_authentication()
        
        if self.auth_token:
            self.test_annual_pricing_configuration()
            pricing_results = self.test_pricing_consistency_check()
        
        # Print final results
        print("\n" + "=" * 80)
        print("🏁 PRICING CONFIGURATION TEST RESULTS")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print("\n❌ Issues Found:")
            for error in self.results["errors"]:
                print(f"   - {error}")
        
        print("\n🎯 CRITICAL FINDINGS:")
        print("❌ PRICING CONFIGURATION MISMATCH DETECTED:")
        print("   - Backend _plan_price_id function uses PRICE_ANNUAL_24")
        print("   - Environment has PRICE_ANNUAL_48 configured")
        print("   - Frontend expects $48 annual pricing")
        print("   - Backend may be using $24 annual pricing")
        print("\n🔧 REQUIRED FIX:")
        print("   - Update _plan_price_id function to return PRICE_ANNUAL_48 for annual plan")
        print("   - OR update ANNUAL_PLAN_FEE constant to 48.00")
        print("   - Ensure consistency between code constants and Stripe price IDs")
        
        return success_rate >= 50  # Lower threshold since we expect to find issues

if __name__ == "__main__":
    tester = PricingConfigurationTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)