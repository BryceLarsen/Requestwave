#!/usr/bin/env python3
"""
Debug the check_pro_access function by simulating its logic
"""

from datetime import datetime, timedelta

# User data from the login response
signup_date = datetime.fromisoformat('2025-07-28T01:17:08.939000')
now = datetime.utcnow()
TRIAL_DAYS = 14
FREE_REQUESTS_LIMIT = 20

print(f"User signup date: {signup_date}")
print(f"Current time: {now}")
print(f"Trial days: {TRIAL_DAYS}")

# Simulate get_subscription_status logic
trial_end = signup_date + timedelta(days=TRIAL_DAYS)
print(f"Trial end: {trial_end}")
print(f"Still in trial: {now < trial_end}")

if now < trial_end:
    plan = "trial"
    print(f"✅ User should have plan: {plan}")
else:
    print(f"❌ User is past trial period")
    
    # Check if has active subscription (subscription_ends_at)
    # From the user data, subscription_ends_at is null
    subscription_ends_at = None
    
    if subscription_ends_at and now < subscription_ends_at:
        plan = "pro"
        print(f"✅ User should have plan: {plan}")
    else:
        plan = "free"
        print(f"❌ User should have plan: {plan}")

print(f"\nFinal plan: {plan}")
print(f"check_pro_access should return: {plan in ['trial', 'pro']}")