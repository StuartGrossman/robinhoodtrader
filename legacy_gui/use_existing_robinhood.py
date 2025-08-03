#!/usr/bin/env python3
"""
Use Existing Robinhood Page
"""
import asyncio
from playwright.async_api import async_playwright

async def use_existing_robinhood():
    """Use the existing Robinhood page that's already logged in."""
    print("🚀 Connecting to existing Robinhood page...")
    
    try:
        playwright = await async_playwright().start()
        
        # Connect to existing Chrome instance
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        # Get existing context and pages
        contexts = browser.contexts
        if not contexts:
            print("❌ No browser contexts found")
            return
        
        context = contexts[0]
        pages = context.pages
        
        # Find the Robinhood page
        robinhood_page = None
        for page in pages:
            if "robinhood.com" in page.url:
                robinhood_page = page
                break
        
        if not robinhood_page:
            print("❌ No Robinhood page found")
            print("Available pages:")
            for i, page in enumerate(pages):
                print(f"  {i}: {page.url}")
            return
        
        print(f"✅ Found Robinhood page: {robinhood_page.url}")
        
        # Navigate to SPY options using the existing page
        print("📈 Navigating to SPY options...")
        await robinhood_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        current_url = robinhood_page.url
        print(f"📊 Current URL: {current_url}")
        
        if "options" in current_url and "SPY" in current_url:
            print("🎉 Successfully navigated to SPY options!")
            print("📊 You can now manually browse and trade SPY options")
            
            # Keep the page open for manual use
            print("⏸️ Page will stay open for manual trading...")
            print("Press Enter to close connection (browser stays open)...")
            input()
        else:
            print("⚠️ Navigation may have been redirected")
            print(f"Current URL: {current_url}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'playwright' in locals():
            await playwright.stop()

if __name__ == "__main__":
    asyncio.run(use_existing_robinhood()) 