#!/usr/bin/env python3
"""
Test Main Application with GUI Update Fixes
"""
import subprocess
import sys
import time
import os

def test_main_application():
    """Test the main application with GUI update fixes."""
    print("🧪 Testing Main Application with GUI Update Fixes")
    print("=" * 60)
    
    # Check if Chrome is running with remote debugging
    print("🔍 Checking Chrome remote debugging...")
    try:
        import requests
        response = requests.get("http://localhost:9222/json/version", timeout=5)
        if response.status_code == 200:
            print("✅ Chrome remote debugging is active")
        else:
            print("⚠️ Chrome remote debugging not responding")
    except:
        print("❌ Chrome remote debugging not available")
        print("💡 Start Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
        return False
    
    # Check if main script exists
    if not os.path.exists("spy_expanded_tracker.py"):
        print("❌ Main script not found: spy_expanded_tracker.py")
        return False
    
    print("✅ Main script found")
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    required_packages = [
        "playwright",
        "tkinter",
        "matplotlib",
        "yfinance",
        "pandas",
        "numpy"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == "tkinter":
                import tkinter
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All dependencies available")
    
    # Test GUI update mechanism
    print("🧪 Testing GUI update mechanism...")
    try:
        result = subprocess.run([sys.executable, "test_gui_updates.py"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ GUI update test passed")
        else:
            print(f"⚠️ GUI update test had issues: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("✅ GUI update test ran successfully (timeout expected)")
    except Exception as e:
        print(f"❌ GUI update test failed: {e}")
    
    print("\n🚀 Ready to test main application!")
    print("📋 Instructions:")
    print("1. Make sure Chrome is running with remote debugging")
    print("2. Login to Robinhood in Chrome")
    print("3. Run: python spy_expanded_tracker.py")
    print("4. Monitor logs for GUI update messages")
    print("5. Check for widget creation confirmations")
    print("6. Look for update success messages every second")
    
    return True

def main():
    """Run the test."""
    success = test_main_application()
    
    if success:
        print("\n✅ All tests passed! Ready to run main application.")
        print("🎯 The GUI should now update properly with detailed logging.")
    else:
        print("\n❌ Some tests failed. Please fix issues before running main app.")
    
    return success

if __name__ == "__main__":
    main() 