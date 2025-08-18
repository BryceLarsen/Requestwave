#!/usr/bin/env python3
"""
Production Stripe Configuration Check Script
Comprehensive validation for production deployment
"""

import os
from dotenv import load_dotenv
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

def check_production_stripe_config():
    print("="*80)
    print("PRODUCTION STRIPE CONFIGURATION CHECK")
    print("="*80)
    
    issues = []
    warnings = []
    
    # 1. Check Stripe API Key (live mode requirement)
    api_key = os.environ.get('STRIPE_API_KEY')
    print(f"\n1. STRIPE_API_KEY:")
    if not api_key:
        print("   ❌ NOT SET")
        issues.append("STRIPE_API_KEY environment variable not set")
    elif api_key.startswith("sk_live_YOUR_REAL"):
        print("   ❌ PLACEHOLDER VALUE")
        issues.append("STRIPE_API_KEY contains placeholder value - replace with real live key")
    elif api_key.startswith("sk_test_"):
        print(f"   ⚠️  TEST KEY ({api_key[:15]}...)")
        warnings.append("Using test key in production - should use live key (sk_live_)")
    elif api_key.startswith("sk_live_"):
        print(f"   ✅ LIVE KEY SET ({api_key[:15]}...)")
    else:
        print(f"   ❓ UNKNOWN FORMAT ({api_key[:15]}...)")
        issues.append("STRIPE_API_KEY has unknown format")
    
    # 2. Check Webhook Secret
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    print(f"\n2. STRIPE_WEBHOOK_SECRET:")
    if not webhook_secret:
        print("   ❌ NOT SET")
        issues.append("STRIPE_WEBHOOK_SECRET environment variable not set")
    elif webhook_secret.startswith("whsec_YOUR_REAL"):
        print("   ❌ PLACEHOLDER VALUE")
        issues.append("STRIPE_WEBHOOK_SECRET contains placeholder value")
    elif webhook_secret.startswith("whsec_"):
        print(f"   ✅ SET ({webhook_secret[:15]}...)")
    else:
        print(f"   ❓ UNKNOWN FORMAT ({webhook_secret[:15]}...)")
        issues.append("STRIPE_WEBHOOK_SECRET has unknown format")
    
    # 3. Check Price IDs
    monthly_price = os.environ.get('PRICE_MONTHLY_5')
    annual_price = os.environ.get('PRICE_ANNUAL_48')
    startup_price = os.environ.get('PRICE_STARTUP_15')
    
    print(f"\n3. STRIPE PRICE IDs:")
    
    print(f"   PRICE_MONTHLY_5 ($5/month): ", end="")
    if not monthly_price or monthly_price.startswith("price_YOUR_REAL"):
        print("❌ NOT CONFIGURED")
        issues.append("PRICE_MONTHLY_5 not configured - need real Stripe price ID for $5/month")
    elif monthly_price.startswith("price_"):
        print(f"✅ SET ({monthly_price})")
    else:
        print(f"❓ UNKNOWN FORMAT ({monthly_price})")
        issues.append("PRICE_MONTHLY_5 has unknown format")
    
    print(f"   PRICE_ANNUAL_48 ($48/year): ", end="")
    if not annual_price or annual_price.startswith("price_YOUR_REAL"):
        print("❌ NOT CONFIGURED")
        issues.append("PRICE_ANNUAL_48 not configured - need real Stripe price ID for $48/year")
    elif annual_price.startswith("price_"):
        print(f"✅ SET ({annual_price})")
    else:
        print(f"❓ UNKNOWN FORMAT ({annual_price})")
        issues.append("PRICE_ANNUAL_48 has unknown format")
    
    print(f"   PRICE_STARTUP_15 ($15 one-time): ", end="")
    if not startup_price or startup_price.startswith("price_YOUR_REAL"):
        print("❌ NOT CONFIGURED")
        issues.append("PRICE_STARTUP_15 not configured - need real Stripe price ID for $15 startup fee")
    elif startup_price.startswith("price_"):
        print(f"✅ SET ({startup_price})")
    else:
        print(f"❓ UNKNOWN FORMAT ({startup_price})")
        issues.append("PRICE_STARTUP_15 has unknown format")
    
    # 4. Check URL Configuration
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    print(f"\n4. URL CONFIGURATION:")
    print(f"   FRONTEND_URL: {frontend_url}")
    
    if frontend_url.startswith('http://localhost') or frontend_url.startswith('https://localhost'):
        warnings.append("FRONTEND_URL is set to localhost - should be production domain")
    elif not frontend_url.startswith('https://'):
        warnings.append("FRONTEND_URL should use HTTPS in production")
    
    # Expected webhook URL
    expected_webhook_url = f"{frontend_url}/api/stripe/webhook"
    print(f"   Expected webhook URL: {expected_webhook_url}")
    
    # 5. Database Configuration
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    print(f"\n5. DATABASE CONFIGURATION:")
    print(f"   MONGO_URL: {'✅ SET' if mongo_url else '❌ NOT SET'}")
    print(f"   DB_NAME: {db_name if db_name else '❌ NOT SET'}")
    
    if not mongo_url:
        issues.append("MONGO_URL environment variable not set")
    if not db_name:
        issues.append("DB_NAME environment variable not set")
    
    # 6. JWT Configuration
    jwt_secret = os.environ.get('JWT_SECRET')
    print(f"\n6. JWT CONFIGURATION:")
    if not jwt_secret:
        print("   ❌ JWT_SECRET NOT SET")
        issues.append("JWT_SECRET environment variable not set")
    elif jwt_secret == 'requestwave-secret-key':
        print("   ⚠️  USING DEFAULT SECRET")
        warnings.append("JWT_SECRET is using default value - should be changed for production")
    else:
        print("   ✅ JWT_SECRET SET (custom value)")
    
    # Summary
    print(f"\n" + "="*80)
    print("CONFIGURATION SUMMARY:")
    print(f"Issues: {len(issues)}")
    print(f"Warnings: {len(warnings)}")
    
    if not issues and not warnings:
        print("✅ ALL CONFIGURATION LOOKS GOOD FOR PRODUCTION!")
        print("\nYour subscription system should work correctly.")
        return True
    
    if issues:
        print("\n❌ CRITICAL ISSUES FOUND (MUST FIX):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS (RECOMMENDED TO FIX):")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if issues:
        print(f"\n🔧 TO FIX CRITICAL ISSUES:")
        print("1. Log into your Stripe Dashboard (https://dashboard.stripe.com)")
        print("2. Switch to 'Live' mode (toggle in top-left)")
        print("3. Go to Developers > API keys")
        print("4. Copy your 'Secret key' (starts with sk_live_)")
        print("5. Go to Products and create price objects for:")
        print("   - Monthly subscription: $5.00/month recurring")
        print("   - Annual subscription: $48.00/year recurring") 
        print("   - Startup fee: $15.00 one-time")
        print("6. Go to Developers > Webhooks")
        print(f"7. Create endpoint: {expected_webhook_url}")
        print("8. Select events: checkout.session.completed, invoice.payment_succeeded, invoice.payment_failed")
        print("9. Copy the webhook signing secret (starts with whsec_)")
        print("10. Update your environment variables with the real values")
        
        return False
    
    print("="*80)
    return len(warnings) == 0

if __name__ == "__main__":
    success = check_production_stripe_config()
    exit(0 if success else 1)