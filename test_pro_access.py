#!/usr/bin/env python3
"""
Test to understand why check_pro_access is allowing access when it shouldn't
"""

import requests
import json

BASE_URL = "https://musician-dashboard.preview.emergentagent.com/api"
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def make_request(method: str, endpoint: str, data=None, auth_token=None):
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    if method.upper() == "GET":
        response = requests.get(url, headers=headers, params=data)
    elif method.upper() == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return response

def main():
    print("🔍 TESTING PRO ACCESS BEHAVIOR")
    print("=" * 80)
    
    # Login
    print("📊 Step 1: Login with brycelarsenmusic@gmail.com")
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
    musician_data = login_data_response["musician"]
    
    print(f"   ✅ Successfully logged in")
    
    # Test different endpoints that should require Pro access
    print("\n📊 Step 2: Test endpoints that use require_pro_access")
    
    endpoints_to_test = [
        ("GET", "/playlists", "Get playlists"),
        ("POST", "/playlists", "Create playlist", {"name": "Test", "song_ids": []}),
    ]
    
    for method, endpoint, description, *data in endpoints_to_test:
        print(f"\n   🔍 Testing: {description}")
        print(f"      Method: {method} {endpoint}")
        
        request_data = data[0] if data else None
        response = make_request(method, endpoint, request_data, auth_token)
        
        print(f"      Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"      ✅ SUCCESS - Pro access granted")
            if method == "POST" and "playlists" in endpoint:
                # Clean up created playlist
                try:
                    created = response.json()
                    if "id" in created:
                        delete_response = requests.delete(f"{BASE_URL}/playlists/{created['id']}", 
                                                        headers={"Authorization": f"Bearer {auth_token}"})
                        print(f"      🧹 Cleaned up test playlist")
                except:
                    pass
        elif response.status_code == 403:
            print(f"      ❌ DENIED - Pro access blocked")
            print(f"      Response: {response.text}")
        else:
            print(f"      ⚠️  UNEXPECTED - Status {response.status_code}")
            print(f"      Response: {response.text[:200]}...")
    
    # Test a non-Pro endpoint for comparison
    print(f"\n   🔍 Testing: Non-Pro endpoint for comparison")
    print(f"      Method: GET /songs")
    
    songs_response = make_request("GET", "/songs", auth_token=auth_token)
    print(f"      Status: {songs_response.status_code}")
    
    if songs_response.status_code == 200:
        songs = songs_response.json()
        print(f"      ✅ SUCCESS - Found {len(songs)} songs")
    else:
        print(f"      ❌ FAILED - Status {songs_response.status_code}")
    
    print("\n" + "=" * 80)
    print("🔍 ANALYSIS:")
    print("If playlist endpoints return 200, then check_pro_access() is returning True")
    print("This means either:")
    print("1. The legacy subscription logic is different than I simulated")
    print("2. There's a bug in check_pro_access()")
    print("3. The endpoints aren't actually using require_pro_access()")
    print("4. There's some other access mechanism at play")
    print("=" * 80)

if __name__ == "__main__":
    main()