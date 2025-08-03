#!/usr/bin/env python3
"""
Debug Browser Connection
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_browser():
    """Debug the browser connection and pages."""
    print("🔍 Debugging Browser Connection...")
    
    try:
        playwright = await async_playwright().start()
        
        # Connect to existing Chrome instance
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        print("✅ Connected to browser")
        
        # List all contexts
        contexts = browser.contexts
        print(f"📋 Found {len(contexts)} browser contexts")
        
        for i, context in enumerate(contexts):
            print(f"\n🔍 Context {i}:")
            print(f"  - Pages: {len(context.pages)}")
            
            # List all pages in this context
            for j, page in enumerate(context.pages):
                try:
                    url = page.url
                    title = await page.title()
                    print(f"    Page {j}: {title} ({url})")
                except Exception as e:
                    print(f"    Page {j}: Error getting info - {e}")
        
        # Try to create a new page
        print("\n🆕 Creating new page...")
        context = contexts[0] if contexts else await browser.new_context()
        new_page = await context.new_page()
        
        print(f"✅ New page created: {new_page.url}")
        
        # Try to navigate to a simple page first
        print("🌐 Testing navigation to Google...")
        await new_page.goto("https://www.google.com", wait_until="domcontentloaded")
        print(f"✅ Google page loaded: {new_page.url}")
        
        # Now try Robinhood
        print("🌐 Testing navigation to Robinhood...")
        try:
            await new_page.goto("https://robinhood.com", wait_until="domcontentloaded")
            print(f"✅ Robinhood page loaded: {new_page.url}")
        except Exception as e:
            print(f"❌ Robinhood navigation failed: {e}")
        
        # Keep browser open
        print("\n⏸️ Press Enter to close...")
        input()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'playwright' in locals():
            await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_browser()) 