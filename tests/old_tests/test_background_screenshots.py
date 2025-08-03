#!/usr/bin/env python3
"""
Test if Playwright can take screenshots of background/inactive tabs
"""
import asyncio
from playwright.async_api import async_playwright

async def test_background_screenshots():
    """Test background tab screenshot capability."""
    print("🧪 Testing background tab screenshots...")
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        if not browser.contexts:
            print("❌ No browser contexts found. Start Chrome with --remote-debugging-port=9222")
            return
        
        context = browser.contexts[0]
        
        # Create 3 tabs
        print("📱 Creating 3 test tabs...")
        tab1 = await context.new_page()
        tab2 = await context.new_page()  
        tab3 = await context.new_page()
        
        # Navigate each to different pages
        await tab1.goto("https://google.com")
        await tab2.goto("https://yahoo.com")
        await tab3.goto("https://bing.com")
        
        await asyncio.sleep(3)
        
        print("📸 Taking simultaneous screenshots of all 3 tabs...")
        
        # Take screenshots simultaneously (tab2 and tab3 will be in background)
        await asyncio.gather(
            tab1.screenshot(path="screenshots/test_tab1_google.png"),
            tab2.screenshot(path="screenshots/test_tab2_yahoo.png"),  # Background tab
            tab3.screenshot(path="screenshots/test_tab3_bing.png")    # Background tab
        )
        
        print("✅ All 3 screenshots taken simultaneously!")
        print("📁 Check screenshots/ folder for:")
        print("   - test_tab1_google.png")
        print("   - test_tab2_yahoo.png (background)")
        print("   - test_tab3_bing.png (background)")
        
        # Clean up
        await tab1.close()
        await tab2.close()
        await tab3.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_background_screenshots())