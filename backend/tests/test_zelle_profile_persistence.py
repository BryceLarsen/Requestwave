"""
Test suite for Zelle profile field persistence.

Verifies:
1. Profile update endpoint accepts Zelle fields
2. Profile fetch endpoint returns saved Zelle values
3. Zelle values persist across save/load cycle
"""
import pytest
import subprocess
import json
import os


class TestZelleProfilePersistence:
    """Test Zelle field save and load on musician profile"""
    
    API_URL = os.getenv("API_URL", "https://learn-later-hub.preview.emergentagent.com/api")
    TEST_EMAIL = "test@test.com"
    TEST_PASSWORD = "test"
    
    def get_token(self):
        """Get auth token for test user"""
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            f"{self.API_URL}/auth/login",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"email": self.TEST_EMAIL, "password": self.TEST_PASSWORD})
        ], capture_output=True, text=True)
        response = json.loads(result.stdout)
        return response.get("token")
    
    def test_zelle_save_and_load(self):
        """
        Test that Zelle fields persist after save and reload.
        
        Steps:
        1. Login and get token
        2. Update profile with Zelle data
        3. Fetch profile
        4. Assert Zelle values match
        """
        token = self.get_token()
        assert token, "Failed to get auth token"
        
        # Unique test values
        test_zelle_email = "pytest-zelle@test.com"
        test_zelle_phone = "555-PYTEST"
        
        # Step 1: Save Zelle data
        save_result = subprocess.run([
            "curl", "-s", "-X", "PUT",
            f"{self.API_URL}/profile",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "zelle_email": test_zelle_email,
                "zelle_phone": test_zelle_phone,
                "zelle_enabled": True
            })
        ], capture_output=True, text=True)
        
        save_response = json.loads(save_result.stdout)
        assert save_response.get("zelle_email") == test_zelle_email, \
            f"Save response zelle_email mismatch: {save_response.get('zelle_email')}"
        assert save_response.get("zelle_phone") == test_zelle_phone, \
            f"Save response zelle_phone mismatch: {save_response.get('zelle_phone')}"
        assert save_response.get("zelle_enabled") == True, \
            f"Save response zelle_enabled mismatch: {save_response.get('zelle_enabled')}"
        
        # Step 2: Fetch profile to verify persistence
        fetch_result = subprocess.run([
            "curl", "-s",
            f"{self.API_URL}/profile",
            "-H", f"Authorization: Bearer {token}"
        ], capture_output=True, text=True)
        
        fetch_response = json.loads(fetch_result.stdout)
        assert fetch_response.get("zelle_email") == test_zelle_email, \
            f"Fetch zelle_email mismatch: expected '{test_zelle_email}', got '{fetch_response.get('zelle_email')}'"
        assert fetch_response.get("zelle_phone") == test_zelle_phone, \
            f"Fetch zelle_phone mismatch: expected '{test_zelle_phone}', got '{fetch_response.get('zelle_phone')}'"
        assert fetch_response.get("zelle_enabled") == True, \
            f"Fetch zelle_enabled mismatch: expected True, got {fetch_response.get('zelle_enabled')}"
    
    def test_zelle_partial_update(self):
        """
        Test that updating only Zelle fields doesn't clear other profile data.
        """
        token = self.get_token()
        assert token, "Failed to get auth token"
        
        # Get current profile to compare
        fetch_result = subprocess.run([
            "curl", "-s",
            f"{self.API_URL}/profile",
            "-H", f"Authorization: Bearer {token}"
        ], capture_output=True, text=True)
        original = json.loads(fetch_result.stdout)
        original_name = original.get("name")
        
        # Update only Zelle
        new_zelle_email = "partial-update-test@zelle.com"
        save_result = subprocess.run([
            "curl", "-s", "-X", "PUT",
            f"{self.API_URL}/profile",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"zelle_email": new_zelle_email})
        ], capture_output=True, text=True)
        
        save_response = json.loads(save_result.stdout)
        
        # Name should be preserved
        assert save_response.get("name") == original_name, \
            f"Name was overwritten: expected '{original_name}', got '{save_response.get('name')}'"
        
        # Zelle should be updated
        assert save_response.get("zelle_email") == new_zelle_email, \
            f"Zelle email not updated: expected '{new_zelle_email}', got '{save_response.get('zelle_email')}'"
    
    def test_zelle_clear_value(self):
        """
        Test that Zelle fields can be cleared by setting to empty string.
        """
        token = self.get_token()
        assert token, "Failed to get auth token"
        
        # First set a value
        subprocess.run([
            "curl", "-s", "-X", "PUT",
            f"{self.API_URL}/profile",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"zelle_email": "to-be-cleared@test.com"})
        ], capture_output=True, text=True)
        
        # Now clear it
        clear_result = subprocess.run([
            "curl", "-s", "-X", "PUT",
            f"{self.API_URL}/profile",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"zelle_email": ""})
        ], capture_output=True, text=True)
        
        clear_response = json.loads(clear_result.stdout)
        assert clear_response.get("zelle_email") == "", \
            f"Zelle email not cleared: got '{clear_response.get('zelle_email')}'"
