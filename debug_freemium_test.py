#!/usr/bin/env python3
"""
Debug specific freemium model issues
"""

import requests
import json

BASE_URL = "https://stagepro-app.preview.emergentagent.com/api"

# Login with existing user
login_data = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

print("🔍 Debugging Freemium Model Issues")
print("=" * 50)

# Step 1: Login
print("📊 Step 1: Login")
login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    login_data_response = login_response.json()
    auth_token = login_data_response["token"]
    musician_id = login_data_response["musician"]["id"]
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    print(f"✅ Logged in as: {login_data_response['musician']['name']}")
    
    # Step 2: Test subscription status endpoint
    print("📊 Step 2: Test subscription status endpoint")
    status_response = requests.get(f"{BASE_URL}/subscription/status", headers=headers)
    print(f"Status endpoint: {status_response.status_code}")
    print(f"Status response: {status_response.text}")
    
    # Step 3: Test checkout endpoint with different formats
    print("📊 Step 3: Test checkout endpoint formats")
    
    # Format 1: Direct JSON
    checkout_data_1 = {
        "package_id": "monthly_plan",
        "origin_url": "https://stagepro-app.preview.emergentagent.com"
    }
    
    checkout_response_1 = requests.post(f"{BASE_URL}/subscription/checkout", json=checkout_data_1, headers=headers)
    print(f"Checkout format 1 status: {checkout_response_1.status_code}")
    print(f"Checkout format 1 response: {checkout_response_1.text}")
    
    # Step 4: Check if there are routing conflicts by testing different endpoints
    print("📊 Step 4: Test endpoint routing")
    
    # Test the old subscription upgrade endpoint
    upgrade_data = {"plan": "monthly"}
    upgrade_response = requests.post(f"{BASE_URL}/subscription/upgrade", json=upgrade_data, headers=headers)
    print(f"Upgrade endpoint status: {upgrade_response.status_code}")
    print(f"Upgrade endpoint response: {upgrade_response.text}")
    
else:
    print(f"❌ Login failed: {login_response.status_code}")