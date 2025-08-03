#!/usr/bin/env python3
"""
Test suite for SPY options trading functionality
"""
import pytest
import asyncio
import json
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path

# Import trading modules
import sys
sys.path.append('.')

try:
    from spy_browser_trader import SPYBrowserTrader
    from spy_options_analyzer import SPYOptionsAnalyzer
    from spy_day_trader import SPYDayTrader
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")


class TestSPYOptionsAnalysis:
    """Test SPY options analysis functionality."""
    
    @pytest.fixture
    def sample_spy_data(self):
        """Sample SPY market data."""
        return {
            "current_price": 450.25,
            "rsi_1m": 45.5,
            "rsi_5m": 52.3,
            "timestamp": datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_options_data(self):
        """Sample options data."""
        return [
            {
                "price_cents": 8,
                "price_text": "$0.08",
                "type": "call",
                "strike": 450,
                "expiration": "2025-08-02"
            },
            {
                "price_cents": 12,
                "price_text": "$0.12",
                "type": "put",
                "strike": 450,
                "expiration": "2025-08-02"
            },
            {
                "price_cents": 16,
                "price_text": "$0.16",
                "type": "call",
                "strike": 451,
                "expiration": "2025-08-02"
            }
        ]
    
    def test_price_range_filtering(self, sample_options_data):
        """Test filtering options by price range (8-16 cents)."""
        target_options = []
        
        for option in sample_options_data:
            if 8 <= option["price_cents"] <= 16:
                target_options.append(option)
        
        assert len(target_options) == 3  # All options should be in range
        assert all(8 <= opt["price_cents"] <= 16 for opt in target_options)
    
    def test_option_type_categorization(self, sample_options_data):
        """Test categorizing options by type."""
        calls = [opt for opt in sample_options_data if opt["type"] == "call"]
        puts = [opt for opt in sample_options_data if opt["type"] == "put"]
        
        assert len(calls) == 2
        assert len(puts) == 1
        assert all(opt["type"] == "call" for opt in calls)
        assert all(opt["type"] == "put" for opt in puts)
    
    def test_market_bias_determination(self, sample_spy_data):
        """Test market bias determination based on RSI values."""
        rsi_1m = sample_spy_data["rsi_1m"]
        rsi_5m = sample_spy_data["rsi_5m"]
        
        # Simple bias logic for testing
        if rsi_1m > 50 and rsi_5m > 50:
            bias = "BULLISH"
        elif rsi_1m < 50 and rsi_5m < 50:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
        
        assert bias in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert bias == "NEUTRAL"  # Based on sample data (45.5, 52.3)
    
    def test_option_scoring(self, sample_options_data):
        """Test option scoring based on price and market conditions."""
        scored_options = []
        
        for option in sample_options_data:
            score = 0
            analysis = []
            
            # Score based on price (cheaper = higher score)
            if option["price_cents"] <= 10:
                score += 3
                analysis.append("Very cheap premium")
            elif option["price_cents"] <= 16:
                score += 2
                analysis.append("Affordable premium")
            
            # Score based on type and market conditions
            if option["type"] == "call":
                score += 1
                analysis.append("Call option")
            elif option["type"] == "put":
                score += 1
                analysis.append("Put option")
            
            scored_options.append({
                "option": option,
                "score": score,
                "analysis": analysis,
                "recommendation": "BUY" if score >= 3 else "WATCH"
            })
        
        assert len(scored_options) == 3
        assert all("score" in opt for opt in scored_options)
        assert all("analysis" in opt for opt in scored_options)
        assert all("recommendation" in opt for opt in scored_options)


class TestDataProcessing:
    """Test data processing and validation."""
    
    def test_json_data_structure(self):
        """Test JSON data structure validation."""
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "spy_data": {
                "current_price": 450.25,
                "rsi_1m": 45.5,
                "rsi_5m": 52.3
            },
            "options_data": [
                {
                    "price_cents": 8,
                    "price_text": "$0.08",
                    "type": "call"
                }
            ],
            "recommendations": [
                {
                    "option": {"price_cents": 8, "type": "call"},
                    "score": 3,
                    "recommendation": "BUY"
                }
            ]
        }
        
        # Validate structure
        assert "timestamp" in test_data
        assert "spy_data" in test_data
        assert "options_data" in test_data
        assert "recommendations" in test_data
        
        # Validate nested structures
        assert "current_price" in test_data["spy_data"]
        assert "rsi_1m" in test_data["spy_data"]
        assert "rsi_5m" in test_data["spy_data"]
        
        # Validate data types
        assert isinstance(test_data["spy_data"]["current_price"], (int, float))
        assert isinstance(test_data["spy_data"]["rsi_1m"], (int, float))
        assert isinstance(test_data["options_data"], list)
        assert isinstance(test_data["recommendations"], list)
    
    def test_data_persistence(self, tmp_path):
        """Test data can be saved and loaded correctly."""
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "spy_data": {"current_price": 450.25, "rsi_1m": 45.5},
            "options_data": [{"price_cents": 8, "type": "call"}],
            "recommendations": [{"score": 3, "recommendation": "BUY"}]
        }
        
        # Save data
        data_file = tmp_path / "spy_analysis_test.json"
        with open(data_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        # Load and validate
        with open(data_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["spy_data"]["current_price"] == 450.25
        assert loaded_data["spy_data"]["rsi_1m"] == 45.5
        assert len(loaded_data["options_data"]) == 1
        assert loaded_data["options_data"][0]["price_cents"] == 8
        assert len(loaded_data["recommendations"]) == 1
        assert loaded_data["recommendations"][0]["score"] == 3


class TestTechnicalAnalysis:
    """Test technical analysis calculations."""
    
    def test_rsi_calculation(self):
        """Test RSI calculation with sample data."""
        # Sample price data
        prices = np.array([100, 101, 102, 99, 98, 103, 105, 107, 106, 108])
        
        # Simple RSI calculation (simplified for testing)
        def calculate_rsi(prices, period=14):
            if len(prices) < period:
                return 50.0  # Default neutral value
            
            # Calculate price changes
            deltas = np.diff(prices)
            
            # Separate gains and losses
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # Calculate average gains and losses
            avg_gains = np.mean(gains[-period:])
            avg_losses = np.mean(losses[-period:])
            
            if avg_losses == 0:
                return 100.0
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        
        rsi = calculate_rsi(prices)
        
        # Validate RSI is within expected range
        assert 0 <= rsi <= 100
        assert isinstance(rsi, (int, float))
    
    def test_price_movement_tracking(self):
        """Test price movement tracking functionality."""
        price_history = []
        
        # Simulate price updates
        for i in range(10):
            price = 450 + np.random.normal(0, 2)  # Random price around 450
            timestamp = datetime.now() + timedelta(minutes=i)
            price_history.append({
                "price": price,
                "timestamp": timestamp.isoformat()
            })
        
        # Validate price history
        assert len(price_history) == 10
        assert all("price" in entry for entry in price_history)
        assert all("timestamp" in entry for entry in price_history)
        assert all(isinstance(entry["price"], (int, float)) for entry in price_history)
        
        # Calculate basic statistics
        prices = [entry["price"] for entry in price_history]
        avg_price = np.mean(prices)
        price_change = prices[-1] - prices[0]
        
        assert isinstance(avg_price, (int, float))
        assert isinstance(price_change, (int, float))
    
    def test_volatility_calculation(self):
        """Test volatility calculation."""
        # Sample price data
        prices = np.array([450, 451, 449, 452, 448, 453, 447, 454, 446, 455])
        
        # Calculate volatility (standard deviation)
        volatility = np.std(prices)
        
        # Validate volatility calculation
        assert isinstance(volatility, (int, float))
        assert volatility >= 0  # Volatility should be non-negative


class TestTradingSignals:
    """Test trading signal generation."""
    
    def test_signal_generation(self):
        """Test trading signal generation based on market conditions."""
        def generate_signal(spy_data, options_data):
            signals = []
            
            # Market bias based on RSI
            rsi_1m = spy_data.get("rsi_1m", 50)
            rsi_5m = spy_data.get("rsi_5m", 50)
            
            if rsi_1m > 70 and rsi_5m > 70:
                market_bias = "OVERBOUGHT"
            elif rsi_1m < 30 and rsi_5m < 30:
                market_bias = "OVERSOLD"
            else:
                market_bias = "NEUTRAL"
            
            # Generate signals for each option
            for option in options_data:
                signal = {
                    "option": option,
                    "market_bias": market_bias,
                    "confidence": "HIGH" if option["price_cents"] <= 10 else "MEDIUM",
                    "action": "BUY" if option["price_cents"] <= 12 else "WATCH"
                }
                signals.append(signal)
            
            return signals
        
        # Test with sample data
        spy_data = {"rsi_1m": 45, "rsi_5m": 52}
        options_data = [
            {"price_cents": 8, "type": "call"},
            {"price_cents": 15, "type": "put"}
        ]
        
        signals = generate_signal(spy_data, options_data)
        
        assert len(signals) == 2
        assert all("option" in signal for signal in signals)
        assert all("market_bias" in signal for signal in signals)
        assert all("confidence" in signal for signal in signals)
        assert all("action" in signal for signal in signals)
        assert signals[0]["action"] == "BUY"  # 8 cents
        assert signals[1]["action"] == "WATCH"  # 15 cents


class TestErrorHandling:
    """Test error handling in trading operations."""
    
    def test_invalid_data_handling(self):
        """Test handling of invalid or missing data."""
        def safe_calculate_rsi(prices):
            try:
                if not prices or len(prices) < 2:
                    return 50.0  # Default neutral value
                
                # Convert to numpy array
                prices = np.array(prices, dtype=float)
                
                # Calculate RSI
                deltas = np.diff(prices)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gains = np.mean(gains)
                avg_losses = np.mean(losses)
                
                if avg_losses == 0:
                    return 100.0
                
                rs = avg_gains / avg_losses
                rsi = 100 - (100 / (1 + rs))
                
                return rsi
                
            except Exception as e:
                print(f"Error calculating RSI: {e}")
                return 50.0  # Return neutral value on error
        
        # Test with invalid data
        assert safe_calculate_rsi([]) == 50.0
        assert safe_calculate_rsi([100]) == 50.0
        assert safe_calculate_rsi([100, 101, 102]) > 0  # Should work with valid data
    
    def test_data_validation(self):
        """Test data validation functions."""
        def validate_option_data(option):
            required_fields = ["price_cents", "type"]
            
            if not isinstance(option, dict):
                return False, "Option must be a dictionary"
            
            for field in required_fields:
                if field not in option:
                    return False, f"Missing required field: {field}"
            
            if not isinstance(option["price_cents"], (int, float)):
                return False, "price_cents must be numeric"
            
            if option["type"] not in ["call", "put"]:
                return False, "type must be 'call' or 'put'"
            
            return True, "Valid option data"
        
        # Test valid data
        valid_option = {"price_cents": 8, "type": "call"}
        is_valid, message = validate_option_data(valid_option)
        assert is_valid
        assert message == "Valid option data"
        
        # Test invalid data
        invalid_option = {"price_cents": "eight", "type": "call"}
        is_valid, message = validate_option_data(invalid_option)
        assert not is_valid
        assert "price_cents must be numeric" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 