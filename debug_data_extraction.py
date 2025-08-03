#!/usr/bin/env python3
"""
Debug Data Extraction - See what's actually in the expanded contract
"""
import asyncio
import re
from playwright.async_api import async_playwright

async def debug_extraction():
    """Debug what data is actually available after expansion."""
    print("🔍 Debug Data Extraction")
    print("=" * 30)
    
    try:
        # Connect and find SPY page
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
        
        # Click PUT tab
        put_tab = spy_page.locator('button:has-text("Put")')
        await put_tab.click()
        await asyncio.sleep(3)
        
        # Find and expand a contract
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
                    
                    # Save full content to file for analysis
                    with open("debug_expanded_content.html", "w") as f:
                        f.write(expanded_content)
                    print("📄 Full content saved to debug_expanded_content.html")
                    
                    # Look for various patterns
                    print("\n🔍 SEARCHING FOR DATA PATTERNS:")
                    print("=" * 50)
                    
                    # Try different bid patterns
                    bid_patterns = [
                        r'Bid[:\s]*\$?(\d+\.\d+)',
                        r'bid[:\s]*\$?(\d+\.\d+)',
                        r'BID[:\s]*\$?(\d+\.\d+)',
                        r'"bid"[:\s]*"?\$?(\d+\.\d+)"?',
                        r'bid.*?(\d+\.\d+)',
                        r'(\d+\.\d+).*?bid',
                    ]
                    
                    print("💰 BID patterns:")
                    for i, pattern in enumerate(bid_patterns):
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        print(f"  {i+1}. {pattern}: {matches[:3] if matches else 'No matches'}")
                    
                    # Try different ask patterns
                    ask_patterns = [
                        r'Ask[:\s]*\$?(\d+\.\d+)',
                        r'ask[:\s]*\$?(\d+\.\d+)',
                        r'ASK[:\s]*\$?(\d+\.\d+)',
                        r'"ask"[:\s]*"?\$?(\d+\.\d+)"?',
                        r'ask.*?(\d+\.\d+)',
                        r'(\d+\.\d+).*?ask',
                    ]
                    
                    print("\n💰 ASK patterns:")
                    for i, pattern in enumerate(ask_patterns):
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        print(f"  {i+1}. {pattern}: {matches[:3] if matches else 'No matches'}")
                    
                    # Try volume patterns
                    volume_patterns = [
                        r'Volume[:\s]*(\d+(?:,\d+)*)',
                        r'volume[:\s]*(\d+(?:,\d+)*)',
                        r'VOLUME[:\s]*(\d+(?:,\d+)*)',
                        r'"volume"[:\s]*"?(\d+(?:,\d+)*)"?',
                        r'vol[:\s]*(\d+(?:,\d+)*)',
                    ]
                    
                    print("\n📊 VOLUME patterns:")
                    for i, pattern in enumerate(volume_patterns):
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        print(f"  {i+1}. {pattern}: {matches[:3] if matches else 'No matches'}")
                    
                    # Try theta patterns
                    theta_patterns = [
                        r'Theta[:\s]*(-?\d+\.\d+)',
                        r'theta[:\s]*(-?\d+\.\d+)',
                        r'THETA[:\s]*(-?\d+\.\d+)',
                        r'"theta"[:\s]*"?(-?\d+\.\d+)"?',
                        r'θ[:\s]*(-?\d+\.\d+)',
                    ]
                    
                    print("\n🏷️ THETA patterns:")
                    for i, pattern in enumerate(theta_patterns):
                        matches = re.findall(pattern, expanded_content, re.IGNORECASE)
                        print(f"  {i+1}. {pattern}: {matches[:3] if matches else 'No matches'}")
                    
                    # Look for any dollar amounts
                    print("\n💵 ALL DOLLAR AMOUNTS:")
                    dollar_amounts = re.findall(r'\$(\d+\.\d+)', expanded_content)
                    print(f"  Found: {dollar_amounts[:10]}")
                    
                    # Look for any numbers with 2-4 decimal places
                    print("\n🔢 ALL DECIMAL NUMBERS:")
                    decimal_numbers = re.findall(r'(\d+\.\d{2,4})', expanded_content)
                    print(f"  Found: {decimal_numbers[:15]}")
                    
                    # Look for common option terms
                    print("\n📋 OPTION TERMS FOUND:")
                    terms = ['bid', 'ask', 'volume', 'theta', 'gamma', 'delta', 'strike', 'premium', 'implied']
                    for term in terms:
                        count = len(re.findall(term, expanded_content, re.IGNORECASE))
                        if count > 0:
                            print(f"  {term}: {count} occurrences")
                    
                    # Extract text around key terms
                    print("\n📝 CONTEXT AROUND KEY TERMS:")
                    key_terms = ['bid', 'ask', 'volume', 'theta']
                    for term in key_terms:
                        matches = re.findall(f'.{{0,30}}{term}.{{0,30}}', expanded_content, re.IGNORECASE)
                        if matches:
                            print(f"  {term.upper()} context:")
                            for match in matches[:3]:
                                clean_match = ' '.join(match.split())  # Clean whitespace
                                print(f"    \"{clean_match}\"")
                    
                    print("\n✅ Debug complete! Check debug_expanded_content.html for full content")
    
    except Exception as e:
        print(f"❌ Debug failed: {e}")
    finally:
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_extraction())