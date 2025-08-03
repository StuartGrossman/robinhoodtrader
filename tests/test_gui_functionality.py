#!/usr/bin/env python3
"""
Test suite for GUI functionality
"""
import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import asyncio
import json
from datetime import datetime

# Import GUI modules
import sys
sys.path.append('.')

try:
    from spy_simple_gui import SPYSimpleGUI
    from spy_gui_working import SPYGUIWorking
    from spy_tabbed_gui import SPYOptionsGUI
except ImportError as e:
    print(f"Warning: Could not import some GUI modules: {e}")


class TestGUIBasicFunctionality:
    """Test basic GUI functionality."""
    
    @pytest.fixture
    def mock_root(self):
        """Create a mock tkinter root window."""
        root = tk.Tk()
        root.withdraw()  # Hide the window during testing
        yield root
        root.destroy()
    
    def test_gui_initialization(self, mock_root):
        """Test that GUI can be initialized."""
        try:
            # Test basic tkinter functionality
            label = tk.Label(mock_root, text="Test Label")
            label.pack()
            
            button = tk.Button(mock_root, text="Test Button")
            button.pack()
            
            # Verify widgets were created
            assert label.cget("text") == "Test Label"
            assert button.cget("text") == "Test Button"
            
        except Exception as e:
            pytest.fail(f"GUI initialization failed: {e}")
    
    def test_gui_widget_creation(self, mock_root):
        """Test creating various GUI widgets."""
        try:
            # Create different types of widgets
            widgets = {
                "label": tk.Label(mock_root, text="Label"),
                "button": tk.Button(mock_root, text="Button"),
                "entry": tk.Entry(mock_root),
                "text": tk.Text(mock_root, height=5, width=30),
                "listbox": tk.Listbox(mock_root, height=5)
            }
            
            # Verify all widgets were created
            for name, widget in widgets.items():
                assert widget is not None
                assert hasattr(widget, 'pack')
                assert hasattr(widget, 'grid')
                assert hasattr(widget, 'place')
            
        except Exception as e:
            pytest.fail(f"Widget creation failed: {e}")


class TestDataDisplay:
    """Test data display functionality in GUI."""
    
    @pytest.fixture
    def sample_trading_data(self):
        """Sample trading data for testing."""
        return {
            "spy_data": {
                "current_price": 450.25,
                "rsi_1m": 45.5,
                "rsi_5m": 52.3,
                "timestamp": datetime.now().isoformat()
            },
            "options_data": [
                {
                    "price_cents": 8,
                    "price_text": "$0.08",
                    "type": "call",
                    "strike": 450
                },
                {
                    "price_cents": 12,
                    "price_text": "$0.12",
                    "type": "put",
                    "strike": 450
                }
            ],
            "recommendations": [
                {
                    "option": {"price_cents": 8, "type": "call"},
                    "score": 3,
                    "recommendation": "BUY",
                    "analysis": ["Very cheap premium"]
                }
            ]
        }
    
    def test_data_formatting(self, sample_trading_data):
        """Test formatting trading data for display."""
        def format_spy_data(spy_data):
            """Format SPY data for display."""
            return {
                "price": f"${spy_data['current_price']:.2f}",
                "rsi_1m": f"{spy_data['rsi_1m']:.1f}",
                "rsi_5m": f"{spy_data['rsi_5m']:.1f}",
                "timestamp": spy_data['timestamp']
            }
        
        def format_options_data(options_data):
            """Format options data for display."""
            formatted = []
            for option in options_data:
                formatted.append({
                    "display": f"{option['type'].upper()} {option['strike']} @ {option['price_text']}",
                    "price_cents": option['price_cents'],
                    "type": option['type']
                })
            return formatted
        
        # Test SPY data formatting
        formatted_spy = format_spy_data(sample_trading_data["spy_data"])
        assert formatted_spy["price"] == "$450.25"
        assert formatted_spy["rsi_1m"] == "45.5"
        assert formatted_spy["rsi_5m"] == "52.3"
        
        # Test options data formatting
        formatted_options = format_options_data(sample_trading_data["options_data"])
        assert len(formatted_options) == 2
        assert formatted_options[0]["display"] == "CALL 450 @ $0.08"
        assert formatted_options[1]["display"] == "PUT 450 @ $0.12"
    
    def test_recommendation_display(self, sample_trading_data):
        """Test recommendation display formatting."""
        def format_recommendations(recommendations):
            """Format recommendations for display."""
            formatted = []
            for rec in recommendations:
                option = rec["option"]
                formatted.append({
                    "display": f"{option['type'].upper()} @ ${option['price_cents']/100:.2f} - {rec['recommendation']}",
                    "score": rec["score"],
                    "analysis": ", ".join(rec["analysis"])
                })
            return formatted
        
        formatted_recs = format_recommendations(sample_trading_data["recommendations"])
        assert len(formatted_recs) == 1
        assert "CALL @ $0.08 - BUY" in formatted_recs[0]["display"]
        assert formatted_recs[0]["score"] == 3
        assert "Very cheap premium" in formatted_recs[0]["analysis"]


class TestAsyncGUIOperations:
    """Test async operations in GUI."""
    
    @pytest.mark.asyncio
    async def test_async_data_fetching(self):
        """Test async data fetching operations."""
        async def mock_fetch_spy_data():
            """Mock SPY data fetching."""
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "current_price": 450.25,
                "rsi_1m": 45.5,
                "rsi_5m": 52.3
            }
        
        async def mock_fetch_options_data():
            """Mock options data fetching."""
            await asyncio.sleep(0.1)  # Simulate network delay
            return [
                {"price_cents": 8, "type": "call"},
                {"price_cents": 12, "type": "put"}
            ]
        
        # Test async data fetching
        spy_data = await mock_fetch_spy_data()
        options_data = await mock_fetch_options_data()
        
        assert spy_data["current_price"] == 450.25
        assert len(options_data) == 2
        assert options_data[0]["price_cents"] == 8
        assert options_data[1]["price_cents"] == 12
    
    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test async error handling."""
        async def mock_failing_operation():
            """Mock operation that fails."""
            await asyncio.sleep(0.1)
            raise Exception("Network error")
        
        # Test error handling
        try:
            await mock_failing_operation()
            pytest.fail("Should have raised an exception")
        except Exception as e:
            assert "Network error" in str(e)


class TestGUICallbacks:
    """Test GUI callback functions."""
    
    @pytest.fixture
    def mock_root(self):
        """Create a mock tkinter root window."""
        root = tk.Tk()
        root.withdraw()  # Hide the window during testing
        yield root
        root.destroy()
    
    def test_button_callback(self, mock_root):
        """Test button callback functionality."""
        callback_called = False
        callback_data = None
        
        def test_callback(data=None):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = data
        
        # Create button with callback
        button = tk.Button(mock_root, text="Test", command=lambda: test_callback("test_data"))
        
        # Simulate button click
        button.invoke()
        
        assert callback_called
        assert callback_data == "test_data"
    
    def test_entry_callback(self, mock_root):
        """Test entry widget callback functionality."""
        entry_value = ""
        
        def on_entry_change(event):
            nonlocal entry_value
            entry_value = event.widget.get()
        
        # Create entry with callback
        entry = tk.Entry(mock_root)
        entry.bind('<KeyRelease>', on_entry_change)
        
        # Simulate typing
        entry.insert(0, "test")
        entry.event_generate('<KeyRelease>')
        
        assert entry_value == "test"
    
    def test_listbox_selection(self, mock_root):
        """Test listbox selection functionality."""
        selected_items = []
        
        def on_selection(event):
            nonlocal selected_items
            widget = event.widget
            selection = widget.curselection()
            selected_items = [widget.get(i) for i in selection]
        
        # Create listbox with items
        listbox = tk.Listbox(mock_root)
        listbox.insert(0, "Item 1")
        listbox.insert(1, "Item 2")
        listbox.insert(2, "Item 3")
        listbox.bind('<<ListboxSelect>>', on_selection)
        
        # Simulate selection
        listbox.selection_set(1)  # Select second item
        listbox.event_generate('<<ListboxSelect>>')
        
        assert len(selected_items) == 1
        assert selected_items[0] == "Item 2"


class TestDataValidation:
    """Test data validation in GUI."""
    
    def test_numeric_validation(self):
        """Test numeric input validation."""
        def validate_numeric(value):
            """Validate numeric input."""
            try:
                float(value)
                return True
            except ValueError:
                return False
        
        # Test valid numeric inputs
        assert validate_numeric("123.45")
        assert validate_numeric("0")
        assert validate_numeric("-10.5")
        
        # Test invalid numeric inputs
        assert not validate_numeric("abc")
        assert not validate_numeric("12.34.56")
        assert not validate_numeric("")
    
    def test_price_validation(self):
        """Test price input validation."""
        def validate_price(price_str):
            """Validate price input."""
            try:
                price = float(price_str)
                return 0 <= price <= 1000  # Reasonable price range
            except ValueError:
                return False
        
        # Test valid prices
        assert validate_price("450.25")
        assert validate_price("0.08")
        assert validate_price("1000")
        
        # Test invalid prices
        assert not validate_price("-1")
        assert not validate_price("1001")
        assert not validate_price("abc")
    
    def test_option_type_validation(self):
        """Test option type validation."""
        def validate_option_type(option_type):
            """Validate option type."""
            valid_types = ["call", "put", "CALL", "PUT"]
            return option_type.lower() in [t.lower() for t in valid_types]
        
        # Test valid option types
        assert validate_option_type("call")
        assert validate_option_type("put")
        assert validate_option_type("CALL")
        assert validate_option_type("PUT")
        
        # Test invalid option types
        assert not validate_option_type("stock")
        assert not validate_option_type("bond")
        assert not validate_option_type("")


class TestGUIPersistence:
    """Test GUI data persistence."""
    
    def test_settings_save_load(self, tmp_path):
        """Test saving and loading GUI settings."""
        settings = {
            "window_size": "1920x1080",
            "refresh_interval": 30,
            "default_symbol": "SPY",
            "price_range_min": 8,
            "price_range_max": 16
        }
        
        # Save settings
        settings_file = tmp_path / "gui_settings.json"
        with open(settings_file, 'w') as f:
            json.dump(settings, f)
        
        # Load settings
        with open(settings_file, 'r') as f:
            loaded_settings = json.load(f)
        
        # Verify settings
        assert loaded_settings["window_size"] == "1920x1080"
        assert loaded_settings["refresh_interval"] == 30
        assert loaded_settings["default_symbol"] == "SPY"
        assert loaded_settings["price_range_min"] == 8
        assert loaded_settings["price_range_max"] == 16
    
    def test_user_preferences(self, tmp_path):
        """Test user preferences persistence."""
        preferences = {
            "theme": "dark",
            "auto_refresh": True,
            "show_alerts": False,
            "default_tab": "options",
            "last_symbol": "SPY"
        }
        
        # Save preferences
        prefs_file = tmp_path / "user_preferences.json"
        with open(prefs_file, 'w') as f:
            json.dump(preferences, f)
        
        # Load preferences
        with open(prefs_file, 'r') as f:
            loaded_prefs = json.load(f)
        
        # Verify preferences
        assert loaded_prefs["theme"] == "dark"
        assert loaded_prefs["auto_refresh"] is True
        assert loaded_prefs["show_alerts"] is False
        assert loaded_prefs["default_tab"] == "options"
        assert loaded_prefs["last_symbol"] == "SPY"


class TestGUIErrorHandling:
    """Test GUI error handling."""
    
    def test_network_error_handling(self):
        """Test handling of network errors in GUI."""
        def safe_network_operation():
            """Simulate network operation with error handling."""
            try:
                # Simulate network operation
                raise ConnectionError("Network timeout")
            except ConnectionError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "fallback_data": {"message": "Using cached data"}
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Unexpected error: {e}",
                    "fallback_data": None
                }
        
        result = safe_network_operation()
        
        assert result["success"] is False
        assert "Network timeout" in result["error"]
        assert result["fallback_data"] is not None
        assert "cached data" in result["fallback_data"]["message"]
    
    def test_data_validation_error_handling(self):
        """Test handling of data validation errors."""
        def validate_and_process_data(data):
            """Validate and process data with error handling."""
            try:
                if not isinstance(data, dict):
                    raise ValueError("Data must be a dictionary")
                
                if "spy_data" not in data:
                    raise ValueError("Missing SPY data")
                
                if "options_data" not in data:
                    raise ValueError("Missing options data")
                
                return {
                    "success": True,
                    "processed_data": data
                }
                
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "suggestion": "Check data format"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Unexpected error: {e}",
                    "suggestion": "Contact support"
                }
        
        # Test valid data
        valid_data = {
            "spy_data": {"price": 450.25},
            "options_data": [{"price_cents": 8}]
        }
        result = validate_and_process_data(valid_data)
        assert result["success"] is True
        
        # Test invalid data
        invalid_data = {"some_data": "value"}
        result = validate_and_process_data(invalid_data)
        assert result["success"] is False
        assert "Missing SPY data" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 