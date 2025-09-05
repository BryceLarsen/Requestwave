#!/usr/bin/env python3
"""
Browser Request Simulation Test
Simulating the exact browser request that would be made from the audience interface
to identify why users see "error creating request" despite backend working.
"""

import requests
import json
import sys
import time

# Configuration
PREVIEW_FRONTEND_URL = "https://requestwave-app.preview.emergentagent.com"
PREVIEW_BACKEND_URL = "https://requestwave-app.preview.emergentagent.com/api"
TEST_MUSICIAN_SLUG = "bryce-larsen"

def simulate_browser_request_flow():
    """Simulate the exact browser request flow"""
    print("🌐 Simulating Browser Request Flow")
    print(f"Frontend URL: {PREVIEW_FRONTEND_URL}")
    print(f"Backend API: {PREVIEW_BACKEND_URL}")
    print("=" * 80)
    
    # Step 1: Simulate user visiting the musician page
    print("\n📱 Step 1: User visits musician page")
    musician_page_url = f"{PREVIEW_FRONTEND_URL}/musician/{TEST_MUSICIAN_SLUG}"
    print(f"User visits: {musician_page_url}")
    
    # Step 2: Frontend loads musician data
    print("\n🎵 Step 2: Frontend loads musician data")
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": PREVIEW_FRONTEND_URL,
            "Referer": musician_page_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}", 
                              headers=headers, timeout=30)
        
        if response.status_code == 200:
            musician_data = response.json()
            print(f"✅ Musician data loaded: {musician_data['name']}")
            print(f"   Requests enabled: {musician_data.get('requests_enabled', 'Unknown')}")
            print(f"   Tips enabled: {musician_data.get('tips_enabled', 'Unknown')}")
        else:
            print(f"❌ Failed to load musician data: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading musician data: {str(e)}")
        return False
    
    # Step 3: Frontend loads songs
    print("\n🎶 Step 3: Frontend loads songs")
    try:
        response = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/songs", 
                              headers=headers, timeout=30)
        
        if response.status_code == 200:
            songs = response.json()
            print(f"✅ Songs loaded: {len(songs)} songs available")
            if songs:
                test_song = songs[0]
                print(f"   Test song: {test_song['title']} by {test_song['artist']}")
            else:
                print("❌ No songs available for testing")
                return False
        else:
            print(f"❌ Failed to load songs: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading songs: {str(e)}")
        return False
    
    # Step 4: User fills out request form and submits
    print("\n📝 Step 4: User submits request")
    
    # Simulate the exact request that the frontend would make
    request_payload = {
        "song_id": test_song["id"],
        "requester_name": "John Smith",
        "requester_email": "john.smith@example.com",
        "dedication": "This is my favorite song! Please play it!",
        "tip_amount": 0.0
    }
    
    # Headers that the browser would send
    request_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Origin": PREVIEW_FRONTEND_URL,
        "Referer": musician_page_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    print(f"   Request URL: {PREVIEW_BACKEND_URL}/requests")
    print(f"   Payload: {json.dumps(request_payload, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                               json=request_payload, 
                               headers=request_headers, 
                               timeout=30)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        print(f"   Response time: {response_time:.0f}ms")
        print(f"   Status code: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ Request created successfully!")
            print(f"   Request ID: {response_data.get('id')}")
            print(f"   Status: {response_data.get('status')}")
            print(f"   Song: {response_data.get('song_title')} by {response_data.get('song_artist')}")
            return True
        else:
            print(f"❌ Request creation failed!")
            print(f"   Error response: {response.text}")
            
            # Check if it's a specific error type
            try:
                error_data = response.json()
                if 'detail' in error_data:
                    print(f"   Error details: {error_data['detail']}")
            except:
                pass
            
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Request error: {str(e)}")
        return False

def test_cors_preflight():
    """Test CORS preflight request"""
    print("\n🔒 Testing CORS Preflight Request")
    print("=" * 50)
    
    try:
        headers = {
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
            "Origin": PREVIEW_FRONTEND_URL,
            "Referer": f"{PREVIEW_FRONTEND_URL}/musician/{TEST_MUSICIAN_SLUG}"
        }
        
        response = requests.options(f"{PREVIEW_BACKEND_URL}/requests", 
                                  headers=headers, timeout=10)
        
        print(f"Preflight status: {response.status_code}")
        print(f"CORS headers:")
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
        }
        
        for key, value in cors_headers.items():
            print(f"  {key}: {value}")
        
        # Check if CORS is properly configured
        allowed_origin = cors_headers.get("Access-Control-Allow-Origin")
        if allowed_origin == PREVIEW_FRONTEND_URL or allowed_origin == "*":
            print("✅ CORS appears to be configured correctly")
            return True
        else:
            print(f"❌ CORS issue: Origin {PREVIEW_FRONTEND_URL} not allowed")
            return False
            
    except Exception as e:
        print(f"❌ CORS preflight error: {str(e)}")
        return False

def test_different_request_scenarios():
    """Test different request scenarios that might cause issues"""
    print("\n🧪 Testing Different Request Scenarios")
    print("=" * 50)
    
    # Get a test song first
    try:
        response = requests.get(f"{PREVIEW_BACKEND_URL}/musicians/{TEST_MUSICIAN_SLUG}/songs", timeout=10)
        if response.status_code != 200 or not response.json():
            print("❌ Cannot get test song")
            return False
        test_song = response.json()[0]
    except Exception as e:
        print(f"❌ Error getting test song: {str(e)}")
        return False
    
    scenarios = [
        {
            "name": "Empty dedication",
            "payload": {
                "song_id": test_song["id"],
                "requester_name": "Test User",
                "requester_email": "test@example.com",
                "dedication": "",
                "tip_amount": 0.0
            }
        },
        {
            "name": "No tip_amount field",
            "payload": {
                "song_id": test_song["id"],
                "requester_name": "Test User",
                "requester_email": "test@example.com",
                "dedication": "Test request"
            }
        },
        {
            "name": "Long dedication",
            "payload": {
                "song_id": test_song["id"],
                "requester_name": "Test User",
                "requester_email": "test@example.com",
                "dedication": "This is a very long dedication message that might cause issues if there are character limits or validation problems. " * 5,
                "tip_amount": 0.0
            }
        },
        {
            "name": "Special characters in name",
            "payload": {
                "song_id": test_song["id"],
                "requester_name": "José María O'Connor-Smith",
                "requester_email": "jose.maria@example.com",
                "dedication": "¡Hola! This song is amazing 🎵",
                "tip_amount": 0.0
            }
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": PREVIEW_FRONTEND_URL
    }
    
    results = []
    for scenario in scenarios:
        try:
            response = requests.post(f"{PREVIEW_BACKEND_URL}/requests", 
                                   json=scenario["payload"], 
                                   headers=headers, 
                                   timeout=10)
            
            success = response.status_code == 200
            results.append({
                "scenario": scenario["name"],
                "success": success,
                "status_code": response.status_code,
                "response": response.text[:200] if not success else "Success"
            })
            
            status = "✅" if success else "❌"
            print(f"{status} {scenario['name']}: {response.status_code}")
            if not success:
                print(f"   Error: {response.text[:100]}...")
                
        except Exception as e:
            results.append({
                "scenario": scenario["name"],
                "success": False,
                "error": str(e)
            })
            print(f"❌ {scenario['name']}: ERROR - {str(e)}")
    
    success_count = len([r for r in results if r.get("success", False)])
    print(f"\nScenario Results: {success_count}/{len(scenarios)} successful")
    
    return success_count == len(scenarios)

def main():
    """Run all browser simulation tests"""
    print("🚀 Browser Request Simulation Test Suite")
    print("Testing why users see 'error creating request' despite backend working")
    print("=" * 80)
    
    # Run tests
    flow_success = simulate_browser_request_flow()
    cors_success = test_cors_preflight()
    scenarios_success = test_different_request_scenarios()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 BROWSER SIMULATION TEST SUMMARY")
    print("=" * 80)
    
    tests = [
        ("Browser Request Flow", flow_success),
        ("CORS Preflight", cors_success),
        ("Request Scenarios", scenarios_success)
    ]
    
    passed = len([t for t in tests if t[1]])
    total = len(tests)
    
    print(f"Tests Passed: {passed}/{total}")
    
    for test_name, success in tests:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Backend request creation is working correctly")
        print("   The issue may be in the frontend JavaScript error handling or")
        print("   in the user's specific browser environment.")
    else:
        print(f"\n❌ {total - passed} TESTS FAILED - Issues identified in request flow")
    
    print("\n🎯 BROWSER SIMULATION TEST COMPLETE")
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)