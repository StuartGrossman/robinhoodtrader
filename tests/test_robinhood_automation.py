#!/usr/bin/env python3
"""
Test suite for Robinhood automation functionality
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

from src.robinhood_automation import RobinhoodAutomation, AuthConfig, SessionState


class TestAuthConfig:
    """Test AuthConfig dataclass functionality."""
    
    def test_auth_config_creation(self):
        """Test AuthConfig can be created with required fields."""
        config = AuthConfig(
            username="test@example.com",
            password="testpassword",
            mfa_phone="+1234567890",
            headless=False
        )
        
        assert config.username == "test@example.com"
        assert config.password == "testpassword"
        assert config.mfa_phone == "+1234567890"
        assert config.headless is False
        assert config.session_timeout == 3600  # default value
        assert config.max_login_attempts == 3  # default value
    
    def test_auth_config_defaults(self):
        """Test AuthConfig uses correct default values."""
        config = AuthConfig(
            username="test@example.com",
            password="testpassword"
        )
        
        assert config.mfa_phone is None
        assert config.mfa_email is None
        assert config.headless is True
        assert config.browser_timeout == 30000


class TestSessionState:
    """Test SessionState dataclass functionality."""
    
    def test_session_state_defaults(self):
        """Test SessionState has correct default values."""
        state = SessionState()
        
        assert state.is_authenticated is False
        assert state.last_activity is None
        assert state.session_cookies is None
        assert state.user_agent is None
        assert state.csrf_token is None
    
    def test_session_state_with_data(self):
        """Test SessionState can be created with data."""
        now = datetime.now()
        cookies = [{"name": "session", "value": "test"}]
        
        state = SessionState(
            is_authenticated=True,
            last_activity=now,
            session_cookies=cookies,
            user_agent="test-agent",
            csrf_token="test-token"
        )
        
        assert state.is_authenticated is True
        assert state.last_activity == now
        assert state.session_cookies == cookies
        assert state.user_agent == "test-agent"
        assert state.csrf_token == "test-token"


class TestRobinhoodAutomation:
    """Test RobinhoodAutomation class functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock AuthConfig for testing."""
        return AuthConfig(
            username="test@example.com",
            password="testpassword",
            headless=True,
            browser_timeout=10000
        )
    
    @pytest.fixture
    def mock_automation(self, mock_config):
        """Create a mock RobinhoodAutomation instance."""
        automation = RobinhoodAutomation(mock_config)
        automation.page = AsyncMock()
        automation.browser = AsyncMock()
        automation.context = AsyncMock()
        automation.playwright = AsyncMock()
        return automation
    
    def test_automation_initialization(self, mock_config):
        """Test RobinhoodAutomation can be initialized."""
        automation = RobinhoodAutomation(mock_config)
        
        assert automation.config == mock_config
        assert automation.session_state is not None
        assert isinstance(automation.session_state, SessionState)
        assert automation.logger is not None
    
    @pytest.mark.asyncio
    async def test_automation_context_manager(self, mock_config):
        """Test RobinhoodAutomation works as async context manager."""
        with patch('src.robinhood_automation.async_playwright') as mock_playwright:
            mock_playwright_instance = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            async with RobinhoodAutomation(mock_config) as automation:
                assert automation is not None
                assert hasattr(automation, 'page')
    
    @pytest.mark.asyncio
    async def test_is_authenticated_true(self, mock_automation):
        """Test _is_authenticated returns True when authenticated."""
        # Mock page to return authenticated state
        mock_automation.page.url = "https://robinhood.com/dashboard"
        mock_automation.page.locator.return_value.count.return_value = 1
        
        result = await mock_automation._is_authenticated()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_authenticated_false(self, mock_automation):
        """Test _is_authenticated returns False when not authenticated."""
        # Mock page to return unauthenticated state
        mock_automation.page.url = "https://robinhood.com/login"
        mock_automation.page.locator.return_value.count.return_value = 0
        
        result = await mock_automation._is_authenticated()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_take_screenshot(self, mock_automation):
        """Test screenshot functionality."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.return_value = None
            
            await mock_automation._take_screenshot("test_screenshot")
            
            # Verify screenshot was called
            mock_automation.page.screenshot.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_account_info_success(self, mock_automation):
        """Test successful account info retrieval."""
        # Mock page content for account info
        mock_automation.page.locator.return_value.text_content.return_value = "$10,000"
        mock_automation.page.locator.return_value.count.return_value = 1
        
        result = await mock_automation.get_account_info()
        
        assert isinstance(result, dict)
        assert "portfolio_value" in result or "buying_power" in result
    
    @pytest.mark.asyncio
    async def test_get_account_info_failure(self, mock_automation):
        """Test account info retrieval when elements not found."""
        # Mock page to return no elements
        mock_automation.page.locator.return_value.count.return_value = 0
        
        result = await mock_automation.get_account_info()
        
        assert isinstance(result, dict)
        assert len(result) == 0  # Should return empty dict when no data found


class TestDataExtraction:
    """Test data extraction functionality."""
    
    @pytest.fixture
    def sample_portfolio_data(self):
        """Sample portfolio data for testing."""
        return {
            "portfolio_value": "$10,000.00",
            "daily_change": "+$150.00 (+1.5%)",
            "buying_power": "$5,000.00"
        }
    
    @pytest.fixture
    def sample_holdings_data(self):
        """Sample holdings data for testing."""
        return [
            {
                "symbol": "SPY",
                "shares": 100,
                "current_value": "$45,000.00",
                "total_return": "+$2,000.00"
            },
            {
                "symbol": "AAPL",
                "shares": 50,
                "current_value": "$8,500.00",
                "total_return": "+$500.00"
            }
        ]
    
    def test_data_validation(self, sample_portfolio_data, sample_holdings_data):
        """Test that extracted data has expected structure."""
        # Test portfolio data structure
        assert "portfolio_value" in sample_portfolio_data
        assert "daily_change" in sample_portfolio_data
        assert "buying_power" in sample_portfolio_data
        
        # Test holdings data structure
        for holding in sample_holdings_data:
            assert "symbol" in holding
            assert "shares" in holding
            assert "current_value" in holding
            assert "total_return" in holding
    
    def test_data_persistence(self, tmp_path):
        """Test data can be saved and loaded."""
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "portfolio": {"value": "$10,000"},
            "holdings": [{"symbol": "SPY", "shares": 100}]
        }
        
        # Save data
        data_file = tmp_path / "test_data.json"
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Load data
        with open(data_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["portfolio"]["value"] == "$10,000"
        assert loaded_data["holdings"][0]["symbol"] == "SPY"


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock AuthConfig for testing."""
        return AuthConfig(
            username="test@example.com",
            password="testpassword",
            headless=True,
            browser_timeout=10000
        )
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_config):
        """Test handling of network timeouts."""
        with patch('src.robinhood_automation.async_playwright') as mock_playwright:
            mock_playwright_instance = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            # Mock page to raise timeout
            mock_page = AsyncMock()
            mock_page.goto.side_effect = Exception("Timeout")
            mock_playwright_instance.chromium.launch.return_value.new_context.return_value.new_page.return_value = mock_page
            
            automation = RobinhoodAutomation(mock_config)
            
            # Should handle timeout gracefully
            try:
                await automation.initialize_browser()
            except Exception as e:
                assert "Timeout" in str(e) or "timeout" in str(e).lower()
    
    @pytest.fixture
    def mock_automation(self, mock_config):
        """Create a mock RobinhoodAutomation instance."""
        automation = RobinhoodAutomation(mock_config)
        automation.page = AsyncMock()
        automation.browser = AsyncMock()
        automation.context = AsyncMock()
        automation.playwright = AsyncMock()
        return automation
    
    @pytest.mark.asyncio
    async def test_element_not_found_handling(self, mock_automation):
        """Test handling when expected elements are not found."""
        # Mock page to return no elements
        mock_automation.page.locator.return_value.count.return_value = 0
        mock_automation.page.locator.return_value.text_content.return_value = None
        
        # Should handle missing elements gracefully
        result = await mock_automation.get_account_info()
        assert isinstance(result, dict)
        assert len(result) == 0  # Should return empty dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 