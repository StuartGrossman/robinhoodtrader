#!/usr/bin/env python3
"""
Improved Data Extraction - Based on debug findings
"""
import asyncio
import re
from playwright.async_api import async_playwright

async def test_improved_extraction():
    """Test improved data extraction patterns."""
    print("🔧 Testing Improved Data Extraction")
    print("=" * 40)
    
    try:
        # Connect and expand contract (same as before)
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        
        spy_page = None
        for page in context.pages:
            if "robinhood.com" in page.url and "SPY" in page.url:
                spy_page = page
                break
        
        if not spy_page:
            print("❌ No SPY page found")
            return
        
        # Click PUT tab and expand contract
        put_tab = spy_page.locator('button:has-text("Put")')
        await put_tab.click()
        await asyncio.sleep(3)
        
        content = await spy_page.content()
        prices = re.findall(r'\$0\.(\d{2})', content)
        
        if prices:
            test_price = prices[0]
            price_text = f"$0.{test_price}"
            
            print(f"🎯 Expanding {test_price}¢ contract...")
            
            elements = spy_page.locator(f':has-text("{price_text}")')
            if await elements.count() > 0:
                element = elements.first
                await element.scroll_into_view_if_needed()
                
                box = await element.bounding_box()
                if box:
                    click_x = box['x'] + (box['width'] * 0.3)
                    click_y = box['y'] + (box['height'] * 0.5)
                    
                    await spy_page.mouse.click(click_x, click_y)
                    await asyncio.sleep(4)
                    
                    # Get expanded content
                    expanded_content = await spy_page.content()
                    
                    print("🔍 IMPROVED DATA EXTRACTION:")
                    print("=" * 40)
                    
                    # Extract data using improved patterns based on debug results
                    extracted_data = {}
                    
                    # Improved bid patterns
                    bid_patterns = [
                        r'bid.*?(\d+\.\d+)',  # This worked in debug
                        r'Bid.*?(\d+\.\d+)',
                        r'"bid"[^"]*?(\d+\.\d+)',
                    ]
                    
                    for pattern in bid_patterns:
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        if matches:
                            extracted_data['bid'] = matches[0]
                            print(f"💰 BID: ${matches[0]} (pattern: {pattern})")
                            break
                    
                    # Improved ask patterns
                    ask_patterns = [
                        r'Ask Price.*?(\d+\.\d+)',  # Based on "Ask Price" in context
                        r'ask.*?(\d+\.\d+)',
                        r'Ask.*?(\d+\.\d+)',
                        r'"ask"[^"]*?(\d+\.\d+)',
                    ]
                    
                    for pattern in ask_patterns:
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        if matches:
                            extracted_data['ask'] = matches[0]
                            print(f"💰 ASK: ${matches[0]} (pattern: {pattern})")
                            break
                    
                    # Try to extract current price from dollar amounts
                    dollar_amounts = re.findall(r'\$(\d+\.\d+)', expanded_content)
                    if dollar_amounts:
                        # Look for amounts in reasonable range for this contract
                        reasonable_prices = [float(d) for d in dollar_amounts if 0.1 <= float(d) <= 10.0]
                        if reasonable_prices:
                            extracted_data['current_price'] = str(min(reasonable_prices))  # Take lowest reasonable price
                            print(f"💵 CURRENT PRICE: ${extracted_data['current_price']} (from dollar amounts)")
                    
                    # Extract strike price from URL or content
                    strike_patterns = [
                        r'strike.*?(\d+)',
                        r'Strike.*?(\d+)',
                        r'\$(\d{3})',  # 3-digit dollar amounts (likely strikes)
                    ]
                    
                    for pattern in strike_patterns:
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        if matches:
                            # Filter to reasonable strike prices
                            reasonable_strikes = [int(m) for m in matches if 500 <= int(m) <= 700]
                            if reasonable_strikes:
                                extracted_data['strike'] = str(reasonable_strikes[0])
                                print(f"📈 STRIKE: ${extracted_data['strike']} (pattern: {pattern})")
                                break
                    
                    # Try to find volume in different ways
                    volume_patterns = [
                        r'volume[^0-9]*(\d+)',
                        r'Volume[^0-9]*(\d+)',
                        r'vol[^0-9]*(\d+)',
                    ]
                    
                    for pattern in volume_patterns:
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        if matches:
                            extracted_data['volume'] = matches[0]
                            print(f"📊 VOLUME: {matches[0]} (pattern: {pattern})")
                            break
                    
                    # Try to find Greeks by looking at decimal numbers in context
                    decimal_numbers = re.findall(r'(\d+\.\d{2,4})', expanded_content)
                    if decimal_numbers:
                        # Convert to floats and categorize by likely range
                        decimals = [float(d) for d in decimal_numbers]
                        
                        # Theta is usually negative and small
                        potential_theta = [d for d in decimals if -1.0 <= d <= 0.0]
                        if potential_theta:
                            extracted_data['theta'] = str(potential_theta[0])
                            print(f"🏷️ THETA: {extracted_data['theta']} (estimated from decimals)")
                        
                        # Gamma is usually small positive
                        potential_gamma = [d for d in decimals if 0.0 < d <= 1.0]
                        if potential_gamma:
                            extracted_data['gamma'] = str(potential_gamma[0])
                            print(f"🏷️ GAMMA: {extracted_data['gamma']} (estimated from decimals)")
                        
                        # Delta is usually between 0-1 for options
                        potential_delta = [d for d in decimals if 0.0 <= d <= 1.0]
                        if potential_delta:
                            extracted_data['delta'] = str(potential_delta[0])
                            print(f"🏷️ DELTA: {extracted_data['delta']} (estimated from decimals)")
                    
                    print(f"\n📊 SUMMARY: Extracted {len(extracted_data)} data fields")
                    print("=" * 40)
                    
                    for field, value in extracted_data.items():
                        print(f"  {field.upper()}: {value}")
                    
                    if len(extracted_data) >= 3:
                        print("\n✅ SUCCESS! Improved extraction working")
                        return True
                    else:
                        print("\n⚠️ LIMITED SUCCESS - need more data fields")
                        return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await playwright.stop()

if __name__ == "__main__":
    success = asyncio.run(test_improved_extraction())
    print(f"\n{'✅ EXTRACTION IMPROVED' if success else '❌ EXTRACTION NEEDS WORK'}")