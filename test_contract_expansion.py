#!/usr/bin/env python3
"""
Test Contract Expansion - Focused test to verify contract detection and expansion works
"""
import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright

class ContractExpansionTest:
    def __init__(self):
        self.browser = None
        self.playwright = None
        
    async def run_test(self):
        """Run the complete contract expansion test."""
        print("🧪 Starting Contract Expansion Test")
        print("=" * 50)
        
        try:
            # Connect to browser
            await self.connect_browser()
            
            # Navigate to options page
            page = await self.navigate_to_options()
            
            # Test CALLS
            print("\n📞 Testing CALLS expansion...")
            calls_results = await self.test_option_type(page, "Call")
            
            # Test PUTS  
            print("\n📉 Testing PUTS expansion...")
            puts_results = await self.test_option_type(page, "Put")
            
            # Results summary
            self.print_results(calls_results, puts_results)
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        finally:
            if self.playwright:
                await self.playwright.stop()
    
    async def connect_browser(self):
        """Connect to Chrome with debugging."""
        print("🌐 Connecting to Chrome...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        if not self.browser.contexts:
            raise Exception("No browser contexts found. Start Chrome with --remote-debugging-port=9222")
        
        print("✅ Connected to Chrome")
    
    async def navigate_to_options(self):
        """Navigate to SPY options page."""
        context = self.browser.contexts[0]
        
        # Check all existing pages first
        pages = context.pages
        print(f"📋 Found {len(pages)} existing pages")
        
        spy_page = None
        for i, page in enumerate(pages):
            url = page.url
            print(f"  Page {i+1}: {url}")
            if "robinhood.com" in url and "SPY" in url:
                spy_page = page
                print(f"  ✅ Found SPY page at tab {i+1}")
                break
        
        # If no SPY page found, try to create new one
        if not spy_page:
            print("🌐 Creating new page for SPY options...")
            try:
                spy_page = await context.new_page()
                await spy_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
                await asyncio.sleep(3)
                print("✅ Successfully navigated to SPY options")
            except Exception as e:
                print(f"❌ Could not navigate to SPY: {e}")
                print("💡 Please manually navigate to robinhood.com/options/chains/SPY in Chrome")
                raise Exception("Manual navigation required")
        
        if "login" in spy_page.url:
            raise Exception("Please log into Robinhood first")
        
        # Wait for page to fully load
        print("⏳ Waiting for page to fully load...")
        await asyncio.sleep(10)  # Give it time to load
        
        # Take screenshot to see what we're working with
        await spy_page.screenshot(path="screenshots/current_spy_page.png")
        print("📸 SPY page screenshot saved")
        
        return spy_page
    
    async def test_option_type(self, page, option_type):
        """Test expansion for specific option type (Call/Put)."""
        results = {
            'option_type': option_type,
            'contracts_found': 0,
            'contracts_expanded': 0,
            'data_extracted': 0,
            'successful_contracts': []
        }
        
        try:
            # Click option type tab - try multiple selectors
            print(f"  🔘 Looking for {option_type} tab...")
            
            # Try different selectors for the tab
            tab_selectors = [
                f'button:has-text("{option_type}")',
                f'[role="tab"]:has-text("{option_type}")',
                f'button[data-testid*="{option_type.lower()}")',
                f'div:has-text("{option_type}s")',
                f'button:has-text("{option_type}s")',
                f'[aria-label*="{option_type}"]'
            ]
            
            tab_clicked = False
            for selector in tab_selectors:
                try:
                    tab_button = page.locator(selector)
                    count = await tab_button.count()
                    print(f"    Trying '{selector}': found {count} elements")
                    
                    if count > 0:
                        await tab_button.first.click()
                        await asyncio.sleep(4)
                        print(f"  ✅ Clicked {option_type} tab using {selector}")
                        tab_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not tab_clicked:
                print(f"  ❌ Could not find {option_type} tab with any selector")
                # Show what's actually on the page
                content = await page.content()
                if "Call" in content or "Put" in content:
                    print(f"  ℹ️ Page contains Call/Put text, but buttons not clickable")
                else:
                    print(f"  ⚠️ Page doesn't contain Call/Put text - may not be loaded")
                return results
            
            # Take full page screenshot
            await page.screenshot(path=f"screenshots/test_{option_type.lower()}_page.png", full_page=True)
            print(f"  📸 Full page screenshot saved")
            
            # Find contracts in 8-16¢ range
            contracts = await self.find_target_contracts(page)
            results['contracts_found'] = len(contracts)
            print(f"  🎯 Found {len(contracts)} contracts in 8-16¢ range")
            
            # Test expansion on first 3 contracts
            for i, contract in enumerate(contracts[:3]):
                print(f"  \n  📋 Testing contract {i+1}/{min(len(contracts), 3)}: {contract['price']}¢")
                
                success = await self.test_single_contract_expansion(page, contract, f"{option_type.lower()}_{i+1}")
                
                if success:
                    results['contracts_expanded'] += 1
                    results['successful_contracts'].append(contract['price'])
                    
                    # Extract data
                    data = await self.extract_contract_data(page, contract['price'])
                    if data and len(data) > 5:  # At least 5 data fields
                        results['data_extracted'] += 1
                        print(f"    ✅ Extracted {len(data)} data fields")
                    else:
                        print(f"    ⚠️ Limited data extraction: {len(data) if data else 0} fields")
                else:
                    print(f"    ❌ Failed to expand contract")
                
                # Small delay between tests
                await asyncio.sleep(2)
            
        except Exception as e:
            print(f"  ❌ Error testing {option_type}: {e}")
        
        return results
    
    async def find_target_contracts(self, page):
        """Find contracts in 8-16¢ price range."""
        contracts = []
        
        try:
            # First, wait for contracts to load
            await asyncio.sleep(3)
            
            # Look for any elements containing dollar prices
            print(f"    🔍 Scanning page for price elements...")
            
            # Try different approaches to find price elements
            selectors_to_try = [
                'span:has-text("$0.")',  # Span containing $0.
                'div:has-text("$0.")',   # Div containing $0.
                'td:has-text("$0.")',    # Table cell with $0.
                '[data-testid*="price"]', # Price test IDs
                'button:has-text("$0.")', # Button with price
            ]
            
            all_price_elements = []
            
            for selector in selectors_to_try:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    print(f"      '{selector}': {count} elements")
                    
                    for i in range(min(count, 30)):  # Check up to 30 elements
                        try:
                            element = elements.nth(i)
                            text = await element.text_content()
                            
                            if text and '$0.' in text:
                                # Extract all prices from this text
                                price_matches = re.findall(r'\$0\.(\d{2})', text)
                                
                                for price_str in price_matches:
                                    price_cents = int(price_str)
                                    if 40 <= price_cents <= 60:  # Adjusted to match current prices
                                        # Check if this element is clickable
                                        box = await element.bounding_box()
                                        if box and box['width'] > 10 and box['height'] > 10:
                                            all_price_elements.append({
                                                'price': price_cents,
                                                'element': element,
                                                'text': text.strip()[:100],
                                                'selector': selector
                                            })
                                            print(f"        ✅ Found {price_cents}¢: {text.strip()[:40]}...")
                                            break  # One price per element
                        except Exception:
                            continue
                            
                except Exception as e:
                    continue
            
            # Remove duplicates by price and sort
            unique_contracts = {}
            for contract in all_price_elements:
                price = contract['price']
                if price not in unique_contracts:
                    unique_contracts[price] = contract
            
            # Sort by price and return
            sorted_contracts = sorted(unique_contracts.values(), key=lambda x: x['price'])
            
            if sorted_contracts:
                prices = [c['price'] for c in sorted_contracts]
                print(f"    🎯 Found contracts at prices: {[f'{p}¢' for p in prices]}")
            else:
                print(f"    ❌ No contracts found in 40-60¢ range")
                
                # Debug: show what prices we did find
                content = await page.content()
                all_prices = re.findall(r'\$0\.(\d{2})', content)
                if all_prices:
                    unique_prices = sorted(list(set(all_prices)))
                    print(f"    🔍 Debug - All prices found on page: {unique_prices}")
            
            return sorted_contracts[:5]  # Return up to 5 contracts
            
        except Exception as e:
            print(f"    ❌ Error finding contracts: {e}")
            return []
    
    async def test_single_contract_expansion(self, page, contract, test_id):
        """Test expanding a single contract."""
        try:
            element = contract['element']
            price = contract['price']
            
            # Scroll contract to top of viewport
            print(f"    🔝 Scrolling {price}¢ contract to top...")
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            # Additional scroll to ensure it's at the very top
            await page.evaluate('''
                (element) => {
                    const rect = element.getBoundingClientRect();
                    window.scrollTo({
                        top: window.scrollY + rect.top - 20,
                        behavior: 'smooth'
                    });
                }
            ''', await element.element_handle())
            
            await asyncio.sleep(2)
            
            # Take before screenshot
            await page.screenshot(path=f"screenshots/test_{test_id}_before.png")
            print(f"    📸 Before screenshot saved")
            
            # Get click position
            box = await element.bounding_box()
            if not box:
                print(f"    ❌ No bounding box for element")
                return False
            
            # Click to expand (click towards left side to avoid buy/sell buttons)
            click_x = box['x'] + (box['width'] * 0.2)  # 20% from left edge
            click_y = box['y'] + (box['height'] * 0.5)  # Center vertically
            
            print(f"    🖱️ Clicking at ({click_x:.0f}, {click_y:.0f}) to expand...")
            await page.mouse.click(click_x, click_y)
            await asyncio.sleep(4)  # Wait for expansion
            
            # Take after screenshot
            await page.screenshot(path=f"screenshots/test_{test_id}_after.png")
            print(f"    📸 After screenshot saved")
            
            # Check if expanded by looking for Greek indicators
            content = await page.content()
            expansion_indicators = ['theta', 'gamma', 'delta', 'bid', 'ask', 'volume']
            
            found_indicators = []
            for indicator in expansion_indicators:
                if indicator.lower() in content.lower():
                    found_indicators.append(indicator)
            
            if len(found_indicators) >= 3:
                print(f"    ✅ Contract expanded! Found: {', '.join(found_indicators)}")
                return True
            else:
                print(f"    ❌ Contract not expanded. Found only: {', '.join(found_indicators)}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error expanding contract: {e}")
            return False
    
    async def extract_contract_data(self, page, price_cents):
        """Extract data from expanded contract."""
        try:
            content = await page.content()
            
            data = {}
            
            # Data extraction patterns
            patterns = {
                'current_price': [r'(?:Last|Price|Mark|Current)[:\s]+\$?(\d+\.\d{2,4})'],
                'bid': [r'Bid[:\s]+\$?(\d+\.\d{2,4})'],
                'ask': [r'Ask[:\s]+\$?(\d+\.\d{2,4})'],
                'volume': [r'Volume[:\s]+(\d+(?:,\d+)*)'],
                'open_interest': [r'Open Interest[:\s]+(\d+(?:,\d+)*)'],
                'theta': [r'Theta[:\s]+(-?\d+\.\d{2,4})', r'θ[:\s]+(-?\d+\.\d{2,4})'],
                'gamma': [r'Gamma[:\s]+(\d+\.\d{2,4})', r'Γ[:\s]+(\d+\.\d{2,4})'],
                'delta': [r'Delta[:\s]+(-?\d+\.\d{2,4})', r'Δ[:\s]+(-?\d+\.\d{2,4})'],
                'high': [r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2,4})'],
                'low': [r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2,4})'],
                'strike': [r'Strike[:\s]+\$?(\d+)'],
            }
            
            for field, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        data[field] = matches[0].replace(',', '').strip()
                        break
            
            return data
            
        except Exception as e:
            print(f"    ❌ Error extracting data: {e}")
            return {}
    
    def print_results(self, calls_results, puts_results):
        """Print test results summary."""
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        for results in [calls_results, puts_results]:
            option_type = results['option_type']
            print(f"\n{option_type.upper()}:")
            print(f"  Contracts Found: {results['contracts_found']}")
            print(f"  Contracts Expanded: {results['contracts_expanded']}")
            print(f"  Data Extracted: {results['data_extracted']}")
            print(f"  Success Rate: {results['contracts_expanded']}/{results['contracts_found']} expanded")
            
            if results['successful_contracts']:
                print(f"  Successful Prices: {[f'{p}¢' for p in results['successful_contracts']]}")
        
        total_found = calls_results['contracts_found'] + puts_results['contracts_found']
        total_expanded = calls_results['contracts_expanded'] + puts_results['contracts_expanded']
        total_data = calls_results['data_extracted'] + puts_results['data_extracted']
        
        print(f"\nOVERALL:")
        print(f"  Total Contracts Found: {total_found}")
        print(f"  Total Expanded Successfully: {total_expanded}")
        print(f"  Total with Data Extracted: {total_data}")
        
        if total_expanded >= 4 and total_data >= 3:
            print("\n✅ TEST PASSED! Contract expansion method is working")
        else:
            print("\n❌ TEST FAILED! Need to improve contract expansion method")
        
        print(f"\n📁 Check screenshots/ folder for visual verification")

async def main():
    """Run the test."""
    import os
    os.makedirs("screenshots", exist_ok=True)
    
    test = ContractExpansionTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main())