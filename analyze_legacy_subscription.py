#!/usr/bin/env python3
"""
Check what the legacy subscription system would return for brycelarsenmusic@gmail.com
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://requestwave-2.preview.emergentagent.com/api"
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

def simulate_legacy_subscription_logic(musician_data):
    """Simulate the legacy get_subscription_status logic"""
    print("🔍 SIMULATING LEGACY SUBSCRIPTION LOGIC")
    print("=" * 60)
    
    now = datetime.utcnow()
    created_at_str = musician_data.get("created_at")
    
    if created_at_str:
        # Parse the created_at date
        try:
            if "T" in created_at_str:
                signup_date = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
            else:
                signup_date = datetime.fromisoformat(created_at_str)
        except:
            signup_date = now
    else:
        signup_date = now
    
    print(f"📊 Signup date: {signup_date}")
    print(f"📊 Current time: {now}")
    
    # Check if still in trial period (14 days from signup - TRIAL_DAYS = 14)
    TRIAL_DAYS = 14
    trial_end = signup_date + timedelta(days=TRIAL_DAYS)
    print(f"📊 Trial end: {trial_end}")
    
    if now < trial_end:
        print(f"   ✅ STILL IN TRIAL PERIOD")
        print(f"   📊 Days remaining: {(trial_end - now).days}")
        return {"plan": "trial", "reason": "within trial period"}
    else:
        print(f"   ❌ Trial period expired {(now - trial_end).days} days ago")
    
    # Check if has active subscription
    subscription_ends_at = musician_data.get("subscription_ends_at")
    print(f"📊 Subscription ends at: {subscription_ends_at}")
    
    if subscription_ends_at:
        try:
            if isinstance(subscription_ends_at, str):
                if "T" in subscription_ends_at:
                    subscription_end = datetime.fromisoformat(subscription_ends_at.replace("Z", "+00:00")).replace(tzinfo=None)
                else:
                    subscription_end = datetime.fromisoformat(subscription_ends_at)
            else:
                subscription_end = subscription_ends_at
            
            print(f"📊 Parsed subscription end: {subscription_end}")
            
            if now < subscription_end:
                print(f"   ✅ ACTIVE SUBSCRIPTION")
                print(f"   📊 Days remaining: {(subscription_end - now).days}")
                return {"plan": "pro", "reason": "active subscription"}
            else:
                print(f"   ❌ Subscription expired {(now - subscription_end).days} days ago")
        except Exception as e:
            print(f"   ⚠️  Error parsing subscription end date: {e}")
    
    # Default to free tier
    print(f"   📊 DEFAULTING TO FREE TIER")
    return {"plan": "free", "reason": "no active trial or subscription"}

def main():
    print("🔍 LEGACY SUBSCRIPTION SYSTEM ANALYSIS")
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
    print(f"   📊 Musician data keys: {list(musician_data.keys())}")
    
    # Show relevant fields
    print("\n📊 Step 2: Analyze musician data for subscription logic")
    relevant_fields = [
        "created_at", "subscription_ends_at", "trial_end", "has_had_trial",
        "audience_link_active", "subscription_status", "stripe_customer_id"
    ]
    
    for field in relevant_fields:
        value = musician_data.get(field)
        print(f"   📊 {field}: {value}")
    
    # Simulate legacy logic
    print("\n📊 Step 3: Simulate legacy subscription logic")
    legacy_result = simulate_legacy_subscription_logic(musician_data)
    
    print(f"\n📊 LEGACY SYSTEM RESULT:")
    print(f"   📊 Plan: {legacy_result['plan']}")
    print(f"   📊 Reason: {legacy_result['reason']}")
    
    # Check if this would allow Pro access
    allows_pro_access = legacy_result['plan'] in ["trial", "pro"]
    print(f"   📊 Allows Pro access: {allows_pro_access}")
    
    print("\n" + "=" * 80)
    print("🔍 CONCLUSION:")
    print(f"- Legacy system would return: plan='{legacy_result['plan']}'")
    print(f"- This {'ALLOWS' if allows_pro_access else 'DENIES'} playlist access")
    print(f"- Freemium system returns: plan='canceled'")
    print(f"- Frontend expects: plan in ['trial', 'pro']")
    
    if legacy_result['plan'] in ["trial", "pro"]:
        print("✅ FRONTEND-BACKEND COMPATIBLE: Both systems allow playlist access")
    else:
        print("❌ FRONTEND-BACKEND MISMATCH: Systems disagree on access")
    
    print("=" * 80)

if __name__ == "__main__":
    main()