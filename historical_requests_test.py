#!/usr/bin/env python3
"""
Quick test for PRIORITY 4: Test Historical Requests
"""

import requests
import json

# Configuration
BASE_URL = "https://livewave-music.emergent.host/api"

# Pro account for testing
PRO_MUSICIAN = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

def test_historical_requests():
    print("🎯 PRIORITY 4: Test Historical Requests")
    print("=" * 80)
    
    # Login
    login_data = {
        "email": PRO_MUSICIAN["email"],
        "password": PRO_MUSICIAN["password"]
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    login_result = login_response.json()
    auth_token = login_result["token"]
    musician_id = login_result["musician"]["id"]
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    print(f"✅ Logged in as: {login_result['musician']['name']}")
    print(f"✅ Musician ID: {musician_id}")
    
    # Get all requests from main dashboard
    print("📊 Step 1: Get all requests from main dashboard")
    
    dashboard_response = requests.get(f"{BASE_URL}/requests/musician/{musician_id}", headers=headers)
    
    if dashboard_response.status_code != 200:
        print(f"❌ Failed to get dashboard requests: {dashboard_response.status_code}")
        return
    
    dashboard_requests = dashboard_response.json()
    print(f"   📊 Total requests in dashboard: {len(dashboard_requests)}")
    
    # Get requests from polling endpoint
    print("📊 Step 2: Get requests from polling endpoint")
    
    polling_response = requests.get(f"{BASE_URL}/requests/updates/{musician_id}", headers=headers)
    
    if polling_response.status_code != 200:
        print(f"❌ Failed to get polling requests: {polling_response.status_code}")
        return
    
    polling_data = polling_response.json()
    polling_requests = polling_data.get("requests", [])
    print(f"   📊 Total requests in polling: {len(polling_requests)}")
    
    # Compare dashboard vs polling requests
    print("📊 Step 3: Compare dashboard vs polling requests")
    
    # Filter dashboard requests to only active ones (should match polling)
    active_dashboard_requests = [req for req in dashboard_requests if req.get("status") not in ["archived"]]
    print(f"   📊 Active requests in dashboard: {len(active_dashboard_requests)}")
    
    # Create sets of request IDs for comparison
    dashboard_ids = set(req.get("id") for req in active_dashboard_requests)
    polling_ids = set(req.get("id") for req in polling_requests)
    
    # Find requests that are in dashboard but not in polling
    missing_from_polling = dashboard_ids - polling_ids
    # Find requests that are in polling but not in dashboard
    extra_in_polling = polling_ids - dashboard_ids
    
    print(f"   📊 Requests in dashboard but missing from polling: {len(missing_from_polling)}")
    print(f"   📊 Requests in polling but not in dashboard: {len(extra_in_polling)}")
    
    # Check for real requests (non-test requests)
    print("📊 Step 4: Identify real vs test requests")
    
    real_requests = []
    test_requests = []
    
    for req in polling_requests:
        requester_email = req.get("requester_email", "")
        requester_name = req.get("requester_name", "")
        
        # Identify test requests by email patterns or names
        is_test_request = (
            "test" in requester_email.lower() or
            "test" in requester_name.lower() or
            "debug" in requester_email.lower() or
            "debug" in requester_name.lower() or
            "@requestwave.com" in requester_email.lower()
        )
        
        if is_test_request:
            test_requests.append(req)
        else:
            real_requests.append(req)
    
    print(f"   📊 Real requests (non-test): {len(real_requests)}")
    print(f"   📊 Test requests: {len(test_requests)}")
    
    if len(real_requests) > 0:
        print("   ✅ Real requests found in polling:")
        for req in real_requests[:5]:  # Show first 5 real requests
            print(f"      {req.get('requester_name')} - {req.get('song_title')} ({req.get('status')})")
    else:
        print("   ℹ️  No real requests found (only test requests)")
    
    # Final assessment
    data_consistency = len(missing_from_polling) == 0
    has_real_requests = len(real_requests) > 0
    
    if data_consistency and has_real_requests:
        print(f"✅ PRIORITY 4 COMPLETE: Historical requests working correctly - {len(real_requests)} real requests appear in polling with proper data consistency")
        return True
    elif data_consistency:
        print(f"✅ PRIORITY 4 WORKING: Historical request data consistency working (no real requests to verify)")
        return True
    else:
        print(f"❌ CRITICAL: Data consistency issues - {len(missing_from_polling)} requests missing from polling endpoint")
        return False

if __name__ == "__main__":
    success = test_historical_requests()
    if success:
        print("\n🎉 PRIORITY 4 PASSED!")
    else:
        print("\n🚨 PRIORITY 4 FAILED!")