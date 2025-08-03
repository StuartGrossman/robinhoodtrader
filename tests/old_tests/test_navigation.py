#!/usr/bin/env python3
"""
Test Navigation to Robinhood
"""
import asyncio
from playwright.async_api import async_playwright

async def test_navigation():
    """Test basic navigation to Robinhood."""
    print("🚀 Testing Robinhood Navigation...")
    
    try:
        playwright = await async_playwright().start()
        
        # Connect to existing Chrome instance
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        # Get existing context and page
        contexts = browser.contexts
        if not contexts:
            print("❌ No browser contexts found")
            return
        
        context = contexts[0]
        pages = context.pages
        
        if not pages:
            page = await context.new_page()
        else:
            page = pages[0]
        
        print(f"✅ Connected! Current URL: {page.url}")
        
        # Try navigating to main Robinhood page first
        print("🌐 Navigating to Robinhood main page...")
        await page.goto("https://robinhood.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"📊 Current URL after navigation: {current_url}")
        
        # Check if we're logged in
        if "login" in current_url:
            print("🔐 Redirected to login - need to authenticate")
        else:
            print("🎉 Successfully on Robinhood main page!")
            
            # Try to navigate to options
            print("📈 Trying to navigate to options...")
            await page.goto("https://robinhood.com/options", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            options_url = page.url
            print(f"📊 Options URL: {options_url}")
            
            if "options" in options_url:
                print("✅ Successfully navigated to options!")
            else:
                print("⚠️ Could not access options page")
        
        # Keep browser open
        print("⏸️ Press Enter to close...")
        input()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'playwright' in locals():
            await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_navigation()) 