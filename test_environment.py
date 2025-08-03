#!/usr/bin/env python3
"""
Environment Test Script
Tests all installed libraries to ensure they are working correctly.
"""

import sys
import traceback

def test_library(library_name, import_statement):
    """Test if a library can be imported successfully."""
    try:
        exec(import_statement)
        print(f"✅ {library_name}: Successfully imported")
        return True
    except ImportError as e:
        print(f"❌ {library_name}: Import failed - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {library_name}: Import warning - {e}")
        return False

def main():
    """Run all library tests."""
    print("🧪 Testing Python Environment for RobinhoodBot")
    print("=" * 50)
    
    # Track successful imports
    successful_imports = 0
    total_tests = 0
    
    # Test screen automation libraries
    print("\n📱 Screen Automation Libraries:")
    libraries = [
        ("Playwright", "from playwright.sync_api import sync_playwright"),
    ]
    
    for lib_name, import_stmt in libraries:
        total_tests += 1
        if test_library(lib_name, import_stmt):
            successful_imports += 1
    
    # Test data processing libraries
    print("\n📊 Data Processing Libraries:")
    libraries = [
        ("NumPy", "import numpy as np"),
        ("Pandas", "import pandas as pd"),
    ]
    
    for lib_name, import_stmt in libraries:
        total_tests += 1
        if test_library(lib_name, import_stmt):
            successful_imports += 1
    
    # Test technical analysis libraries
    print("\n📈 Technical Analysis Libraries:")
    libraries = [
        ("TA-Lib", "import talib"),
        ("yfinance", "import yfinance as yf"),
        ("matplotlib", "import matplotlib.pyplot as plt"),
        ("seaborn", "import seaborn as sns"),
        ("scikit-learn", "from sklearn.ensemble import RandomForestClassifier"),
        ("mplfinance", "import mplfinance as mpf"),
        ("plotly", "import plotly.graph_objects as go"),
        ("dash", "import dash"),
    ]
    
    for lib_name, import_stmt in libraries:
        total_tests += 1
        if test_library(lib_name, import_stmt):
            successful_imports += 1
    
    # Test Firebase connectivity
    print("\n🔥 Firebase Libraries:")
    libraries = [
        ("Firebase Admin", "import firebase_admin"),
        ("Pyrebase4", "import pyrebase"),
        ("Google Cloud Firestore", "from google.cloud import firestore"),
    ]
    
    for lib_name, import_stmt in libraries:
        total_tests += 1
        if test_library(lib_name, import_stmt):
            successful_imports += 1
    
    # Test utility libraries
    print("\n🛠️  Utility Libraries:")
    libraries = [
        ("python-dotenv", "from dotenv import load_dotenv"),
        ("schedule", "import schedule"),
        ("APScheduler", "from apscheduler.schedulers.blocking import BlockingScheduler"),
    ]
    
    for lib_name, import_stmt in libraries:
        total_tests += 1
        if test_library(lib_name, import_stmt):
            successful_imports += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {successful_imports}/{total_tests} libraries successfully imported")
    
    if successful_imports == total_tests:
        print("🎉 All libraries are working correctly!")
        print("✅ Environment setup complete and ready for development.")
        return True
    else:
        failed = total_tests - successful_imports
        print(f"⚠️  {failed} libraries failed to import.")
        print("❌ Please check the installation of failed libraries.")
        return False

def test_playwright_browsers():
    """Test if Playwright browsers are installed."""
    print("\n🌐 Testing Playwright Browser Installation:")
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Test Chromium
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://example.com")
                print("✅ Chromium: Browser launched successfully")
                browser.close()
            except Exception as e:
                print(f"❌ Chromium: Failed - {e}")
            
            # Test Firefox
            try:
                browser = p.firefox.launch(headless=True)
                page = browser.new_page()
                page.goto("https://example.com")
                print("✅ Firefox: Browser launched successfully")
                browser.close()
            except Exception as e:
                print(f"❌ Firefox: Failed - {e}")
                
            # Test WebKit
            try:
                browser = p.webkit.launch(headless=True)
                page = browser.new_page()
                page.goto("https://example.com")
                print("✅ WebKit: Browser launched successfully")
                browser.close()
            except Exception as e:
                print(f"❌ WebKit: Failed - {e}")
                
    except Exception as e:
        print(f"❌ Playwright test failed: {e}")

def test_sample_functionality():
    """Test basic functionality with sample data."""
    print("\n🔬 Testing Sample Functionality:")
    
    try:
        # Test data processing
        import pandas as pd
        import numpy as np
        
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'price': np.random.randn(10) * 10 + 100
        })
        print("✅ Pandas: Sample DataFrame created successfully")
        
        # Test technical analysis
        import yfinance as yf
        # Note: This requires internet connection
        # ticker = yf.Ticker("AAPL")
        # data = ticker.history(period="5d")
        print("✅ yfinance: Library loaded (skipping data fetch test)")
        
        # Test TA-Lib with sample data
        import talib
        close_prices = np.array([100, 101, 102, 99, 98, 103, 105, 107, 106, 108], dtype=float)
        sma = talib.SMA(close_prices, timeperiod=5)
        print("✅ TA-Lib: SMA calculation successful")
        
    except Exception as e:
        print(f"❌ Sample functionality test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print(f"Python Version: {sys.version}")
    print(f"Python Path: {sys.executable}")
    
    success = main()
    test_playwright_browsers()
    test_sample_functionality()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
