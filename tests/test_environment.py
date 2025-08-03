#!/usr/bin/env python3
"""
Comprehensive environment test for RobinhoodBot
Tests all dependencies, system requirements, and basic functionality
"""
import sys
import os
import asyncio
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# Test imports for all major dependencies
def test_core_dependencies():
    """Test core Python dependencies."""
    print("🧪 Testing Core Dependencies...")
    
    dependencies = {
        "asyncio": "Async I/O support",
        "json": "JSON data handling",
        "pathlib": "Path handling",
        "datetime": "Date/time handling",
        "numpy": "Numerical computing",
        "pandas": "Data manipulation"
    }
    
    results = {}
    for dep, description in dependencies.items():
        try:
            __import__(dep)
            results[dep] = {"status": "✅", "description": description}
            print(f"  ✅ {dep}: {description}")
        except ImportError as e:
            results[dep] = {"status": "❌", "description": description, "error": str(e)}
            print(f"  ❌ {dep}: {description} - {e}")
    
    return results

def test_automation_dependencies():
    """Test automation and web scraping dependencies."""
    print("\n🤖 Testing Automation Dependencies...")
    
    dependencies = {
        "playwright": "Web automation",
        "cryptography": "Encryption utilities",
        "python-dotenv": "Environment variables"
    }
    
    results = {}
    for dep, description in dependencies.items():
        try:
            __import__(dep)
            results[dep] = {"status": "✅", "description": description}
            print(f"  ✅ {dep}: {description}")
        except ImportError as e:
            results[dep] = {"status": "❌", "description": description, "error": str(e)}
            print(f"  ❌ {dep}: {description} - {e}")
    
    return results

def test_financial_dependencies():
    """Test financial and technical analysis dependencies."""
    print("\n📈 Testing Financial Dependencies...")
    
    dependencies = {
        "yfinance": "Yahoo Finance data",
        "talib": "Technical Analysis Library",
        "mplfinance": "Financial plotting",
        "plotly": "Interactive plotting",
        "scikit-learn": "Machine learning"
    }
    
    results = {}
    for dep, description in dependencies.items():
        try:
            __import__(dep)
            results[dep] = {"status": "✅", "description": description}
            print(f"  ✅ {dep}: {description}")
        except ImportError as e:
            results[dep] = {"status": "❌", "description": description, "error": str(e)}
            print(f"  ❌ {dep}: {description} - {e}")
    
    return results

def test_firebase_dependencies():
    """Test Firebase and cloud storage dependencies."""
    print("\n🔥 Testing Firebase Dependencies...")
    
    dependencies = {
        "firebase_admin": "Firebase Admin SDK",
        "pyrebase": "Pyrebase4 client",
        "google.cloud.firestore": "Firestore client"
    }
    
    results = {}
    for dep, description in dependencies.items():
        try:
            if dep == "google.cloud.firestore":
                from google.cloud import firestore
            else:
                __import__(dep)
            results[dep] = {"status": "✅", "description": description}
            print(f"  ✅ {dep}: {description}")
        except ImportError as e:
            results[dep] = {"status": "❌", "description": description, "error": str(e)}
            print(f"  ❌ {dep}: {description} - {e}")
    
    return results

def test_system_requirements():
    """Test system requirements and capabilities."""
    print("\n💻 Testing System Requirements...")
    
    requirements = {
        "python_version": f"Python {sys.version_info.major}.{sys.version_info.minor}",
        "platform": sys.platform,
        "architecture": sys.maxsize > 2**32 and "64-bit" or "32-bit",
        "async_support": "Async/await support",
        "json_support": "JSON encoding/decoding",
        "file_io": "File I/O operations"
    }
    
    results = {}
    
    # Test Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 8):
        results["python_version"] = {"status": "✅", "version": python_version}
        print(f"  ✅ Python version: {python_version}")
    else:
        results["python_version"] = {"status": "❌", "version": python_version, "error": "Python 3.8+ required"}
        print(f"  ❌ Python version: {python_version} (3.8+ required)")
    
    # Test platform
    results["platform"] = {"status": "✅", "platform": sys.platform}
    print(f"  ✅ Platform: {sys.platform}")
    
    # Test architecture
    arch = "64-bit" if sys.maxsize > 2**32 else "32-bit"
    results["architecture"] = {"status": "✅", "architecture": arch}
    print(f"  ✅ Architecture: {arch}")
    
    # Test async support
    try:
        asyncio.run(asyncio.sleep(0))
        results["async_support"] = {"status": "✅"}
        print("  ✅ Async/await support")
    except Exception as e:
        results["async_support"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ Async/await support: {e}")
    
    # Test JSON support
    try:
        json.dumps({"test": "data"})
        json.loads('{"test": "data"}')
        results["json_support"] = {"status": "✅"}
        print("  ✅ JSON encoding/decoding")
    except Exception as e:
        results["json_support"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ JSON encoding/decoding: {e}")
    
    # Test file I/O
    try:
        test_file = Path("test_io.tmp")
        test_file.write_text("test")
        test_file.unlink()
        results["file_io"] = {"status": "✅"}
        print("  ✅ File I/O operations")
    except Exception as e:
        results["file_io"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ File I/O operations: {e}")
    
    return results

def test_data_processing():
    """Test data processing capabilities."""
    print("\n📊 Testing Data Processing...")
    
    results = {}
    
    # Test NumPy
    try:
        arr = np.array([1, 2, 3, 4, 5])
        mean = np.mean(arr)
        std = np.std(arr)
        assert mean == 3.0
        assert std > 0
        results["numpy"] = {"status": "✅", "mean": mean, "std": std}
        print(f"  ✅ NumPy: mean={mean}, std={std:.2f}")
    except Exception as e:
        results["numpy"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ NumPy: {e}")
    
    # Test Pandas
    try:
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5),
            'price': [100, 101, 102, 99, 98],
            'volume': [1000, 1100, 1200, 900, 800]
        })
        assert len(df) == 5
        assert df['price'].mean() == 100.0
        results["pandas"] = {"status": "✅", "rows": len(df), "columns": len(df.columns)}
        print(f"  ✅ Pandas: {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        results["pandas"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ Pandas: {e}")
    
    # Test JSON data handling
    try:
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "prices": [100, 101, 102, 99, 98],
            "metadata": {"symbol": "SPY", "interval": "1m"}
        }
        json_str = json.dumps(test_data)
        loaded_data = json.loads(json_str)
        assert loaded_data["metadata"]["symbol"] == "SPY"
        assert len(loaded_data["prices"]) == 5
        results["json_processing"] = {"status": "✅", "data_size": len(json_str)}
        print(f"  ✅ JSON processing: {len(json_str)} bytes")
    except Exception as e:
        results["json_processing"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ JSON processing: {e}")
    
    return results

def test_technical_analysis():
    """Test technical analysis capabilities."""
    print("\n📈 Testing Technical Analysis...")
    
    results = {}
    
    # Test TA-Lib
    try:
        import talib
        # Sample price data
        close_prices = np.array([100, 101, 102, 99, 98, 103, 105, 107, 106, 108], dtype=float)
        
        # Calculate SMA
        sma = talib.SMA(close_prices, timeperiod=5)
        assert len(sma) == len(close_prices)
        assert not np.isnan(sma[-1])  # Last value should be calculated
        
        # Calculate RSI
        rsi = talib.RSI(close_prices, timeperiod=5)
        assert len(rsi) == len(close_prices)
        assert 0 <= rsi[-1] <= 100  # RSI should be between 0 and 100
        
        results["talib"] = {"status": "✅", "sma": sma[-1], "rsi": rsi[-1]}
        print(f"  ✅ TA-Lib: SMA={sma[-1]:.2f}, RSI={rsi[-1]:.2f}")
    except Exception as e:
        results["talib"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ TA-Lib: {e}")
    
    # Test yfinance
    try:
        import yfinance as yf
        # Test basic functionality (without actual network call)
        ticker = yf.Ticker("SPY")
        assert ticker.ticker == "SPY"
        results["yfinance"] = {"status": "✅", "ticker": "SPY"}
        print("  ✅ yfinance: Ticker object created")
    except Exception as e:
        results["yfinance"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ yfinance: {e}")
    
    return results

def test_automation_capabilities():
    """Test automation capabilities."""
    print("\n🤖 Testing Automation Capabilities...")
    
    results = {}
    
    # Test Playwright
    try:
        from playwright.async_api import async_playwright
        results["playwright"] = {"status": "✅", "module": "async_playwright"}
        print("  ✅ Playwright: async_playwright imported")
    except Exception as e:
        results["playwright"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ Playwright: {e}")
    
    # Test cryptography
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        cipher = Fernet(key)
        test_data = b"test data"
        encrypted = cipher.encrypt(test_data)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == test_data
        results["cryptography"] = {"status": "✅", "key_length": len(key)}
        print(f"  ✅ Cryptography: {len(key)}-byte key generated")
    except Exception as e:
        results["cryptography"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ Cryptography: {e}")
    
    return results

def test_project_structure():
    """Test project structure and file organization."""
    print("\n📁 Testing Project Structure...")
    
    results = {}
    
    # Check for required directories
    required_dirs = ["src", "tests", "data", "logs", "config"]
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            results[f"dir_{dir_name}"] = {"status": "✅", "path": str(dir_path)}
            print(f"  ✅ Directory: {dir_name}")
        else:
            results[f"dir_{dir_name}"] = {"status": "❌", "path": str(dir_path)}
            print(f"  ❌ Directory: {dir_name} (missing)")
    
    # Check for required files
    required_files = [
        "requirements.txt",
        "main.py",
        "src/robinhood_automation.py",
        "tests/__init__.py"
    ]
    
    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists() and file_path.is_file():
            size = file_path.stat().st_size
            results[f"file_{file_name}"] = {"status": "✅", "size": size}
            print(f"  ✅ File: {file_name} ({size} bytes)")
        else:
            results[f"file_{file_name}"] = {"status": "❌", "path": str(file_path)}
            print(f"  ❌ File: {file_name} (missing)")
    
    return results

def test_environment_variables():
    """Test environment variable handling."""
    print("\n🔧 Testing Environment Variables...")
    
    results = {}
    
    # Test python-dotenv
    try:
        from dotenv import load_dotenv
        # Try to load .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv()
            results["dotenv"] = {"status": "✅", "env_file": "loaded"}
            print("  ✅ python-dotenv: .env file loaded")
        else:
            results["dotenv"] = {"status": "⚠️", "env_file": "not found"}
            print("  ⚠️ python-dotenv: .env file not found")
    except Exception as e:
        results["dotenv"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ python-dotenv: {e}")
    
    # Test environment variable access
    try:
        test_var = os.getenv("TEST_VAR", "default_value")
        assert test_var == "default_value"
        results["env_access"] = {"status": "✅", "test_var": test_var}
        print("  ✅ Environment variable access")
    except Exception as e:
        results["env_access"] = {"status": "❌", "error": str(e)}
        print(f"  ❌ Environment variable access: {e}")
    
    return results

def generate_test_report(all_results):
    """Generate a comprehensive test report."""
    print("\n" + "="*60)
    print("📋 ENVIRONMENT TEST REPORT")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    warnings = 0
    
    for category, results in all_results.items():
        print(f"\n{category.upper()}:")
        print("-" * len(category))
        
        for test_name, result in results.items():
            total_tests += 1
            status = result["status"]
            
            if status == "✅":
                passed_tests += 1
                print(f"  ✅ {test_name}")
            elif status == "❌":
                failed_tests += 1
                print(f"  ❌ {test_name}")
                if "error" in result:
                    print(f"      Error: {result['error']}")
            elif status == "⚠️":
                warnings += 1
                print(f"  ⚠️ {test_name}")
                if "env_file" in result:
                    print(f"      Note: {result['env_file']}")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests} ✅")
    print(f"  Failed: {failed_tests} ❌")
    print(f"  Warnings: {warnings} ⚠️")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"  Success Rate: {success_rate:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 All critical tests passed! Environment is ready for development.")
        return True
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed. Please check the errors above.")
        return False

def main():
    """Run all environment tests."""
    print("🧪 RobinhoodBot Environment Test Suite")
    print("=" * 50)
    
    all_results = {
        "Core Dependencies": test_core_dependencies(),
        "Automation Dependencies": test_automation_dependencies(),
        "Financial Dependencies": test_financial_dependencies(),
        "Firebase Dependencies": test_firebase_dependencies(),
        "System Requirements": test_system_requirements(),
        "Data Processing": test_data_processing(),
        "Technical Analysis": test_technical_analysis(),
        "Automation Capabilities": test_automation_capabilities(),
        "Project Structure": test_project_structure(),
        "Environment Variables": test_environment_variables()
    }
    
    success = generate_test_report(all_results)
    
    # Save results to file
    timestamp = datetime.now().isoformat()
    report_data = {
        "timestamp": timestamp,
        "results": all_results,
        "success": success
    }
    
    report_file = Path("environment_test_report.json")
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 