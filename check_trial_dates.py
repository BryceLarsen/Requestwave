#!/usr/bin/env python3
"""
Precise date calculation test
"""

from datetime import datetime, timedelta

def main():
    print("🔍 PRECISE DATE CALCULATION")
    print("=" * 50)
    
    # User's signup date
    signup_str = "2025-07-28T01:17:08.939000"
    signup_date = datetime.fromisoformat(signup_str)
    
    print(f"📊 Signup date: {signup_date}")
    
    # Current time (approximate)
    now = datetime.utcnow()
    print(f"📊 Current time: {now}")
    
    # Trial period
    TRIAL_DAYS = 14
    trial_end = signup_date + timedelta(days=TRIAL_DAYS)
    print(f"📊 Trial end: {trial_end}")
    
    # Check if still in trial
    still_in_trial = now < trial_end
    print(f"📊 Still in trial: {still_in_trial}")
    
    if still_in_trial:
        days_remaining = (trial_end - now).days
        hours_remaining = (trial_end - now).seconds // 3600
        print(f"📊 Time remaining: {days_remaining} days, {hours_remaining} hours")
    else:
        days_expired = (now - trial_end).days
        hours_expired = (now - trial_end).seconds // 3600
        print(f"📊 Trial expired: {days_expired} days, {hours_expired} hours ago")
    
    print("=" * 50)

if __name__ == "__main__":
    main()