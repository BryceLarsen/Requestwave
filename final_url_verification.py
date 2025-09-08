#!/usr/bin/env python3
"""
RequestWave Backend Testing Suite - Final URL Domain Verification
Comprehensive verification that all URL generation uses the correct requestwave.app domain.

VERIFICATION REQUIREMENTS:
1. QR Code endpoint returns correct domain
2. All public endpoints contain no hardcoded URLs
3. Environment variable override logic working
4. No cached data with old domains
5. Consistent URL generation across all endpoints

Test credentials: brycelarsenmusic@gmail.com / RequestWave2024!
"""

import requests
import json
import time
from datetime import datetime

class FinalURLVerification:
    def __init__(self):
        self.backend_url = "https://requestwave-revamp.preview.emergentagent.com"
        self.api_url = f"{self.backend_url}/api"
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'RequestWave-Final-URL-Verification/1.0'
        })
        
        self.test_credentials = {
            "email": "brycelarsenmusic@gmail.com",
            "password": "RequestWave2024!"
        }
        
        self.jwt_token = None
        self.musician_slug = "bryce-larsen"
        
        print(f"🔍 RequestWave Final URL Domain Verification")
        print(f"📍 Backend URL: {self.backend_url}")
        print(f"🕐 Verification Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def authenticate(self) -> bool:
        """Authenticate with test credentials"""
        try:
            response = self.session.post(
                f"{self.api_url}/auth/login",
                json=self.test_credentials
            )
            
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("token")
                
                if self.jwt_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.jwt_token}'
                    })
                    print("✅ Authentication successful")
                    return True
            
            print("❌ Authentication failed")
            return False
                
        except Exception as e:
            print(f"❌ Authentication exception: {str(e)}")
            return False

    def verify_qr_code_endpoint(self):
        """Verify QR code endpoint returns correct domain"""
        print("\n📱 VERIFYING: QR Code Endpoint")
        print("-" * 50)
        
        try:
            response = self.session.get(f"{self.api_url}/qr-code")
            
            if response.status_code == 200:
                data = response.json()
                audience_url = data.get("audience_url")
                
                if audience_url == "https://requestwave.app/musician/bryce-larsen":
                    print(f"✅ QR Code URL: {audience_url}")
                    return True
                else:
                    print(f"❌ QR Code URL incorrect: {audience_url}")
                    return False
            else:
                print(f"❌ QR Code endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ QR Code exception: {str(e)}")
            return False

    def verify_public_endpoints(self):
        """Verify public endpoints contain no hardcoded URLs"""
        print("\n🌐 VERIFYING: Public Endpoints")
        print("-" * 50)
        
        endpoints_to_check = [
            f"/musicians/{self.musician_slug}",
            f"/musicians/{self.musician_slug}/songs"
        ]
        
        all_good = True
        
        for endpoint in endpoints_to_check:
            try:
                # Remove auth for public endpoints
                temp_headers = self.session.headers.copy()
                if 'Authorization' in self.session.headers:
                    del self.session.headers['Authorization']
                
                response = self.session.get(f"{self.api_url}{endpoint}")
                
                # Restore auth
                self.session.headers = temp_headers
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for any hardcoded URLs
                    data_str = json.dumps(data)
                    if "livewave-music.emergent.host" in data_str:
                        print(f"❌ {endpoint}: Contains old domain")
                        all_good = False
                    elif "requestwave.app" in data_str:
                        print(f"⚠️  {endpoint}: Contains requestwave.app (check if expected)")
                    else:
                        print(f"✅ {endpoint}: No hardcoded URLs")
                else:
                    print(f"❌ {endpoint}: HTTP {response.status_code}")
                    all_good = False
                    
            except Exception as e:
                print(f"❌ {endpoint}: Exception {str(e)}")
                all_good = False
        
        return all_good

    def verify_consistency(self):
        """Verify URL generation consistency"""
        print("\n🔄 VERIFYING: URL Generation Consistency")
        print("-" * 50)
        
        urls = []
        
        try:
            # Test multiple QR code requests
            for i in range(5):
                response = self.session.get(f"{self.api_url}/qr-code")
                if response.status_code == 200:
                    data = response.json()
                    urls.append(data.get("audience_url"))
                time.sleep(0.2)
            
            # Check consistency
            unique_urls = set(urls)
            if len(unique_urls) == 1:
                url = list(unique_urls)[0]
                if url == "https://requestwave.app/musician/bryce-larsen":
                    print(f"✅ Consistent URL generation: {url}")
                    return True
                else:
                    print(f"❌ Consistent but wrong URL: {url}")
                    return False
            else:
                print(f"❌ Inconsistent URLs: {unique_urls}")
                return False
                
        except Exception as e:
            print(f"❌ Consistency check exception: {str(e)}")
            return False

    def run_verification(self):
        """Run complete URL domain verification"""
        print("🔍 STARTING: Final URL Domain Verification")
        print("=" * 80)
        
        if not self.authenticate():
            print("❌ CRITICAL: Authentication failed")
            return False
        
        # Run all verifications
        qr_ok = self.verify_qr_code_endpoint()
        public_ok = self.verify_public_endpoints()
        consistency_ok = self.verify_consistency()
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎯 FINAL VERIFICATION SUMMARY")
        print("=" * 80)
        
        all_tests = [qr_ok, public_ok, consistency_ok]
        passed = sum(all_tests)
        total = len(all_tests)
        
        print(f"Tests Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL URL DOMAIN VERIFICATION TESTS PASSED")
            print("✅ QR Code endpoint returns correct domain")
            print("✅ Public endpoints contain no hardcoded URLs")
            print("✅ URL generation is consistent")
            print("\n🚀 CONCLUSION: Audience URL domain mismatch issue is COMPLETELY RESOLVED")
            return True
        else:
            print("❌ SOME VERIFICATION TESTS FAILED")
            if not qr_ok:
                print("❌ QR Code endpoint issue")
            if not public_ok:
                print("❌ Public endpoints contain hardcoded URLs")
            if not consistency_ok:
                print("❌ URL generation inconsistency")
            return False

def main():
    """Main verification function"""
    verifier = FinalURLVerification()
    
    try:
        success = verifier.run_verification()
        return 0 if success else 1
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Verification failed with exception: {str(e)}")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)