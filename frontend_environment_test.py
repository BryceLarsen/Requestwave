#!/usr/bin/env python3
"""
Frontend Environment Detection Test
Testing the exact API URL that the frontend would use based on environment detection logic
"""

import requests
import json
import sys

# Test the environment detection logic from the frontend
def test_frontend_environment_detection():
    """Test what API URL the frontend would use"""
    print("🔍 Testing Frontend Environment Detection Logic")
    print("=" * 60)
    
    # From frontend/.env
    REACT_APP_BACKEND_URL = "https://requestwave-app.preview.emergentagent.com"
    
    # Simulate the frontend's environment detection logic
    # The frontend checks:
    # 1. window.location.hostname === 'requestwave.app' 
    # 2. window.location.hostname.includes('requestwave.emergent.host')
    # 3. process.env.NODE_ENV === 'production'
    
    # For preview environment (requestwave-app.preview.emergentagent.com):
    hostname = "requestwave-app.preview.emergentagent.com"
    
    # Check conditions
    is_production_domain = hostname == 'requestwave.app'
    includes_emergent_host = 'requestwave.emergent.host' in hostname
    
    print(f"Current hostname: {hostname}")
    print(f"Is production domain (requestwave.app): {is_production_domain}")
    print(f"Includes 'requestwave.emergent.host': {includes_emergent_host}")
    print(f"REACT_APP_BACKEND_URL: {REACT_APP_BACKEND_URL}")
    
    # Frontend logic: if (isProductionDeployment()) return 'https://requestwave.app/api'
    if is_production_domain or includes_emergent_host:
        api_url = 'https://requestwave.app/api'
        print(f"❌ ISSUE FOUND: Frontend would use PRODUCTION API: {api_url}")
        print("   This means frontend is calling the wrong backend!")
    else:
        api_url = f'{REACT_APP_BACKEND_URL}/api'
        print(f"✅ Frontend would use PREVIEW API: {api_url}")
    
    print("\n" + "=" * 60)
    print("🧪 Testing Both API URLs")
    print("=" * 60)
    
    # Test both URLs
    preview_api = f'{REACT_APP_BACKEND_URL}/api'
    production_api = 'https://requestwave.app/api'
    
    # Test preview API
    try:
        response = requests.get(f"{preview_api}/musicians/bryce-larsen", timeout=10)
        print(f"✅ Preview API ({preview_api}): {response.status_code}")
    except Exception as e:
        print(f"❌ Preview API ({preview_api}): ERROR - {str(e)}")
    
    # Test production API
    try:
        response = requests.get(f"{production_api}/musicians/bryce-larsen", timeout=10)
        print(f"✅ Production API ({production_api}): {response.status_code}")
    except Exception as e:
        print(f"❌ Production API ({production_api}): ERROR - {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS")
    print("=" * 60)
    
    if includes_emergent_host:
        print("❌ CRITICAL ISSUE IDENTIFIED:")
        print("   The frontend hostname 'requestwave-app.preview.emergentagent.com'")
        print("   contains 'requestwave.emergent.host', which triggers the production")
        print("   environment detection logic in the frontend.")
        print("")
        print("   This causes the frontend to use 'https://requestwave.app/api'")
        print("   instead of the correct preview backend URL.")
        print("")
        print("🔧 SOLUTION:")
        print("   The environment detection logic needs to be more specific")
        print("   to avoid false positives with preview URLs.")
        return False
    else:
        print("✅ Environment detection logic appears correct")
        return True

if __name__ == "__main__":
    success = test_frontend_environment_detection()
    sys.exit(0 if success else 1)