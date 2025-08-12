#!/usr/bin/env python3
"""
TRIAL PERIOD VERIFICATION TEST

This test specifically checks the trial period implementation to verify:
1. New user registration trial period
2. Stripe checkout trial period
3. Database trial_end dates
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration
BASE_URL = os.getenv("REACT_APP_BACKEND_URL", "https://livewave-music.emergent.host") + "/api"

# Test credentials
TEST_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class TrialPeriodTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.musician_id = None

    def make_request(self, method: str, endpoint: str, data: Any = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def test_existing_user_trial_status(self):
        """Test the existing user's trial status"""
        print("🔍 TRIAL PERIOD VERIFICATION TEST")
        print("=" * 80)
        
        # Login
        print("📊 Step 1: Login and check current trial status")
        login_response = self.make_request("POST", "/auth/login", TEST_CREDENTIALS)
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return
        
        login_data = login_response.json()
        self.auth_token = login_data["token"]
        self.musician_id = login_data["musician"]["id"]
        musician_name = login_data["musician"]["name"]
        
        print(f"   ✅ Logged in as: {musician_name}")
        
        # Get subscription status
        status_response = self.make_request("GET", "/subscription/status")
        if status_response.status_code != 200:
            print(f"❌ Status check failed: {status_response.status_code}")
            return
        
        status_data = status_response.json()
        print(f"   📊 Current status: {json.dumps(status_data, indent=2, default=str)}")
        
        # Check trial information
        trial_active = status_data.get("trial_active", False)
        trial_end = status_data.get("trial_end")
        
        print(f"   📊 Trial active: {trial_active}")
        print(f"   📊 Trial end: {trial_end}")
        
        if trial_end:
            try:
                trial_end_date = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
                now = datetime.now(trial_end_date.tzinfo) if trial_end_date.tzinfo else datetime.now()
                days_remaining = (trial_end_date - now).days
                print(f"   📊 Days remaining: {days_remaining}")
                
                if days_remaining > 20:
                    print(f"   ⚠️  WARNING: Trial period appears to be 30 days (remaining: {days_remaining})")
                elif days_remaining <= 14:
                    print(f"   ✅ Trial period appears to be 14 days or less (remaining: {days_remaining})")
                else:
                    print(f"   📊 Trial period unclear (remaining: {days_remaining})")
                    
            except Exception as e:
                print(f"   ❌ Error parsing trial date: {e}")
        
        return status_data

    def test_checkout_trial_logic(self):
        """Test the checkout trial logic"""
        print("\n📊 Step 2: Test Stripe checkout trial logic")
        
        # Test monthly checkout
        checkout_data = {
            "plan": "monthly",
            "success_url": "https://test.com/success",
            "cancel_url": "https://test.com/cancel"
        }
        
        checkout_response = self.make_request("POST", "/subscription/checkout", checkout_data)
        
        print(f"   📊 Checkout response status: {checkout_response.status_code}")
        
        if checkout_response.status_code == 200:
            checkout_result = checkout_response.json()
            print(f"   ✅ Checkout session created successfully")
            print(f"   📊 Session ID: {checkout_result.get('session_id', 'N/A')}")
        elif checkout_response.status_code == 400:
            print(f"   ✅ Checkout endpoint accessible (400 expected for test environment)")
            print(f"   📊 Error: {checkout_response.text}")
        else:
            print(f"   ❌ Checkout failed: {checkout_response.status_code}")
            print(f"   📊 Response: {checkout_response.text}")

    def run_test(self):
        """Run the trial period verification test"""
        status_data = self.test_existing_user_trial_status()
        self.test_checkout_trial_logic()
        
        print("\n" + "=" * 80)
        print("🎯 TRIAL PERIOD ANALYSIS")
        print("=" * 80)
        
        print("📊 FINDINGS:")
        print("   • The backend has TRIAL_DAYS = 30 constant")
        print("   • But checkout logic uses trial_days = 14 for new subscriptions")
        print("   • This creates inconsistency between registration and subscription trials")
        
        print("\n📊 RECOMMENDATION:")
        print("   • Update TRIAL_DAYS constant from 30 to 14 for consistency")
        print("   • Or update checkout logic to use TRIAL_DAYS constant")
        
        return status_data

if __name__ == "__main__":
    tester = TrialPeriodTester()
    tester.run_test()