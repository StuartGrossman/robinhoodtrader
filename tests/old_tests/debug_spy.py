#!/usr/bin/env python3
"""
Debug version - Simple console output to see what's happening
"""
import asyncio
import sys
import traceback
from playwright.async_api import async_playwright

async def debug_connection():
    """Test Chrome connection with detailed logging."""
    print("🚀 DEBUG: Starting connection test...")
    print(f"🐍 Python version: {sys.version}")
    
    try:
        print("📱 Starting Playwright...")
        playwright = await async_playwright().start()
        print("✅ Playwright started successfully")
        
        print("🔗 Attempting to connect to Chrome on port 9222...")
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        print("✅ Connected to Chrome successfully")
        
        print("📋 Getting browser contexts...")
        contexts = browser.contexts
        print(f"📊 Found {len(contexts)} contexts")
        
        if not contexts:
            print("❌ No contexts found - Chrome may not be running properly")
            return
        
        context = contexts[0]
        pages = context.pages
        print(f"📄 Found {len(pages)} pages in context")
        
        if not pages:
            print("🆕 Creating new page...")
            page = await context.new_page()
        else:
            print("📖 Using existing page...")
            page = pages[0]
        
        print(f"🌐 Current URL: {page.url}")
        
        print("🧭 Navigating to SPY options...")
        await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
        print("✅ Navigation complete")
        
        await asyncio.sleep(2)
        
        current_url = page.url
        print(f"🎯 Final URL: {current_url}")
        
        if "login" in current_url:
            print("🔐 Login required - please log into Robinhood first")
        else:
            print("✅ Logged in successfully")
        
        # Get page title
        title = await page.title()
        print(f"📰 Page title: {title}")
        
        # Take screenshot
        print("📸 Taking screenshot...")
        await page.screenshot(path="debug_screenshot.png")
        print("✅ Screenshot saved as debug_screenshot.png")
        
        # Try to find some text on the page
        print("🔍 Looking for SPY text on page...")
        spy_elements = page.locator("text=SPY")
        spy_count = await spy_elements.count()
        print(f"📊 Found {spy_count} elements containing 'SPY'")
        
        # Look for price patterns
        print("💰 Looking for price patterns...")
        price_elements = page.locator("text=/\\$\\d+\\.\\d+/")
        price_count = await price_elements.count()
        print(f"💵 Found {price_count} elements with price patterns")
        
        # Look specifically for options prices
        print("🔍 Looking for options prices in 8-16 cent range...")
        option_price_elements = page.locator("text=/\\$0\\.(0[8-9]|1[0-6])/")
        option_price_count = await option_price_elements.count()
        print(f"🎯 Found {option_price_count} elements with options prices in range")
        
        if option_price_count > 0:
            print("📋 First few option prices found:")
            for i in range(min(5, option_price_count)):
                try:
                    element = option_price_elements.nth(i)
                    text = await element.text_content()
                    print(f"  {i+1}: {text}")
                except Exception as e:
                    print(f"  {i+1}: Error getting text - {e}")
        
        # Get some page content
        print("📝 Getting page content sample...")
        page_content = await page.content()
        content_length = len(page_content)
        print(f"📊 Page content length: {content_length} characters")
        
        # Look for specific text patterns in content
        import re
        price_matches = re.findall(r'\$0\.(\d{2})', page_content)
        print(f"💰 Found {len(price_matches)} price matches in content")
        
        target_prices = [p for p in price_matches if 8 <= int(p) <= 16]
        print(f"🎯 Found {len(target_prices)} prices in 8-16 cent range: {target_prices[:10]}")
        
        print("✅ Debug complete - check debug_screenshot.png")
        
        # Clean up
        await playwright.stop()
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        print("📋 Full traceback:")
        traceback.print_exc()

def main():
    """Main debug function."""
    print("🐛 SPY Options Debug Tool")
    print("=" * 50)
    
    try:
        asyncio.run(debug_connection())
    except Exception as e:
        print(f"❌ Main error: {e}")
        traceback.print_exc()
    
    print("\n🏁 Debug session complete")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()