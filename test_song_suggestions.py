#!/usr/bin/env python3
"""
Song Suggestion Feature Testing Script
"""

from backend_test import RequestWaveAPITester

if __name__ == "__main__":
    tester = RequestWaveAPITester()
    
    print("🎵 SONG SUGGESTION FEATURE TESTING")
    print("=" * 50)
    print("Testing the NEW Song Suggestion feature - comprehensive testing of the Pro feature functionality")
    print()
    
    # Reset results for focused testing
    tester.results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # Authentication setup
    tester.test_musician_registration()
    
    if not tester.auth_token:
        print("❌ CRITICAL: Could not authenticate - cannot proceed with song suggestion tests")
        exit(1)
    
    print(f"✅ Authenticated as musician: {tester.musician_slug}")
    print()
    
    # Run all song suggestion tests
    print("🔍 Running Song Suggestion Feature Tests...")
    print()
    
    tester.test_song_suggestion_creation_endpoint()
    tester.test_song_suggestion_required_fields_validation()
    tester.test_song_suggestion_email_validation()
    tester.test_song_suggestion_duplicate_prevention()
    tester.test_song_suggestion_pro_feature_access_control()
    tester.test_song_suggestion_invalid_musician_slug()
    tester.test_musician_song_suggestions_management()
    tester.test_song_suggestion_status_update_accept()
    tester.test_song_suggestion_status_update_reject()
    tester.test_song_suggestion_delete()
    tester.test_song_suggestion_authentication_required()
    tester.test_song_suggestion_duplicate_song_prevention()
    
    # Print focused summary
    print("\n" + "=" * 60)
    print("🏁 SONG SUGGESTION FEATURE TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {tester.results['passed']}")
    print(f"❌ Failed: {tester.results['failed']}")
    
    if tester.results['errors']:
        print("\n🔍 Failed Tests:")
        for error in tester.results['errors']:
            print(f"   • {error}")
    else:
        print("\n🎉 All Song Suggestion Feature tests passed!")
        print("✅ Song suggestion creation working correctly")
        print("✅ Required field validation working")
        print("✅ Duplicate prevention working")
        print("✅ Pro feature access control implemented")
        print("✅ Musician management endpoints working")
        print("✅ Status updates (accept/reject) working")
        print("✅ Authentication and authorization working")
        print("✅ Database operations working correctly")
    
    success = tester.results['failed'] == 0
    exit(0 if success else 1)