"""
Test suite for BILLING_ENABLED bypass in check_request_allowed()

Verifies:
1. BILLING_ENABLED=false allows unlimited requests (no 402)
2. BILLING_ENABLED=true preserves existing subscription gating
"""
import pytest
import os
from unittest.mock import patch, AsyncMock
import sys

# Add backend to path
sys.path.insert(0, '/app/backend')


class TestBillingEnabledBypass:
    """Test check_request_allowed() behavior based on BILLING_ENABLED flag"""
    
    @pytest.mark.asyncio
    async def test_billing_disabled_allows_all_requests(self):
        """
        When BILLING_ENABLED=false, check_request_allowed() should return True
        regardless of subscription status.
        """
        # Import with BILLING_ENABLED=false
        with patch.dict(os.environ, {'BILLING_ENABLED': 'false'}):
            # Reload the module to pick up the env change
            import importlib
            import server
            importlib.reload(server)
            
            # Verify BILLING_ENABLED is False
            assert server.BILLING_ENABLED == False, "BILLING_ENABLED should be False"
            
            # Mock get_subscription_status to return a status that would deny requests
            mock_status = AsyncMock()
            mock_status.can_make_request = False  # Would normally block
            
            with patch.object(server, 'get_subscription_status', return_value=mock_status):
                # Call check_request_allowed with any musician_id
                result = await server.check_request_allowed("any-musician-id")
                
                # Should return True because billing is disabled
                assert result == True, "Should allow request when BILLING_ENABLED=false"
    
    @pytest.mark.asyncio
    async def test_billing_enabled_respects_subscription_deny(self):
        """
        When BILLING_ENABLED=true, check_request_allowed() should respect
        subscription status and deny requests when can_make_request=False.
        """
        with patch.dict(os.environ, {'BILLING_ENABLED': 'true'}):
            import importlib
            import server
            importlib.reload(server)
            
            # Verify BILLING_ENABLED is True
            assert server.BILLING_ENABLED == True, "BILLING_ENABLED should be True"
            
            # Mock get_subscription_status to return a status that denies requests
            mock_status = AsyncMock()
            mock_status.can_make_request = False
            
            with patch.object(server, 'get_subscription_status', return_value=mock_status):
                result = await server.check_request_allowed("any-musician-id")
                
                # Should return False because subscription denies it
                assert result == False, "Should deny request when subscription.can_make_request=False"
    
    @pytest.mark.asyncio
    async def test_billing_enabled_respects_subscription_allow(self):
        """
        When BILLING_ENABLED=true, check_request_allowed() should respect
        subscription status and allow requests when can_make_request=True.
        """
        with patch.dict(os.environ, {'BILLING_ENABLED': 'true'}):
            import importlib
            import server
            importlib.reload(server)
            
            assert server.BILLING_ENABLED == True
            
            # Mock get_subscription_status to return a status that allows requests
            mock_status = AsyncMock()
            mock_status.can_make_request = True
            
            with patch.object(server, 'get_subscription_status', return_value=mock_status):
                result = await server.check_request_allowed("any-musician-id")
                
                # Should return True because subscription allows it
                assert result == True, "Should allow request when subscription.can_make_request=True"


class TestBillingEnabledParsing:
    """Test BILLING_ENABLED environment variable parsing"""
    
    def test_billing_enabled_false_string(self):
        """'false' string should result in False"""
        with patch.dict(os.environ, {'BILLING_ENABLED': 'false'}):
            result = os.getenv("BILLING_ENABLED", "false").lower() == "true"
            assert result == False
    
    def test_billing_enabled_true_string(self):
        """'true' string should result in True"""
        with patch.dict(os.environ, {'BILLING_ENABLED': 'true'}):
            result = os.getenv("BILLING_ENABLED", "false").lower() == "true"
            assert result == True
    
    def test_billing_enabled_TRUE_uppercase(self):
        """'TRUE' uppercase should result in True (case-insensitive)"""
        with patch.dict(os.environ, {'BILLING_ENABLED': 'TRUE'}):
            result = os.getenv("BILLING_ENABLED", "false").lower() == "true"
            assert result == True
    
    def test_billing_enabled_missing_defaults_false(self):
        """Missing env var should default to False"""
        env_copy = os.environ.copy()
        if 'BILLING_ENABLED' in env_copy:
            del env_copy['BILLING_ENABLED']
        with patch.dict(os.environ, env_copy, clear=True):
            result = os.getenv("BILLING_ENABLED", "false").lower() == "true"
            assert result == False
    
    def test_billing_enabled_random_value_is_false(self):
        """Any non-'true' value should result in False"""
        with patch.dict(os.environ, {'BILLING_ENABLED': 'yes'}):
            result = os.getenv("BILLING_ENABLED", "false").lower() == "true"
            assert result == False
        
        with patch.dict(os.environ, {'BILLING_ENABLED': '1'}):
            result = os.getenv("BILLING_ENABLED", "false").lower() == "true"
            assert result == False
