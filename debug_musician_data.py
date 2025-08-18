#!/usr/bin/env python3
"""
DEBUG MUSICIAN DATA - Check actual musician record in database
"""

import requests
import json
from typing import Any

# Configuration
BASE_URL = "https://ff9606ce-1843-4dc8-a0da-da1fe6ced548.preview.emergentagent.com/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def make_request(method: str, endpoint: str, data: Any = None, auth_token: str = None):
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    
    # Default headers
    request_headers = {"Content-Type": "application/json"}
    if auth_token:
        request_headers["Authorization"] = f"Bearer {auth_token}"
    
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

def debug_musician_data():
    """Debug musician data to understand Pro access issue"""
    print("🔍 DEBUGGING MUSICIAN DATA")
    print("=" * 80)
    
    # Login first
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    login_response = make_request("POST", "/auth/login", login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    login_data_response = login_response.json()
    auth_token = login_data_response["token"]
    musician_id = login_data_response["musician"]["id"]
    
    print(f"✅ Logged in as: {login_data_response['musician']['name']}")
    print(f"📊 Musician ID: {musician_id}")
    
    # Get /me endpoint data
    me_response = make_request("GET", "/me", auth_token=auth_token)
    if me_response.status_code == 200:
        me_data = me_response.json()
        print(f"\n📊 /me endpoint data:")
        print(json.dumps(me_data, indent=2))
    else:
        print(f"❌ /me endpoint failed: {me_response.status_code}")
    
    # Get subscription status
    status_response = make_request("GET", "/subscription/status", auth_token=auth_token)
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"\n📊 Subscription status data:")
        print(json.dumps(status_data, indent=2))
    else:
        print(f"❌ Subscription status failed: {status_response.status_code}")
    
    # Try to access debug endpoint if it exists
    debug_response = make_request("GET", "/debug/musician", auth_token=auth_token)
    if debug_response.status_code == 200:
        debug_data = debug_response.json()
        print(f"\n📊 Debug musician data:")
        print(json.dumps(debug_data, indent=2))
    else:
        print(f"⚠️  Debug endpoint not accessible: {debug_response.status_code}")

if __name__ == "__main__":
    debug_musician_data()