#!/usr/bin/env python3
"""
Test runner for RobinhoodBot
Executes all test suites and generates comprehensive reports
"""
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

def run_test_suite(test_file, description):
    """Run a specific test suite and return results."""
    print(f"\n🧪 Running {description}...")
    print("=" * 50)
    
    try:
        # Run pytest on the test file
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=300)
        
        # Parse results
        success = result.returncode == 0
        output = result.stdout
        errors = result.stderr
        
        # Count test results
        passed = output.count("PASSED")
        failed = output.count("FAILED")
        errors_count = output.count("ERROR")
        
        return {
            "success": success,
            "passed": passed,
            "failed": failed,
            "errors": errors_count,
            "output": output,
            "error_output": errors,
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "output": "",
            "error_output": "Test suite timed out after 5 minutes",
            "return_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "output": "",
            "error_output": str(e),
            "return_code": -1
        }

def run_environment_test():
    """Run the comprehensive environment test."""
    print("\n🔧 Running Environment Test...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "tests/test_environment.py"
        ], capture_output=True, text=True, timeout=300)
        
        success = result.returncode == 0
        output = result.stdout
        errors = result.stderr
        
        return {
            "success": success,
            "output": output,
            "error_output": errors,
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error_output": "Environment test timed out after 5 minutes",
            "return_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error_output": str(e),
            "return_code": -1
        }

def check_test_files():
    """Check which test files exist and are ready to run."""
    test_files = {
        "tests/test_robinhood_automation.py": "Robinhood Automation Tests",
        "tests/test_spy_options_trading.py": "SPY Options Trading Tests", 
        "tests/test_gui_functionality.py": "GUI Functionality Tests",
        "tests/test_integration.py": "Integration Tests"
    }
    
    available_tests = {}
    for test_file, description in test_files.items():
        if Path(test_file).exists():
            available_tests[test_file] = description
        else:
            print(f"⚠️ Test file not found: {test_file}")
    
    return available_tests

def generate_summary_report(all_results):
    """Generate a comprehensive summary report."""
    print("\n" + "="*60)
    print("📋 COMPREHENSIVE TEST REPORT")
    print("="*60)
    
    total_suites = len(all_results)
    successful_suites = sum(1 for result in all_results.values() if result["success"])
    total_tests = sum(result.get("passed", 0) + result.get("failed", 0) for result in all_results.values())
    total_passed = sum(result.get("passed", 0) for result in all_results.values())
    total_failed = sum(result.get("failed", 0) for result in all_results.values())
    
    print(f"\n📊 SUMMARY:")
    print(f"  Test Suites: {total_suites}")
    print(f"  Successful Suites: {successful_suites}")
    print(f"  Failed Suites: {total_suites - successful_suites}")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed Tests: {total_passed}")
    print(f"  Failed Tests: {total_failed}")
    
    if total_tests > 0:
        success_rate = (total_passed / total_tests * 100)
        print(f"  Success Rate: {success_rate:.1f}%")
    
    print(f"\n📋 DETAILED RESULTS:")
    for test_name, result in all_results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"\n  {test_name}: {status}")
        
        if "passed" in result and "failed" in result:
            print(f"    Tests: {result['passed']} passed, {result['failed']} failed")
        
        if result.get("error_output"):
            print(f"    Errors: {result['error_output'][:200]}...")
    
    # Overall assessment
    if successful_suites == total_suites and total_failed == 0:
        print(f"\n🎉 EXCELLENT! All test suites passed successfully!")
        return True
    elif successful_suites >= total_suites * 0.8:
        print(f"\n✅ GOOD! Most test suites passed. {total_suites - successful_suites} suite(s) need attention.")
        return True
    else:
        print(f"\n⚠️ NEEDS ATTENTION! {total_suites - successful_suites} test suite(s) failed.")
        return False

def save_detailed_report(all_results):
    """Save detailed test results to JSON file."""
    timestamp = datetime.now().isoformat()
    report_data = {
        "timestamp": timestamp,
        "test_results": all_results,
        "summary": {
            "total_suites": len(all_results),
            "successful_suites": sum(1 for result in all_results.values() if result["success"]),
            "total_tests": sum(result.get("passed", 0) + result.get("failed", 0) for result in all_results.values()),
            "total_passed": sum(result.get("passed", 0) for result in all_results.values()),
            "total_failed": sum(result.get("failed", 0) for result in all_results.values())
        }
    }
    
    report_file = Path("test_results_report.json")
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    return report_file

def main():
    """Run all available tests."""
    print("🚀 RobinhoodBot Test Runner")
    print("=" * 50)
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {Path.cwd()}")
    
    # Check available test files
    available_tests = check_test_files()
    
    if not available_tests:
        print("❌ No test files found! Please ensure test files are in the tests/ directory.")
        return False
    
    print(f"\n📁 Found {len(available_tests)} test suite(s):")
    for test_file, description in available_tests.items():
        print(f"  • {description} ({test_file})")
    
    # Run all test suites
    all_results = {}
    
    # Run environment test first
    env_result = run_environment_test()
    all_results["Environment Test"] = env_result
    
    # Run pytest test suites
    for test_file, description in available_tests.items():
        result = run_test_suite(test_file, description)
        all_results[description] = result
    
    # Generate summary
    overall_success = generate_summary_report(all_results)
    
    # Save detailed report
    report_file = save_detailed_report(all_results)
    
    # Print recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    failed_suites = [name for name, result in all_results.items() if not result["success"]]
    if failed_suites:
        print(f"  • Review failed test suites: {', '.join(failed_suites)}")
        print(f"  • Check detailed error messages in the report")
        print(f"  • Ensure all dependencies are properly installed")
    
    if overall_success:
        print(f"  • All critical tests passed - system is ready for development!")
        print(f"  • Consider running tests regularly during development")
    
    print(f"  • Detailed results available in: {report_file}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 