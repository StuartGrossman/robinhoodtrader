#!/usr/bin/env python3
"""
RobinhoodBot Launcher
Simple script to run the main SPY options tracker
"""
import sys
import os

def main():
    """Launch the main application."""
    print("🚀 RobinhoodBot - SPY Options Tracker")
    print("=" * 50)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("   Consider running: source venv/bin/activate")
        print()
    
    # Check if Chrome is running with remote debugging
    print("📋 Prerequisites Check:")
    print("   1. Chrome should be running with remote debugging")
    print("   2. You should be logged into Robinhood")
    print("   3. Virtual environment should be activated")
    print()
    
    # Import and run main application
    try:
        from main import main as run_main
        print("✅ Starting SPY Options Tracker...")
        print("   Choose option type when prompted:")
        print("   1. CALLS (expanded contracts)")
        print("   2. PUTS (expanded contracts)")
        print("   3. Both (separate windows)")
        print()
        run_main()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        print("   Check the logs for more details")

if __name__ == "__main__":
    main() 