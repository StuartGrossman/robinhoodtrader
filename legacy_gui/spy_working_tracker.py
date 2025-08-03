#!/usr/bin/env python3
"""
SPY Working Contract Tracker - Based on proven test method
"""
import asyncio
import json
import yfinance as yf
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright
import talib
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import time

class WorkingContractTracker:
    def __init__(self, option_type):
        self.option_type = option_type.lower()  # 'call' or 'put'
        self.contracts = {}  # contract_key -> data
        self.browser = None
        self.playwright = None
        self.page = None
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup simple working GUI."""
        self.root = tk.Tk()
        self.root.title(f"🚀 SPY {self.option_type.upper()} Working Tracker")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0d1117')
        
        # Title
        title = tk.Label(self.root, text=f"📊 SPY {self.option_type.upper()} TRACKER (WORKING VERSION)", 
                        font=('Arial', 16, 'bold'), fg='#7ee787', bg='#0d1117')
        title.pack(pady=10)
        
        # Controls
        controls_frame = tk.Frame(self.root, bg='#161b22')
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_btn = tk.Button(controls_frame, text=f"🔄 Find & Expand {self.option_type.upper()}s", 
                                  command=self.start_analysis,
                                  font=('Arial', 12, 'bold'),
                                  bg='#238636', fg='white', pady=8)
        self.start_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.status_label = tk.Label(controls_frame, text="Status: Ready", 
                                    font=('Arial', 11), fg='#7ee787', bg='#161b22')
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Terminal
        self.terminal = scrolledtext.ScrolledText(self.root, height=30, width=120,
                                                 bg='#0d1117', fg='#f0f6fc', 
                                                 font=('Courier', 10))
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Welcome message
        self.log("🎯 Working Contract Tracker Ready")
        self.log("📋 Uses PROVEN method from successful test")
        self.log("🎯 Target: Find contracts in 40-80¢ range")
        self.log("🔄 Expand contracts using tested click method")
        
    def log(self, message):
        """Add message to terminal."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {message}\n")
        self.terminal.see(tk.END)
        self.root.update()
        
    def update_status(self, status):
        """Update status display."""
        self.status_label.config(text=f"Status: {status}")
        self.root.update()
    
    def start_analysis(self):
        """Start analysis in background."""
        self.start_btn.config(state='disabled', text='🔄 Working...')
        thread = threading.Thread(target=self.run_analysis_thread)
        thread.daemon = True
        thread.start()
        
    def run_analysis_thread(self):
        """Run analysis in separate thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.find_and_expand_contracts())
        except Exception as e:
            self.log(f"❌ Analysis error: {e}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state='normal', text=f'🔄 Find & Expand {self.option_type.upper()}s'))
    
    async def find_and_expand_contracts(self):
        """Find and expand contracts using PROVEN method."""
        try:
            # Connect to browser
            self.update_status("Connecting to browser...")
            self.log("🌐 Connecting to browser...")
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            if not self.browser.contexts:
                self.log("❌ No browser contexts found")
                return
            
            # Find or create SPY page
            context = self.browser.contexts[0]
            pages = context.pages
            
            self.log(f"🔍 Checking {len(pages)} browser tabs...")
            
            spy_page = None
            for i, page in enumerate(pages):
                url = page.url
                if "robinhood.com" in url:
                    self.log(f"  Tab {i+1}: {url}")
                    if "SPY" in url:
                        spy_page = page
                        self.log(f"  ✅ Found SPY page at tab {i+1}")
                        break
            
            # If no SPY page found, try to navigate to it
            if not spy_page:
                self.log("🌐 No SPY page found, attempting to navigate...")
                
                # Try to use an existing Robinhood page
                rh_page = None
                for page in pages:
                    if "robinhood.com" in page.url:
                        rh_page = page
                        break
                
                if rh_page:
                    self.log("📊 Found Robinhood page, navigating to SPY options...")
                    try:
                        await rh_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
                        await asyncio.sleep(5)
                        spy_page = rh_page
                        self.log("✅ Successfully navigated to SPY options")
                    except Exception as nav_error:
                        self.log(f"❌ Navigation failed: {nav_error}")
                        self.log("💡 Please manually navigate to robinhood.com/options/chains/SPY")
                        return
                else:
                    # Create new page
                    self.log("🆕 Creating new page for SPY options...")
                    try:
                        spy_page = await context.new_page()
                        await spy_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
                        await asyncio.sleep(5)
                        self.log("✅ Successfully created and navigated to SPY options")
                    except Exception as create_error:
                        self.log(f"❌ Failed to create new page: {create_error}")
                        self.log("💡 Please manually navigate to robinhood.com/options/chains/SPY")
                        return
            
            # Check if we're logged in
            if "login" in spy_page.url:
                self.log("🔐 Please log into Robinhood first")
                return
            
            self.page = spy_page
            self.log("✅ Found SPY options page")
            
            # Click option type tab
            self.update_status(f"Clicking {self.option_type} tab...")
            self.log(f"📈 Clicking {self.option_type.upper()} tab...")
            
            tab_button = spy_page.locator(f'button:has-text("{self.option_type.title()}")')
            if await tab_button.count() > 0:
                await tab_button.click()
                await asyncio.sleep(4)
                self.log(f"✅ Clicked {self.option_type.upper()} tab")
            else:
                self.log(f"❌ Could not find {self.option_type.upper()} tab")
                return
            
            # Take screenshot
            await spy_page.screenshot(path=f"screenshots/working_{self.option_type}_page.png")
            self.log("📸 Page screenshot saved")
            
            # Find contracts using PROVEN method
            self.update_status("Finding contracts...")
            self.log("🔍 Finding contracts using proven method...")
            
            contracts = await self.find_contracts_proven_method(spy_page)
            
            if not contracts:
                self.log("❌ No contracts found")
                return
            
            self.log(f"🎯 Found {len(contracts)} contracts to expand")
            
            # Expand each contract
            for i, contract in enumerate(contracts[:5]):  # Limit to 5
                self.log(f"\n📋 [{i+1}/{min(len(contracts), 5)}] Expanding {contract['price']}¢ contract...")
                
                success = await self.expand_contract_proven_method(spy_page, contract)
                
                if success:
                    self.log(f"✅ Successfully expanded {contract['price']}¢ contract")
                    
                    # Extract data
                    data = await self.extract_contract_data(spy_page, contract['price'])
                    if data:
                        self.contracts[f"{self.option_type}_{contract['price']}"] = data
                        self.log(f"📊 Extracted {len(data)} data fields")
                        self.display_contract_summary(data)
                    
                    # Take screenshot of expanded contract
                    await spy_page.screenshot(path=f"screenshots/expanded_{self.option_type}_{contract['price']}.png")
                    
                else:
                    self.log(f"❌ Failed to expand {contract['price']}¢ contract")
                
                # Small delay between expansions
                await asyncio.sleep(2)
            
            self.log(f"\n🎉 Analysis complete! Successfully processed {len(self.contracts)} contracts")
            self.update_status(f"Complete - {len(self.contracts)} contracts expanded")
            
        except Exception as e:
            self.log(f"❌ Error in analysis: {e}")
        finally:
            if self.playwright:
                await self.playwright.stop()
    
    async def find_contracts_proven_method(self, page):
        """Find contracts using the proven method from our test."""
        try:
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Get all prices on page
            content = await page.content()
            all_prices = re.findall(r'\$0\.(\d{2})', content)
            
            if not all_prices:
                self.log("❌ No price patterns found")
                return []
            
            unique_prices = sorted(list(set(all_prices)))
            self.log(f"💰 Found prices on page: {unique_prices}")
            
            # Filter to reasonable range (30-90¢ to be safe)
            target_prices = [p for p in unique_prices if 30 <= int(p) <= 90]
            
            if not target_prices:
                self.log(f"⚠️ No contracts in 30-90¢ range. Available: {unique_prices}")
                # Use any available prices as fallback
                target_prices = unique_prices[:5]
            
            self.log(f"🎯 Target prices: {target_prices}")
            
            # Find clickable elements for each price
            contracts = []
            
            for price_str in target_prices[:10]:  # Limit to 10
                try:
                    price_cents = int(price_str)
                    price_text = f"$0.{price_str}"
                    
                    # Use proven selector
                    elements = page.locator(f':has-text("{price_text}")')
                    count = await elements.count()
                    
                    if count > 0:
                        element = elements.first
                        box = await element.bounding_box()
                        
                        if box and box['width'] > 10 and box['height'] > 10:
                            contracts.append({
                                'price': price_cents,
                                'element': element,
                                'text': price_text
                            })
                            self.log(f"  ✅ Found clickable {price_cents}¢ contract")
                        
                except Exception:
                    continue
            
            return contracts
            
        except Exception as e:
            self.log(f"❌ Error finding contracts: {e}")
            return []
    
    async def expand_contract_proven_method(self, page, contract):
        """Expand contract using proven method."""
        try:
            element = contract['element']
            price = contract['price']
            
            # Scroll to top
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            # Additional scroll to top
            await page.evaluate('''
                (element) => {
                    const rect = element.getBoundingClientRect();
                    window.scrollTo({
                        top: window.scrollY + rect.top - 30,
                        behavior: 'smooth'
                    });
                }
            ''', await element.element_handle())
            
            await asyncio.sleep(2)
            
            # Get click position
            box = await element.bounding_box()
            if not box:
                return False
            
            # Use proven click position (30% from left)
            click_x = box['x'] + (box['width'] * 0.3)
            click_y = box['y'] + (box['height'] * 0.5)
            
            self.log(f"  🖱️ Clicking at ({click_x:.0f}, {click_y:.0f}) to expand...")
            
            # Click
            await page.mouse.click(click_x, click_y)
            await asyncio.sleep(4)
            
            # Check if expanded
            content = await page.content()
            indicators = ['theta', 'gamma', 'bid', 'ask', 'volume']
            found = [ind for ind in indicators if ind.lower() in content.lower()]
            
            if len(found) >= 3:
                self.log(f"  ✅ Contract expanded! Found: {', '.join(found)}")
                return True
            else:
                self.log(f"  ⚠️ May not be expanded. Found: {', '.join(found)}")
                return False
                
        except Exception as e:
            self.log(f"  ❌ Error expanding: {e}")
            return False
    
    async def extract_contract_data(self, page, price_cents):
        """Extract data from expanded contract."""
        try:
            content = await page.content()
            
            data = {
                'price_cents': price_cents,
                'timestamp': datetime.now().isoformat()
            }
            
            # IMPROVED data extraction patterns based on successful testing
            patterns = {
                'bid': [
                    r'bid.*?(\d+\.\d+)',
                    r'Bid.*?(\d+\.\d+)',
                    r'"bid"[^"]*?(\d+\.\d+)',
                ],
                'ask': [
                    r'Ask Price.*?(\d+\.\d+)',
                    r'ask.*?(\d+\.\d+)',
                    r'Ask.*?(\d+\.\d+)',
                    r'"ask"[^"]*?(\d+\.\d+)',
                ],
                'volume': [
                    r'volume[^0-9]*(\d+)',
                    r'Volume[^0-9]*(\d+)',
                    r'vol[^0-9]*(\d+)',
                ]
            }
            
            # Extract using improved patterns
            for field, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        data[field] = matches[0].replace(',', '').strip()
                        break
            
            # Extract current price from dollar amounts
            dollar_amounts = re.findall(r'\$(\d+\.\d+)', content)
            if dollar_amounts:
                reasonable_prices = [float(d) for d in dollar_amounts if 0.1 <= float(d) <= 10.0]
                if reasonable_prices:
                    data['current_price'] = str(min(reasonable_prices))
            
            # Extract strike price
            strike_patterns = [r'strike.*?(\d+)', r'Strike.*?(\d+)', r'\$(\d{3})']
            for pattern in strike_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    reasonable_strikes = [int(m) for m in matches if 500 <= int(m) <= 700]
                    if reasonable_strikes:
                        data['strike'] = str(reasonable_strikes[0])
                        break
            
            # Extract Greeks from decimal numbers (estimated)
            decimal_numbers = re.findall(r'(\d+\.\d{2,4})', content)
            if decimal_numbers:
                decimals = [float(d) for d in decimal_numbers]
                
                # Theta (usually negative, but we'll take small positives too)
                potential_theta = [d for d in decimals if -1.0 <= d <= 1.0]
                if potential_theta:
                    data['theta'] = str(potential_theta[0])
                
                # Gamma (usually small positive)
                potential_gamma = [d for d in decimals if 0.0 < d <= 1.0]
                if potential_gamma:
                    data['gamma'] = str(potential_gamma[0])
                
                # Delta (between 0-1 for options)
                potential_delta = [d for d in decimals if 0.0 <= d <= 1.0 and d != float(data.get('gamma', -1))]
                if potential_delta:
                    data['delta'] = str(potential_delta[0])
            
            return data
            
        except Exception as e:
            self.log(f"❌ Error extracting data: {e}")
            return None
    
    def display_contract_summary(self, data):
        """Display contract data summary."""
        self.log("  " + "="*40)
        self.log(f"  📊 CONTRACT: {data.get('price_cents', 'N/A')}¢")
        self.log(f"  💰 Bid: ${data.get('bid', 'N/A')}")
        self.log(f"  💰 Ask: ${data.get('ask', 'N/A')}")
        self.log(f"  📊 Volume: {data.get('volume', 'N/A')}")
        self.log(f"  🏷️ Theta: {data.get('theta', 'N/A')}")
        self.log(f"  🏷️ Gamma: {data.get('gamma', 'N/A')}")
        self.log(f"  📈 Strike: ${data.get('strike', 'N/A')}")
        self.log("  " + "="*40)
    
    def show(self):
        """Show the GUI."""
        self.root.mainloop()

def main():
    """Main function."""
    print("🚀 SPY Working Contract Tracker")
    print("=" * 40)
    print("Choose option type:")
    print("1. CALLS")
    print("2. PUTS")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == '1':
        tracker = WorkingContractTracker('call')
    elif choice == '2':
        tracker = WorkingContractTracker('put')
    else:
        print("Invalid choice. Using CALLS.")
        tracker = WorkingContractTracker('call')
    
    # Make screenshots directory
    import os
    os.makedirs("screenshots", exist_ok=True)
    
    tracker.show()

if __name__ == "__main__":
    main()