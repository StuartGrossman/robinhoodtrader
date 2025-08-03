#!/usr/bin/env python3
"""
Connect to Existing Chrome Browser
Uses your existing Chrome session with all cookies intact
"""
import asyncio
from playwright.async_api import async_playwright

async def connect_to_chrome():
    """Connect to existing Chrome browser."""
    print("🚀 Connecting to your existing Chrome browser...")
    
    try:
        playwright = await async_playwright().start()
        
        # Connect to existing Chrome instance
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        # Get existing context and page
        contexts = browser.contexts
        if not contexts:
            print("❌ No browser contexts found")
            return None, None, None
        
        context = contexts[0]  # Use first context
        pages = context.pages
        
        if not pages:
            # Create new page if none exist
            page = await context.new_page()
        else:
            page = pages[0]  # Use first page
        
        print("✅ Connected to existing Chrome browser!")
        print(f"📊 Current URL: {page.url}")
        
        return playwright, browser, page
        
    except Exception as e:
        print(f"❌ Could not connect to Chrome: {e}")
        print("💡 Make sure Chrome is running with: --remote-debugging-port=9222")
        return None, None, None

async def navigate_to_spy_options(page):
    """Navigate to SPY options with existing session."""
    print("\n📊 Navigating to SPY options...")
    
    try:
        # Navigate to SPY options
        await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Set zoom for better visibility
        await page.evaluate("document.body.style.zoom = '0.5'")
        
        current_url = page.url
        print(f"✅ Navigated to: {current_url}")
        
        # Check if we're logged in (no login redirect)
        if "login" in current_url:
            print("🔐 Still need to login - please login manually")
            return False
        else:
            print("🎉 Already logged in with existing cookies!")
            return True
            
    except Exception as e:
        print(f"❌ Navigation error: {e}")
        return False

async def main():
    """Main function."""
    print("🚀 SPY Options - Existing Browser Connection")
    print("=" * 50)
    print("📋 First, run this command in a new terminal:")
    print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
    print("   --remote-debugging-port=9222 --user-data-dir=$HOME/chrome_robinhood")
    print("🔐 Then log into Robinhood in that Chrome window")
    print("▶️  Run this script again after you're logged in")
    print("=" * 50)
    
    # Connect to existing browser
    playwright, browser, page = await connect_to_chrome()
    
    if not page:
        print("❌ Could not connect to browser")
        return
    
    try:
        # Navigate to SPY options
        success = await navigate_to_spy_options(page)
        
        if success:
            print("\n🎯 SUCCESS! You're now on SPY options with your authenticated session")
            print("🌐 Browser will stay open for manual trading")
            print("📊 You can now manually browse and trade SPY options")
            print("⏸️  Press Enter to close connection...")
            
            # Keep connection alive
            input()
        else:
            print("\n⚠️ Please log in manually, then re-run this script")
            input("Press Enter to close...")
            
    except KeyboardInterrupt:
        print("\n⏸️ Interrupted")
    finally:
        # Don't close browser - just disconnect
        if playwright:
            await playwright.stop()
        print("👋 Disconnected (browser stays open)")

if __name__ == "__main__":
    asyncio.run(main())