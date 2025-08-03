#!/usr/bin/env python3
"""
Test script for SPY Expanded Tracker fixes
"""
import asyncio
import sys
import os

# Add the current directory to the path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spy_expanded_tracker import SPYExpandedTerminal

async def test_browser_connection():
    """Test the browser connection logic."""
    print("🧪 Testing browser connection...")
    
    terminal = SPYExpandedTerminal('call')
    
    try:
        # Test the browser connection logic
        await terminal.find_and_expand_contracts()
        print("✅ Browser connection test completed")
    except Exception as e:
        print(f"❌ Browser connection test failed: {e}")
        import traceback
        print(f"📋 Full error: {traceback.format_exc()}")
    finally:
        # Clean up
        if hasattr(terminal, 'playwright') and terminal.playwright:
            await terminal.playwright.stop()

def test_gui_launch():
    """Test GUI launch without browser automation."""
    print("🧪 Testing GUI launch...")
    
    try:
        terminal = SPYExpandedTerminal('call')
        print("✅ GUI created successfully")
        
        # Test basic GUI functionality
        terminal.log("Test log message")
        terminal.update_status("Test status")
        print("✅ Basic GUI functions work")
        
        return terminal
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        import traceback
        print(f"📋 Full error: {traceback.format_exc()}")
        return None

def main():
    """Main test function."""
    print("🚀 SPY Expanded Tracker Fixes Test")
    print("=" * 50)
    
    # Test 1: GUI creation
    terminal = test_gui_launch()
    if not terminal:
        print("❌ GUI test failed, stopping")
        return
    
    # Test 2: Browser connection (async)
    print("\n" + "=" * 50)
    print("Testing browser connection...")
    
    try:
        asyncio.run(test_browser_connection())
    except Exception as e:
        print(f"❌ Async test failed: {e}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main() 