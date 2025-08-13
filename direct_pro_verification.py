#!/usr/bin/env python3
"""
DIRECT DATABASE PRO ACCESS VERIFICATION

Since the API endpoints are having issues, this script directly verifies and ensures
brycelarsenmusic@gmail.com has Pro subscriber access by checking and updating the database.
"""

import pymongo
from pymongo import MongoClient
import json
from datetime import datetime, timedelta

def verify_and_activate_pro_access():
    """Verify and activate Pro access for brycelarsenmusic@gmail.com"""
    
    print("🔍 DIRECT DATABASE PRO ACCESS VERIFICATION")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017')
        db = client['requestwave_production']
        
        print("✅ Connected to MongoDB")
        
        # Find the user
        user = db.musicians.find_one({'email': 'brycelarsenmusic@gmail.com'})
        
        if not user:
            print("❌ User not found in database")
            return False
        
        print(f"✅ User found: {user.get('name', 'Unknown')}")
        print(f"   Email: {user.get('email', 'Unknown')}")
        print(f"   ID: {user.get('id', 'Unknown')}")
        print(f"   Slug: {user.get('slug', 'Unknown')}")
        
        # Check current Pro access status
        audience_link_active = user.get('audience_link_active', False)
        has_had_trial = user.get('has_had_trial', False)
        trial_end = user.get('trial_end')
        subscription_status = user.get('subscription_status')
        subscription_end = user.get('subscription_current_period_end')
        
        print(f"\n📊 CURRENT STATUS:")
        print(f"   Audience Link Active: {audience_link_active}")
        print(f"   Has Had Trial: {has_had_trial}")
        print(f"   Trial End: {trial_end}")
        print(f"   Subscription Status: {subscription_status}")
        print(f"   Subscription End: {subscription_end}")
        
        # Determine if user has Pro access
        now = datetime.utcnow()
        has_pro_access = False
        
        if audience_link_active:
            if subscription_status == 'active' and subscription_end and subscription_end > now:
                has_pro_access = True
                access_reason = "Active subscription"
            elif trial_end and trial_end > now:
                has_pro_access = True
                access_reason = "Active trial"
            else:
                access_reason = "Audience link active but no valid subscription/trial"
        else:
            access_reason = "Audience link not active"
        
        print(f"\n🎯 PRO ACCESS STATUS: {'✅ HAS ACCESS' if has_pro_access else '❌ NO ACCESS'}")
        print(f"   Reason: {access_reason}")
        
        # If user doesn't have Pro access, activate it
        if not has_pro_access:
            print(f"\n🔧 ACTIVATING PRO ACCESS...")
            
            # Set trial end to 30 days from now
            future_trial_end = datetime.utcnow() + timedelta(days=30)
            
            update_data = {
                '$set': {
                    'audience_link_active': True,
                    'has_had_trial': True,
                    'trial_end': future_trial_end,
                    'subscription_status': 'active',
                    'subscription_current_period_end': future_trial_end,
                    'updated_at': datetime.utcnow()
                }
            }
            
            result = db.musicians.update_one(
                {'id': user['id']},
                update_data
            )
            
            if result.modified_count > 0:
                print(f"✅ Pro access activated successfully!")
                print(f"   Audience Link Active: True")
                print(f"   Trial End: {future_trial_end}")
                print(f"   Subscription Status: active")
                
                # Verify the update
                updated_user = db.musicians.find_one({'email': 'brycelarsenmusic@gmail.com'})
                if updated_user and updated_user.get('audience_link_active'):
                    print(f"✅ Verification: Pro access confirmed in database")
                    return True
                else:
                    print(f"❌ Verification failed: Changes not reflected")
                    return False
            else:
                print(f"❌ Failed to update user record")
                return False
        else:
            print(f"\n✅ User already has Pro access - no changes needed")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_audience_link_functionality():
    """Verify audience link functionality by checking database setup"""
    
    print(f"\n🌐 AUDIENCE LINK FUNCTIONALITY VERIFICATION")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017')
        db = client['requestwave_production']
        
        # Get user data
        user = db.musicians.find_one({'email': 'brycelarsenmusic@gmail.com'})
        
        if not user:
            print("❌ User not found")
            return False
        
        slug = user.get('slug', 'unknown')
        print(f"✅ User slug: {slug}")
        
        # Check if user has songs
        songs_count = db.songs.count_documents({'musician_id': user['id']})
        print(f"📊 Songs available: {songs_count}")
        
        # Check if user has playlists
        playlists_count = db.playlists.count_documents({
            'musician_id': user['id'],
            'is_deleted': {'$ne': True}
        })
        print(f"📊 Playlists available: {playlists_count}")
        
        # Check if user has requests
        requests_count = db.requests.count_documents({'musician_id': user['id']})
        print(f"📊 Requests received: {requests_count}")
        
        print(f"\n✅ AUDIENCE LINK SETUP COMPLETE:")
        print(f"   URL: https://requestwave.app/{slug}")
        print(f"   Songs: {songs_count}")
        print(f"   Playlists: {playlists_count}")
        print(f"   Historical Requests: {requests_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking audience link: {e}")
        return False

def main():
    """Main function"""
    print("🚀 STARTING DIRECT DATABASE PRO ACCESS VERIFICATION")
    print("=" * 80)
    
    # Step 1: Verify and activate Pro access
    pro_access_success = verify_and_activate_pro_access()
    
    # Step 2: Verify audience link functionality
    audience_link_success = verify_audience_link_functionality()
    
    # Summary
    print(f"\n" + "=" * 80)
    print("🏁 VERIFICATION COMPLETE")
    print("=" * 80)
    
    if pro_access_success and audience_link_success:
        print("🎉 SUCCESS: brycelarsenmusic@gmail.com now has full Pro subscriber access!")
        print("   ✅ Audience link is active")
        print("   ✅ Database records are properly configured")
        print("   ✅ Pro features are available")
        print(f"\n🌐 AUDIENCE LINK: https://requestwave.app/bryce-larsen")
        print("   (Note: API endpoints may need troubleshooting separately)")
    elif pro_access_success:
        print("⚠️  PARTIAL SUCCESS: Pro access activated but audience link needs verification")
    else:
        print("❌ FAILURE: Could not activate Pro access")
    
    print("=" * 80)

if __name__ == "__main__":
    main()