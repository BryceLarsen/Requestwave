#!/usr/bin/env python3
"""
TRIAL PERIOD VERIFICATION TEST

This test creates a new user to verify the 14-day trial implementation
"""

import requests
import json
import uuid
import time

BASE_URL = "https://livewave-music.emergent.host/api"

def test_trial_period_verification():
    """Test that new users get 14-day trial (not 30 days)"""
    
    # Create a unique test user
    test_user = {
        "name": f"Trial Test User {uuid.uuid4().hex[:8]}",
        "email": f"trial.test.{uuid.uuid4().hex[:8]}@requestwave.com",
        "password": "TestPassword123!"
    }
    
    print(f"🧪 Creating new test user: {test_user['email']}")
    
    # Register new user
    register_response = requests.post(f"{BASE_URL}/auth/register", json=test_user)
    
    if register_response.status_code != 200:
        print(f"❌ Registration failed: {register_response.status_code}, {register_response.text}")
        return
    
    register_data = register_response.json()
    auth_token = register_data["token"]
    
    print(f"✅ New user registered: {register_data['musician']['name']}")
    
    # Test checkout with new user (should get 14-day trial)
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    checkout_data = {
        "plan": "monthly",
        "success_url": "https://test.com/success",
        "cancel_url": "https://test.com/cancel"
    }
    
    print("🧪 Testing checkout for new user (should get 14-day trial)...")
    
    checkout_response = requests.post(f"{BASE_URL}/subscription/checkout", json=checkout_data, headers=headers)
    
    print(f"📊 Checkout response: {checkout_response.status_code}")
    print(f"📊 Response: {checkout_response.text}")
    
    if checkout_response.status_code == 200:
        print("✅ Checkout successful - check backend logs for trial_period_days=14")
    else:
        print(f"❌ Checkout failed: {checkout_response.text}")
    
    # Check subscription status
    status_response = requests.get(f"{BASE_URL}/subscription/status", headers=headers)
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"📊 New user subscription status: {json.dumps(status_data, indent=2, default=str)}")
    
    print("\n🔍 Check backend logs for 'trial_period_days=14' entry")

if __name__ == "__main__":
    test_trial_period_verification()