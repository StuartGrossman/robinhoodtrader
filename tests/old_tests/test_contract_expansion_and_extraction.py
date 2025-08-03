#!/usr/bin/env python3
"""
Comprehensive test for contract expansion and data extraction
This test actually opens a contract, expands it, and extracts all data.
"""
import asyncio
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright

class ContractExpansionTest:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.main_context = None
        self.main_page = None
        
    async def setup_browser(self):
        """Setup browser connection."""
        try:
            self.playwright = await async_playwright().start()
            
            # Try to connect to existing browser first
            try:
                print("🔗 Attempting to connect to existing browser...")
                self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
                
                if not self.browser.contexts:
                    print("❌ No browser contexts found, launching new browser...")
                    await self.browser.close()
                    self.browser = await self.playwright.chromium.launch(headless=False)
                    print("✅ Launched new browser instance")
                else:
                    print("✅ Connected to existing browser")
                    
            except Exception as connect_error:
                print(f"⚠️ Failed to connect to existing browser: {connect_error}")
                print("🚀 Launching new browser instance...")
                self.browser = await self.playwright.chromium.launch(headless=False)
                print("✅ Launched new browser instance")
            
            # Create main context and page
            self.main_context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
            self.main_page = self.main_context.pages[0] if self.main_context.pages else await self.main_context.new_page()
            
            return True
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            return False
    
    async def navigate_to_spy_options(self):
        """Navigate to SPY options page."""
        try:
            print("📊 Loading SPY options page...")
            await self.main_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to load
            print("✅ SPY options page loaded")
            return True
        except Exception as e:
            print(f"❌ Failed to navigate to SPY options: {e}")
            return False
    
    async def click_call_tab(self):
        """Click the CALL tab."""
        try:
            print("📈 Clicking CALL tab...")
            await self.main_page.click('button:has-text("CALL")')
            await asyncio.sleep(2)
            print("✅ Clicked CALL tab")
            return True
        except Exception as e:
            print(f"❌ Failed to click CALL tab: {e}")
            return False
    
    async def find_and_expand_contract(self, target_price_cents):
        """Find and expand a specific contract."""
        try:
            price_text = f"$0.{target_price_cents:02d}"
            print(f"🔍 Looking for contract: {price_text}")
            
            # Try different price formats and search methods - target the contract row, not just the button
            search_patterns = [
                f'[data-testid*="ChainTableRow"]:has-text("{target_price_cents:02d}")',  # Contract row
                f'div:has-text("{price_text}")',  # Any div containing the price
                f'[class*="row"]:has-text("{target_price_cents:02d}")',  # Row with price
                f'button:has-text("{price_text}")',  # Button as fallback
                f'text="{price_text}"',
                f'text="{target_price_cents:02d}¢"',
                f'text="{target_price_cents}¢"',
            ]
            
            # Scroll to find the contract
            found = False
            price_elements = None
            
            for scroll_attempt in range(10):
                try:
                    await self.main_page.evaluate("window.scrollBy(0, 200)")
                    await asyncio.sleep(1)
                    
                    # Try different search patterns
                    for pattern in search_patterns:
                        try:
                            elements = self.main_page.locator(pattern)
                            count = await elements.count()
                            
                            if count > 0:
                                print(f"✅ Found {price_text} using pattern: {pattern}")
                                price_elements = elements
                                found = True
                                break
                        except:
                            continue
                    
                    if found:
                        break
                    else:
                        print(f"🔍 Scroll attempt {scroll_attempt + 1}: {price_text} not found yet")
                        
                except Exception as scroll_error:
                    print(f"⚠️ Scroll error: {scroll_error}")
                    continue
            
            if not found:
                print(f"❌ Could not find {price_text} after scrolling")
                print("🔍 Trying to find any available contracts...")
                
                # Try to find any contract in the 8-16¢ range
                for cents in range(8, 17):
                    test_price = f"$0.{cents:02d}"
                    for pattern in search_patterns:
                        try:
                            elements = self.main_page.locator(pattern)
                            count = await elements.count()
                            if count > 0:
                                print(f"✅ Found alternative contract: {test_price}")
                                price_elements = elements
                                found = True
                                target_price_cents = cents
                                price_text = test_price
                                break
                        except:
                            continue
                    if found:
                        break
                
                if not found:
                    print("❌ Could not find any contracts in 8-16¢ range")
                    return None
            
            # Try to click and expand the contract
            print(f"🖱️ Attempting to expand {price_text}...")
            
            # Try multiple click strategies - click on the contract row, not the button
            click_strategies = [
                lambda: price_elements.first.click(),
                lambda: price_elements.first.click(button="left"),
                lambda: price_elements.first.click(force=True),
                lambda: price_elements.first.click(delay=100),
            ]
            
            expanded = False
            for strategy_idx, click_strategy in enumerate(click_strategies):
                try:
                    print(f"  🖱️ Trying click strategy {strategy_idx + 1}")
                    await click_strategy()
                    await asyncio.sleep(3)  # Wait for expansion
                    
                    # Check if expansion worked
                    if await self.verify_expansion():
                        print(f"  ✅ Strategy {strategy_idx + 1} worked!")
                        expanded = True
                        break
                    else:
                        print(f"  ⚠️ Strategy {strategy_idx + 1} didn't expand contract")
                        
                except Exception as strategy_error:
                    print(f"  ❌ Strategy {strategy_idx + 1} failed: {strategy_error}")
                    continue
            
            if not expanded:
                print(f"❌ Failed to expand {price_text}")
                return None
            
            print(f"✅ Successfully expanded {price_text}")
            return target_price_cents
            
        except Exception as e:
            print(f"❌ Error expanding contract: {e}")
            return None
    
    async def verify_expansion(self):
        """Verify that the contract is actually expanded."""
        try:
            # Wait for expansion to complete
            await asyncio.sleep(2)
            
            # Get page content
            content = await self.main_page.content()
            
            # Check for expansion text indicators
            expansion_text_indicators = [
                'theta', 'gamma', 'delta', 'vega', 
                'volume', 'open interest', 'implied volatility',
                'bid', 'ask', 'strike', 'expiration'
            ]
            
            text_indicators_found = sum(1 for indicator in expansion_text_indicators 
                                       if indicator.lower() in content.lower())
            
            print(f"  🔍 Found {text_indicators_found}/{len(expansion_text_indicators)} text indicators")
            
            # Also check for HTML element indicators
            expansion_indicators = [
                '[class*="expanded"]',
                '[class*="details"]',
                '[class*="option-details"]',
                '[class*="contract-details"]',
                '[class*="greeks"]',
                '[class*="volume"]',
                '[class*="bid-ask"]',
                '[class*="strike"]',
                '[class*="expiration"]'
            ]
            
            element_indicators_found = 0
            for indicator in expansion_indicators:
                try:
                    elements = self.main_page.locator(indicator)
                    if await elements.count() > 0:
                        element_indicators_found += 1
                except:
                    continue
            
            print(f"  🔍 Found {element_indicators_found} HTML element indicators")
            
            # Consider expanded if we have sufficient indicators
            is_expanded = text_indicators_found >= 3 or element_indicators_found >= 2
            
            if is_expanded:
                print(f"  ✅ Contract appears to be expanded")
            else:
                print(f"  ❌ Contract does not appear to be expanded")
            
            return is_expanded
            
        except Exception as e:
            print(f"  ❌ Error verifying expansion: {e}")
            return False
    
    async def extract_contract_data(self, price_cents):
        """Extract all data from the expanded contract."""
        try:
            print(f"📊 Extracting data from expanded contract...")
            
            # Wait for data to load
            await asyncio.sleep(3)
            
            # Get page content
            content = await self.main_page.content()
            
            # Enhanced extraction patterns based on actual HTML structure
            patterns = {
                'current_price': [
                    r'(?:Last|Price|Mark|Current)[:\s]+\$?(\d+\.\d{2,4})',
                    r'Premium[:\s]+\$?(\d+\.\d{2,4})', 
                    r'\$(\d+\.\d{2,4})\s*(?:Last|Current)',
                    r'(\d+\.\d{2,4})\s*USD',
                    r'Mark[:\s]*\$?(\d+\.\d{2,4})',
                    r'Share price[:\s]*\$?(\d+\.\d{2,4})',
                    r'Mark[:\s]*\$?(\d+\.\d{2,4})',  # From HTML: Mark $4.22
                ],
                'bid': [
                    r'Bid[:\s]+\$?(\d+\.\d{2,4})',
                    r'Bid\s*\$?(\d+\.\d{2,4})',
                    r'Bid[:\s]*\$?(\d+\.\d{2,4})',
                    r'\$(\d+\.\d{2,4})\s*×\s*\d+',
                    r'Bid[:\s]*(\d+\.\d{2,4})',
                    r'\$(\d+\.\d{2,4})\s*×\s*\d+',  # From HTML: $4.20 × 75
                    r'Bid.*?\$(\d+\.\d{2,4})',  # Match Bid followed by $price
                ],
                'ask': [
                    r'Ask[:\s]+\$?(\d+\.\d{2,4})',
                    r'Ask\s*\$?(\d+\.\d{2,4})',
                    r'Ask[:\s]*\$?(\d+\.\d{2,4})',
                    r'\$(\d+\.\d{2,4})\s*×\s*\d+',
                    r'Ask[:\s]*(\d+\.\d{2,4})',
                    r'\$(\d+\.\d{2,4})\s*×\s*\d+',  # From HTML: $4.24 × 112
                    r'Ask.*?\$(\d+\.\d{2,4})',  # Match Ask followed by $price
                ],
                'volume': [
                    r'Volume[:\s]+(\d+(?:,\d+)*)',
                    r'Vol[:\s]+(\d+(?:,\d+)*)',
                    r'Volume[:\s]*(\d+(?:,\d+)*)',
                    r'Volume[:\s]*(\d{1,3}(?:,\d{3})*)',
                    r'Volume[:\s]*(\d+)',
                    r'Volume[:\s]*(\d{1,3}(?:,\d{3})*)',  # From HTML: 20,484
                    r'Volume.*?(\d{1,3}(?:,\d{3})*)',  # Match Volume followed by number
                ],
                'open_interest': [
                    r'Open Interest[:\s]+(\d+(?:,\d+)*)',
                    r'OI[:\s]+(\d+(?:,\d+)*)',
                    r'Open Interest[:\s]*(\d+(?:,\d+)*)',
                    r'Open interest[:\s]*(\d{1,3}(?:,\d{3})*)',
                    r'Open Interest[:\s]*(\d+)',
                    r'Open interest[:\s]*(\d+)',  # From HTML: 98
                    r'Open interest.*?(\d+)',  # Match Open interest followed by number
                ],
                'theta': [
                    r'Theta[:\s]+(-?\d+\.\d{2,4})',
                    r'θ[:\s]+(-?\d+\.\d{2,4})',
                    r'Theta[:\s]*(-?\d+\.\d+)',
                    r'θ[:\s]*(-?\d+\.\d+)',
                    r'Theta[:\s]*(-?\d+\.\d{4})',
                    r'Theta[:\s]*(\d+\.\d{4})',
                    r'Theta[:\s]*(-?\d+\.\d{4})',
                    r'Theta[:\s]*(-?\d+\.\d{2,4})',
                    r'Theta[:\s]*(-?\d+\.\d{4})',  # From HTML: -0.9404
                    r'Theta.*?(-?\d+\.\d{4})',  # Match Theta followed by number
                ],
                'gamma': [
                    r'Gamma[:\s]+(\d+\.\d{2,4})',
                    r'Γ[:\s]+(\d+\.\d{2,4})',
                    r'Gamma[:\s]*(\d+\.\d+)',
                    r'Γ[:\s]*(\d+\.\d+)',
                    r'Gamma[:\s]*(\d+\.\d{4})',
                    r'Gamma[:\s]*(\d+\.\d{2,4})',
                    r'Gamma[:\s]*(\d+\.\d{4})',  # From HTML: 0.0481
                    r'Gamma.*?(\d+\.\d{4})',  # Match Gamma followed by number
                ],
                'delta': [
                    r'Delta[:\s]+(-?\d+\.\d{2,4})',
                    r'Δ[:\s]+(-?\d+\.\d{2,4})',
                    r'Delta[:\s]*(-?\d+\.\d+)',
                    r'Δ[:\s]*(-?\d+\.\d+)',
                    r'Delta[:\s]*(-?\d+\.\d{4})',
                    r'Delta[:\s]*(-?\d+\.\d{2,4})',
                    r'Delta[:\s]*(\d+\.\d{4})',  # From HTML: 0.5934
                    r'Delta.*?(\d+\.\d{4})',  # Match Delta followed by number
                ],
                'vega': [
                    r'Vega[:\s]+(\d+\.\d{2,4})',
                    r'ν[:\s]+(\d+\.\d{2,4})',
                    r'Vega[:\s]*(\d+\.\d+)',
                    r'ν[:\s]*(\d+\.\d+)',
                    r'Vega[:\s]*(\d+\.\d{4})',
                    r'Vega[:\s]*(\d+\.\d{2,4})',
                    r'Vega[:\s]*(\d+\.\d{4})',  # From HTML: 0.1667
                    r'Vega.*?(\d+\.\d{4})',  # Match Vega followed by number
                ],
                'high': [
                    r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2,4})',
                    r'High\s+\$?(\d+\.\d{2,4})',
                    r'High[:\s]*\$?(\d+\.\d{2,4})',
                    r'High[:\s]*\$?(\d+\.\d{2,4})',  # From HTML: $7.09
                ],
                'low': [
                    r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2,4})',
                    r'Low\s+\$?(\d+\.\d{2,4})',
                    r'Low[:\s]*\$?(\d+\.\d{2,4})',
                    r'Low[:\s]*\$?(\d+\.\d{2,4})',  # From HTML: $3.05
                ],
                'iv': [
                    r'(?:Implied\s+)?(?:Vol|Volatility)[:\s]+(\d+\.\d+)%?',
                    r'IV[:\s]+(\d+\.\d+)%?',
                    r'Implied Volatility[:\s]*(\d+\.\d+)%?',
                    r'Implied volatility[:\s]*(\d+\.\d+)%?',  # From HTML: 18.75%
                ],
                'strike': [
                    r'Strike[:\s]+\$?(\d+)',
                    r'Strike\s+Price[:\s]+\$?(\d+)',
                    r'Strike[:\s]*\$?(\d+)',
                ],
                'expiration': [
                    r'(?:Exp|Expires?)[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
                    r'Expiration[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
                    r'Expires[:\s]*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
                ]
            }
            
            data = {
                'type': 'CALL',
                'price_cents': price_cents,
                'price_text': f"$0.{price_cents:02d}",
                'symbol': 'SPY',
                'timestamp': datetime.now().isoformat()
            }
            
            extracted_fields = 0
            for field, pattern_list in patterns.items():
                for pattern in pattern_list:
                    try:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            value = matches[0].replace(',', '').strip()
                            data[field] = value
                            extracted_fields += 1
                            print(f"    ✅ {field}: {value}")
                            break
                    except Exception as pattern_error:
                        continue
            
            print(f"📊 Total fields extracted: {extracted_fields}")
            
            # Take a screenshot of the expanded contract
            try:
                screenshot_path = f"screenshots/test_expanded_contract_{price_cents:02d}.png"
                await self.main_page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
            except Exception as screenshot_error:
                print(f"⚠️ Screenshot failed: {screenshot_error}")
            
            # Save HTML content for debugging
            try:
                html_path = f"screenshots/test_expanded_contract_{price_cents:02d}.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"📄 HTML saved: {html_path}")
            except Exception as html_error:
                print(f"⚠️ HTML save failed: {html_error}")
            
            return data, extracted_fields
            
        except Exception as e:
            print(f"❌ Error extracting data: {e}")
            return None, 0
    
    async def run_test(self, target_price_cents=8):
        """Run the complete test."""
        print("🚀 Contract Expansion and Data Extraction Test")
        print("=" * 60)
        
        try:
            # Setup browser
            if not await self.setup_browser():
                return False
            
            # Navigate to SPY options
            if not await self.navigate_to_spy_options():
                return False
            
            # Click CALL tab
            if not await self.click_call_tab():
                return False
            
            # Find and expand contract
            expanded_price_cents = await self.find_and_expand_contract(target_price_cents)
            if not expanded_price_cents:
                return False
            
            # Extract data
            data, fields_extracted = await self.extract_contract_data(expanded_price_cents)
            
            if data and fields_extracted >= 5:
                print(f"\n✅ TEST PASSED: Successfully extracted {fields_extracted} fields")
                print(f"📋 Extracted data: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"\n❌ TEST FAILED: Only extracted {fields_extracted} fields")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
        finally:
            # Cleanup
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

async def main():
    """Main test function."""
    test = ContractExpansionTest()
    success = await test.run_test(target_price_cents=8)
    
    if success:
        print("\n🎉 SUCCESS: Contract expansion and data extraction working!")
    else:
        print("\n💥 FAILURE: Contract expansion and data extraction failed!")
    
    return success

if __name__ == "__main__":
    asyncio.run(main()) 