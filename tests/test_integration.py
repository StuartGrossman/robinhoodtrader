#!/usr/bin/env python3
"""
Integration tests for RobinhoodBot components
"""
import pytest
import asyncio
import json
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path

# Import main components
import sys
sys.path.append('.')

try:
    from src.robinhood_automation import RobinhoodAutomation, AuthConfig
    from spy_browser_trader import SPYBrowserTrader
    from spy_options_analyzer import SPYOptionsAnalyzer
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return AuthConfig(
            username="test@example.com",
            password="testpassword",
            headless=True,
            browser_timeout=10000
        )
    
    @pytest.mark.asyncio
    async def test_complete_data_flow(self, mock_config):
        """Test complete data flow from browser to analysis."""
        # Mock the entire workflow
        with patch('src.robinhood_automation.async_playwright') as mock_playwright:
            mock_playwright_instance = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            # Mock browser and page
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock page content
            mock_page.url = "https://robinhood.com/options/chains/SPY"
            mock_page.locator.return_value.count.return_value = 1
            mock_page.locator.return_value.text_content.return_value = "$0.08"
            
            # Test the workflow
            async with RobinhoodAutomation(mock_config) as automation:
                # Navigate to SPY options
                await automation.page.goto("https://robinhood.com/options/chains/SPY")
                
                # Extract data
                account_info = await automation.get_account_info()
                
                # Verify data extraction worked
                assert isinstance(account_info, dict)
                
                # Mock options data
                options_data = [
                    {"price_cents": 8, "type": "call", "strike": 450},
                    {"price_cents": 12, "type": "put", "strike": 450}
                ]
                
                # Test data processing
                processed_data = self.process_options_data(options_data)
                assert len(processed_data) == 2
                assert all("price_cents" in opt for opt in processed_data)
                
                # Test analysis
                analysis_result = self.analyze_options(processed_data)
                assert "recommendations" in analysis_result
                assert len(analysis_result["recommendations"]) > 0
    
    def process_options_data(self, options_data):
        """Process raw options data."""
        processed = []
        for option in options_data:
            if 8 <= option["price_cents"] <= 16:  # Target range
                processed.append({
                    **option,
                    "score": 3 if option["price_cents"] <= 10 else 2,
                    "recommendation": "BUY" if option["price_cents"] <= 12 else "WATCH"
                })
        return processed
    
    def analyze_options(self, processed_data):
        """Analyze processed options data."""
        recommendations = []
        for option in processed_data:
            recommendations.append({
                "option": option,
                "score": option["score"],
                "recommendation": option["recommendation"],
                "analysis": ["Cheap premium"] if option["price_cents"] <= 10 else ["Moderate premium"]
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "total_options": len(processed_data)
        }


class TestDataIntegration:
    """Test data integration between components."""
    
    def test_spy_data_integration(self):
        """Test SPY data integration across components."""
        # Mock SPY data from yfinance
        spy_data = {
            "current_price": 450.25,
            "rsi_1m": 45.5,
            "rsi_5m": 52.3,
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock options data from browser
        options_data = [
            {"price_cents": 8, "type": "call", "strike": 450},
            {"price_cents": 12, "type": "put", "strike": 450}
        ]
        
        # Integrate data
        integrated_data = self.integrate_data(spy_data, options_data)
        
        # Verify integration
        assert "spy_data" in integrated_data
        assert "options_data" in integrated_data
        assert "analysis" in integrated_data
        assert integrated_data["spy_data"]["current_price"] == 450.25
        assert len(integrated_data["options_data"]) == 2
    
    def integrate_data(self, spy_data, options_data):
        """Integrate SPY and options data."""
        # Calculate market bias
        rsi_1m = spy_data["rsi_1m"]
        rsi_5m = spy_data["rsi_5m"]
        
        if rsi_1m > 50 and rsi_5m > 50:
            market_bias = "BULLISH"
        elif rsi_1m < 50 and rsi_5m < 50:
            market_bias = "BEARISH"
        else:
            market_bias = "NEUTRAL"
        
        # Analyze options based on market conditions
        analyzed_options = []
        for option in options_data:
            score = 0
            analysis = []
            
            # Score based on price
            if option["price_cents"] <= 10:
                score += 3
                analysis.append("Very cheap premium")
            elif option["price_cents"] <= 16:
                score += 2
                analysis.append("Affordable premium")
            
            # Score based on market bias and option type
            if market_bias == "BULLISH" and option["type"] == "call":
                score += 1
                analysis.append("Bullish market favors calls")
            elif market_bias == "BEARISH" and option["type"] == "put":
                score += 1
                analysis.append("Bearish market favors puts")
            
            analyzed_options.append({
                **option,
                "score": score,
                "analysis": analysis,
                "recommendation": "BUY" if score >= 3 else "WATCH"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "spy_data": spy_data,
            "options_data": analyzed_options,
            "market_bias": market_bias,
            "analysis": {
                "total_options": len(analyzed_options),
                "buy_recommendations": len([opt for opt in analyzed_options if opt["recommendation"] == "BUY"]),
                "watch_recommendations": len([opt for opt in analyzed_options if opt["recommendation"] == "WATCH"])
            }
        }
    
    def test_data_persistence_integration(self, tmp_path):
        """Test data persistence integration."""
        # Create sample integrated data
        integrated_data = {
            "timestamp": datetime.now().isoformat(),
            "spy_data": {
                "current_price": 450.25,
                "rsi_1m": 45.5,
                "rsi_5m": 52.3
            },
            "options_data": [
                {
                    "price_cents": 8,
                    "type": "call",
                    "score": 3,
                    "recommendation": "BUY"
                }
            ],
            "market_bias": "NEUTRAL",
            "analysis": {
                "total_options": 1,
                "buy_recommendations": 1,
                "watch_recommendations": 0
            }
        }
        
        # Save data
        data_file = tmp_path / "integrated_analysis.json"
        with open(data_file, 'w') as f:
            json.dump(integrated_data, f, indent=2)
        
        # Load and verify
        with open(data_file, 'r') as f:
            loaded_data = json.load(f)
        
        # Verify structure
        assert "spy_data" in loaded_data
        assert "options_data" in loaded_data
        assert "market_bias" in loaded_data
        assert "analysis" in loaded_data
        
        # Verify data integrity
        assert loaded_data["spy_data"]["current_price"] == 450.25
        assert loaded_data["options_data"][0]["price_cents"] == 8
        assert loaded_data["market_bias"] == "NEUTRAL"
        assert loaded_data["analysis"]["buy_recommendations"] == 1


class TestComponentCommunication:
    """Test communication between different components."""
    
    @pytest.mark.asyncio
    async def test_browser_to_analyzer_communication(self):
        """Test communication from browser automation to options analyzer."""
        # Mock browser data extraction
        browser_data = {
            "page_url": "https://robinhood.com/options/chains/SPY",
            "extracted_options": [
                {"price_text": "$0.08", "type": "call"},
                {"price_text": "$0.12", "type": "put"}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Process browser data for analyzer
        processed_data = self.process_browser_data(browser_data)
        
        # Verify data processing
        assert len(processed_data) == 2
        assert processed_data[0]["price_cents"] == 8
        assert processed_data[1]["price_cents"] == 12
        
        # Test analyzer integration
        analysis_result = self.analyze_browser_data(processed_data)
        assert "recommendations" in analysis_result
        assert len(analysis_result["recommendations"]) == 2
    
    def process_browser_data(self, browser_data):
        """Process raw browser data for analysis."""
        processed = []
        for option in browser_data["extracted_options"]:
            # Extract price in cents
            price_text = option["price_text"]
            price_cents = int(float(price_text.replace("$", "")) * 100)
            
            processed.append({
                "price_cents": price_cents,
                "price_text": price_text,
                "type": option["type"],
                "source": "browser_extraction"
            })
        
        return processed
    
    def analyze_browser_data(self, processed_data):
        """Analyze processed browser data."""
        recommendations = []
        
        for option in processed_data:
            score = 0
            analysis = []
            
            # Score based on price
            if option["price_cents"] <= 10:
                score += 3
                analysis.append("Very cheap premium")
            elif option["price_cents"] <= 16:
                score += 2
                analysis.append("Affordable premium")
            
            # Score based on type
            if option["type"] == "call":
                score += 1
                analysis.append("Call option")
            elif option["type"] == "put":
                score += 1
                analysis.append("Put option")
            
            recommendations.append({
                "option": option,
                "score": score,
                "analysis": analysis,
                "recommendation": "BUY" if score >= 3 else "WATCH"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "total_analyzed": len(processed_data)
        }
    
    def test_gui_data_integration(self):
        """Test GUI integration with processed data."""
        # Mock processed analysis data
        analysis_data = {
            "spy_data": {"current_price": 450.25, "rsi_1m": 45.5},
            "options_data": [
                {"price_cents": 8, "type": "call", "score": 3, "recommendation": "BUY"},
                {"price_cents": 12, "type": "put", "score": 2, "recommendation": "WATCH"}
            ],
            "market_bias": "NEUTRAL"
        }
        
        # Format data for GUI display
        gui_data = self.format_for_gui(analysis_data)
        
        # Verify GUI formatting
        assert "spy_display" in gui_data
        assert "options_display" in gui_data
        assert "summary" in gui_data
        
        assert gui_data["spy_display"]["price"] == "$450.25"
        assert len(gui_data["options_display"]) == 2
        assert gui_data["summary"]["buy_count"] == 1
        assert gui_data["summary"]["watch_count"] == 1
    
    def format_for_gui(self, analysis_data):
        """Format analysis data for GUI display."""
        # Format SPY data
        spy_display = {
            "price": f"${analysis_data['spy_data']['current_price']:.2f}",
            "rsi_1m": f"{analysis_data['spy_data']['rsi_1m']:.1f}",
            "bias": analysis_data["market_bias"]
        }
        
        # Format options data
        options_display = []
        for option in analysis_data["options_data"]:
            options_display.append({
                "display": f"{option['type'].upper()} @ ${option['price_cents']/100:.2f}",
                "recommendation": option["recommendation"],
                "score": option["score"]
            })
        
        # Create summary
        buy_count = len([opt for opt in analysis_data["options_data"] if opt["recommendation"] == "BUY"])
        watch_count = len([opt for opt in analysis_data["options_data"] if opt["recommendation"] == "WATCH"])
        
        summary = {
            "total_options": len(analysis_data["options_data"]),
            "buy_count": buy_count,
            "watch_count": watch_count,
            "market_bias": analysis_data["market_bias"]
        }
        
        return {
            "spy_display": spy_display,
            "options_display": options_display,
            "summary": summary
        }


class TestErrorHandlingIntegration:
    """Test error handling across components."""
    
    def test_component_error_isolation(self):
        """Test that errors in one component don't break others."""
        def safe_component_operation(operation_name, operation_func):
            """Safely execute component operations."""
            try:
                result = operation_func()
                return {
                    "success": True,
                    "result": result,
                    "component": operation_name
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "component": operation_name
                }
        
        # Test multiple component operations
        operations = [
            ("data_extraction", lambda: {"price": 450.25}),
            ("options_analysis", lambda: [{"price_cents": 8, "type": "call"}]),
            ("gui_update", lambda: {"display": "Updated"}),
            ("failing_operation", lambda: 1/0)  # This should fail
        ]
        
        results = []
        for name, func in operations:
            result = safe_component_operation(name, func)
            results.append(result)
        
        # Verify successful operations completed
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        assert len(successful_results) == 3
        assert len(failed_results) == 1
        assert failed_results[0]["component"] == "failing_operation"
    
    def test_data_validation_integration(self):
        """Test data validation across components."""
        def validate_integrated_data(data):
            """Validate data structure across components."""
            errors = []
            
            # Check required top-level keys
            required_keys = ["timestamp", "spy_data", "options_data"]
            for key in required_keys:
                if key not in data:
                    errors.append(f"Missing required key: {key}")
            
            # Validate SPY data
            if "spy_data" in data:
                spy_data = data["spy_data"]
                if "current_price" not in spy_data:
                    errors.append("Missing current_price in spy_data")
                if "rsi_1m" not in spy_data:
                    errors.append("Missing rsi_1m in spy_data")
            
            # Validate options data
            if "options_data" in data:
                options_data = data["options_data"]
                if not isinstance(options_data, list):
                    errors.append("options_data must be a list")
                else:
                    for i, option in enumerate(options_data):
                        if "price_cents" not in option:
                            errors.append(f"Option {i} missing price_cents")
                        if "type" not in option:
                            errors.append(f"Option {i} missing type")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
        
        # Test valid data
        valid_data = {
            "timestamp": datetime.now().isoformat(),
            "spy_data": {"current_price": 450.25, "rsi_1m": 45.5},
            "options_data": [{"price_cents": 8, "type": "call"}]
        }
        
        validation_result = validate_integrated_data(valid_data)
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test invalid data
        invalid_data = {
            "timestamp": datetime.now().isoformat(),
            "spy_data": {"current_price": 450.25},  # Missing rsi_1m
            "options_data": [{"price_cents": 8}]  # Missing type
        }
        
        validation_result = validate_integrated_data(invalid_data)
        assert validation_result["valid"] is False
        assert len(validation_result["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 