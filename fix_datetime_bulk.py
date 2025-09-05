#!/usr/bin/env python3
"""
Bulk fix datetime serialization issues in server.py
Fix all MongoDB-stored datetime objects that cause JSON serialization errors
"""

import re

def fix_datetime_serialization():
    with open('/app/backend/server.py', 'r') as f:
        content = f.read()
    
    # Critical fixes for MongoDB documents that get returned in API responses
    fixes = [
        # Timestamp fields in MongoDB documents
        (r'"timestamp": datetime\.utcnow\(\)', '"timestamp": datetime.utcnow().isoformat()'),
        (r'"applied_at": datetime\.utcnow\(\)', '"applied_at": datetime.utcnow().isoformat()'),
        (r'"last_login": datetime\.utcnow\(\)', '"last_login": datetime.utcnow().isoformat()'),
        (r'"trial_start_date": datetime\.utcnow\(\)', '"trial_start_date": datetime.utcnow().isoformat()'),
        (r'"archived_at": datetime\.utcnow\(\)', '"archived_at": datetime.utcnow().isoformat()'),
        (r'"restored_at": datetime\.utcnow\(\)', '"restored_at": datetime.utcnow().isoformat()'),
        (r'"used_at": datetime\.utcnow\(\)', '"used_at": datetime.utcnow().isoformat()'),
        (r'"updated_at": datetime\.utcnow\(\)', '"updated_at": datetime.utcnow().isoformat()'),
        
        # Trial end dates that get returned in subscription status
        (r'trial_end = datetime\.utcnow\(\) \+ timedelta\(days=TRIAL_DAYS\)', 'trial_end = (datetime.utcnow() + timedelta(days=TRIAL_DAYS)).isoformat()'),
        (r'trial_end = datetime\.utcnow\(\) \+ timedelta\(days=14\)', 'trial_end = (datetime.utcnow() + timedelta(days=14)).isoformat()'),
        
        # Password reset expires_at that gets stored in DB
        (r'"expires_at": datetime\.utcnow\(\) \+ timedelta\(minutes=60\)', '"expires_at": datetime.utcnow() + timedelta(minutes=60)'),
        (r'"expires_at": datetime\.utcnow\(\) \+ timedelta\(days=7\)', '"expires_at": datetime.utcnow() + timedelta(days=7)'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content)
        
    with open('/app/backend/server.py', 'w') as f:
        f.write(content)
    
    print("Fixed critical datetime serialization issues")

if __name__ == "__main__":
    fix_datetime_serialization()