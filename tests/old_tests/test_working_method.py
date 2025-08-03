#!/usr/bin/env python3
"""
Test Working Method - Command line test without GUI
"""
import asyncio
import re
from playwright.async_api import async_playwright

async def test_working_method():
    """Test the working method without GUI."""
    print("🧪 Testing Working Method")
    print("=" * 30)
    
    try:
        # Connect to browser
        print("🌐 Connecting to browser...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        if not browser.contexts:
            print("❌ No browser contexts found")
            return
        
        # Find or create SPY page
        context = browser.contexts[0]
        pages = context.pages
        
        print(f"🔍 Checking {len(pages)} browser tabs...")
        
        spy_page = None
        for i, page in enumerate(pages):
            url = page.url
            print(f"  Tab {i+1}: {url}")
            if "robinhood.com" in url and "SPY" in url:
                spy_page = page
                print(f"  ✅ Found SPY page at tab {i+1}")
                break
        
        # If no SPY page, try to navigate
        if not spy_page:
            print("🌐 No SPY page found, attempting to navigate...")
            
            # Find any Robinhood page
            rh_page = None
            for page in pages:
                if "robinhood.com" in page.url:
                    rh_page = page
                    break
            
            if rh_page:
                print("📊 Found Robinhood page, navigating to SPY options...")
                await rh_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
                await asyncio.sleep(5)
                spy_page = rh_page
                print("✅ Successfully navigated to SPY options")
            else:
                print("❌ No Robinhood page found")
                return
        
        # Click PUT tab
        print("📉 Clicking PUT tab...")
        put_tab = spy_page.locator('button:has-text("Put")')
        if await put_tab.count() > 0:
            await put_tab.click()
            await asyncio.sleep(4)
            print("✅ Clicked PUT tab")
        else:
            print("❌ Could not find PUT tab")
            return
        
        # Take screenshot
        await spy_page.screenshot(path="screenshots/working_test_puts.png")
        print("📸 Screenshot saved")
        
        # Find contracts
        print("🔍 Finding contracts...")
        content = await spy_page.content()
        prices = re.findall(r'\$0\.(\d{2})', content)
        
        if prices:
            unique_prices = sorted(list(set(prices)))
            print(f"💰 Found prices: {unique_prices}")
            
            # Filter to reasonable range
            target_prices = [p for p in unique_prices if 30 <= int(p) <= 90]
            print(f"🎯 Target prices: {target_prices}")
            
            if target_prices:
                # Test expanding first contract
                test_price = target_prices[0]
                price_text = f"$0.{test_price}"
                
                print(f"🧪 Testing expansion of {test_price}¢ contract...")
                
                elements = spy_page.locator(f':has-text("{price_text}")')
                count = await elements.count()
                print(f"📋 Found {count} elements with {price_text}")
                
                if count > 0:
                    element = elements.first
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    
                    box = await element.bounding_box()
                    if box:
                        click_x = box['x'] + (box['width'] * 0.3)
                        click_y = box['y'] + (box['height'] * 0.5)
                        
                        print(f"🖱️ Clicking at ({click_x:.0f}, {click_y:.0f})...")
                        
                        # Before screenshot
                        await spy_page.screenshot(path="screenshots/working_before.png")
                        
                        # Click
                        await spy_page.mouse.click(click_x, click_y)
                        await asyncio.sleep(4)
                        
                        # After screenshot
                        await spy_page.screenshot(path="screenshots/working_after.png")
                        
                        # Check expansion
                        new_content = await spy_page.content()
                        indicators = ['theta', 'gamma', 'bid', 'ask', 'volume']
                        found = [ind for ind in indicators if ind.lower() in new_content.lower()]
                        
                        if len(found) >= 3:
                            print(f"✅ SUCCESS! Contract expanded. Found: {', '.join(found)}")
                            
                            # Try to extract some data
                            patterns = {
                                'bid': r'Bid[:\s]+\$?(\d+\.\d{2,4})',
                                'ask': r'Ask[:\s]+\$?(\d+\.\d{2,4})',
                                'volume': r'Volume[:\s]+(\d+(?:,\d+)*)',
                                'theta': r'Theta[:\s]+(-?\d+\.\d{2,4})'
                            }
                            
                            extracted = {}
                            for field, pattern in patterns.items():
                                matches = re.findall(pattern, new_content, re.IGNORECASE)
                                if matches:
                                    extracted[field] = matches[0]
                            
                            if extracted:
                                print("📊 Extracted data:")
                                for field, value in extracted.items():
                                    print(f"  {field}: {value}")
                            
                            return True
                        else:
                            print(f"❌ Contract may not be expanded. Found: {', '.join(found)}")
                            return False
                    else:
                        print("❌ Could not get bounding box")
                        return False
                else:
                    print("❌ No clickable elements found")
                    return False
            else:
                print(f"❌ No contracts in target range")
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
    import os
    os.makedirs("screenshots", exist_ok=True)
    
    success = asyncio.run(test_working_method())
    print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}")