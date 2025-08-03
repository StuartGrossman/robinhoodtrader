#!/usr/bin/env python3
"""
SPY Options Day Trading Bot
Follows a systematic approach for same-day SPY options trading:
1. Manual login to Robinhood
2. Navigate to same-day SPY options chain
3. Track options in 8-16 cent range (puts and calls)
4. Monitor volatility and price movement
5. Track daily lows and RSI values
6. Provide trading signals
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from src.robinhood_automation import RobinhoodAutomation, AuthConfig

class SPYDayTrader:
    def __init__(self, automation):
        self.automation = automation
        self.tracked_options = []
        self.price_history = {}
        self.daily_lows = {}
        self.trading_data = {
            "session_start": datetime.now().isoformat(),
            "spy_price_history": [],
            "tracked_options": [],
            "trading_signals": []
        }
        
    async def initialize_session(self):
        """Initialize trading session with manual login."""
        print("🚀 SPY Day Trading Session Starting")
        print("=" * 50)
        print("📋 TRADING PROCESS:")
        print("1. ✅ Open browser (DONE)")
        print("2. 🔐 Manual login (YOUR TURN)")
        print("3. 📊 Navigate to same-day SPY options")
        print("4. 🎯 Filter options: 8-16 cent range")
        print("5. 📈 Monitor volatility & price movement")
        print("6. 📉 Track daily lows & RSI signals")
        print("7. 🎯 Generate trading signals")
        print("=" * 50)
        
        # Navigate to login page first
        await self.automation.page.goto("https://robinhood.com/login", wait_until="networkidle")
        
        # Set zoom for better visibility
        await self.automation.page.evaluate("document.body.style.zoom = '0.5'")
        
        print("🌐 Browser opened at login page (zoomed to 50%)")
        print("🔐 Please log in manually in the browser window...")
        print("⏳ Waiting for you to complete login...")
        
        # Wait for login completion
        await self.wait_for_login()
        
    async def wait_for_login(self):
        """Wait for manual login completion."""
        print("⏳ Monitoring for successful login...")
        
        for i in range(300):  # Wait up to 5 minutes
            try:
                # Check if we're authenticated
                if await self.automation._is_authenticated():
                    print("✅ Login successful! Proceeding to options chain...")
                    return True
                    
                # Check current URL to see progress
                current_url = self.automation.page.url
                if "login" not in current_url.lower():
                    print(f"🔄 Page changed to: {current_url}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                await asyncio.sleep(1)
                continue
                
        print("⏰ Login timeout - please ensure you're logged in")
        return False
        
    async def navigate_to_same_day_options(self):
        """Navigate to same-day SPY options chain."""
        print("\n📊 Navigating to SPY options chain...")
        
        # Get today's date for same-day options
        today = datetime.now()
        
        # Try the direct options chain URL
        spy_options_url = "https://robinhood.com/options/chains/SPY"
        
        try:
            await self.automation.page.goto(spy_options_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)
            
            print(f"✅ Navigated to: {spy_options_url}")
            print("🔄 Scrolling to load options data...")
            
            # Scroll down to load more options data
            await self.automation.page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(2)
            await self.automation.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)
            
            print("🔍 Looking for same-day expiration options...")
            
            # Look for today's expiration date in various formats
            today_formats = [
                today.strftime("%m/%d"),
                today.strftime("%m/%d/%Y"), 
                today.strftime("%m/%d/%y"),
                today.strftime("%-m/%-d"),  # No leading zeros
                "Today",
                today.strftime("%B %d")  # Full month name
            ]
            
            print(f"🎯 Searching for expiration dates: {today_formats}")
            
            # Try to find and click today's expiration
            expiration_found = False
            for date_format in today_formats:
                if expiration_found:
                    break
                    
                date_selectors = [
                    f'text="{date_format}"',
                    f'button:has-text("{date_format}")',
                    f'[data-testid*="expiration"]:has-text("{date_format}")',
                    f'div:has-text("{date_format}")',
                    f'span:has-text("{date_format}")',
                    f'li:has-text("{date_format}")'
                ]
                
                for selector in date_selectors:
                    try:
                        elements = self.automation.page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            print(f"📅 Found expiration '{date_format}' with selector: {selector}")
                            await elements.first.click()
                            await asyncio.sleep(3)
                            print("✅ Selected same-day expiration")
                            expiration_found = True
                            break
                    except Exception as e:
                        continue
            
            if not expiration_found:
                print("⚠️ Could not find today's expiration - using default view")
            
            # Scroll to see more options
            print("📜 Scrolling to load all option chains...")
            for i in range(3):
                await self.automation.page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
            
            # Look for and expand option chains if needed
            expand_selectors = [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                '[data-testid*="expand"]',
                'button:has-text("+")'
            ]
            
            for selector in expand_selectors:
                try:
                    elements = self.automation.page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        print(f"🔄 Found {count} expand buttons, clicking them...")
                        for i in range(min(count, 5)):  # Click first 5
                            await elements.nth(i).click()
                            await asyncio.sleep(1)
                except Exception:
                    continue
            
            # Final scroll to see all loaded data
            await self.automation.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # Take screenshot of options chain
            await self.automation._take_screenshot("spy_options_chain_loaded")
            
            print("✅ Options chain loaded and ready for scanning")
            return True
            
        except Exception as e:
            print(f"❌ Error navigating to options: {e}")
            return False
            
    async def scan_options_in_range(self):
        """Scan for options in the 8-16 cent price range."""
        print("\n🎯 Scanning for options in 8-16 cent range...")
        
        target_options = []
        
        try:
            # Wait for options data to load
            await asyncio.sleep(3)
            
            # First, let's get all text content to see what's available
            print("🔍 Analyzing page content...")
            page_text = await self.automation.page.text_content('body')
            
            # Look for option price patterns in the text
            import re
            price_patterns = re.findall(r'\$0\.\d{2}', page_text)
            if price_patterns:
                print(f"📊 Found price patterns: {price_patterns[:10]}...")
            
            # Look for option price elements with broader selectors
            price_selectors = [
                'span:has-text("$0.")',
                'div:has-text("$0.")',
                'td:has-text("$0.")',
                '[class*="price"]:has-text("$")',
                '[data-testid*="price"]',
                'span:text-matches(r"^\\$0\\.\\d+$")',
                '*:has-text("$"):text-matches(r"\\$0\\.(0[8-9]|1[0-6])")'
            ]
            
            print("🔍 Scanning option prices with multiple selectors...")
            
            for i, selector in enumerate(price_selectors):
                try:
                    elements = self.automation.page.locator(selector)
                    count = await elements.count()
                    
                    if count > 0:
                        print(f"📊 Selector {i+1}: Found {count} elements with '{selector[:30]}...'")
                        
                        for j in range(min(count, 20)):  # Check first 20 elements
                            try:
                                element = elements.nth(j)
                                price_text = await element.text_content()
                                
                                if price_text and price_text.strip():
                                    print(f"   Price text {j+1}: '{price_text.strip()}'")
                                    
                                    if self.is_in_target_range(price_text):
                                        # Found option in target range
                                        option_data = await self.extract_option_details(element)
                                        if option_data:
                                            target_options.append(option_data)
                                            print(f"🎯 FOUND TARGET: {option_data['type']} {option_data['strike']} @ {option_data['price']}")
                                        
                            except Exception as e:
                                continue
                                
                        # If we found some options with this selector, stop trying others
                        if target_options:
                            break
                            
                except Exception as e:
                    print(f"⚠️ Error with selector '{selector[:30]}...': {e}")
                    continue
            
            # Alternative approach: scan all table rows
            if not target_options:
                print("🔄 Trying table-based scanning...")
                table_elements = self.automation.page.locator('tr, div[role="row"]')
                table_count = await table_elements.count()
                
                if table_count > 0:
                    print(f"📊 Found {table_count} table rows to scan")
                    
                    for i in range(min(table_count, 50)):
                        try:
                            row = table_elements.nth(i)
                            row_text = await row.text_content()
                            
                            if row_text and '$0.' in row_text:
                                print(f"   Row {i}: {row_text[:100]}...")
                                
                                # Extract prices from the row text
                                row_prices = re.findall(r'\$0\.\d{2}', row_text)
                                for price in row_prices:
                                    if self.is_in_target_range(price):
                                        option_data = {
                                            "timestamp": datetime.now().isoformat(),
                                            "price": price,
                                            "full_text": row_text[:200],
                                            "type": "CALL" if "Call" in row_text else "PUT" if "Put" in row_text else "UNKNOWN",
                                            "strike": self.extract_strike_price(row_text),
                                            "volume": self.extract_volume(row_text),
                                            "source": "table_scan"
                                        }
                                        target_options.append(option_data)
                                        print(f"🎯 TABLE FOUND: {option_data['type']} {option_data['strike']} @ {option_data['price']}")
                                        
                        except Exception as e:
                            continue
            
            self.tracked_options = target_options
            print(f"\n✅ Found {len(target_options)} options in 8-16¢ range")
            
            # Save initial scan results
            if target_options:
                self.trading_data["tracked_options"] = target_options
                await self.save_trading_data()
            
            return target_options
            
        except Exception as e:
            print(f"❌ Error scanning options: {e}")
            return []
            
    def is_in_target_range(self, price_text):
        """Check if price is in 8-16 cent range."""
        try:
            # Extract numeric value from price text
            price_text = price_text.replace('$', '').replace('¢', '')
            
            # Convert to cents
            if '.' in price_text:
                price_value = float(price_text)
                price_cents = price_value * 100
            else:
                price_cents = float(price_text)
                
            # Check if in range (8-16 cents)
            return 8 <= price_cents <= 16
            
        except:
            return False
            
    async def extract_option_details(self, element):
        """Extract detailed information about an option."""
        try:
            # Get parent container to find strike, type, etc.
            parent = element.locator('xpath=ancestor::tr | xpath=ancestor::div[contains(@class,"option")]')
            
            if await parent.count() > 0:
                parent_text = await parent.first.text_content()
                
                # Extract details from text
                option_data = {
                    "timestamp": datetime.now().isoformat(),
                    "price": await element.text_content(),
                    "full_text": parent_text,
                    "type": "CALL" if "Call" in parent_text or "C" in parent_text else "PUT",
                    "strike": self.extract_strike_price(parent_text),
                    "volume": self.extract_volume(parent_text),
                    "bid": None,
                    "ask": None
                }
                
                return option_data
                
        except Exception as e:
            print(f"⚠️ Error extracting option details: {e}")
            
        return None
        
    def extract_strike_price(self, text):
        """Extract strike price from option text."""
        import re
        # Look for dollar amounts that could be strikes
        strikes = re.findall(r'\$(\d+\.?\d*)', text)
        if strikes:
            return f"${strikes[0]}"
        return "Unknown"
        
    def extract_volume(self, text):
        """Extract volume from option text."""
        import re
        # Look for volume indicators
        volumes = re.findall(r'Vol:?\s*(\d+)', text, re.IGNORECASE)
        if volumes:
            return volumes[0]
        return "0"
        
    async def monitor_price_movement(self):
        """Monitor price movement of tracked options."""
        print("\n📈 Starting price movement monitoring...")
        print("🎯 Tracking volatility and identifying daily lows...")
        print("⏸️  Press Ctrl+C to stop monitoring and get trading signals")
        
        monitoring_count = 0
        
        try:
            while True:
                monitoring_count += 1
                print(f"\n📊 Monitoring cycle #{monitoring_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Update SPY current price
                spy_price = await self.get_current_spy_price()
                if spy_price:
                    self.trading_data["spy_price_history"].append({
                        "timestamp": datetime.now().isoformat(),
                        "price": spy_price
                    })
                    print(f"📈 SPY: {spy_price}")
                
                # Update tracked options prices
                updated_options = await self.update_tracked_options()
                
                # Analyze for daily lows and signals
                signals = self.analyze_for_signals()
                if signals:
                    print("🚨 TRADING SIGNALS DETECTED:")
                    for signal in signals:
                        print(f"   {signal}")
                
                # Save data periodically
                if monitoring_count % 5 == 0:
                    await self.save_trading_data()
                
                # Wait before next cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            return await self.generate_final_signals()
            
    async def get_current_spy_price(self):
        """Get current SPY price."""
        try:
            # Navigate to SPY if not already there
            current_url = self.automation.page.url
            if "SPY" not in current_url:
                await self.automation.page.goto("https://robinhood.com/stocks/SPY", wait_until="networkidle")
                await asyncio.sleep(2)
            
            # Look for price elements
            price_selectors = [
                '[data-testid="stock-price"]',
                '.stock-price',
                'span:text-matches(r"\\$\\d+\\.\\d+")>text',
                'div:has-text("$"):text-matches(r"\\$\\d+\\.\\d+")'
            ]
            
            for selector in price_selectors:
                elements = self.automation.page.locator(selector)
                if await elements.count() > 0:
                    price_text = await elements.first.text_content()
                    if price_text and "$" in price_text:
                        return price_text.strip()
                        
        except Exception as e:
            print(f"⚠️ Error getting SPY price: {e}")
            
        return None
        
    async def update_tracked_options(self):
        """Update prices for tracked options."""
        # This would require navigating back to options chain
        # For now, return placeholder
        print("🔄 Updating tracked options prices...")
        return self.tracked_options
        
    def analyze_for_signals(self):
        """Analyze current data for trading signals."""
        signals = []
        
        # Check for daily lows
        if len(self.trading_data["spy_price_history"]) > 10:
            recent_prices = [float(p["price"].replace("$", "")) for p in self.trading_data["spy_price_history"][-10:]]
            current_price = recent_prices[-1]
            min_price = min(recent_prices)
            
            if current_price == min_price:
                signals.append(f"🔴 SPY at potential daily low: ${current_price}")
                
        # Add more signal logic here (RSI, volume, etc.)
        
        return signals
        
    async def generate_final_signals(self):
        """Generate final trading recommendations."""
        print("\n" + "=" * 50)
        print("🎯 FINAL TRADING ANALYSIS")
        print("=" * 50)
        
        print(f"📊 Tracked Options: {len(self.tracked_options)}")
        print(f"📈 SPY Price Points: {len(self.trading_data['spy_price_history'])}")
        
        # Show tracked options
        if self.tracked_options:
            print("\n🎯 OPTIONS IN 8-16¢ RANGE:")
            for option in self.tracked_options[:10]:
                print(f"   {option['type']} {option['strike']} @ {option['price']}")
        
        # Generate recommendations
        recommendations = [
            "Monitor RSI on 1m and 5m charts",
            "Look for volume spikes in tracked options", 
            "Consider entries on daily low breaks",
            "Set tight stop losses for day trades"
        ]
        
        print("\n💡 TRADING RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"   • {rec}")
            
        await self.save_trading_data()
        return recommendations
        
    async def save_trading_data(self):
        """Save trading session data."""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save session data
            session_file = data_dir / f"spy_trading_session_{timestamp}.json"
            with open(session_file, 'w') as f:
                json.dump(self.trading_data, f, indent=2)
            
            # Save as latest
            latest_file = data_dir / "spy_trading_latest.json"
            with open(latest_file, 'w') as f:
                json.dump(self.trading_data, f, indent=2)
                
            print(f"💾 Trading data saved: {session_file.name}")
            
        except Exception as e:
            print(f"⚠️ Error saving data: {e}")

async def main():
    """Main SPY day trading function."""
    print("🚀 SPY Options Day Trader")
    print("=" * 50)
    
    # Create config
    config = AuthConfig(
        username="grossman.stuart1@gmail.com",
        password="Alenviper123!",
        headless=False,
        browser_timeout=60000
    )
    
    automation = RobinhoodAutomation(config)
    trader = SPYDayTrader(automation)
    
    try:
        # Step 1: Initialize browser and wait for manual login
        await automation.initialize_browser()
        await trader.initialize_session()
        
        # Step 2: Navigate to same-day options
        if await trader.navigate_to_same_day_options():
            
            # Step 3: Scan for options in 8-16 cent range
            target_options = await trader.scan_options_in_range()
            
            if target_options:
                # Step 4: Monitor price movement and generate signals
                await trader.monitor_price_movement()
            else:
                print("❌ No options found in target range")
                
        print("\n🌐 Browser staying open for manual trading...")
        print("⏸️  Press Enter to close when done...")
        input()
        
    except KeyboardInterrupt:
        print("\n⏸️  Session interrupted - Press Enter to close...")
        input()
    finally:
        await automation.close()

if __name__ == "__main__":
    asyncio.run(main())