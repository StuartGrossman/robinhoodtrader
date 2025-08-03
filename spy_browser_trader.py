#!/usr/bin/env python3
"""
SPY Options Browser Trader - Uses existing browser session
This version connects to your existing Chrome browser to avoid login issues
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

class SPYBrowserTrader:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
        self.tracked_options = []
        
    async def connect_to_existing_browser(self):
        """Connect to existing Chrome browser instead of creating new one."""
        print("🔗 Connecting to your existing Chrome browser...")
        print("📋 Make sure Chrome is open and you're logged into Robinhood!")
        
        try:
            self.playwright = await async_playwright().start()
            
            # Connect to existing Chrome browser
            # You need to start Chrome with debugging port:
            # chrome --remote-debugging-port=9222 --user-data-dir="~/chrome_debug"
            
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
                contexts = self.browser.contexts
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    if pages:
                        self.page = pages[0]
                        print("✅ Connected to existing browser session!")
                        return True
            except:
                print("⚠️ Could not connect to existing browser. Starting new one...")
                
            # Fallback: create new browser but use user data
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--disable-infobars"
                ]
            )
            
            # Create context
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            
            self.page = await context.new_page()
            
            # Set zoom to 50%
            await self.page.evaluate("document.body.style.zoom = '0.5'")
            
            print("✅ New browser session created (you'll need to login)")
            return True
            
        except Exception as e:
            print(f"❌ Error connecting to browser: {e}")
            return False
    
    async def navigate_to_spy_options(self):
        """Navigate directly to SPY options chain."""
        print("\n📊 Navigating to SPY options chain...")
        
        try:
            # Go directly to SPY options
            url = "https://robinhood.com/options/chains/SPY"
            print(f"🌐 Going to: {url}")
            
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # Set zoom
            await self.page.evaluate("document.body.style.zoom = '0.5'")
            
            print(f"✅ Current URL: {self.page.url}")
            
            # Check if we need to login
            if "login" in self.page.url:
                print("🔐 Please log in manually in the browser window...")
                print("⏳ Waiting for you to complete login...")
                
                # Wait for redirect away from login
                for i in range(120):  # 2 minutes
                    await asyncio.sleep(1)
                    current_url = self.page.url
                    if "login" not in current_url:
                        print(f"✅ Login successful! Now at: {current_url}")
                        break
                else:
                    print("⏰ Login timeout")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error navigating: {e}")
            return False
    
    async def load_options_data(self):
        """Properly load and expand options data."""
        print("\n🔄 Loading options data...")
        
        try:
            # Wait for page to load
            await asyncio.sleep(5)
            
            # Scroll to load data progressively
            print("📜 Scrolling to load all options...")
            
            # Get page height and scroll incrementally
            total_height = await self.page.evaluate("document.body.scrollHeight")
            current_position = 0
            scroll_step = 300
            
            while current_position < total_height:
                await self.page.evaluate(f"window.scrollTo(0, {current_position})")
                await asyncio.sleep(0.5)  # Short pause between scrolls
                current_position += scroll_step
                
                # Check if new content loaded
                new_height = await self.page.evaluate("document.body.scrollHeight")
                if new_height > total_height:
                    total_height = new_height
            
            print("✅ Finished scrolling")
            
            # Look for and click "Show more" or expand buttons
            expand_buttons = [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'button:has-text("View more")',
                '[aria-label*="expand"]',
                '[data-testid*="expand"]'
            ]
            
            for selector in expand_buttons:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        print(f"🔄 Found {count} '{selector}' buttons, clicking...")
                        for i in range(min(count, 10)):
                            try:
                                await elements.nth(i).click()
                                await asyncio.sleep(1)
                                print(f"   Clicked expand button {i+1}")
                            except:
                                continue
                except:
                    continue
            
            # Select today's expiration if available
            await self.select_today_expiration()
            
            # Final scroll to top to see all loaded data
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)
            
            print("✅ Options data loaded and expanded")
            return True
            
        except Exception as e:
            print(f"❌ Error loading options: {e}")
            return False
    
    async def select_today_expiration(self):
        """Try to select today's expiration date."""
        print("📅 Looking for today's expiration...")
        
        today = datetime.now()
        date_formats = [
            today.strftime("%m/%d"),
            today.strftime("%-m/%-d"),
            today.strftime("%m/%d/%Y"),
            today.strftime("%m/%d/%y"),
            "Today"
        ]
        
        for date_str in date_formats:
            try:
                # Look for date in various elements
                selectors = [
                    f'text="{date_str}"',
                    f'button:has-text("{date_str}")',
                    f'span:has-text("{date_str}")',
                    f'div:has-text("{date_str}")'
                ]
                
                for selector in selectors:
                    elements = self.page.locator(selector)
                    if await elements.count() > 0:
                        try:
                            await elements.first.click()
                            await asyncio.sleep(2)
                            print(f"✅ Selected expiration: {date_str}")
                            return True
                        except:
                            continue
                            
            except:
                continue
        
        print("⚠️ Could not find today's expiration - using default")
        return False
    
    async def extract_options_in_range(self):
        """Extract options in 8-16 cent range."""
        print("\n🎯 Extracting options in 8-16¢ range...")
        
        target_options = []
        
        try:
            # Get all text content first
            print("🔍 Analyzing page content...")
            page_content = await self.page.content()
            
            # Look for price patterns
            import re
            all_prices = re.findall(r'\$0\.\d{2}', page_content)
            target_prices = [p for p in all_prices if self.is_target_price(p)]
            
            print(f"📊 Found {len(all_prices)} total prices, {len(target_prices)} in target range")
            print(f"🎯 Target prices: {target_prices[:10]}")
            
            # Try different methods to extract option data
            methods = [
                self.extract_from_table_rows,
                self.extract_from_price_elements,
                self.extract_from_option_cards
            ]
            
            for method in methods:
                try:
                    options = await method()
                    if options:
                        target_options.extend(options)
                        print(f"✅ Method {method.__name__} found {len(options)} options")
                        break
                except Exception as e:
                    print(f"⚠️ Method {method.__name__} failed: {e}")
                    continue
            
            # Remove duplicates
            unique_options = []
            seen = set()
            for option in target_options:
                key = f"{option['type']}_{option['strike']}_{option['price']}"
                if key not in seen:
                    seen.add(key)
                    unique_options.append(option)
            
            self.tracked_options = unique_options
            print(f"\n✅ Found {len(unique_options)} unique options in 8-16¢ range:")
            
            for option in unique_options:
                print(f"   🎯 {option['type']} ${option['strike']} @ {option['price']}")
            
            return unique_options
            
        except Exception as e:
            print(f"❌ Error extracting options: {e}")
            return []
    
    def is_target_price(self, price_str):
        """Check if price is in 8-16 cent range."""
        try:
            # Extract numeric value (remove $ and convert to cents)
            price_value = float(price_str.replace('$', ''))
            price_cents = price_value * 100
            return 8 <= price_cents <= 16
        except:
            return False
    
    async def extract_from_table_rows(self):
        """Extract options from table rows."""
        print("📊 Extracting from table rows...")
        
        options = []
        table_rows = self.page.locator('tr, div[role="row"]')
        count = await table_rows.count()
        
        print(f"   Found {count} table rows")
        
        for i in range(min(count, 100)):
            try:
                row = table_rows.nth(i)
                row_text = await row.text_content()
                
                if '$0.' in row_text:
                    import re
                    prices = re.findall(r'\$0\.\d{2}', row_text)
                    for price in prices:
                        if self.is_target_price(price):
                            option = self.parse_option_from_text(row_text, price)
                            if option:
                                options.append(option)
                                
            except:
                continue
        
        return options
    
    async def extract_from_price_elements(self):
        """Extract options from price elements."""
        print("📊 Extracting from price elements...")
        
        options = []
        price_selectors = [
            'span:has-text("$0.")',
            'div:has-text("$0.")',
            'td:has-text("$0.")'
        ]
        
        for selector in price_selectors:
            try:
                elements = self.page.locator(selector)
                count = await elements.count()
                
                for i in range(min(count, 50)):
                    element = elements.nth(i)
                    price_text = await element.text_content()
                    
                    if self.is_target_price(price_text):
                        # Get parent context for more info
                        parent = element.locator('xpath=..')
                        parent_text = await parent.text_content()
                        
                        option = self.parse_option_from_text(parent_text, price_text)
                        if option:
                            options.append(option)
                            
            except:
                continue
        
        return options
    
    async def extract_from_option_cards(self):
        """Extract options from option cards/containers."""
        print("📊 Extracting from option cards...")
        
        options = []
        card_selectors = [
            '[data-testid*="option"]',
            '.option-card',
            '.option-row',
            'div:has-text("Call"):has-text("$")',
            'div:has-text("Put"):has-text("$")'
        ]
        
        for selector in card_selectors:
            try:
                elements = self.page.locator(selector)
                count = await elements.count()
                
                for i in range(min(count, 50)):
                    element = elements.nth(i)
                    card_text = await element.text_content()
                    
                    if '$0.' in card_text:
                        import re
                        prices = re.findall(r'\$0\.\d{2}', card_text)
                        for price in prices:
                            if self.is_target_price(price):
                                option = self.parse_option_from_text(card_text, price)
                                if option:
                                    options.append(option)
                                    
            except:
                continue
        
        return options
    
    def parse_option_from_text(self, text, price):
        """Parse option details from text."""
        try:
            import re
            
            # Determine type
            option_type = "CALL" if "Call" in text or "call" in text else "PUT" if "Put" in text or "put" in text else "UNKNOWN"
            
            # Extract strike price
            strikes = re.findall(r'\$(\d+\.?\d*)', text)
            strike = strikes[0] if strikes else "Unknown"
            
            # Extract volume if available
            volumes = re.findall(r'(\d+)\s*(?:vol|volume)', text, re.IGNORECASE)
            volume = volumes[0] if volumes else "0"
            
            return {
                "timestamp": datetime.now().isoformat(),
                "type": option_type,
                "strike": strike,
                "price": price,
                "volume": volume,
                "full_text": text[:200]
            }
            
        except:
            return None
    
    async def save_data(self):
        """Save extracted data."""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "session_type": "browser_trader",
                "tracked_options": self.tracked_options,
                "total_found": len(self.tracked_options)
            }
            
            # Save timestamped file
            filename = data_dir / f"spy_browser_trader_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Save latest
            latest_file = data_dir / "spy_browser_latest.json"
            with open(latest_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Data saved: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False
    
    async def close(self):
        """Clean up resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass

async def main():
    """Main function."""
    print("🚀 SPY Browser Trader")
    print("=" * 50)
    print("🔗 This version connects to your existing browser")
    print("📋 Make sure you're logged into Robinhood!")
    print("=" * 50)
    
    trader = SPYBrowserTrader()
    
    try:
        # Connect to browser
        if await trader.connect_to_existing_browser():
            
            # Navigate to SPY options
            if await trader.navigate_to_spy_options():
                
                # Load options data
                if await trader.load_options_data():
                    
                    # Extract target options
                    options = await trader.extract_options_in_range()
                    
                    # Save data
                    await trader.save_data()
                    
                    print(f"\n🎯 SUMMARY: Found {len(options)} options in 8-16¢ range")
                    
        print("\n🌐 Browser staying open for manual trading...")
        print("⏸️  Press Enter to close...")
        input()
        
    except KeyboardInterrupt:
        print("\n⏸️  Interrupted - Press Enter to close...")
        input()
    finally:
        await trader.close()

if __name__ == "__main__":
    asyncio.run(main())