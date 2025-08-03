#!/usr/bin/env python3
"""
Simple Contract Expansion Test - Just test basic expansion mechanism
"""
import asyncio
import re
from playwright.async_api import async_playwright

async def simple_test():
    """Simple test to see if we can expand any contract."""
    print("🧪 Simple Contract Expansion Test")
    print("=" * 40)
    
    try:
        # Connect to browser
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        if not browser.contexts:
            print("❌ No browser contexts found")
            return
        
        # Get SPY page
        context = browser.contexts[0]
        pages = context.pages
        
        spy_page = None
        for page in pages:
            if "robinhood.com" in page.url and "SPY" in page.url:
                spy_page = page
                break
        
        if not spy_page:
            print("❌ No SPY page found")
            return
        
        print("✅ Found SPY page")
        
        # Click Call tab
        print("📞 Clicking Call tab...")
        call_tab = spy_page.locator('button:has-text("Call")')
        if await call_tab.count() > 0:
            await call_tab.click()
            await asyncio.sleep(3)
            print("✅ Clicked Call tab")
        
        # Take screenshot
        await spy_page.screenshot(path="screenshots/simple_test_page.png")
        print("📸 Screenshot saved")
        
        # Find ANY price element to test expansion
        print("🔍 Looking for any contract to test expansion...")
        
        # Look for any $0.xx price
        content = await spy_page.content()
        prices = re.findall(r'\$0\.(\d{2})', content)
        
        if prices:
            print(f"💰 Found prices: {prices[:5]}...")
            
            # Try to find and click the first price we can
            test_price = prices[0]
            print(f"🎯 Testing expansion with {test_price}¢ contract...")
            
            # Look for elements containing this price
            price_text = f"$0.{test_price}"
            price_elements = spy_page.locator(f'text="{price_text}"')
            count = await price_elements.count()
            print(f"📋 Found {count} elements with {price_text}")
            
            # If exact match fails, try broader search
            if count == 0:
                price_elements = spy_page.locator(f':has-text("{price_text}")')
                count = await price_elements.count()
                print(f"📋 Broader search found {count} elements containing {price_text}")
            
            if count > 0:
                # Try to click the first one
                element = price_elements.first
                
                # Scroll to it
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                
                # Get position and click
                box = await element.bounding_box()
                if box:
                    click_x = box['x'] + (box['width'] * 0.3)
                    click_y = box['y'] + (box['height'] * 0.5)
                    
                    print(f"🖱️ Clicking at ({click_x:.0f}, {click_y:.0f})...")
                    
                    # Before screenshot
                    await spy_page.screenshot(path="screenshots/simple_before.png")
                    
                    # Click
                    await spy_page.mouse.click(click_x, click_y)
                    await asyncio.sleep(4)
                    
                    # After screenshot
                    await spy_page.screenshot(path="screenshots/simple_after.png")
                    
                    # Check if expanded
                    new_content = await spy_page.content()
                    indicators = ['theta', 'gamma', 'bid', 'ask', 'volume']
                    found = [ind for ind in indicators if ind.lower() in new_content.lower()]
                    
                    if len(found) >= 3:
                        print(f"✅ SUCCESS! Contract expanded. Found: {', '.join(found)}")
                        return True
                    else:
                        print(f"❌ Contract may not have expanded. Found: {', '.join(found)}")
                        return False
        else:
            print("❌ No price patterns found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if 'playwright' in locals():
            await playwright.stop()

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}")