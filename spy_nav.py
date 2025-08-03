#!/usr/bin/env python3
"""
SPY Options Navigator - Uses your existing Chrome session
"""
import asyncio
from playwright.async_api import async_playwright

async def connect_to_chrome():
    """Connect to existing Chrome browser."""
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        contexts = browser.contexts
        if not contexts:
            print("❌ No browser contexts found")
            return None, None, None
        
        context = contexts[0]
        pages = context.pages
        
        if not pages:
            page = await context.new_page()
        else:
            page = pages[0]
        
        return playwright, browser, page
        
    except Exception as e:
        print(f"❌ Could not connect to Chrome: {e}")
        print("💡 Run the Chrome command first!")
        return None, None, None

async def navigate_to_spy():
    """Navigate directly to SPY options."""
    playwright, browser, page = await connect_to_chrome()
    
    if not page:
        return
    
    try:
        print("📊 Navigating to SPY options...")
        await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        current_url = page.url
        if "login" in current_url:
            print("🔐 Please log into Robinhood first")
        else:
            print("✅ Success! SPY options loaded")
            print("🌐 Browser stays open for trading")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if playwright:
            await playwright.stop()

def print_chrome_command():
    """Print the Chrome command to run."""
    print("🚀 SPY Options Navigator")
    print("=" * 40)
    print("📋 STEP 1: Run this command in terminal:")
    print()
    print("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
    print("--remote-debugging-port=9222 \\")
    print("--user-data-dir=$HOME/chrome_robinhood")
    print()
    print("🔐 STEP 2: Log into Robinhood in that Chrome")
    print("▶️  STEP 3: Run this script again")
    print("=" * 40)

async def main():
    """Main function."""
    # Check if Chrome is running with remote debugging
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        print("✅ Connected to Chrome!")
        await browser.close()
        await playwright.stop()
        
        # Chrome is running, navigate to SPY
        await navigate_to_spy()
        
    except Exception as e:
        print(f"❌ Cannot connect to Chrome: {e}")
        print()
        # Chrome not running with debugging, show command
        print_chrome_command()

if __name__ == "__main__":
    asyncio.run(main())