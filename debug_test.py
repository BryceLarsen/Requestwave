#!/usr/bin/env python3
"""
Debug test for On Stage functionality issues
"""

import requests
import json

BASE_URL = "https://livewave-music.emergent.host/api"
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def make_request(method, endpoint, data=None, headers=None):
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    
    # Default headers
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=request_headers, params=data)
        elif method.upper() == "POST":
            response = requests.post(url, headers=request_headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=request_headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except Exception as e:
        print(f"Request failed: {e}")
        raise

def main():
    print("🔍 DEBUG: On Stage Functionality Issues")
    print("=" * 60)
    
    # Step 1: Login
    print("📊 Step 1: Login with brycelarsenmusic@gmail.com")
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    login_response = make_request("POST", "/auth/login", login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return
    
    login_result = login_response.json()
    auth_token = login_result["token"]
    musician_id = login_result["musician"]["id"]
    musician_slug = login_result["musician"]["slug"]
    
    print(f"   ✅ Successfully logged in as: {login_result['musician']['name']}")
    print(f"   ✅ Musician ID: {musician_id}")
    print(f"   ✅ Auth token: {auth_token[:20]}...")
    
    # Step 2: Test polling endpoint
    print("📊 Step 2: Test polling endpoint")
    
    auth_headers = {"Authorization": f"Bearer {auth_token}"}
    
    polling_response = make_request("GET", f"/requests/updates/{musician_id}", headers=auth_headers)
    
    print(f"   📊 Polling response status: {polling_response.status_code}")
    if polling_response.status_code == 200:
        polling_data = polling_response.json()
        print(f"   📊 Polling response keys: {list(polling_data.keys())}")
        print(f"   📊 Full response: {json.dumps(polling_data, indent=2)}")
    else:
        print(f"   ❌ Polling response: {polling_response.text}")
    
    # Step 3: Test status update endpoint with a real request
    print("📊 Step 3: Get existing requests")
    
    requests_response = make_request("GET", "/requests", headers=auth_headers)
    
    if requests_response.status_code == 200:
        requests_data = requests_response.json()
        print(f"   📊 Found {len(requests_data)} requests")
        
        if len(requests_data) > 0:
            test_request = requests_data[0]
            test_request_id = test_request["id"]
            current_status = test_request["status"]
            
            print(f"   📊 Testing with request ID: {test_request_id}")
            print(f"   📊 Current status: {current_status}")
            
            # Try to update status
            new_status = "accepted" if current_status == "pending" else "pending"
            status_update_data = {"status": new_status}
            
            print(f"   📊 Updating status to: {new_status}")
            
            status_response = make_request("PUT", f"/requests/{test_request_id}/status", status_update_data, headers=auth_headers)
            
            print(f"   📊 Status update response: {status_response.status_code}")
            if status_response.status_code == 200:
                status_result = status_response.json()
                print(f"   ✅ Status update successful: {json.dumps(status_result, indent=2)}")
            else:
                print(f"   ❌ Status update failed: {status_response.text}")
        else:
            print("   ℹ️  No existing requests to test with")
    else:
        print(f"   ❌ Failed to get requests: {requests_response.status_code}")
        print(f"   Response: {requests_response.text}")

if __name__ == "__main__":
    main()