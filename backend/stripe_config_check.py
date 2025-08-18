#!/usr/bin/env python3
"""
Stripe Configuration Check Script
Run this to verify your Stripe configuration before deployment
"""

import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

def check_stripe_config():
    print("="*60)
    print("STRIPE CONFIGURATION CHECK")
    print("="*60)
    
    # Check API Key
    api_key = os.environ.get('STRIPE_API_KEY')
    print(f"\n1. STRIPE_API_KEY:")
    if not api_key:
        print("   ❌ NOT SET")
    elif api_key.startswith("sk_live_YOUR_REAL"):
        print("   ❌ PLACEHOLDER VALUE - Replace with real Stripe secret key")
    elif api_key.startswith("sk_live_"):
        print(f"   ✅ LIVE KEY SET ({api_key[:12]}...)")
    elif api_key.startswith("sk_test_"):
        print(f"   ⚠️  TEST KEY SET ({api_key[:12]}...) - Use live key for production")
    else:
        print(f"   ❓ UNKNOWN FORMAT ({api_key[:12]}...)")
    
    # Check Webhook Secret
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    print(f"\n2. STRIPE_WEBHOOK_SECRET:")
    if not webhook_secret:
        print("   ❌ NOT SET")
    elif webhook_secret.startswith("whsec_YOUR_REAL"):
        print("   ❌ PLACEHOLDER VALUE - Replace with real webhook secret")
    elif webhook_secret.startswith("whsec_"):
        print(f"   ✅ SET ({webhook_secret[:12]}...)")
    else:
        print(f"   ❓ UNKNOWN FORMAT ({webhook_secret[:12]}...)")
    
    # Check Price IDs
    monthly_price = os.environ.get('PRICE_MONTHLY_5')
    annual_price = os.environ.get('PRICE_ANNUAL_48')
    startup_price = os.environ.get('PRICE_STARTUP_15')
    
    print(f"\n3. PRICE IDs:")
    print(f"   PRICE_MONTHLY_5: ", end="")
    if not monthly_price or monthly_price.startswith("price_YOUR_REAL"):
        print("❌ NOT CONFIGURED")
    elif monthly_price.startswith("price_"):
        print(f"✅ SET ({monthly_price})")
    else:
        print(f"❓ UNKNOWN FORMAT ({monthly_price})")
    
    print(f"   PRICE_ANNUAL_48: ", end="")
    if not annual_price or annual_price.startswith("price_YOUR_REAL"):
        print("❌ NOT CONFIGURED")
    elif annual_price.startswith("price_"):
        print(f"✅ SET ({annual_price})")
    else:
        print(f"❓ UNKNOWN FORMAT ({annual_price})")
    
    print(f"   PRICE_STARTUP_15: ", end="")
    if not startup_price or startup_price.startswith("price_YOUR_REAL"):
        print("❌ NOT CONFIGURED")
    elif startup_price.startswith("price_"):
        print(f"✅ SET ({startup_price})")
    else:
        print(f"❓ UNKNOWN FORMAT ({startup_price})")
    
    # Summary
    print(f"\n" + "="*60)
    print("CONFIGURATION SUMMARY:")
    
    issues = []
    if not api_key or api_key.startswith("sk_live_YOUR_REAL"):
        issues.append("- Replace STRIPE_API_KEY with your real Stripe secret key")
    if not webhook_secret or webhook_secret.startswith("whsec_YOUR_REAL"):
        issues.append("- Replace STRIPE_WEBHOOK_SECRET with your real webhook secret")
    if not monthly_price or monthly_price.startswith("price_YOUR_REAL"):
        issues.append("- Replace PRICE_MONTHLY_5 with your real monthly price ID")
    if not annual_price or annual_price.startswith("price_YOUR_REAL"):
        issues.append("- Replace PRICE_ANNUAL_48 with your real annual price ID")
    
    if not issues:
        print("✅ ALL STRIPE CONFIGURATION LOOKS GOOD!")
        print("\nYour subscription system should work correctly.")
    else:
        print("❌ CONFIGURATION ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        print(f"\nTo fix these issues:")
        print("1. Log into your Stripe Dashboard")
        print("2. Get your live API keys from the Developers section")
        print("3. Create price objects for monthly ($5) and annual ($48) subscriptions")
        print("4. Set up a webhook endpoint and get the webhook secret")
        print("5. Update your environment variables with the real values")
    
    print("="*60)

if __name__ == "__main__":
    check_stripe_config()