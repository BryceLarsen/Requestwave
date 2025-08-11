#!/usr/bin/env python3
"""
Debug script to test the subscription status endpoint directly
"""

import requests
import json

# Configuration
BASE_URL = "https://livewave-music.emergent.host/api"
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def login():
    """Login and get token"""
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        data = response.json()
        return data["token"]
    else:
        print(f"Login failed: {response.status_code}, {response.text}")
        return None

def test_subscription_status(token):
    """Test the subscription status endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("Testing GET /api/subscription/status...")
    response = requests.get(f"{BASE_URL}/subscription/status", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"JSON Response: {json.dumps(data, indent=2, default=str)}")
            
            # Check which model this looks like
            if "audience_link_active" in data and "trial_active" in data:
                print("✅ This is the NEW freemium SubscriptionStatus model")
            elif "requests_used" in data and "requests_limit" in data:
                print("❌ This is the OLD LegacySubscriptionStatus model")
            else:
                print("⚠️  Unknown model format")
                
        except json.JSONDecodeError:
            print("❌ Response is not valid JSON")

if __name__ == "__main__":
    token = login()
    if token:
        test_subscription_status(token)
    else:
        print("Cannot test - login failed")