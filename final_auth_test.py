#!/usr/bin/env python3
"""
FINAL AUTHENTICATION TEST AFTER PASSWORD RESET

Testing authentication after password was reset to RequestWave2024!
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional

# Configuration
INTERNAL_URL = "http://localhost:8001/api"
EXTERNAL_URL = "https://requestwave.app/api"

# User credentials (password was reset)
USER_CREDENTIALS = {
    "email": "brycelarsenmusic@gmail.com",
    "password": "RequestWave2024!"
}

class FinalAuthTester:
    def __init__(self):
        self.internal_token = None
        self.external_token = None
        self.results = []

    def make_request(self, method: str, endpoint: str, base_url: str, data: Any = None, headers: Dict = None, timeout: int = 30) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{base_url}{endpoint}"
        
        # Default headers
        request_headers = {"Content-Type": "application/json"}
        
        # Override with custom headers
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise

    def test_comprehensive_auth(self):
        """Test comprehensive authentication flow"""
        print("🔍 FINAL AUTHENTICATION TEST AFTER PASSWORD RESET")
        print("=" * 80)
        
        # Test 1: Internal Login
        print("📊 Test 1: Internal Login")
        try:
            response = self.make_request("POST", "/auth/login", INTERNAL_URL, USER_CREDENTIALS)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                self.internal_token = data["token"]
                print(f"   ✅ INTERNAL LOGIN SUCCESSFUL")
                print(f"   📊 User: {data['musician']['name']} ({data['musician']['email']})")
                print(f"   📊 Subscription Status: {data['musician']['subscription_status']}")
                print(f"   📊 Audience Link Active: {data['musician']['audience_link_active']}")
                self.results.append("✅ Internal Login: WORKING")
            else:
                print(f"   ❌ INTERNAL LOGIN FAILED: {response.text}")
                self.results.append("❌ Internal Login: FAILED")
        except Exception as e:
            print(f"   ❌ INTERNAL LOGIN ERROR: {str(e)}")
            self.results.append("❌ Internal Login: ERROR")
        
        print()
        
        # Test 2: External Login
        print("📊 Test 2: External Login")
        try:
            response = self.make_request("POST", "/auth/login", EXTERNAL_URL, USER_CREDENTIALS)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                self.external_token = data["token"]
                print(f"   ✅ EXTERNAL LOGIN SUCCESSFUL")
                print(f"   📊 User: {data['musician']['name']} ({data['musician']['email']})")
                self.results.append("✅ External Login: WORKING")
            else:
                print(f"   ❌ EXTERNAL LOGIN FAILED: {response.text}")
                self.results.append("❌ External Login: FAILED")
        except Exception as e:
            print(f"   ❌ EXTERNAL LOGIN ERROR: {str(e)}")
            self.results.append("❌ External Login: ERROR")
        
        print()
        
        # Test 3: Internal Protected Endpoint
        if self.internal_token:
            print("📊 Test 3: Internal Protected Endpoint Access")
            try:
                headers = {"Authorization": f"Bearer {self.internal_token}"}
                response = self.make_request("GET", "/songs", INTERNAL_URL, headers=headers)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ INTERNAL PROTECTED ACCESS SUCCESSFUL")
                    print(f"   📊 Retrieved {len(data)} songs")
                    self.results.append("✅ Internal Protected Access: WORKING")
                else:
                    print(f"   ❌ INTERNAL PROTECTED ACCESS FAILED: {response.text}")
                    self.results.append("❌ Internal Protected Access: FAILED")
            except Exception as e:
                print(f"   ❌ INTERNAL PROTECTED ACCESS ERROR: {str(e)}")
                self.results.append("❌ Internal Protected Access: ERROR")
            print()
        
        # Test 4: External Protected Endpoint
        if self.external_token:
            print("📊 Test 4: External Protected Endpoint Access")
            try:
                headers = {"Authorization": f"Bearer {self.external_token}"}
                response = self.make_request("GET", "/songs", EXTERNAL_URL, headers=headers)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ EXTERNAL PROTECTED ACCESS SUCCESSFUL")
                    print(f"   📊 Retrieved {len(data)} songs")
                    self.results.append("✅ External Protected Access: WORKING")
                else:
                    print(f"   ❌ EXTERNAL PROTECTED ACCESS FAILED: {response.text}")
                    self.results.append("❌ External Protected Access: FAILED")
            except Exception as e:
                print(f"   ❌ EXTERNAL PROTECTED ACCESS ERROR: {str(e)}")
                self.results.append("❌ External Protected Access: ERROR")
            print()
        
        # Test 5: Internal Subscription Status
        if self.internal_token:
            print("📊 Test 5: Internal Subscription Status")
            try:
                headers = {"Authorization": f"Bearer {self.internal_token}"}
                response = self.make_request("GET", "/subscription/status", INTERNAL_URL, headers=headers)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ INTERNAL SUBSCRIPTION STATUS SUCCESSFUL")
                    print(f"   📊 Plan: {data.get('plan', 'unknown')}")
                    print(f"   📊 Audience Link Active: {data.get('audience_link_active', 'unknown')}")
                    print(f"   📊 Trial Active: {data.get('trial_active', 'unknown')}")
                    self.results.append("✅ Internal Subscription Status: WORKING")
                else:
                    print(f"   ❌ INTERNAL SUBSCRIPTION STATUS FAILED: {response.text}")
                    self.results.append("❌ Internal Subscription Status: FAILED")
            except Exception as e:
                print(f"   ❌ INTERNAL SUBSCRIPTION STATUS ERROR: {str(e)}")
                self.results.append("❌ Internal Subscription Status: ERROR")
            print()
        
        # Test 6: Internal Forgot Password (to confirm it still works)
        print("📊 Test 6: Internal Forgot Password (Verification)")
        try:
            forgot_data = {"email": USER_CREDENTIALS["email"]}
            response = self.make_request("POST", "/auth/forgot-password", INTERNAL_URL, forgot_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ INTERNAL FORGOT PASSWORD WORKING")
                print(f"   📊 Message: {data.get('message', 'No message')}")
                self.results.append("✅ Internal Forgot Password: WORKING")
            else:
                print(f"   ❌ INTERNAL FORGOT PASSWORD FAILED: {response.text}")
                self.results.append("❌ Internal Forgot Password: FAILED")
        except Exception as e:
            print(f"   ❌ INTERNAL FORGOT PASSWORD ERROR: {str(e)}")
            self.results.append("❌ Internal Forgot Password: ERROR")
        
        print()
        
        # Test 7: External Forgot Password
        print("📊 Test 7: External Forgot Password")
        try:
            forgot_data = {"email": USER_CREDENTIALS["email"]}
            response = self.make_request("POST", "/auth/forgot-password", EXTERNAL_URL, forgot_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ EXTERNAL FORGOT PASSWORD WORKING")
                print(f"   📊 Message: {data.get('message', 'No message')}")
                self.results.append("✅ External Forgot Password: WORKING")
            else:
                print(f"   ❌ EXTERNAL FORGOT PASSWORD FAILED: {response.text}")
                self.results.append("❌ External Forgot Password: FAILED")
        except Exception as e:
            print(f"   ❌ EXTERNAL FORGOT PASSWORD ERROR: {str(e)}")
            self.results.append("❌ External Forgot Password: ERROR")
        
        print()
        
        # Final Summary
        print("=" * 80)
        print("🔍 FINAL AUTHENTICATION TEST SUMMARY")
        print("=" * 80)
        
        for result in self.results:
            print(f"   {result}")
        
        # Count results
        working_count = len([r for r in self.results if "WORKING" in r])
        total_count = len(self.results)
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   ✅ Working: {working_count}/{total_count}")
        print(f"   ❌ Failed: {total_count - working_count}/{total_count}")
        print(f"   📈 Success Rate: {(working_count/total_count*100):.1f}%")
        
        # Diagnosis
        print(f"\n🔍 FINAL DIAGNOSIS:")
        if self.internal_token and not self.external_token:
            print(f"   ❌ CRITICAL ROUTING ISSUE: Internal authentication works, external fails")
            print(f"   📊 User account is healthy and password is correct")
            print(f"   🔧 SOLUTION NEEDED: Fix external API routing/proxy configuration")
            print(f"   ✅ USER CAN LOGIN: Password reset successful, credentials are valid")
        elif self.internal_token and self.external_token:
            print(f"   ✅ AUTHENTICATION WORKING: Both internal and external login successful")
            print(f"   📊 User can now login with brycelarsenmusic@gmail.com / RequestWave2024!")
        else:
            print(f"   ❌ AUTHENTICATION BROKEN: Neither internal nor external login working")
            print(f"   📊 Backend authentication system has issues")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = FinalAuthTester()
    tester.test_comprehensive_auth()