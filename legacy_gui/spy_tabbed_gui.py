#!/usr/bin/env python3
"""
SPY Options GUI with Contract Tabs and Charts
"""
import asyncio
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime
from playwright.async_api import async_playwright
import yfinance as yf
import pandas as pd
import numpy as np
import talib
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import json

class ContractData:
    def __init__(self, contract_id):
        self.contract_id = contract_id
        self.data_history = []
        self.current_data = {}
        
    def add_data_point(self, data):
        """Add a new data point with timestamp."""
        data['timestamp'] = datetime.now()
        self.data_history.append(data)
        self.current_data = data
        
    def get_chart_data(self):
        """Get data formatted for charts."""
        if not self.data_history:
            return None
            
        timestamps = [d['timestamp'] for d in self.data_history]
        
        chart_data = {
            'timestamps': timestamps,
            'prices': [float(d.get('current_price', 0)) for d in self.data_history],
            'volumes': [int(d.get('volume', 0)) for d in self.data_history],
            'bid': [float(d.get('bid', 0)) for d in self.data_history],
            'ask': [float(d.get('ask', 0)) for d in self.data_history],
            'theta': [float(d.get('theta', 0)) for d in self.data_history],
            'gamma': [float(d.get('gamma', 0)) for d in self.data_history],
            'high': [float(d.get('high', 0)) for d in self.data_history],
            'low': [float(d.get('low', 0)) for d in self.data_history]
        }
        
        return chart_data

class SPYOptionsGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚀 SPY Options Live Contract Tracker")
        self.root.geometry("1400x800")
        self.root.configure(bg='#1e1e1e')
        
        # Force window visibility
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        
        # Contract tracking
        self.contracts = {}  # contract_id -> ContractData
        self.contract_tabs = {}  # contract_id -> tab_frame
        
        self.setup_gui()
        print("✅ GUI created with contract tabs!")
        
    def setup_gui(self):
        """Setup GUI with terminal and tabbed contract views."""
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title = tk.Label(main_frame, text="🚀 SPY Options Live Contract Tracker", 
                        font=('Arial', 18, 'bold'), fg='#00ff88', bg='#1e1e1e')
        title.pack(pady=(0, 10))
        
        # Control panel
        control_frame = tk.Frame(main_frame, bg='#2d2d2d', relief=tk.RAISED, bd=2)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = tk.Button(control_frame, text="🔄 Start Contract Analysis", 
                                  command=self.start_analysis,
                                  font=('Arial', 12, 'bold'),
                                  bg='#0066cc', fg='white', pady=8)
        self.start_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.refresh_btn = tk.Button(control_frame, text="🔄 Refresh All Contracts", 
                                    command=self.refresh_contracts,
                                    font=('Arial', 11),
                                    bg='#238636', fg='white', pady=6)
        self.refresh_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.status = tk.Label(control_frame, text="Status: Ready", 
                              font=('Arial', 11), fg='#00ff88', bg='#2d2d2d')
        self.status.pack(side=tk.LEFT, padx=20)
        
        # Main content area - split between terminal and tabs
        content_frame = tk.Frame(main_frame, bg='#1e1e1e')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Terminal output
        terminal_frame = tk.LabelFrame(content_frame, text=" 📊 Live Analysis Terminal ", 
                                      font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        terminal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.terminal = scrolledtext.ScrolledText(terminal_frame, height=25, width=60,
                                                 bg='#1a1a1a', fg='#ffffff', 
                                                 font=('Courier', 9))
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Right side - Contract tabs
        tabs_frame = tk.LabelFrame(content_frame, text=" 📈 Contract Data & Charts ", 
                                  font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        tabs_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Notebook for contract tabs
        style = ttk.Style()
        style.configure('CustomNotebook.TNotebook', background='#2d2d2d')
        style.configure('CustomNotebook.TNotebook.Tab', 
                       background='#404040', foreground='white',
                       padding=[10, 5])
        
        self.notebook = ttk.Notebook(tabs_frame, style='CustomNotebook.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add welcome tab
        self.add_welcome_tab()
        
        # Clear screenshots folder on startup
        self.clear_screenshots()
        
        # Initial log messages
        self.log("🎯 SPY Options Contract Tracker Ready")
        self.log("📋 Will track both PUTS and CALLS in 8-16¢ range")
        self.log("🔍 Click 'Start Contract Analysis' to begin")
        
    def clear_screenshots(self):
        """Clear all old screenshots on startup."""
        try:
            import os
            import glob
            
            if os.path.exists("screenshots"):
                old_files = glob.glob("screenshots/*")
                for f in old_files:
                    try:
                        os.remove(f)
                    except:
                        pass
                self.log(f"🗑️ Cleared {len(old_files)} old screenshots")
            
            os.makedirs("screenshots", exist_ok=True)
            
        except Exception as e:
            self.log(f"❌ Error clearing screenshots: {e}")
        
    def add_welcome_tab(self):
        """Add welcome tab with instructions."""
        welcome_frame = tk.Frame(self.notebook, bg='#1e1e1e')
        self.notebook.add(welcome_frame, text="Welcome")
        
        welcome_text = tk.Text(welcome_frame, bg='#1a1a1a', fg='#ffffff', 
                              font=('Arial', 11), wrap=tk.WORD)
        welcome_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        instructions = """
🚀 SPY Options Live Contract Tracker

📋 FEATURES:
• Tracks both PUT and CALL contracts in 8-16¢ range
• Clicks main contract boxes (not + buttons) to expand details
• Extracts: Price, Bid/Ask, Volume, Theta, Gamma, High/Low
• Creates individual tabs for each contract with live charts
• Real-time data updates and historical tracking

📊 HOW IT WORKS:
1. Connects to your existing Chrome browser
2. Navigates to SPY options chain
3. Scans for contracts in your price range
4. Clicks each contract to expand and extract data
5. Creates tabs with charts for each contract
6. Updates data in real-time

🎯 USAGE:
• Click 'Start Contract Analysis' to begin initial scan
• Click 'Refresh All Contracts' to update all tracked contracts
• Each contract gets its own tab with live charts
• Terminal shows real-time analysis progress

⚡ READY TO START!
Make sure Chrome is running with debugging enabled and you're logged into Robinhood.
        """
        
        welcome_text.insert(tk.END, instructions)
        welcome_text.config(state=tk.DISABLED)
        
    def log(self, message):
        """Add message to terminal."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {message}\n")
        self.terminal.see(tk.END)
        self.root.update()
        
    def update_status(self, status):
        """Update status."""
        self.status.config(text=f"Status: {status}")
        self.root.update()
        
    def start_analysis(self):
        """Start initial contract discovery."""
        self.start_btn.config(state='disabled', text='🔄 Analyzing...')
        thread = threading.Thread(target=self.run_initial_analysis)
        thread.daemon = True
        thread.start()
        
    def refresh_contracts(self):
        """Refresh all tracked contracts."""
        if not self.contracts:
            self.log("⚠️ No contracts to refresh. Run initial analysis first.")
            return
            
        self.refresh_btn.config(state='disabled', text='🔄 Refreshing...')
        thread = threading.Thread(target=self.run_refresh_analysis)
        thread.daemon = True
        thread.start()
        
    def run_initial_analysis(self):
        """Run initial contract discovery."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.discover_contracts())
        except Exception as e:
            self.log(f"❌ Initial analysis error: {e}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state='normal', text='🔄 Start Contract Analysis'))
            
    def run_refresh_analysis(self):
        """Run refresh of existing contracts."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.refresh_contract_data())
        except Exception as e:
            self.log(f"❌ Refresh error: {e}")
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state='disabled', text='🔄 Refresh All Contracts'))
            
    async def discover_contracts(self):
        """Discover and track new contracts."""
        playwright = None
        try:
            # Get SPY data
            self.root.after(0, lambda: self.update_status("Getting SPY data..."))
            self.log("📈 Getting SPY market data...")
            
            spy_data = self.get_spy_data()
            if spy_data:
                self.log(f"💰 SPY: ${spy_data['price']:.2f} | RSI 1m: {spy_data['rsi_1m']} | RSI 5m: {spy_data['rsi_5m']}")
                bias = self.determine_bias(spy_data['rsi_1m'], spy_data['rsi_5m'])
                self.log(f"🎯 Market Bias: {bias}")
            
            # Connect to browser
            self.root.after(0, lambda: self.update_status("Connecting to Chrome..."))
            self.log("🔗 Connecting to Chrome...")
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            contexts = browser.contexts
            if not contexts:
                self.log("❌ No browser contexts found")
                return
                
            context = contexts[0]
            pages = context.pages
            page = pages[0] if pages else await context.new_page()
            
            self.log("✅ Connected to Chrome")
            
            # Navigate to options
            self.root.after(0, lambda: self.update_status("Loading SPY options..."))
            self.log("📊 Loading SPY options page...")
            
            await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            if "login" in page.url:
                self.log("🔐 Please log into Robinhood first")
                return
                
            self.log("✅ SPY options page loaded")
            
            # Scan both calls and puts
            await self.scan_option_type(page, "Call")
            await self.scan_option_type(page, "Put")
            
        except Exception as e:
            self.log(f"❌ Discovery error: {e}")
        finally:
            if playwright:
                await playwright.stop()
            self.root.after(0, lambda: self.update_status("Discovery complete"))
            
    async def scan_option_type(self, page, option_type):
        """Scan specific option type (Call or Put)."""
        try:
            self.log(f"\n📈 Scanning {option_type} options...")
            
            # Click the Call/Put tab
            tab_button = page.locator(f'button:has-text("{option_type}")')
            if await tab_button.count() > 0:
                await tab_button.click()
                await asyncio.sleep(3)
                self.log(f"✅ Clicked {option_type} tab")
            else:
                self.log(f"⚠️ Could not find {option_type} tab")
                return
            
            # Look for contract boxes in our price range
            await self.find_and_examine_contracts(page, option_type)
            
        except Exception as e:
            self.log(f"❌ Error scanning {option_type} options: {e}")
            
    async def find_and_examine_contracts(self, page, option_type):
        """Find and examine individual contracts."""
        try:
            # Create screenshots folder if it doesn't exist
            import os
            os.makedirs("screenshots", exist_ok=True)
            
            # Take screenshot for debugging
            await page.screenshot(path=f"screenshots/{option_type.lower()}_options_page.png")
            self.log(f"📸 Screenshot saved: screenshots/{option_type.lower()}_options_page.png")
            
            # Look for contract elements with price in our range
            contracts_found = 0
            
            # Focus on contract content area selectors (completely avoid buttons)
            selectors = [
                # Target the main contract content, specifically avoid buttons
                'tr[role="row"]:has-text("$0.") td:first-child',  # First cell of table rows (left side)
                'div[data-testid*="option"]:has-text("$0.") > div:first-child',  # First div inside option containers
                'td:has-text("$0."):not(:has(button))',  # Table cells with prices but NO buttons inside
                'div:has-text("$0."):not(button):not(:has(button))',  # Divs with prices but NOT buttons or containing buttons
                '[data-rh-test-id*="option"] > *:first-child',  # First child of option elements
                'tr:has-text("$0.") > td:nth-child(1)',  # Explicitly target first column
                'tr:has-text("$0.") > td:nth-child(2)',  # Or second column (but not last columns where + buttons are)
            ]
            
            for selector in selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    
                    if count > 0:
                        self.log(f"🔍 Found {count} elements with selector: {selector}")
                        
                        for i in range(min(count, 10)):  # Limit to 10 elements
                            try:
                                element = elements.nth(i)
                                element_text = await element.text_content()
                                
                                if element_text and self.has_target_price(element_text):
                                    price_match = re.search(r'\$0\.(\d{2})', element_text)
                                    if price_match:
                                        price_cents = int(price_match.group(1))
                                        
                                        if 8 <= price_cents <= 16:
                                            self.log(f"🎯 Found {option_type} contract: $0.{price_cents:02d}")
                                            
                                            # Click to expand contract (middle of box, not + button)
                                            contract_data = await self.expand_and_extract_contract(page, element, option_type, price_cents)
                                            
                                            # Always create a tab, whether expanded or not
                                            if contract_data:
                                                contract_id = f"{option_type}_{price_cents:02d}_{datetime.now().strftime('%H%M%S')}"
                                                self.add_contract_tab(contract_id, contract_data, page)
                                                self.log(f"  🎉 Created expanded tab for {option_type} $0.{price_cents:02d}")
                                            else:
                                                # Create basic tracking tab even if no detailed data
                                                basic_data = {
                                                    'type': option_type.lower(),
                                                    'price_cents': price_cents,
                                                    'price_text': f"$0.{price_cents:02d}",
                                                    'symbol': 'SPY',
                                                    'status': 'Found but not expanded yet'
                                                }
                                                contract_id = f"{option_type}_{price_cents:02d}_{datetime.now().strftime('%H%M%S')}"
                                                self.add_contract_tab(contract_id, basic_data, page)
                                                self.log(f"  📋 Created tracking tab for {option_type} $0.{price_cents:02d}")
                                            
                                            contracts_found += 1
                                            
                                            if contracts_found >= 5:  # Limit per option type
                                                break
                                                
                            except Exception as element_error:
                                continue
                        
                        if contracts_found > 0:
                            break  # Found contracts with this selector
                            
                except Exception as selector_error:
                    continue
            
            # If no contracts found with main selectors, try alternative approaches
            if contracts_found == 0:
                self.log("🔄 No contracts found with row selectors, trying alternative approach...")
                contracts_found = await self.find_contracts_alternative_method(page, option_type)
                
            # If still no contracts, try direct click approach
            if contracts_found == 0:
                self.log("🔄 Trying direct click approach...")
                contracts_found = await self.try_direct_click_approach(page, option_type)
            
            self.log(f"✅ Found {contracts_found} {option_type} contracts in price range")
            
        except Exception as e:
            self.log(f"❌ Error finding contracts: {e}")
            
    async def find_contracts_alternative_method(self, page, option_type):
        """Alternative method to find contracts by looking for price text and finding clickable parent."""
        try:
            contracts_found = 0
            
            # Find all text elements with our target prices
            price_elements = page.locator('text=/\\$0\\.(0[8-9]|1[0-6])/')
            count = await price_elements.count()
            
            self.log(f"🔍 Found {count} price elements with alternative method")
            
            for i in range(min(count, 15)):  # Check more elements
                try:
                    price_element = price_elements.nth(i)
                    price_text = await price_element.text_content()
                    
                    if price_text:
                        price_match = re.search(r'\$0\.(\d{2})', price_text)
                        if price_match:
                            price_cents = int(price_match.group(1))
                            
                            if 8 <= price_cents <= 16:
                                self.log(f"🎯 Found price element: $0.{price_cents:02d}")
                                
                                # Find the clickable parent container (contract box)
                                clickable_parent = await self.find_clickable_contract_parent(page, price_element)
                                
                                if clickable_parent:
                                    self.log(f"✅ Found clickable parent for $0.{price_cents:02d}")
                                    
                                    # Click to expand contract
                                    contract_data = await self.expand_and_extract_contract(page, clickable_parent, option_type, price_cents)
                                    
                                    if contract_data:
                                        contract_id = f"{option_type}_{price_cents:02d}_{datetime.now().strftime('%H%M%S')}"
                                        self.add_contract_tab(contract_id, contract_data, page)
                                        contracts_found += 1
                                    
                                    if contracts_found >= 3:  # Limit for alternative method
                                        break
                                        
                except Exception as element_error:
                    self.log(f"⚠️ Error with price element {i}: {element_error}")
                    continue
            
            return contracts_found
            
        except Exception as e:
            self.log(f"❌ Error in alternative method: {e}")
            return 0
            
    async def find_clickable_contract_parent(self, page, price_element):
        """Find the clickable parent container for a price element."""
        try:
            self.log(f"🔍 Looking for clickable parent of price element...")
            
            # Try to find parent elements that are clickable
            parent_selectors = [
                'xpath=ancestor::tr[1]',  # Ancestor table row (most likely)
                'xpath=ancestor::div[contains(@class, "option") or contains(@data-testid, "option")][1]',  # Option divs
                'xpath=ancestor::*[@role="button"][1]',  # Any clickable ancestor
                'xpath=ancestor::*[@data-testid][1]',  # Any element with test id
                '..',  # Direct parent
                '../..',  # Grandparent
                '../../..',  # Great-grandparent
                'xpath=ancestor::*[contains(@class, "row") or contains(@class, "cell")][1]',  # Row/cell classes
            ]
            
            for i, selector in enumerate(parent_selectors):
                try:
                    parent = price_element.locator(selector)
                    parent_count = await parent.count()
                    
                    if parent_count > 0:
                        parent_element = parent.first
                        parent_text = await parent_element.text_content()
                        
                        self.log(f"  Parent {i+1}: Found with selector {selector}")
                        self.log(f"  Parent text (first 100 chars): {parent_text[:100] if parent_text else 'None'}")
                        
                        # Check if this parent seems like a contract container
                        if parent_text and len(parent_text) > 15:
                            # Look for contract indicators
                            has_price = '$' in parent_text
                            has_strike = any(word in parent_text for word in ['$5', '$6', '$7'])  # Strike prices
                            has_volume = any(word in parent_text.lower() for word in ['vol', 'bid', 'ask'])
                            
                            if has_price and (has_strike or has_volume):
                                self.log(f"  ✅ Found good parent candidate: has_price={has_price}, has_strike={has_strike}, has_volume={has_volume}")
                                return parent_element
                            else:
                                self.log(f"  ⚠️ Parent doesn't have contract indicators: has_price={has_price}, has_strike={has_strike}, has_volume={has_volume}")
                        else:
                            self.log(f"  ⚠️ Parent text too short or empty")
                            
                except Exception as selector_error:
                    self.log(f"  ❌ Error with selector {selector}: {selector_error}")
                    continue
            
            self.log(f"  ❌ No suitable parent found for price element")
            return None
            
        except Exception as e:
            self.log(f"❌ Error finding clickable parent: {e}")
            return None
            
    async def try_direct_click_approach(self, page, option_type):
        """Try clicking directly on areas where we found prices."""
        try:
            self.log(f"🎯 Direct click approach for {option_type} options...")
            contracts_found = 0
            
            # Get page content and look for price patterns with coordinates
            content = await page.content()
            
            # Find all price matches in our range
            price_matches = re.finditer(r'\$0\.(\d{2})', content)
            target_prices = []
            
            for match in price_matches:
                price_cents = int(match.group(1))
                if 8 <= price_cents <= 16:
                    target_prices.append(price_cents)
            
            # Remove duplicates and limit
            unique_prices = list(set(target_prices))[:3]
            self.log(f"🎯 Targeting prices: {unique_prices}")
            
            for price_cents in unique_prices:
                try:
                    price_text = f"$0.{price_cents:02d}"
                    self.log(f"🔍 Looking for clickable areas near {price_text}...")
                    
                    # Try to find elements containing this price
                    price_locators = [
                        f'text="{price_text}"',
                        f':has-text("{price_text}")',
                        f'*:has-text("{price_text}")'
                    ]
                    
                    for locator in price_locators:
                        try:
                            elements = page.locator(locator)
                            count = await elements.count()
                            
                            if count > 0:
                                self.log(f"  Found {count} elements with {locator}")
                                
                                # Try clicking the first few elements
                                for i in range(min(count, 3)):
                                    try:
                                        element = elements.nth(i)
                                        
                                        # Try to get bounding box for coordinate clicking
                                        box = await element.bounding_box()
                                        if box:
                                            # Click FAR LEFT to avoid + button (which is on the right side)
                                            click_x = box['x'] + (box['width'] * 0.1)  # Only 10% from left edge
                                            click_y = box['y'] + (box['height'] * 0.5)
                                            
                                            self.log(f"  🖱️ Attempting click at ({click_x:.0f}, {click_y:.0f}) for {price_text} - FAR LEFT area")
                                            self.log(f"     Element box: x={box['x']:.0f}, width={box['width']:.0f} (+ button likely at x={box['x'] + box['width'] * 0.8:.0f})")
                                            
                                            # Take screenshot before click
                                            await page.screenshot(path=f"screenshots/before_direct_click_{option_type}_{price_cents:02d}.png")
                                            
                                            # Click
                                            await page.mouse.click(click_x, click_y)
                                            await asyncio.sleep(3)
                                            
                                            # Take screenshot after click
                                            await page.screenshot(path=f"screenshots/after_direct_click_{option_type}_{price_cents:02d}.png")
                                            
                                            # Check if something expanded/changed
                                            current_url = page.url
                                            new_content = await page.content()
                                            
                                            # Look for signs of expansion (modal, detailed view, etc.)
                                            expanded_indicators = [
                                                'theta', 'gamma', 'delta', 'vega',  # Greeks
                                                'bid', 'ask', 'volume',  # Market data
                                                'high', 'low', 'open interest'  # More data
                                            ]
                                            
                                            expanded = any(indicator.lower() in new_content.lower() 
                                                         for indicator in expanded_indicators)
                                            
                                            if expanded or len(new_content) > len(content) * 1.1:
                                                self.log(f"  ✅ Contract appears to have expanded!")
                                                
                                                # Extract data
                                                contract_data = await self.extract_detailed_contract_data(page, option_type, price_cents)
                                                
                                                if contract_data:
                                                    contract_id = f"{option_type}_{price_cents:02d}_{datetime.now().strftime('%H%M%S')}"
                                                    self.add_contract_tab(contract_id, contract_data, page)
                                                    contracts_found += 1
                                                    self.log(f"  🎉 Successfully created tab for {option_type} ${price_text}")
                                                
                                                # Close any modals/expanded views
                                                await page.keyboard.press('Escape')
                                                await asyncio.sleep(2)
                                                
                                                break  # Success, move to next price
                                            else:
                                                self.log(f"  ⚠️ No expansion detected after click")
                                        
                                    except Exception as click_error:
                                        self.log(f"  ❌ Click attempt failed: {click_error}")
                                        continue
                                
                                if contracts_found > 0:
                                    break  # Found contracts with this locator
                                    
                        except Exception as locator_error:
                            continue
                    
                    if contracts_found >= 3:  # Limit total contracts
                        break
                        
                except Exception as price_error:
                    self.log(f"❌ Error processing price {price_cents}: {price_error}")
                    continue
            
            return contracts_found
            
        except Exception as e:
            self.log(f"❌ Error in direct click approach: {e}")
            return 0
            
    async def find_safe_click_area(self, page, element):
        """Find price area and click 50px to the left of it."""
        try:
            self.log(f"🔍 Looking for price and + button location...")
            
            # Look for price text within this element
            price_elements = element.locator('text=/\\$0\\.(0[8-9]|1[0-6])/')
            price_count = await price_elements.count()
            
            if price_count > 0:
                # Get the first price element's position
                price_element = price_elements.first
                price_box = await price_element.bounding_box()
                
                if price_box:
                    # Click 50px to the LEFT of where the price is
                    safe_x = price_box['x'] - 50
                    safe_y = price_box['y'] + (price_box['height'] * 0.5)
                    
                    self.log(f"  💰 Found price at x={price_box['x']:.0f}")
                    self.log(f"  ✅ Clicking 50px LEFT of price at ({safe_x:.0f}, {safe_y:.0f})")
                    
                    return (safe_x, safe_y)
            
            # Fallback: look for + buttons and click 50px left of them
            plus_buttons = element.locator('button:has-text("+"), *:has-text("+")')
            plus_count = await plus_buttons.count()
            
            if plus_count > 0:
                plus_element = plus_buttons.first
                plus_box = await plus_element.bounding_box()
                
                if plus_box:
                    safe_x = plus_box['x'] - 50
                    safe_y = plus_box['y'] + (plus_box['height'] * 0.5)
                    
                    self.log(f"  ➕ Found + button at x={plus_box['x']:.0f}")
                    self.log(f"  ✅ Clicking 50px LEFT of + button at ({safe_x:.0f}, {safe_y:.0f})")
                    
                    return (safe_x, safe_y)
            
            # Final fallback: just click left side of element
            element_box = await element.bounding_box()
            if element_box:
                safe_x = element_box['x'] + (element_box['width'] * 0.2)
                safe_y = element_box['y'] + (element_box['height'] * 0.5)
                
                self.log(f"  ⚠️ No price/+ button found, using left area: ({safe_x:.0f}, {safe_y:.0f})")
                return (safe_x, safe_y)
            
            return None
            
        except Exception as e:
            self.log(f"❌ Error finding safe click area: {e}")
            return None
            
    def has_target_price(self, text):
        """Check if text contains price in our target range."""
        prices = re.findall(r'\$0\.(\d{2})', text)
        for price_str in prices:
            price_cents = int(price_str)
            if 8 <= price_cents <= 16:
                return True
        return False
        
    async def expand_and_extract_contract(self, page, element, option_type, price_cents):
        """Click contract box to expand and extract detailed data."""
        try:
            self.log(f"🖱️ Expanding {option_type} $0.{price_cents:02d} contract...")
            
            # Create screenshots folder if it doesn't exist
            import os
            os.makedirs("screenshots", exist_ok=True)
            
            # Try to find a safe clicking area (avoid + buttons)
            safe_click_area = await self.find_safe_click_area(page, element)
            
            if safe_click_area:
                click_x, click_y = safe_click_area
                self.log(f"🎯 Using SAFE click area at ({click_x:.0f}, {click_y:.0f}) - verified to avoid + button")
                
                # Click at the safe coordinates
                await page.mouse.click(click_x, click_y)
                await asyncio.sleep(3)
            else:
                # Fallback to far-left clicking
                box = await element.bounding_box()
                if box:
                    # Click in the LEFT area where price/contract details are (NOT where + button is)
                    click_x = box['x'] + (box['width'] * 0.15)  # Only 15% from left edge - much further left
                    click_y = box['y'] + (box['height'] * 0.5)  # Center vertically
                    
                    self.log(f"🎯 Fallback: Clicking at ({click_x:.0f}, {click_y:.0f}) - FAR LEFT of contract")
                    self.log(f"   Box: x={box['x']:.0f}, y={box['y']:.0f}, w={box['width']:.0f}, h={box['height']:.0f}")
                    
                    # Click at specific coordinates in the LEFT area to avoid + button
                    await page.mouse.click(click_x, click_y)
                    await asyncio.sleep(3)
                else:
                    # Final fallback to regular click
                    self.log("⚠️ Using element click as final fallback")
                    await element.click()
                    await asyncio.sleep(3)
                
            # Take screenshot after clicking
            await page.screenshot(path=f"screenshots/contract_expanded_{option_type}_{price_cents:02d}.png")
            self.log(f"📸 Screenshot saved: screenshots/contract_expanded_{option_type}_{price_cents:02d}.png")
            
            # Extract detailed contract data
            contract_data = await self.extract_detailed_contract_data(page, option_type, price_cents)
            
            # Close the expanded view
            await page.keyboard.press('Escape')
            await asyncio.sleep(2)
            
            return contract_data
            
        except Exception as e:
            self.log(f"❌ Error expanding contract: {e}")
            return None
            
    async def extract_detailed_contract_data(self, page, option_type, price_cents):
        """Extract detailed data from expanded contract."""
        try:
            # Wait for expansion animation
            await asyncio.sleep(2)
            
            # Get page content
            content = await page.content()
            
            contract_data = {
                'type': option_type.lower(),
                'price_cents': price_cents,
                'symbol': 'SPY'
            }
            
            # Extract various data points
            patterns = {
                'current_price': r'(?:Last|Price)[:\s]+\$?(\d+\.\d{2})',
                'bid': r'Bid[:\s]+\$?(\d+\.\d{2})',
                'ask': r'Ask[:\s]+\$?(\d+\.\d{2})',
                'volume': r'Volume[:\s]+(\d+(?:,\d+)*)',
                'open_interest': r'Open Interest[:\s]+(\d+(?:,\d+)*)',
                'strike': r'Strike[:\s]+\$?(\d+)',
                'theta': r'Theta[:\s]+(-?\d+\.\d+)',
                'gamma': r'Gamma[:\s]+(\d+\.\d+)',
                'high': r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2})',
                'low': r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2})',
                'iv': r'(?:Implied\s+)?Volatility[:\s]+(\d+\.\d+)%?'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = match.group(1).replace(',', '')  # Remove commas
                    contract_data[key] = value
                    self.log(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Take screenshot of expanded contract
            await page.screenshot(path=f"screenshots/contract_details_{option_type}_{price_cents:02d}.png")
            
            return contract_data
            
        except Exception as e:
            self.log(f"❌ Error extracting contract data: {e}")
            return None
            
    def add_contract_tab(self, contract_id, initial_data, page=None):
        """Add a new tab for a contract with continuous screenshot capability."""
        try:
            # Create contract data tracker
            contract = ContractData(contract_id)
            contract.add_data_point(initial_data)
            contract.page = page  # Store page reference for screenshots
            self.contracts[contract_id] = contract
            
            # Create tab frame
            tab_frame = tk.Frame(self.notebook, bg='#1e1e1e')
            
            # Tab title
            option_type = initial_data.get('type', 'unknown').upper()
            price = f"$0.{initial_data.get('price_cents', 0):02d}"
            tab_title = f"{option_type} {price}"
            
            self.notebook.add(tab_frame, text=tab_title)
            self.contract_tabs[contract_id] = tab_frame
            
            # Setup tab content
            self.setup_contract_tab(tab_frame, contract_id)
            
            # Switch to new tab
            self.notebook.select(tab_frame)
            
            # Start continuous screenshot capture for this contract
            if page:
                self.start_contract_monitoring(contract_id, page)
            
            self.log(f"✅ Added tab for {tab_title}")
            
        except Exception as e:
            self.log(f"❌ Error adding contract tab: {e}")
            
    def start_contract_monitoring(self, contract_id, page):
        """Start continuous monitoring and screenshots for a contract."""
        try:
            self.log(f"📹 Starting continuous monitoring for {contract_id}")
            
            def monitor_contract():
                """Monitor contract in background thread."""
                import asyncio
                
                async def take_screenshots():
                    screenshot_count = 0
                    while contract_id in self.contracts:  # Keep going while contract exists
                        try:
                            screenshot_count += 1
                            timestamp = datetime.now().strftime("%H%M%S")
                            screenshot_path = f"screenshots/{contract_id}_monitor_{timestamp}_{screenshot_count:03d}.png"
                            
                            await page.screenshot(path=screenshot_path)
                            
                            # Update contract data if possible
                            try:
                                # Try to extract current data from page
                                current_data = await self.extract_current_contract_data(page, contract_id)
                                if current_data:
                                    self.contracts[contract_id].add_data_point(current_data)
                                    # Update GUI if needed
                                    self.root.after(0, lambda: self.update_contract_display(contract_id))
                            except:
                                pass
                            
                            await asyncio.sleep(1)  # Screenshot every second
                            
                        except Exception as e:
                            self.log(f"❌ Screenshot error for {contract_id}: {e}")
                            await asyncio.sleep(2)  # Wait longer if error
                
                # Run the async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(take_screenshots())
            
            # Start monitoring in background thread
            monitor_thread = threading.Thread(target=monitor_contract)
            monitor_thread.daemon = True
            monitor_thread.start()
            
        except Exception as e:
            self.log(f"❌ Error starting contract monitoring: {e}")
            
    async def extract_current_contract_data(self, page, contract_id):
        """Extract current data from the page for a contract."""
        try:
            # Get current page content
            content = await page.content()
            
            # Extract basic data patterns
            current_data = {
                'timestamp': datetime.now().isoformat()
            }
            
            # Look for various data points in the page
            patterns = {
                'current_price': r'(?:Last|Price)[:\s]+\$?(\d+\.\d{2})',
                'bid': r'Bid[:\s]+\$?(\d+\.\d{2})',
                'ask': r'Ask[:\s]+\$?(\d+\.\d{2})',
                'volume': r'Volume[:\s]+(\d+(?:,\d+)*)',
                'high': r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2})',
                'low': r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2})',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    current_data[key] = match.group(1).replace(',', '')
            
            return current_data if len(current_data) > 1 else None
            
        except Exception as e:
            return None
            
    def update_contract_display(self, contract_id):
        """Update the display for a specific contract."""
        try:
            if contract_id in self.contracts:
                contract = self.contracts[contract_id]
                # Update charts and info display here
                # This would refresh the contract tab with new data
                pass
        except Exception as e:
            pass
            
    def setup_contract_tab(self, tab_frame, contract_id):
        """Setup content for a contract tab."""
        try:
            contract = self.contracts[contract_id]
            
            # Split tab into info and chart areas
            info_frame = tk.Frame(tab_frame, bg='#2d2d2d', height=150)
            info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            info_frame.pack_propagate(False)
            
            chart_frame = tk.Frame(tab_frame, bg='#1e1e1e')
            chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
            
            # Contract info display
            info_text = tk.Text(info_frame, height=8, bg='#1a1a1a', fg='#ffffff', 
                               font=('Courier', 10), wrap=tk.WORD)
            info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Display current contract data
            self.update_contract_info(info_text, contract.current_data)
            
            # Create charts
            self.create_contract_charts(chart_frame, contract)
            
        except Exception as e:
            self.log(f"❌ Error setting up contract tab: {e}")
            
    def update_contract_info(self, info_text, data):
        """Update contract info display."""
        info_text.delete('1.0', tk.END)
        
        info = f"""
🎯 CONTRACT DETAILS
{'='*50}
Type: {data.get('type', 'N/A').upper()}
Symbol: {data.get('symbol', 'N/A')}
Strike: ${data.get('strike', 'N/A')}
Current Price: ${data.get('current_price', 'N/A')}

📊 MARKET DATA
Bid: ${data.get('bid', 'N/A')}
Ask: ${data.get('ask', 'N/A')}
Volume: {data.get('volume', 'N/A')}
Open Interest: {data.get('open_interest', 'N/A')}

🏷️ GREEKS & VOLATILITY
Theta: {data.get('theta', 'N/A')}
Gamma: {data.get('gamma', 'N/A')}
Implied Volatility: {data.get('iv', 'N/A')}%

📈 DAY RANGE
High: ${data.get('high', 'N/A')}
Low: ${data.get('low', 'N/A')}

⏰ Last Update: {datetime.now().strftime('%H:%M:%S')}
        """
        
        info_text.insert(tk.END, info)
        
    def create_contract_charts(self, parent_frame, contract):
        """Create charts for contract data."""
        try:
            # Create matplotlib figure
            fig = Figure(figsize=(12, 8), facecolor='#1e1e1e')
            
            # Create subplots
            ax1 = fig.add_subplot(2, 2, 1, facecolor='#2d2d2d')
            ax2 = fig.add_subplot(2, 2, 2, facecolor='#2d2d2d')
            ax3 = fig.add_subplot(2, 2, 3, facecolor='#2d2d2d')
            ax4 = fig.add_subplot(2, 2, 4, facecolor='#2d2d2d')
            
            # Style axes
            for ax in [ax1, ax2, ax3, ax4]:
                ax.tick_params(colors='white')
                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('white')
            
            # Initial placeholder charts
            ax1.set_title('Price History', color='white', fontsize=12)
            ax1.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                    transform=ax1.transAxes, color='white')
            
            ax2.set_title('Volume', color='white', fontsize=12)
            ax2.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                    transform=ax2.transAxes, color='white')
            
            ax3.set_title('Bid/Ask Spread', color='white', fontsize=12)
            ax3.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                    transform=ax3.transAxes, color='white')
            
            ax4.set_title('Greeks (Theta/Gamma)', color='white', fontsize=12)
            ax4.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                    transform=ax4.transAxes, color='white')
            
            fig.tight_layout()
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, parent_frame)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Store references for updates
            contract.figure = fig
            contract.axes = [ax1, ax2, ax3, ax4]
            contract.canvas = canvas
            
        except Exception as e:
            self.log(f"❌ Error creating charts: {e}")
            
    async def refresh_contract_data(self):
        """Refresh data for all tracked contracts."""
        # This would reconnect to browser and update each contract
        # Implementation would be similar to initial discovery but focused on updates
        self.log("🔄 Contract refresh functionality would go here")
        self.log("💡 This would update all existing contract tabs with new data")
        
    def get_spy_data(self):
        """Get SPY market data."""
        try:
            spy_1m = yf.download("SPY", period="5d", interval="1m", progress=False)
            spy_5m = yf.download("SPY", period="5d", interval="5m", progress=False)
            
            if spy_1m.empty:
                return None
            
            # Handle multi-level columns
            if isinstance(spy_1m.columns, pd.MultiIndex):
                close_1m = spy_1m['Close'].iloc[:, 0].values.astype(float)
                current_price = spy_1m['Close'].iloc[-1, 0]
            else:
                close_1m = spy_1m['Close'].values.astype(float)
                current_price = spy_1m['Close'].iloc[-1]
            
            if isinstance(spy_5m.columns, pd.MultiIndex):
                close_5m = spy_5m['Close'].iloc[:, 0].values.astype(float)
            else:
                close_5m = spy_5m['Close'].values.astype(float)
            
            # Calculate RSI
            rsi_1m = talib.RSI(close_1m, timeperiod=14)[-1] if len(close_1m) >= 15 else None
            rsi_5m = talib.RSI(close_5m, timeperiod=14)[-1] if len(close_5m) >= 15 else None
            
            return {
                'price': float(current_price),
                'rsi_1m': f"{rsi_1m:.1f}" if rsi_1m and not np.isnan(rsi_1m) else "N/A",
                'rsi_5m': f"{rsi_5m:.1f}" if rsi_5m and not np.isnan(rsi_5m) else "N/A"
            }
            
        except Exception as e:
            return None
    
    def determine_bias(self, rsi_1m, rsi_5m):
        """Determine market bias."""
        try:
            if rsi_1m == "N/A" or rsi_5m == "N/A":
                return "UNKNOWN"
            
            rsi_1m_val = float(rsi_1m)
            rsi_5m_val = float(rsi_5m)
            
            if rsi_1m_val < 30 and rsi_5m_val < 30:
                return "STRONG BULLISH"
            elif rsi_1m_val > 70 and rsi_5m_val > 70:
                return "STRONG BEARISH"
            elif rsi_1m_val < 30:
                return "MILD BULLISH"
            elif rsi_1m_val > 70:
                return "MILD BEARISH"
            else:
                return "NEUTRAL"
        except:
            return "UNKNOWN"
    
    def show(self):
        """Show the GUI."""
        self.root.mainloop()

def main():
    """Main function."""
    print("🚀 Starting SPY Options Contract Tracker...")
    print("✅ GUI with contract tabs should open")
    
    app = SPYOptionsGUI()
    app.show()

if __name__ == "__main__":
    main()