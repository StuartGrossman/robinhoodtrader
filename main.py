#!/usr/bin/env python3
"""
SPY Options Expanded Contract Tracker
Keeps each contract in expanded state for continuous monitoring
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
import sqlite3
import os
import random

class DatabaseManager:
    def __init__(self, db_path="data/options_data.db"):
        self.db_path = db_path
        self.ensure_data_dir()
        self.init_database()
    
    def ensure_data_dir(self):
        """Ensure data directory exists."""
        os.makedirs("data", exist_ok=True)
    
    def init_database(self):
        """Initialize SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create contracts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_key TEXT UNIQUE,
                    option_type TEXT,
                    price_cents INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create data_points table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_key TEXT,
                    timestamp TIMESTAMP,
                    current_price REAL,
                    bid REAL,
                    ask REAL,
                    volume INTEGER,
                    open_interest INTEGER,
                    theta REAL,
                    gamma REAL,
                    delta REAL,
                    vega REAL,
                    high REAL,
                    low REAL,
                    FOREIGN KEY (contract_key) REFERENCES contracts (contract_key)
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Database initialized successfully")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
    
    def save_contract(self, contract_key, option_type, price_cents):
        """Save contract to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO contracts (contract_key, option_type, price_cents)
                VALUES (?, ?, ?)
            ''', (contract_key, option_type, price_cents))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error saving contract: {e}")
            return False
    
    def save_data_point(self, contract_key, data):
        """Save data point to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO data_points (
                    contract_key, timestamp, current_price, bid, ask, volume, 
                    open_interest, theta, gamma, delta, vega, high, low
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contract_key,
                data.get('timestamp', datetime.now()),
                data.get('current_price', 0),
                data.get('bid', 0),
                data.get('ask', 0),
                data.get('volume', 0),
                data.get('open_interest', 0),
                data.get('theta', 0),
                data.get('gamma', 0),
                data.get('delta', 0),
                data.get('vega', 0),
                data.get('high', 0),
                data.get('low', 0)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error saving data point: {e}")
            return False
    
    def get_contract_data(self, contract_key, limit=200):
        """Get recent data points for a contract."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM data_points 
                WHERE contract_key = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (contract_key, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries
            data_points = []
            for row in rows:
                data_points.append({
                    'timestamp': row[2],
                    'current_price': row[3],
                    'bid': row[4],
                    'ask': row[5],
                    'volume': row[6],
                    'open_interest': row[7],
                    'theta': row[8],
                    'gamma': row[9],
                    'delta': row[10],
                    'vega': row[11],
                    'high': row[12],
                    'low': row[13]
                })
            
            return data_points
            
        except Exception as e:
            print(f"❌ Error getting contract data: {e}")
            return []

class ExpandedContractTracker:
    def __init__(self, contract_key, option_type, price_cents, db_manager):
        self.contract_key = contract_key  # e.g., "call_09"
        self.option_type = option_type
        self.price_cents = price_cents
        self.data_history = []
        self.current_data = {}
        self.last_update = None
        self.db_manager = db_manager
        
        # Browser tab for this specific contract
        self.page = None
        self.context = None
        self.is_expanded = False
        self.monitoring_active = False
        self.tab_dedicated = False  # Track if this contract has its own tab
        
        # Save contract to database
        self.db_manager.save_contract(contract_key, option_type, price_cents)
        
    def add_data_point(self, data):
        """Add timestamped data point."""
        data['timestamp'] = datetime.now()
        self.data_history.append(data)
        self.current_data = data
        self.last_update = datetime.now()
        
        # Save to database
        self.db_manager.save_data_point(self.contract_key, data)
        
        # Keep only last 200 data points for better graphs
        if len(self.data_history) > 200:
            self.data_history = self.data_history[-200:]
    
    def get_chart_data(self):
        """Get data formatted for charts."""
        if not self.data_history:
            return None
        
        return {
            'timestamps': [d['timestamp'] for d in self.data_history],
            'prices': [self.safe_float(d.get('current_price', 0)) for d in self.data_history],
            'volumes': [self.safe_int(d.get('volume', 0)) for d in self.data_history],
            'bids': [self.safe_float(d.get('bid', 0)) for d in self.data_history],
            'asks': [self.safe_float(d.get('ask', 0)) for d in self.data_history],
            'thetas': [self.safe_float(d.get('theta', 0)) for d in self.data_history],
            'gammas': [self.safe_float(d.get('gamma', 0)) for d in self.data_history],
            'highs': [self.safe_float(d.get('high', 0)) for d in self.data_history],
            'lows': [self.safe_float(d.get('low', 0)) for d in self.data_history],
        }
    
    def safe_float(self, value):
        """Safely convert value to float."""
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace('$', '').strip()
            return float(value) if value else 0.0
        except:
            return 0.0
    
    def safe_int(self, value):
        """Safely convert value to int."""
        try:
            if isinstance(value, str):
                value = value.replace(',', '').strip()
            return int(float(value)) if value else 0
        except:
            return 0

class SPYExpandedTerminal:
    def __init__(self, option_type):
        self.option_type = option_type.lower()  # 'call' or 'put'
        self.contracts = {}  # contract_key -> ExpandedContractTracker
        self.contract_tabs = {}
        self.browser = None
        self.playwright = None
        self.tracked_prices = set()  # Track prices we're already monitoring
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup GUI for this terminal."""
        self.root = tk.Tk()
        self.root.title(f"🚀 SPY {self.option_type.upper()} Expanded Contract Tracker")
        self.root.geometry("1800x1000")
        self.root.configure(bg='#0d1117')
        
        # Position windows
        if self.option_type == 'call':
            self.root.geometry("1800x1000+50+50")
        else:
            self.root.geometry("1800x1000+1900+50")
        
        self.root.lift()
        self.root.focus_force()
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#0d1117')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_color = '#7ee787' if self.option_type == 'call' else '#fbb6ce'
        title = tk.Label(main_frame, text=f"📊 SPY {self.option_type.upper()} EXPANDED CONTRACT TRACKER", 
                        font=('SF Pro Display', 18, 'bold'), fg=title_color, bg='#0d1117')
        title.pack(pady=(0, 10))
        
        # Controls
        controls_frame = tk.Frame(main_frame, bg='#161b22', relief=tk.RAISED, bd=1)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = tk.Button(controls_frame, text=f"🔄 Find & Expand {self.option_type.upper()}s", 
                                  command=self.start_analysis,
                                  font=('SF Pro Display', 12, 'bold'),
                                  bg='#238636', fg='white', pady=8)
        self.start_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.refresh_btn = tk.Button(controls_frame, text="🔄 Refresh All Contracts", 
                                    command=self.refresh_all_contracts,
                                    font=('SF Pro Display', 10, 'bold'),
                                    bg='#fd7e14', fg='white', pady=8)
        self.refresh_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.status_label = tk.Label(controls_frame, text="Status: Ready to find contracts", 
                                    font=('SF Mono', 11), fg=title_color, bg='#161b22')
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Content area - Terminal on left, Tabs on right
        content_frame = tk.Frame(main_frame, bg='#0d1117')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Terminal (left side)
        terminal_frame = tk.LabelFrame(content_frame, text=f" 📊 {self.option_type.upper()} Analysis Log ",
                                      font=('SF Pro Display', 12, 'bold'), fg=title_color, bg='#161b22')
        terminal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.terminal = scrolledtext.ScrolledText(terminal_frame, height=40, width=60,
                                                 bg='#0d1117', fg='#f0f6fc', 
                                                 font=('SF Mono', 9))
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Contract tabs (right side)
        tabs_frame = tk.LabelFrame(content_frame, text=f" 📈 EXPANDED {self.option_type.upper()} Contracts ",
                                  font=('SF Pro Display', 12, 'bold'), fg=title_color, bg='#161b22')
        tabs_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Notebook for contract tabs
        style = ttk.Style()
        style.configure('Expanded.TNotebook', background='#161b22')
        style.configure('Expanded.TNotebook.Tab', background='#21262d', foreground='white')
        
        self.notebook = ttk.Notebook(tabs_frame, style='Expanded.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Clear screenshots after GUI is set up
        self.clear_screenshots()
        
        # Welcome message
        self.log(f"🎯 {self.option_type.upper()} Expanded Contract Tracker Ready")
        self.log("📋 Will find contracts in current price range and keep them EXPANDED")
        self.log("🔍 Each contract gets its OWN DEDICATED browser tab")
        self.log("📊 Screenshots focus on expanded contract details every second")
        self.log("📊 Target: 7-10 tabs open simultaneously")
        self.log("📈 Live graphs show real Theta, Gamma, Volume, Bid/Ask data")
        
    def clear_screenshots(self):
        """Clear screenshots for this option type."""
        try:
            import os
            import glob
            
            pattern = f"screenshots/expanded_{self.option_type}_*"
            old_files = glob.glob(pattern)
            for f in old_files:
                try:
                    os.remove(f)
                except:
                    pass
            
            os.makedirs("screenshots", exist_ok=True)
            if old_files:
                self.log(f"🗑️ Cleared {len(old_files)} old expanded {self.option_type} screenshots")
                
        except Exception as e:
            self.log(f"❌ Error clearing screenshots: {e}")
    
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
        """Start finding and expanding contracts."""
        self.start_btn.config(state='disabled', text=f'🔄 Finding {self.option_type.upper()}s...')
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
        """Find contracts and keep each one expanded in separate browser contexts."""
        try:
            # Start playwright
            self.update_status("Starting browser...")
            self.log("🌐 Starting Playwright browser...")
            
            self.playwright = await async_playwright().start()
            
            # Try to connect to existing browser first
            try:
                self.log("🔗 Attempting to connect to existing browser...")
                self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
                
                if not self.browser.contexts:
                    self.log("❌ No browser contexts found, launching new browser...")
                    await self.browser.close()
                    self.browser = await self.playwright.chromium.launch(headless=False)
                    self.log("✅ Launched new browser instance")
                else:
                    self.log("✅ Connected to existing browser")
                    
            except Exception as connect_error:
                self.log(f"⚠️ Failed to connect to existing browser: {connect_error}")
                self.log("🚀 Launching new browser instance...")
                self.browser = await self.playwright.chromium.launch(headless=False)
                self.log("✅ Launched new browser instance")
            
            # Get existing context and find Robinhood page
            main_context = self.browser.contexts[0]
            
            # Look for existing Robinhood page
            robinhood_page = None
            for page in main_context.pages:
                if "robinhood.com" in page.url:
                    robinhood_page = page
                    break
            
            if robinhood_page:
                self.log(f"✅ Found existing Robinhood page: {robinhood_page.url}")
                main_page = robinhood_page
            else:
                # Create new page if no Robinhood page found
                main_page = main_context.pages[0] if main_context.pages else await main_context.new_page()
                self.log("📄 Using existing page or created new page")
            
            self.update_status("Loading options page...")
            self.log("📊 Loading SPY options page...")
            
            # Only navigate if we're not already on the options page
            current_url = main_page.url
            if "options/chains/SPY" not in current_url:
                # Add retry logic for page navigation
                max_navigation_attempts = 3
                for attempt in range(max_navigation_attempts):
                    try:
                        await main_page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded", timeout=45000)
                        await asyncio.sleep(5)
                        break
                    except Exception as nav_error:
                        self.log(f"⚠️ Navigation attempt {attempt + 1} failed: {nav_error}")
                        if attempt < max_navigation_attempts - 1:
                            self.log("🔄 Retrying navigation in 3 seconds...")
                            await asyncio.sleep(3)
                        else:
                            self.log("❌ Failed to navigate to options page after all attempts")
                            return
            else:
                self.log("✅ Already on SPY options page")
            
            if "login" in main_page.url:
                self.log("🔐 Please log into Robinhood first")
                return
            
            # Click appropriate tab ONLY ONCE on main page for scanning
            self.log(f"📈 Clicking {self.option_type.upper()} tab for initial scan...")
            tab_button = main_page.locator(f'button:has-text("{self.option_type.title()}")')
            if await tab_button.count() > 0:
                await tab_button.click()
                await asyncio.sleep(3)
                self.log(f"✅ Clicked {self.option_type.upper()} tab for scanning")
            
            # Scroll to find lower-priced contracts in main page
            self.log(f"📜 Scrolling main page to find 8-16¢ contracts...")
            
            # CALLS: Scroll UP to find lower prices (8¢, 9¢, etc.)
            # PUTS: Scroll DOWN to find lower prices (8¢, 9¢, etc.)
            scroll_direction = -1 if self.option_type.lower() == 'call' else 1
            scroll_amount = 500 * scroll_direction
            
            # Scroll multiple times to ensure we see all target prices
            for scroll_attempt in range(8):
                await main_page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(1)
                
                # Check if we can find any target prices after this scroll
                content = await main_page.content()
                target_prices = [8, 9, 10, 11, 12, 13, 14, 15, 16]
                found_prices = []
                
                for price in target_prices:
                    price_text = f"$0.{price:02d}"
                    if price_text in content:
                        found_prices.append(price)
                
                if len(found_prices) >= 3:  # Found at least 3 target prices
                    self.log(f"✅ Found {len(found_prices)} target prices after scroll attempt {scroll_attempt + 1}")
                    break
                else:
                    self.log(f"🔍 Scroll attempt {scroll_attempt + 1}: Found {len(found_prices)} target prices")
            
            await asyncio.sleep(2)  # Final wait after scrolling
            
            # Take screenshot of the scanning page
            await main_page.screenshot(path=f"screenshots/scanning_{self.option_type}_page.png")
            self.log("📸 Screenshot taken of scanning page")
            
            # Find contracts in price range
            self.update_status("Scanning for contracts...")
            self.log("🔍 Scanning for contracts in 8-16¢ range...")
            
            contracts_to_expand = await self.find_contracts_in_range(main_page)
            
            if not contracts_to_expand:
                self.log("❌ No contracts found in price range")
                return
            
            self.log(f"🎯 Found {len(contracts_to_expand)} contracts to expand and track")
            
            # For each contract, create separate browser TAB and expand
            for price_cents in contracts_to_expand:
                try:
                    contract_key = f"{self.option_type}_{price_cents:02d}"
                    
                    # Skip if already tracking this price
                    if price_cents in self.tracked_prices:
                        self.log(f"⚠️ Already tracking {price_cents}¢ contract, skipping")
                        continue
                    
                    self.log(f"🚀 Creating NEW TAB for {contract_key} ({price_cents}¢)...")
                    
                    # Create new browser TAB for this contract
                    success = await self.create_expanded_contract_context(price_cents)
                    
                    if success:
                        self.tracked_prices.add(price_cents)
                        self.log(f"✅ Successfully expanded {contract_key} in dedicated tab")
                    else:
                        self.log(f"❌ Failed to expand {contract_key}")
                    
                    # Small delay between tab creations
                    await asyncio.sleep(2)
                    
                except Exception as contract_error:
                    self.log(f"❌ Error with {price_cents}¢ contract: {contract_error}")
                    continue
            
            self.log(f"🎉 Setup complete! Tracking {len(self.contracts)} expanded contracts in {len(self.contracts)} dedicated tabs")
            self.update_status(f"Monitoring {len(self.contracts)} contracts in {len(self.contracts)} tabs")
            
            if len(self.contracts) >= 7:
                self.log("✅ Target reached: 7+ contracts in separate tabs!")
            else:
                self.log(f"🎯 Target: Need {7 - len(self.contracts)} more contracts for 7+ tabs")
            
        except Exception as e:
            self.log(f"❌ Error in find_and_expand_contracts: {e}")
            import traceback
            self.log(f"📋 Full error traceback: {traceback.format_exc()}")
    
    async def find_contracts_in_range(self, page):
        """Find contracts in 8-16¢ price range."""
        try:
            # Take screenshot of options page
            await page.screenshot(path=f"screenshots/scanning_{self.option_type}_page.png")
            
            # Get page content and find prices
            content = await page.content()
            
            # Debug: Check if we can see the page content
            if "SPY" not in content:
                self.log("⚠️ Page content doesn't contain SPY - might not be loaded")
            
            # Focus only on $0.08 contract
            target_prices = [8]  # Only track 8¢ contract
            
            self.log(f"🎯 Focusing on $0.08 contract only")
            
            return target_prices
            
        except Exception as e:
            self.log(f"❌ Error finding contracts: {e}")
            return []
    
    async def create_expanded_contract_context(self, price_cents):
        """Create separate browser TAB with expanded contract."""
        try:
            contract_key = f"{self.option_type}_{price_cents:02d}"
            
            # Create new PAGE in existing context (this creates a new TAB)
            main_context = self.browser.contexts[0]
            page = await main_context.new_page()
            
            self.log(f"  📋 Created new browser TAB for {contract_key}")
            
            # Navigate to options page in NEW TAB with retry logic
            self.log(f"  🌐 Navigating to SPY options in new tab...")
            
            max_nav_attempts = 3
            navigation_success = False
            
            for nav_attempt in range(max_nav_attempts):
                try:
                    await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(5)  # Extra time for full page load
                    navigation_success = True
                    break
                except Exception as nav_error:
                    self.log(f"  ⚠️ Navigation attempt {nav_attempt + 1} failed: {nav_error}")
                    if nav_attempt < max_nav_attempts - 1:
                        self.log(f"  🔄 Retrying navigation in 3 seconds...")
                        await asyncio.sleep(3)
                    else:
                        self.log(f"  ❌ Failed to navigate after {max_nav_attempts} attempts")
                        await page.close()
                        return False
            
            if not navigation_success:
                return False
            
            # Check if page loaded properly
            try:
                if "login" in page.url:
                    self.log(f"  ❌ Redirected to login page in new tab")
                    await page.close()
                    return False
                
                # Verify we're on the right page
                page_title = await page.title()
                if "SPY" not in page_title.upper():
                    self.log(f"  ⚠️ Page title doesn't contain SPY: {page_title}")
                else:
                    self.log(f"  ✅ Page loaded: {page_title}")
            except Exception as title_error:
                self.log(f"  ⚠️ Could not get page title: {title_error}")
            
            # Click option type tab in THIS NEW TAB with retry
            self.log(f"  📋 Clicking {self.option_type.upper()} tab in new tab for {price_cents}¢...")
            
            max_tab_attempts = 3
            tab_clicked = False
            
            for tab_attempt in range(max_tab_attempts):
                try:
                    tab_button = page.locator(f'button:has-text("{self.option_type.title()}")')
                    if await tab_button.count() > 0:
                        await tab_button.click()
                        await asyncio.sleep(4)
                        self.log(f"  ✅ Clicked {self.option_type.upper()} tab in dedicated tab")
                        tab_clicked = True
                        break
                    else:
                        self.log(f"  ⚠️ Tab button not found on attempt {tab_attempt + 1}")
                        if tab_attempt < max_tab_attempts - 1:
                            await asyncio.sleep(2)
                        else:
                            self.log(f"  ⚠️ Could not find {self.option_type.upper()} tab button after {max_tab_attempts} attempts")
                except Exception as tab_error:
                    self.log(f"  ⚠️ Tab click attempt {tab_attempt + 1} failed: {tab_error}")
                    if tab_attempt < max_tab_attempts - 1:
                        await asyncio.sleep(2)
            
            # Wait for the options chain to load
            await asyncio.sleep(3)
            
            # Scroll to find lower-priced contracts based on option type
            self.log(f"  📜 Scrolling to find {price_cents}¢ contract...")
            
            # CALLS: Scroll UP to find lower prices (8¢, 9¢, etc.)
            # PUTS: Scroll DOWN to find lower prices (8¢, 9¢, etc.)
            scroll_direction = -1 if self.option_type.lower() == 'call' else 1
            scroll_amount = 300 * scroll_direction
            
            # Scroll multiple times to ensure we reach the target price
            for scroll_attempt in range(8):  # Increased attempts
                try:
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(1)
                    
                    # Check if we can find the target price after this scroll
                    price_text = f"$0.{price_cents:02d}"
                    price_elements = page.locator(f'text="{price_text}"')
                    count = await price_elements.count()
                    
                    if count > 0:
                        self.log(f"  ✅ Found {price_text} after scroll attempt {scroll_attempt + 1}")
                        break
                    else:
                        self.log(f"  🔍 Scroll attempt {scroll_attempt + 1}: {price_text} not found yet")
                except Exception as scroll_error:
                    self.log(f"  ⚠️ Scroll attempt {scroll_attempt + 1} failed: {scroll_error}")
                    continue
            
            await asyncio.sleep(2)  # Final wait after scrolling
            
            # Find and click the specific contract to expand it
            price_text = f"$0.{price_cents:02d}"
            self.log(f"  🔍 Looking for {price_text} to expand...")
            
            # Try different price formats and search methods - target the contract row, not just the button
            search_patterns = [
                f'[data-testid*="ChainTableRow"]:has-text("{price_cents:02d}")',  # Contract row
                f'div:has-text("{price_text}")',  # Any div containing the price
                f'[class*="row"]:has-text("{price_cents:02d}")',  # Row with price
                f'button:has-text("{price_text}")',  # Button as fallback
                f'text="{price_text}"',
                f'text="{price_cents:02d}¢"',
                f'text="{price_cents}¢"',
            ]
            
            # Try different search patterns
            price_elements = None
            count = 0
            
            for pattern in search_patterns:
                try:
                    elements = page.locator(pattern)
                    count = await elements.count()
                    
                    if count > 0:
                        self.log(f"  ✅ Found {price_text} using pattern: {pattern}")
                        price_elements = elements
                        break
                except:
                    continue
            
            if count == 0:
                self.log(f"  ❌ Could not find {price_text} on page")
                self.log(f"  🔍 Debug: Taking screenshot of current page...")
                try:
                    await page.screenshot(path=f"screenshots/debug_{contract_key}_not_found.png")
                except:
                    pass
                await page.close()
                return False
            
            # Try to click and expand the contract
            expanded = False
            for i in range(min(count, 3)):
                try:
                    element = price_elements.nth(i)
                    
                    # Take before screenshot
                    try:
                        await page.screenshot(path=f"screenshots/expanded_{contract_key}_before_click.png")
                    except:
                        pass
                    
                    # Try different click strategies - click on the contract row, not the button
                    click_strategies = [
                        lambda: element.click(),  # Direct click
                        lambda: element.click(button="left"),  # Left click
                        lambda: element.click(force=True),  # Force click
                        # Click more to the left on the contract row (not the button)
                        lambda: page.mouse.click(element.bounding_box()['x'] + 50, 
                                               element.bounding_box()['y'] + element.bounding_box()['height']/2),  # Left side of row
                        lambda: page.mouse.click(element.bounding_box()['x'] + 100, 
                                               element.bounding_box()['y'] + element.bounding_box()['height']/2),  # Further left
                        lambda: page.mouse.click(element.bounding_box()['x'] + 150, 
                                               element.bounding_box()['y'] + element.bounding_box()['height']/2),  # Even further left
                        lambda: element.click(delay=100),  # Click with delay
                        lambda: element.click(button="left", delay=100),  # Left click with delay
                    ]
                    
                    for strategy_idx, click_strategy in enumerate(click_strategies):
                        try:
                            self.log(f"  🖱️ Clicking {price_text} with strategy {strategy_idx + 1}")
                            await click_strategy()
                            await asyncio.sleep(3)  # Wait for expansion
                            
                            # Check if contract expanded by looking for expansion indicators
                            try:
                                # Wait a moment for any expansion to complete
                                await asyncio.sleep(2)
                                
                                # Look for expanded content indicators - more comprehensive list
                                expansion_indicators = [
                                    '[class*="expanded"]',
                                    '[class*="details"]',
                                    '[class*="option-details"]',
                                    '[class*="contract-details"]',
                                    '[class*="expanded-view"]',
                                    '[class*="option-expanded"]',
                                    '[data-testid*="expanded"]',
                                    '[data-testid*="details"]',
                                    '[data-testid*="option-details"]',
                                    '[class*="greeks"]',
                                    '[class*="volume"]',
                                    '[class*="bid-ask"]',
                                    '[class*="strike"]',
                                    '[class*="expiration"]'
                                ]
                                
                                # Also check for specific text content that indicates expansion
                                try:
                                    page_content = await page.content()
                                    expansion_text_indicators = [
                                        'theta', 'gamma', 'delta', 'vega', 
                                        'volume', 'open interest', 'implied volatility',
                                        'bid', 'ask', 'strike', 'expiration'
                                    ]
                                    
                                    text_indicators_found = sum(1 for indicator in expansion_text_indicators 
                                                               if indicator.lower() in page_content.lower())
                                    
                                    self.log(f"  🔍 Found {text_indicators_found}/{len(expansion_text_indicators)} text indicators")
                                    
                                    if text_indicators_found >= 3:
                                        self.log(f"  ✅ Contract expanded successfully! (text indicators)")
                                        expanded = True
                                        break
                                    
                                except Exception as text_check_error:
                                    self.log(f"  ⚠️ Text check failed: {text_check_error}")
                                
                                # Check for HTML element indicators
                                expanded_found = False
                                for indicator in expansion_indicators:
                                    try:
                                        expanded_elements = page.locator(indicator)
                                        if await expanded_elements.count() > 0:
                                            self.log(f"  ✅ Found expansion indicator: {indicator}")
                                            expanded_found = True
                                            break
                                    except:
                                        continue
                                
                                if expanded_found:
                                    self.log(f"  ✅ Contract expanded successfully!")
                                    expanded = True
                                    break
                                else:
                                    self.log(f"  ⚠️ Strategy {strategy_idx + 1}: No expansion indicators found")
                                    
                            except Exception as check_error:
                                self.log(f"  ⚠️ Could not check expansion: {check_error}")
                        except Exception as strategy_error:
                            self.log(f"  ⚠️ Click strategy {strategy_idx + 1} failed: {strategy_error}")
                            continue
                    
                    if expanded:
                        break
                    
                    # Take after screenshot
                    try:
                        await page.screenshot(path=f"screenshots/expanded_{contract_key}_after_click.png")
                    except:
                        pass
                
                except Exception as click_error:
                    self.log(f"  ❌ Click attempt {i+1} failed: {click_error}")
                    continue
            
            if not expanded:
                self.log(f"  ⚠️ Regular click methods failed, trying JavaScript fallback...")
                
                # Try JavaScript click as last resort
                try:
                    # Try to find and click the element using JavaScript
                    js_click_result = await page.evaluate(f"""
                        (() => {{
                            const elements = document.querySelectorAll('button, div, span');
                            for (let el of elements) {{
                                if (el.textContent && el.textContent.includes('{price_text}')) {{
                                    el.click();
                                    return true;
                                }}
                            }}
                            return false;
                        }})()
                    """)
                    
                    if js_click_result:
                        self.log(f"  ✅ JavaScript click successful!")
                        await asyncio.sleep(3)  # Wait for expansion
                        
                        # Check if it worked
                        try:
                            page_content = await page.content()
                            expansion_text_indicators = [
                                'theta', 'gamma', 'delta', 'vega', 
                                'volume', 'open interest', 'implied volatility'
                            ]
                            
                            text_indicators_found = sum(1 for indicator in expansion_text_indicators 
                                                       if indicator.lower() in page_content.lower())
                            
                            if text_indicators_found >= 2:
                                self.log(f"  ✅ Contract expanded successfully! (JavaScript fallback)")
                                expanded = True
                            else:
                                self.log(f"  ❌ JavaScript click didn't expand contract")
                                
                        except Exception as js_check_error:
                            self.log(f"  ⚠️ Could not verify JavaScript expansion: {js_check_error}")
                    else:
                        self.log(f"  ❌ JavaScript click failed - element not found")
                        
                except Exception as js_error:
                    self.log(f"  ❌ JavaScript fallback failed: {js_error}")
            
            if not expanded:
                self.log(f"  ❌ Failed to expand {price_text}")
                await page.close()
                return False
            
            # Contract is now expanded - create tracker
            tracker = ExpandedContractTracker(contract_key, self.option_type, price_cents, self.db_manager)
            tracker.page = page
            tracker.context = main_context  # Reference to main context
            tracker.is_expanded = True
            tracker.tab_dedicated = True
            
            self.log(f"  ✅ Contract {price_text} is now EXPANDED in dedicated tab #{len(self.contracts) + 1}")
            
            # Extract initial data - WAIT until we get proper data
            self.log(f"  🔍 Extracting expanded contract data for {price_text}...")
            
            max_attempts = 5
            for attempt in range(max_attempts):
                initial_data = await self.extract_expanded_contract_data(page, price_cents)
                
                if initial_data and len(initial_data) > 5:  # Need at least 5 fields
                    tracker.add_data_point(initial_data)
                    self.log(f"  ✅ SUCCESS: Extracted {len(initial_data)} fields on attempt {attempt + 1}")
                    
                    # Store tracker
                    self.contracts[contract_key] = tracker
                    
                    # Create GUI tab
                    self.create_contract_tab(contract_key)
                    
                    # Start continuous monitoring for this contract
                    self.start_contract_monitoring(contract_key)
                    
                    return True
                else:
                    self.log(f"  ⚠️ Attempt {attempt + 1}: Only got {len(initial_data) if initial_data else 0} fields")
                    
                    if attempt < max_attempts - 1:
                        self.log(f"  🔄 Retrying data extraction in 3 seconds...")
                        await asyncio.sleep(3)
                        
                        # Try gentle scrolling again - just a tiny bit
                        try:
                            await page.evaluate("window.scrollBy(0, 50)")
                            await asyncio.sleep(2)
                        except:
                            pass
                    else:
                        self.log(f"  ❌ FAILED: Could not extract sufficient data after {max_attempts} attempts")
                        await page.close()
                        return False
            
        except Exception as e:
            self.log(f"❌ Error creating expanded context: {e}")
            import traceback
            self.log(f"📋 Full error traceback: {traceback.format_exc()}")
            return False
    
    async def extract_expanded_contract_data(self, page, price_cents):
        """Extract data from expanded contract view."""
        try:
            await asyncio.sleep(3)  # Wait for data to load
            
            # Scroll down to see all expanded contract details
            self.log(f"  📜 Scrolling to view expanded contract details...")
            
            # Take a screenshot before scrolling to see the expanded state
            try:
                await page.screenshot(path=f"screenshots/before_scroll_{self.option_type}_{price_cents:02d}.png")
            except:
                pass
            
            # Gentle scroll down just a little to see the expanded details
            try:
                await page.evaluate("window.scrollBy(0, 100)")
                await asyncio.sleep(1)
            except Exception as scroll_error:
                self.log(f"  ⚠️ Initial scroll failed: {scroll_error}")
            
            # Try to find the expanded contract area without excessive scrolling
            try:
                # Look for the expanded contract container with more specific selectors
                expanded_selectors = [
                    '[class*="expanded"]',
                    '[class*="details"]', 
                    '[class*="contract"]',
                    '[class*="option"]',
                    '[data-testid*="expanded"]',
                    '[data-testid*="details"]'
                ]
                
                found_element = False
                for selector in expanded_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            # Just scroll the element into view, don't move too much
                            await elements.first.scroll_into_view_if_needed()
                            self.log(f"  📜 Found and scrolled to expanded contract element")
                            found_element = True
                            break
                    except:
                        continue
                
                if not found_element:
                    # If no specific elements found, just scroll a tiny bit more
                    self.log(f"  📜 No specific elements found, gentle scroll...")
                    try:
                        await page.evaluate("window.scrollBy(0, 50)")
                        await asyncio.sleep(1)
                    except:
                        pass
                        
            except Exception as scroll_error:
                self.log(f"  ⚠️ Scroll error: {scroll_error}")
            
            # Take a screenshot after scrolling to see what we have
            try:
                await page.screenshot(path=f"screenshots/after_scroll_{self.option_type}_{price_cents:02d}.png")
            except:
                pass
            
            await asyncio.sleep(2)  # Wait for scroll to complete
            
            # Get page content with retry
            content = None
            max_content_attempts = 3
            for content_attempt in range(max_content_attempts):
                try:
                    content = await page.content()
                    break
                except Exception as content_error:
                    self.log(f"  ⚠️ Content extraction attempt {content_attempt + 1} failed: {content_error}")
                    if content_attempt < max_content_attempts - 1:
                        await asyncio.sleep(2)
                    else:
                        self.log(f"  ❌ Failed to get page content after {max_content_attempts} attempts")
                        return None
            
            if not content:
                return None
            
            # Check if contract is actually expanded
            expansion_indicators = ['theta', 'gamma', 'delta', 'vega', 'volume', 'open interest', 'implied volatility']
            found_indicators = sum(1 for indicator in expansion_indicators if indicator.lower() in content.lower())
            
            self.log(f"  🔍 Found {found_indicators}/{len(expansion_indicators)} expansion indicators in page content")
            
            # Check if we're still on the right contract
            price_text = f"$0.{price_cents:02d}"
            if price_text not in content:
                self.log(f"  ⚠️ WARNING: {price_text} not found in page content - may have scrolled too far!")
                # Try to scroll back up to find our contract
                try:
                    await page.evaluate("window.scrollBy(0, -200)")
                    await asyncio.sleep(1)
                    content = await page.content()
                except:
                    pass
            
            if found_indicators < 2:
                self.log(f"  ⚠️ Contract may not be properly expanded - only {found_indicators} indicators found")
                self.log(f"  🔍 Looking for: {expansion_indicators}")
                self.log(f"  📜 Page contains: {[ind for ind in expansion_indicators if ind.lower() in content.lower()]}")
            
            data = {
                'type': self.option_type,
                'price_cents': price_cents,
                'price_text': f"$0.{price_cents:02d}",
                'symbol': 'SPY',
                'timestamp': datetime.now().isoformat()
            }
            
            # Enhanced extraction patterns for expanded view with Robinhood-specific patterns
            patterns = {
                'current_price': [
                    r'Last trade[:\s]*\$?(0?\.\d{2,4})',  # Look for "Last trade" specifically
                    r'Last trade[:\s]*\$?(\d{1,2}\.\d{2,4})',  # Allow up to 2 digits
                    r'Mark[:\s]*\$?(0?\.\d{2,4})',  # Mark price for options
                    r'(?:Last|Price|Mark|Current)[:\s]+\$?(0?\.\d{2,4})',  # Option prices < $1
                    r'Premium[:\s]+\$?(0?\.\d{2,4})', 
                    r'\$(0?\.\d{2,4})\s*(?:Last|Current)',
                ],
                'bid': [
                    r'Bid[:\s]+\$?(\d+\.\d{2,4})',
                    r'Bid\s*\$?(\d+\.\d{2,4})',
                    r'Bid[:\s]*\$?(\d+\.\d{2,4})',
                    r'\$(\d+\.\d{2,4})\s*×\s*\d+',  # $0.07 × 1,062 format
                    r'Bid[:\s]*(\d+\.\d{2,4})',  # Robinhood format
                    r'Bid.*?\$(\d+\.\d{2,4})',  # Match Bid followed by $price
                ],
                'ask': [
                    r'Ask[:\s]+\$?(\d+\.\d{2,4})',
                    r'Ask\s*\$?(\d+\.\d{2,4})',
                    r'Ask[:\s]*\$?(\d+\.\d{2,4})',
                    r'\$(\d+\.\d{2,4})\s*×\s*\d+',  # $0.08 × 1,501 format
                    r'Ask[:\s]*(\d+\.\d{2,4})',  # Robinhood format
                    r'Ask.*?\$(\d+\.\d{2,4})',  # Match Ask followed by $price
                ],
                'volume': [
                    r'Volume[:\s]+(\d+(?:,\d+)*)',
                    r'Vol[:\s]+(\d+(?:,\d+)*)',
                    r'Volume[:\s]*(\d+(?:,\d+)*)',
                    r'Volume[:\s]*(\d{1,3}(?:,\d{3})*)',  # 14,029 format
                    r'Volume[:\s]*(\d+)',  # Simple format
                    r'Volume.*?(\d{1,3}(?:,\d{3})*)',  # Match Volume followed by number
                ],
                'open_interest': [
                    r'Open Interest[:\s]+(\d+(?:,\d+)*)',
                    r'OI[:\s]+(\d+(?:,\d+)*)',
                    r'Open Interest[:\s]*(\d+(?:,\d+)*)',
                    r'Open interest[:\s]*(\d{1,3}(?:,\d{3})*)',  # 3,726 format
                    r'Open Interest[:\s]*(\d+)',  # Simple format
                    r'Open interest.*?(\d+)',  # Match Open interest followed by number
                ],
                'theta': [
                    r'Theta[:\s]+(-?\d+\.\d{2,4})',
                    r'θ[:\s]+(-?\d+\.\d{2,4})',
                    r'Theta[:\s]*(-?\d+\.\d+)',  # More flexible
                    r'θ[:\s]*(-?\d+\.\d+)',
                    r'Theta[:\s]*(-?\d+\.\d{4})',  # 4 decimal places
                    r'Theta[:\s]*(\d+\.\d{4})',  # Positive format
                    r'Theta[:\s]*(-?\d+\.\d{4})',  # -0.1305 format
                    r'Theta[:\s]*(-?\d+\.\d{2,4})',  # Robinhood format
                    r'Theta.*?(-?\d+\.\d{4})',  # Match Theta followed by number
                ],
                'gamma': [
                    r'Gamma[:\s]+(\d+\.\d{2,4})',
                    r'Γ[:\s]+(\d+\.\d{2,4})',
                    r'Gamma[:\s]*(\d+\.\d+)',  # More flexible
                    r'Γ[:\s]*(\d+\.\d+)',
                    r'Gamma[:\s]*(\d+\.\d{4})',  # 4 decimal places
                    r'Gamma[:\s]*(\d+\.\d{2,4})',  # Robinhood format
                    r'Gamma.*?(\d+\.\d{4})',  # Match Gamma followed by number
                ],
                'delta': [
                    r'Delta[:\s]+(-?\d+\.\d{2,4})',
                    r'Δ[:\s]+(-?\d+\.\d{2,4})',
                    r'Delta[:\s]*(-?\d+\.\d+)',  # More flexible
                    r'Δ[:\s]*(-?\d+\.\d+)',
                    r'Delta[:\s]*(-?\d+\.\d{4})',  # 4 decimal places
                    r'Delta[:\s]*(-?\d+\.\d{2,4})',  # Robinhood format
                    r'Delta.*?(\d+\.\d{4})',  # Match Delta followed by number
                ],
                'vega': [
                    r'Vega[:\s]*(\d+\.\d{4})',
                    r'Vega[:\s]*\$?(\d+\.\d{4})',
                    r'Vega\s*(\d+\.\d{4})',
                    r'Vega.*?(\d+\.\d{4})',
                ],
                'high': [
                    r'High[:\s]*\$?(\d+\.\d{2,4})',
                    r'High\s*\$?(\d+\.\d{2,4})',
                    r'Day High[:\s]*\$?(\d+\.\d{2,4})',
                    r'Daily High[:\s]*\$?(\d+\.\d{2,4})',
                    r'High.*?\$(\d+\.\d{2,4})',
                    r'(\d+\.\d{2,4})\s*High',  # Price followed by "High"
                ],
                'low': [
                    r'Low[\s\n]*\$?(0?\.\d{2})',  # Low with newline/space then price
                    r'Low[:\s]*\$?(0?\.\d{2,4})',  # Look for prices starting with 0. or just .
                    r'Low\s*\$?(0?\.\d{2,4})',
                    r'Day Low[:\s]*\$?(0?\.\d{2,4})',
                    r'Daily Low[:\s]*\$?(0?\.\d{2,4})',
                    r'Low.*?\$(0?\.\d{2,4})',
                    r'(0?\.\d{2,4})\s*Low',  # Price followed by "Low"
                    # Special pattern to get the second price after High (which should be Low)
                    r'High[:\s]*\$?0?\.\d{2,4}[^\d]+(0?\.\d{2,4})',
                    # Look for Low in a table/list structure after High
                    r'High.*?</?\w+>.*?Low.*?(0?\.\d{2,4})',
                    # Look for pattern where Low value might be in next element/line
                    r'Low[^0-9\$]{0,20}(0?\.\d{2,4})',
                    # Fallback patterns that look for any decimal under 10
                    r'Low[:\s]*\$?(\d{1}\.\d{2,4})',  # Single digit prices
                    r'Low.*?\$(\d{1}\.\d{2,4})',
                    # Last resort - any price after High that's under 10
                    r'High[:\s]*\$?\d+\.\d{2,4}[^\d]+(\d{1,2}\.\d{2,4})',
                ],
                'iv': [
                    r'Implied volatility[\s\n]*(\d+\.\d+)%',  # Implied volatility with newline
                    r'Implied volatility[:\s]*(\d+\.\d+)%?',
                    r'(?:Implied\s+)?(?:Vol|Volatility)[:\s]+(\d+\.\d+)%?',
                    r'IV[:\s]+(\d+\.\d+)%?',
                    r'(\d+\.\d+)%',  # Just find percentage values
                ],
                'strike': [
                    r'\$(\d{3,4})\s+Call',  # $635 Call format
                    r'\$(\d{3,4})\s+Put',   # $635 Put format
                    r'SPY\s+\$(\d{3,4})',   # SPY $635 format
                    r'Strike[:\s]+\$?(\d+)',
                    r'Strike\s+Price[:\s]+\$?(\d+)',
                    r'Strike[:\s]*\$?(\d+)',  # Robinhood format
                ],
                'expiration': [
                    r'Call\s+(\d{1,2}/\d{1,2})',  # Call 8/4 format
                    r'Put\s+(\d{1,2}/\d{1,2})',   # Put 8/4 format
                    r'(\d{1,2}/\d{1,2})$',         # Date at end of title
                    r'(?:Exp|Expires?)[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
                    r'Expiration[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
                    r'Expires[:\s]*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',  # Robinhood format
                ]
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
                            self.log(f"    ✅ {field}: {value} (pattern: {pattern[:30]}...)")
                            break  # Found match, move to next field
                    except Exception as pattern_error:
                        continue
            
            # If we didn't extract enough data, try direct text matching
            if extracted_fields < 5:
                self.log(f"    🔍 Trying direct text matching...")
                
                # Look for specific text patterns in the HTML
                try:
                    if "Bid" in content and "×" in content:
                        bid_match = re.search(r'\$(\d+\.\d{2,4})\s*×', content)
                        if bid_match and 'bid' not in data:
                            data['bid'] = bid_match.group(1)
                            extracted_fields += 1
                            self.log(f"    ✅ bid: {bid_match.group(1)} (direct match)")
                    
                    if "Ask" in content and "×" in content:
                        ask_match = re.search(r'\$(\d+\.\d{2,4})\s*×', content)
                        if ask_match and 'ask' not in data:
                            data['ask'] = ask_match.group(1)
                            extracted_fields += 1
                            self.log(f"    ✅ ask: {ask_match.group(1)} (direct match)")
                    
                    if "Volume" in content:
                        vol_match = re.search(r'Volume[:\s]*(\d{1,3}(?:,\d{3})*)', content)
                        if vol_match and 'volume' not in data:
                            data['volume'] = vol_match.group(1).replace(',', '')
                            extracted_fields += 1
                            self.log(f"    ✅ volume: {vol_match.group(1)} (direct match)")
                    
                    if "Open interest" in content:
                        oi_match = re.search(r'Open interest[:\s]*(\d{1,3}(?:,\d{3})*)', content)
                        if oi_match and 'open_interest' not in data:
                            data['open_interest'] = oi_match.group(1).replace(',', '')
                            extracted_fields += 1
                            self.log(f"    ✅ open_interest: {oi_match.group(1)} (direct match)")
                    
                    # Look for High/Low data
                    if "High" in content:
                        high_match = re.search(r'High[:\s]*\$?(\d+\.\d{2,4})', content)
                        if high_match and 'high' not in data:
                            data['high'] = high_match.group(1)
                            extracted_fields += 1
                            self.log(f"    ✅ high: {high_match.group(1)} (direct match)")
                        else:
                            # Try alternative patterns
                            high_patterns = [
                                r'Day High[:\s]*\$?(\d+\.\d{2,4})',
                                r'Daily High[:\s]*\$?(\d+\.\d{2,4})',
                                r'High.*?\$(\d+\.\d{2,4})',
                                r'(\d+\.\d{2,4})\s*High'
                            ]
                            for pattern in high_patterns:
                                high_match = re.search(pattern, content)
                                if high_match and 'high' not in data:
                                    data['high'] = high_match.group(1)
                                    extracted_fields += 1
                                    self.log(f"    ✅ high: {high_match.group(1)} (pattern: {pattern})")
                                    break
                    
                    # Try to extract High and Low together since they appear in proximity
                    high_low_match = re.search(r'High[:\s]*\$?(\d+\.\d{2,4}).*?Low[:\s]*\$?(\d+\.\d{2,4})', content, re.IGNORECASE | re.DOTALL)
                    if high_low_match:
                        if 'high' not in data:
                            data['high'] = high_low_match.group(1)
                            extracted_fields += 1
                            self.log(f"    ✅ high: {high_low_match.group(1)} (high-low pair)")
                        if 'low' not in data:
                            data['low'] = high_low_match.group(2)
                            extracted_fields += 1
                            self.log(f"    ✅ low: {high_low_match.group(2)} (high-low pair)")
                    
                    # Also try reverse pattern (Low before High)
                    low_high_match = re.search(r'Low[:\s]*\$?(\d+\.\d{2,4}).*?High[:\s]*\$?(\d+\.\d{2,4})', content, re.IGNORECASE | re.DOTALL)
                    if low_high_match:
                        if 'low' not in data:
                            data['low'] = low_high_match.group(1)
                            extracted_fields += 1
                            self.log(f"    ✅ low: {low_high_match.group(1)} (low-high pair)")
                        if 'high' not in data:
                            data['high'] = low_high_match.group(2)
                            extracted_fields += 1
                            self.log(f"    ✅ high: {low_high_match.group(2)} (low-high pair)")
                    
                    if "Low" in content:
                        low_match = re.search(r'Low[:\s]*\$?(\d+\.\d{2,4})', content)
                        if low_match and 'low' not in data:
                            data['low'] = low_match.group(1)
                            extracted_fields += 1
                            self.log(f"    ✅ low: {low_match.group(1)} (direct match)")
                        else:
                            # Try alternative patterns
                            low_patterns = [
                                r'Day Low[:\s]*\$?(\d+\.\d{2,4})',
                                r'Daily Low[:\s]*\$?(\d+\.\d{2,4})',
                                r'Low.*?\$(\d+\.\d{2,4})',
                                r'(\d+\.\d{2,4})\s*Low',
                                # Look for low value that appears after high in the same context
                                r'High.*?(\d+\.\d{2,4}).*?Low.*?(\d+\.\d{2,4})',
                                r'High[:\s]*\$?(\d+\.\d{2,4}).*?Low[:\s]*\$?(\d+\.\d{2,4})',
                                # Look for any price near "Low" text
                                r'Low[:\s]*(\d+\.\d{2,4})',
                                r'(\d+\.\d{2,4})[^0-9]*Low',
                                # Look for low in expanded contract context
                                r'expanded.*?Low[:\s]*\$?(\d+\.\d{2,4})',
                                r'contract.*?Low[:\s]*\$?(\d+\.\d{2,4})',
                                # Look for low value in the same section as other data
                                r'(?:Volume|Open interest|Theta|Gamma).*?Low[:\s]*\$?(\d+\.\d{2,4})'
                            ]
                            for pattern in low_patterns:
                                low_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                                if low_match and 'low' not in data:
                                    # If pattern has multiple groups, take the last one (usually the low value)
                                    if len(low_match.groups()) > 1:
                                        data['low'] = low_match.group(-1)  # Last group
                                    else:
                                        data['low'] = low_match.group(1)
                                    extracted_fields += 1
                                    self.log(f"    ✅ low: {data['low']} (pattern: {pattern[:50]}...)")
                                    break
                    
                    # Look for Greeks with more flexible patterns
                    greek_patterns = {
                        'delta': r'Delta[:\s]*(-?\d+\.\d{4})',
                        'gamma': r'Gamma[:\s]*(\d+\.\d{4})',
                        'theta': r'Theta[:\s]*(-?\d+\.\d{4})',
                        'vega': r'Vega[:\s]*(\d+\.\d{4})'
                    }
                    
                    for greek, pattern in greek_patterns.items():
                        if greek not in data:
                            greek_match = re.search(pattern, content)
                            if greek_match:
                                data[greek] = greek_match.group(1)
                                extracted_fields += 1
                                self.log(f"    ✅ {greek}: {greek_match.group(1)} (direct match)")
                except Exception as direct_error:
                    self.log(f"    ⚠️ Direct matching failed: {direct_error}")
            
            # Take screenshot of the expanded contract
            try:
                screenshot_path = f"screenshots/expanded_{self.option_type}_{price_cents:02d}_initial.png"
                await page.screenshot(path=screenshot_path)
            except:
                pass
            
            self.log(f"  📊 Extracted {extracted_fields} data fields from expanded contract")
            
            # Debug: Show what was extracted
            if extracted_fields > 0:
                self.log(f"  🔍 Extracted data: {list(data.keys())}")
                for key, value in data.items():
                    if key not in ['type', 'price_cents', 'price_text', 'symbol', 'timestamp']:
                        self.log(f"    {key}: {value}")
            else:
                self.log(f"  ❌ No data fields extracted!")
                self.log(f"  🔍 Page content sample: {content[:1000]}...")
                
                # Look for any numbers that might be our data
                self.log(f"  🔍 Searching for potential data patterns...")
                try:
                    all_numbers = re.findall(r'\d+\.\d+', content)
                    self.log(f"  📊 Found {len(all_numbers)} decimal numbers: {all_numbers[:10]}")
                    
                    # Look for Greek letters or words
                    greek_words = re.findall(r'(?:theta|gamma|delta|vega|volume|open interest|implied volatility)', content, re.IGNORECASE)
                    self.log(f"  📊 Found {len(greek_words)} Greek/data words: {greek_words[:10]}")
                    
                    # Look for high/low specific content
                    high_low_content = re.findall(r'(?:high|low|day high|day low|daily high|daily low)', content, re.IGNORECASE)
                    self.log(f"  📊 Found {len(high_low_content)} high/low references: {high_low_content[:10]}")
                    
                    # Look for specific values we know should be there
                    self.log(f"  🔍 Looking for specific known values...")
                    if "0.08" in content:
                        self.log(f"    ✅ Found bid price: 0.08")
                    if "0.09" in content:
                        self.log(f"    ✅ Found ask price: 0.09")
                    if "9778" in content or "9,778" in content:
                        self.log(f"    ✅ Found volume: 9,778")
                    if "1863" in content or "1,863" in content:
                        self.log(f"    ✅ Found open interest: 1,863")
                    if "0.1401" in content:
                        self.log(f"    ✅ Found theta: 0.1401")
                    if "0.0116" in content:
                        self.log(f"    ✅ Found gamma: 0.0116")
                    if "0.0347" in content:
                        self.log(f"    ✅ Found delta: 0.0347")
                    if "0.0339" in content:
                        self.log(f"    ✅ Found vega: 0.0339")
                    
                    # Special debugging for Low extraction since it's failing
                    if 'low' not in data:
                        self.log(f"  🔍 DEBUG: Low value not found, investigating...")
                        
                        # Find all occurrences of "low" in the content
                        low_indices = []
                        for match in re.finditer(r'low', content, re.IGNORECASE):
                            low_indices.append(match.start())
                        
                        self.log(f"  📍 Found {len(low_indices)} occurrences of 'low' in content")
                        
                        # Look at context around each "low" occurrence
                        for idx, pos in enumerate(low_indices[:5]):  # Check first 5 occurrences
                            context_start = max(0, pos - 50)
                            context_end = min(len(content), pos + 50)
                            context = content[context_start:context_end]
                            self.log(f"  📍 Low context {idx + 1}: ...{context}...")
                            
                            # Try to extract any numbers near this "low"
                            numbers_near = re.findall(r'\d+\.\d{2,4}', context)
                            if numbers_near:
                                self.log(f"    💡 Numbers near 'low': {numbers_near}")
                        
                        # Try more aggressive patterns
                        aggressive_patterns = [
                            # Look for any number within 100 chars after "low"
                            r'low.{0,100}?(\d+\.\d{2,4})',
                            # Look for any number within 100 chars before "low"
                            r'(\d+\.\d{2,4}).{0,100}?low',
                            # Look for "Low" followed by any non-digit chars then a number
                            r'Low[^\d]{0,50}(\d+\.\d{2,4})',
                            # Look for numbers between High and next section
                            r'High[:\s]*\$?(\d+\.\d{2,4})[^0-9]+(\d+\.\d{2,4})',
                            # Look for second number after High
                            r'High.*?(\d+\.\d{2,4}).*?(\d+\.\d{2,4})',
                        ]
                        
                        for pattern in aggressive_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                            if matches:
                                self.log(f"  🎯 Aggressive pattern '{pattern[:30]}...' found: {matches}")
                                if isinstance(matches[0], tuple) and len(matches[0]) > 1:
                                    # For patterns with multiple groups, try the second one as low
                                    potential_low = matches[0][1]
                                    self.log(f"  💡 Potential low value from tuple: {potential_low}")
                                elif isinstance(matches[0], str):
                                    potential_low = matches[0]
                                    self.log(f"  💡 Potential low value: {potential_low}")
                    
                    # Look for high/low values specifically
                    high_low_numbers = re.findall(r'(\d+\.\d{2,4})\s*(?:high|low)', content, re.IGNORECASE)
                    if high_low_numbers:
                        self.log(f"    ✅ Found high/low numbers: {high_low_numbers}")
                    
                    # Look for any price-like numbers near "high" or "low" words
                    high_low_context = re.findall(r'(?:high|low)[:\s]*\$?(\d+\.\d{2,4})', content, re.IGNORECASE)
                    if high_low_context:
                        self.log(f"    ✅ Found high/low context: {high_low_context}")
                        
                except Exception as debug_error:
                    self.log(f"  ⚠️ Debug search failed: {debug_error}")
                
                # Take a debug screenshot to see what the page looks like
                try:
                    debug_screenshot = f"screenshots/debug_extraction_{self.option_type}_{price_cents:02d}.png"
                    await page.screenshot(path=debug_screenshot)
                    self.log(f"  📸 Debug screenshot: {debug_screenshot}")
                except:
                    pass
                
                # Save the HTML content for debugging
                try:
                    html_debug_file = f"screenshots/debug_html_{self.option_type}_{price_cents:02d}.html"
                    with open(html_debug_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.log(f"  📄 HTML content saved to: {html_debug_file}")
                except:
                    pass
            
            # Validate high/low values before returning
            if 'high' in data:
                try:
                    high_val = float(data['high'])
                    # If high is > 50, it's probably a stock price, not option price
                    if high_val > 50:
                        self.log(f"  ⚠️ High value {high_val} seems like stock price, removing")
                        del data['high']
                        extracted_fields -= 1
                except:
                    pass
            
            if 'low' in data:
                try:
                    low_val = float(data['low'])
                    # If low is > 50, it's probably a stock price, not option price
                    if low_val > 50:
                        self.log(f"  ⚠️ Low value {low_val} seems like stock price, removing")
                        del data['low']
                        extracted_fields -= 1
                    # Also check if low is greater than high (if we have both)
                    elif 'high' in data:
                        high_val = float(data.get('high', 0))
                        if low_val > high_val and high_val > 0:
                            self.log(f"  ⚠️ Low {low_val} > High {high_val}, swapping")
                            data['high'], data['low'] = data['low'], data['high']
                except:
                    pass
            
            return data if extracted_fields > 3 else None
            
        except Exception as e:
            self.log(f"❌ Error extracting expanded data: {e}")
            import traceback
            self.log(f"📋 Full error traceback: {traceback.format_exc()}")
            return None
    
    def create_contract_tab(self, contract_key):
        """Create GUI tab for expanded contract."""
        try:
            tracker = self.contracts[contract_key]
            
            # Create tab frame
            tab_frame = tk.Frame(self.notebook, bg='#0d1117')
            price_text = f"$0.{tracker.price_cents:02d}"
            
            self.notebook.add(tab_frame, text=price_text)
            self.contract_tabs[contract_key] = tab_frame
            
            # Setup tab content
            self.setup_expanded_tab_content(tab_frame, contract_key)
            
            # Switch to new tab
            self.notebook.select(tab_frame)
            
            self.log(f"📋 Created GUI tab for {contract_key}")
            
        except Exception as e:
            self.log(f"❌ Error creating contract tab: {e}")
    
    def setup_expanded_tab_content(self, tab_frame, contract_key):
        """Setup content for expanded contract tab."""
        try:
            # Info section at top
            info_frame = tk.Frame(tab_frame, bg='#161b22', height=180)
            info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            info_frame.pack_propagate(False)
            
            # Contract info display
            info_text = tk.Text(info_frame, height=9, bg='#0d1117', fg='#f0f6fc',
                               font=('SF Mono', 10), wrap=tk.WORD)
            info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Store reference for updates
            setattr(self, f'info_text_{contract_key}', info_text)
            self.log(f"✅ Created info widget for {contract_key}")
            
            # Charts section
            charts_frame = tk.Frame(tab_frame, bg='#0d1117')
            charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
            
            # Create live charts
            self.create_live_charts(charts_frame, contract_key)
            
            # Update initial display
            self.update_contract_info_display(contract_key)
            
            # Add manual refresh button for testing
            refresh_button = tk.Button(tab_frame, text="🔄 Refresh Display", 
                                     command=lambda ck=contract_key: self.manual_refresh(ck),
                                     bg='#238636', fg='white', font=('SF Mono', 9))
            refresh_button.pack(pady=5)
            
            # Add force chart update button
            chart_button = tk.Button(tab_frame, text="📊 Force Chart Update", 
                                   command=lambda ck=contract_key: self.force_chart_update(ck),
                                   bg='#f85149', fg='white', font=('SF Mono', 9))
            chart_button.pack(pady=2)
            
            # Add test data button for debugging
            test_button = tk.Button(tab_frame, text="🧪 Add Test Data", 
                                  command=lambda ck=contract_key: self.add_test_data_to_charts(ck),
                                  bg='#d29922', fg='white', font=('SF Mono', 9))
            test_button.pack(pady=2)
            
        except Exception as e:
            self.log(f"❌ Error setting up tab content: {e}")
    
    def create_live_charts(self, parent_frame, contract_key):
        """Create live updating charts for expanded contract."""
        try:
            tracker = self.contracts[contract_key]
            
            # Create matplotlib figure
            fig = Figure(figsize=(14, 10), facecolor='#0d1117')
            
            # Create 6 subplots for comprehensive data
            ax1 = fig.add_subplot(2, 3, 1, facecolor='#161b22')  # Price
            ax2 = fig.add_subplot(2, 3, 2, facecolor='#161b22')  # Volume
            ax3 = fig.add_subplot(2, 3, 3, facecolor='#161b22')  # Bid/Ask
            ax4 = fig.add_subplot(2, 3, 4, facecolor='#161b22')  # Theta
            ax5 = fig.add_subplot(2, 3, 5, facecolor='#161b22')  # Gamma
            ax6 = fig.add_subplot(2, 3, 6, facecolor='#161b22')  # High/Low
            
            axes = [ax1, ax2, ax3, ax4, ax5, ax6]
            
            # Style all axes
            for ax in axes:
                ax.tick_params(colors='white', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('white')
                ax.grid(True, alpha=0.3, color='white')
            
            # Set titles
            titles = ['Price Over Time', 'Volume', 'Bid/Ask Spread', 'Theta Decay', 'Gamma', 'Daily High/Low']
            for ax, title in zip(axes, titles):
                ax.set_title(title, color='white', fontsize=10, pad=10)
            
            # Initial placeholder
            for ax in axes:
                ax.text(0.5, 0.5, 'Collecting live data...', ha='center', va='center',
                       transform=ax.transAxes, color='white', fontsize=9)
            
            fig.tight_layout(pad=2.0)
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, parent_frame)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Store references for live updates
            tracker.figure = fig
            tracker.axes = axes
            tracker.canvas = canvas
            self.log(f"✅ Created chart widgets for {contract_key}")
            
        except Exception as e:
            self.log(f"❌ Error creating live charts: {e}")
    
    def start_contract_monitoring(self, contract_key):
        """Start continuous monitoring for specific expanded contract."""
        try:
            tracker = self.contracts[contract_key]
            tracker.monitoring_active = True
            
            self.log(f"📹 Starting continuous monitoring for expanded {contract_key}")
            
            # Start timer-based chart updates
            self.start_chart_update_timer(contract_key)
            
            def monitor_expanded_contract():
                """Monitor expanded contract continuously."""
                import asyncio
                
                async def monitoring_loop():
                    screenshot_count = 0
                    
                    while tracker.monitoring_active and tracker.page:
                        try:
                            screenshot_count += 1
                            timestamp = datetime.now().strftime("%H%M%S")
                            
                            # Take screenshot of EXPANDED contract
                            screenshot_path = f"screenshots/expanded_{contract_key}_live_{timestamp}_{screenshot_count:03d}.png"
                            await tracker.page.screenshot(path=screenshot_path)
                            self.log(f"📸 Screenshot #{screenshot_count} saved: {screenshot_path}")
                            
                            # Extract current data from EXPANDED view
                            current_data = await self.extract_expanded_contract_data(tracker.page, tracker.price_cents)
                            if current_data:
                                self.log(f"🔍 Data extraction #{screenshot_count}: SUCCESS - Price:${current_data.get('current_price', 'N/A')} Bid:${current_data.get('bid', 'N/A')} Ask:${current_data.get('ask', 'N/A')} Vol:{current_data.get('volume', 'N/A')} Θ:{current_data.get('theta', 'N/A')}")
                                
                                # Log high/low data specifically
                                high = current_data.get('high', 'N/A')
                                low = current_data.get('low', 'N/A')
                                self.log(f"📊 High/Low data: High=${high} Low=${low}")
                                
                            else:
                                self.log(f"🔍 Data extraction #{screenshot_count}: FAILED - No data extracted")
                                # Try to get page content for debugging
                                try:
                                    page_content = await tracker.page.content()
                                    self.log(f"🔍 Page content length: {len(page_content)} characters")
                                except Exception as content_error:
                                    self.log(f"🔍 Could not get page content: {content_error}")
                            
                            if current_data:
                                # Add data point to tracker
                                tracker.add_data_point(current_data)
                                self.log(f"💾 Data point #{screenshot_count} added to tracker - Total points: {len(tracker.data_history)}")
                                
                                # Update GUI displays immediately with proper error handling
                                try:
                                    self.root.after(0, lambda ck=contract_key: self.update_contract_info_display(ck))
                                    self.log(f"🔄 GUI info display updated for {contract_key}")
                                    
                                    # Update charts with more detailed logging
                                    self.root.after(0, lambda ck=contract_key: self.update_live_charts(ck))
                                    self.log(f"📊 Chart update triggered for {contract_key}")
                                    
                                except Exception as gui_error:
                                    self.log(f"⚠️ GUI update error for {contract_key}: {gui_error}")
                                
                                # Log every 5 seconds to show progress
                                if screenshot_count % 5 == 0:
                                    price = current_data.get('current_price', 'N/A')
                                    volume = current_data.get('volume', 'N/A')
                                    theta = current_data.get('theta', 'N/A')
                                    bid = current_data.get('bid', 'N/A')
                                    ask = current_data.get('ask', 'N/A')
                                    tab_num = list(self.contracts.keys()).index(contract_key) + 1
                                    self.log(f"  📊 Tab#{tab_num} {contract_key}: ${price} (Bid:${bid} Ask:${ask}), Vol={volume}, Θ={theta} | Data points: {len(tracker.data_history)}")
                                    
                                    # Show data stream summary
                                    self.log(f"  📈 Data Stream Summary: {len(tracker.data_history)} points collected, {screenshot_count} screenshots taken")
                                    
                                    # Show continuous monitoring status
                                    self.log(f"  📊 Continuous Monitoring: Screenshots every 1s, Data extraction every 1s, Chart updates every 1s")
                                    
                                    # Debug widgets every 30 seconds
                                    if screenshot_count % 30 == 0:
                                        self.debug_widgets(contract_key)
                                
                                # Log every second for first 10 seconds to show it's working
                                if screenshot_count <= 10:
                                    price = current_data.get('current_price', 'N/A')
                                    bid = current_data.get('bid', 'N/A')
                                    ask = current_data.get('ask', 'N/A')
                                    volume = current_data.get('volume', 'N/A')
                                    theta = current_data.get('theta', 'N/A')
                                    self.log(f"  ⏰ {contract_key}: ${price} (Bid:${bid} Ask:${ask}) Vol:{volume} Θ:{theta} | Update #{screenshot_count}")
                                
                                # Log every 10 seconds after first 10 seconds
                                elif screenshot_count % 10 == 0:
                                    price = current_data.get('current_price', 'N/A')
                                    bid = current_data.get('bid', 'N/A')
                                    ask = current_data.get('ask', 'N/A')
                                    volume = current_data.get('volume', 'N/A')
                                    theta = current_data.get('theta', 'N/A')
                                    self.log(f"  🔄 {contract_key}: ${price} (Bid:${bid} Ask:${ask}) Vol:{volume} Θ:{theta} | Update #{screenshot_count}")
                                
                                # Show database save confirmation every 20 seconds
                                if screenshot_count % 20 == 0:
                                    self.log(f"💾 Database: Saved {screenshot_count} data points for {contract_key}")
                            
                            await asyncio.sleep(1)  # Screenshot every second
                            
                        except Exception as e:
                            if tracker.monitoring_active:
                                self.log(f"❌ Monitoring error for {contract_key}: {e}")
                                import traceback
                                self.log(f"🔍 Monitoring traceback: {traceback.format_exc()}")
                            await asyncio.sleep(2)
                
                # Run monitoring loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(monitoring_loop())
            
            # Start monitoring in background thread
            monitor_thread = threading.Thread(target=monitor_expanded_contract)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Update status to show monitoring is active
            self.update_status(f"Monitoring {contract_key} - Live updates every second")
            self.log(f"✅ Started monitoring {contract_key} - Screenshots every 1 second")
            
        except Exception as e:
            self.log(f"❌ Error starting monitoring for {contract_key}: {e}")
    
    def start_chart_update_timer(self, contract_key):
        """Start timer-based chart updates."""
        def update_charts_timer():
            if contract_key in self.contracts:
                tracker = self.contracts[contract_key]
                if tracker.monitoring_active and len(tracker.data_history) > 0:
                    self.log(f"⏰ Timer-based chart update for {contract_key} - {len(tracker.data_history)} data points")
                    
                    # Add a small amount of test data every 10 seconds to ensure charts have multiple points
                    if len(tracker.data_history) < 5 and tracker.monitoring_active:
                        self.log(f"🧪 Adding test data point to {contract_key} for chart testing")
                        latest_data = tracker.data_history[-1].copy()
                        
                        # Convert string values to float before doing math
                        current_price = float(latest_data.get('current_price', 0.07))
                        bid = float(latest_data.get('bid', 0.07))
                        ask = float(latest_data.get('ask', 0.07))
                        volume = int(latest_data.get('volume', 5))
                        
                        latest_data['current_price'] = current_price + (random.random() - 0.5) * 0.01
                        latest_data['bid'] = bid + (random.random() - 0.5) * 0.005
                        latest_data['ask'] = ask + (random.random() - 0.5) * 0.005
                        latest_data['volume'] = volume + random.randint(-1, 1)
                        latest_data['timestamp'] = datetime.now()
                        tracker.add_data_point(latest_data)
                        self.log(f"🧪 Added test data point - Total points: {len(tracker.data_history)}")
                    
                    self.update_live_charts(contract_key)
                    # Schedule next update in 2 seconds
                    self.root.after(2000, update_charts_timer)
        
        # Start the timer
        self.root.after(2000, update_charts_timer)
        self.log(f"⏰ Started timer-based chart updates for {contract_key} (every 2 seconds)")
    
    def refresh_all_contracts(self):
        """Clear all contracts and start fresh."""
        self.log("🔄 REFRESHING ALL CONTRACTS...")
        self.log("🗑️ Clearing all contract data and charts...")
        
        # Stop all monitoring
        for contract_key, tracker in self.contracts.items():
            tracker.monitoring_active = False
            self.log(f"  ⏹️ Stopped monitoring for {contract_key}")
        
        # Clear all data
        self.contracts.clear()
        self.tracked_prices.clear()
        
        # Clear GUI tabs
        for tab_widget in self.contract_tabs.values():
            tab_widget.destroy()
        self.contract_tabs.clear()
        
        # Clear all tabs from notebook
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        
        # Clear screenshots
        self.clear_screenshots()
        
        self.log("✅ All contracts cleared! Ready to start fresh.")
        self.update_status("All contracts cleared - ready to scan again")
    
    def update_contract_info_display(self, contract_key):
        """Update contract info display."""
        try:
            tracker = self.contracts[contract_key]
            data = tracker.current_data
            
            # Calculate spread safely
            try:
                bid_val = data.get('bid', 'N/A')
                ask_val = data.get('ask', 'N/A')
                if bid_val != 'N/A' and ask_val != 'N/A' and bid_val and ask_val:
                    spread = float(ask_val) - float(bid_val)
                    spread_str = f"${spread:.4f}"
                else:
                    spread_str = 'N/A'
            except:
                spread_str = 'N/A'
            
            info = f"""
🎯 EXPANDED CONTRACT: {contract_key.upper()}
{'='*60}
Status: EXPANDED & MONITORING (Dedicated Tab)
Type: {data.get('type', 'N/A').upper()}
Price: {data.get('price_text', 'N/A')}
Strike: ${data.get('strike', 'N/A')}
Expiration: {data.get('expiration', 'N/A')}
Tab Number: #{list(self.contracts.keys()).index(contract_key) + 1 if contract_key in self.contracts else 'N/A'}

📊 LIVE MARKET DATA
Current Premium: ${data.get('current_price', 'N/A')}
Bid: ${data.get('bid', 'N/A')}
Ask: ${data.get('ask', 'N/A')}
Spread: {spread_str}
Volume: {data.get('volume', 'N/A')}
Open Interest: {data.get('open_interest', 'N/A')}

🏷️ LIVE GREEKS
Delta: {data.get('delta', 'N/A')}
Gamma: {data.get('gamma', 'N/A')}
Theta: {data.get('theta', 'N/A')}
Vega: {data.get('vega', 'N/A')}

📈 DAILY RANGE
High: ${data.get('high', 'N/A')}
Low: ${data.get('low', 'N/A')}
Implied Vol: {data.get('iv', 'N/A')}%

⏰ Live Updates
Last Update: {tracker.last_update.strftime('%H:%M:%S') if tracker.last_update else 'Never'}
Data Points: {len(tracker.data_history)}
Screenshots: Every 1 second
            """
            
            # Update the info text widget
            info_widget = getattr(self, f'info_text_{contract_key}', None)
            if info_widget:
                info_widget.delete('1.0', tk.END)
                info_widget.insert('1.0', info)
                self.log(f"✅ Updated info display for {contract_key}")
            else:
                self.log(f"⚠️ Info widget not found for {contract_key}")
            
        except Exception as e:
            self.log(f"❌ Error updating contract info display for {contract_key}: {e}")
    
    def manual_refresh(self, contract_key):
        """Manual refresh for testing GUI updates."""
        try:
            self.log(f"🔄 Manual refresh requested for {contract_key}")
            self.update_contract_info_display(contract_key)
            self.update_live_charts(contract_key)
            self.log(f"✅ Manual refresh completed for {contract_key}")
        except Exception as e:
            self.log(f"❌ Manual refresh failed for {contract_key}: {e}")
    
    def debug_widgets(self, contract_key):
        """Debug widget references for a contract."""
        try:
            tracker = self.contracts[contract_key]
            info_widget = getattr(self, f'info_text_{contract_key}', None)
            
            self.log(f"🔍 Debug widgets for {contract_key}:")
            self.log(f"  - Info widget exists: {info_widget is not None}")
            self.log(f"  - Tracker has figure: {hasattr(tracker, 'figure')}")
            self.log(f"  - Tracker has axes: {hasattr(tracker, 'axes')}")
            self.log(f"  - Tracker has canvas: {hasattr(tracker, 'canvas')}")
            self.log(f"  - Data history length: {len(tracker.data_history)}")
            
        except Exception as e:
            self.log(f"❌ Error debugging widgets for {contract_key}: {e}")
    
    def update_live_charts(self, contract_key):
        """Update live charts with real data."""
        try:
            tracker = self.contracts[contract_key]
            
            if not hasattr(tracker, 'figure') or not hasattr(tracker, 'axes'):
                self.log(f"⚠️ Chart widgets not found for {contract_key}")
                self.debug_widgets(contract_key)
                return
            
            chart_data = tracker.get_chart_data()
            if not chart_data or len(tracker.data_history) < 1:
                self.log(f"⚠️ Insufficient chart data for {contract_key}: {len(tracker.data_history)} points")
                return
            
            self.log(f"📊 Updating charts for {contract_key} with {len(tracker.data_history)} data points")
            
            # Clear all axes
            for ax in tracker.axes:
                ax.clear()
                ax.set_facecolor('#161b22')
                ax.tick_params(colors='white', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('white')
                ax.grid(True, alpha=0.3, color='white')
            
            ax1, ax2, ax3, ax4, ax5, ax6 = tracker.axes
            
            # Chart 1: Price Over Time
            ax1.set_title('Price Over Time', color='white', fontsize=10, pad=10)
            if any(p > 0 for p in chart_data['prices']):
                valid_prices = [p for p in chart_data['prices'] if p > 0]
                if valid_prices:
                    ax1.plot(range(len(valid_prices)), valid_prices, color='#7ee787', linewidth=2, marker='o', markersize=3)
                    ax1.set_ylabel('Premium ($)', color='white', fontsize=8)
                    self.log(f"📈 Chart 1: Plotted {len(valid_prices)} price points")
            
            # Chart 2: Volume
            ax2.set_title('Volume', color='white', fontsize=10, pad=10)
            if any(v > 0 for v in chart_data['volumes']):
                valid_volumes = [v for v in chart_data['volumes'] if v > 0]
                if valid_volumes:
                    ax2.bar(range(len(valid_volumes)), valid_volumes, color='#58a6ff', alpha=0.7)
                    ax2.set_ylabel('Volume', color='white', fontsize=8)
                    self.log(f"📊 Chart 2: Plotted {len(valid_volumes)} volume points")
            
            # Chart 3: Bid/Ask Spread
            ax3.set_title('Bid/Ask Spread', color='white', fontsize=10, pad=10)
            valid_bids = [b for b in chart_data['bids'] if b > 0]
            valid_asks = [a for a in chart_data['asks'] if a > 0]
            
            if valid_bids:
                ax3.plot(range(len(valid_bids)), valid_bids, color='#7ee787', label='Bid', linewidth=2)
            if valid_asks:
                ax3.plot(range(len(valid_asks)), valid_asks, color='#fbb6ce', label='Ask', linewidth=2)
            
            if valid_bids or valid_asks:
                ax3.legend(fontsize=8)
                ax3.set_ylabel('Price ($)', color='white', fontsize=8)
                self.log(f"💹 Chart 3: Plotted {len(valid_bids)} bids, {len(valid_asks)} asks")
            
            # Chart 4: Theta Decay
            ax4.set_title('Theta Decay', color='white', fontsize=10, pad=10)
            valid_thetas = [t for t in chart_data['thetas'] if t != 0]
            if valid_thetas:
                ax4.plot(range(len(valid_thetas)), valid_thetas, color='#ffa657', linewidth=2, marker='s', markersize=3)
                ax4.set_ylabel('Theta', color='white', fontsize=8)
                self.log(f"📉 Chart 4: Plotted {len(valid_thetas)} theta points")
            
            # Chart 5: Gamma
            ax5.set_title('Gamma', color='white', fontsize=10, pad=10)
            valid_gammas = [g for g in chart_data['gammas'] if g != 0]
            if valid_gammas:
                ax5.plot(range(len(valid_gammas)), valid_gammas, color='#f85149', linewidth=2, marker='^', markersize=3)
                ax5.set_ylabel('Gamma', color='white', fontsize=8)
                self.log(f"📈 Chart 5: Plotted {len(valid_gammas)} gamma points")
            
            # Chart 6: Daily High/Low
            ax6.set_title('Daily High/Low', color='white', fontsize=10, pad=10)
            valid_highs = [h for h in chart_data['highs'] if h > 0]
            valid_lows = [l for l in chart_data['lows'] if l > 0]
            
            if valid_highs:
                ax6.plot(range(len(valid_highs)), valid_highs, color='#7ee787', label='High', linewidth=2)
            if valid_lows:
                ax6.plot(range(len(valid_lows)), valid_lows, color='#f85149', label='Low', linewidth=2)
            
            if valid_highs or valid_lows:
                ax6.legend(fontsize=8)
                ax6.set_ylabel('Price ($)', color='white', fontsize=8)
                self.log(f"📊 Chart 6: Plotted {len(valid_highs)} highs, {len(valid_lows)} lows")
            
            # Update canvas
            tracker.canvas.draw()
            self.log(f"✅ Updated charts for {contract_key} with {len(tracker.data_history)} data points")
            
            # Log chart data details
            if len(tracker.data_history) > 0:
                latest = tracker.data_history[-1]
                self.log(f"📈 Chart data: Price=${latest.get('current_price', 'N/A')} Bid=${latest.get('bid', 'N/A')} Ask=${latest.get('ask', 'N/A')} Vol={latest.get('volume', 'N/A')} Θ={latest.get('theta', 'N/A')}")
                
                # Show database status
                db_data = self.db_manager.get_contract_data(contract_key, limit=5)
                self.log(f"💾 Database: {len(db_data)} recent data points saved for {contract_key}")
                
                # Show chart update confirmation
                self.log(f"🎨 Charts refreshed for {contract_key} - Canvas redrawn")
            
        except Exception as e:
            self.log(f"❌ Error updating live charts for {contract_key}: {e}")
            import traceback
            self.log(f"🔍 Traceback: {traceback.format_exc()}")
    
    def show(self):
        """Show this terminal window."""
        self.root.mainloop()
    
    def force_chart_update(self, contract_key):
        """Force update charts for debugging."""
        try:
            self.log(f"🔧 FORCE CHART UPDATE for {contract_key}")
            tracker = self.contracts[contract_key]
            
            self.log(f"📊 Tracker data: {len(tracker.data_history)} points")
            if len(tracker.data_history) > 0:
                latest = tracker.data_history[-1]
                self.log(f"📈 Latest data: {latest}")
            
            # Force chart update
            self.update_live_charts(contract_key)
            self.log(f"✅ Force chart update completed for {contract_key}")
            
        except Exception as e:
            self.log(f"❌ Force chart update error for {contract_key}: {e}")
    
    def add_test_data_to_charts(self, contract_key):
        """Add test data to charts for debugging."""
        try:
            tracker = self.contracts[contract_key]
            
            # Generate some test data points
            from datetime import datetime, timedelta
            
            base_price = 0.07
            base_volume = 5
            
            for i in range(20):
                # Create test data point
                test_data = {
                    'current_price': base_price + (random.random() - 0.5) * 0.02,
                    'bid': base_price + (random.random() - 0.5) * 0.01,
                    'ask': base_price + (random.random() - 0.5) * 0.01,
                    'volume': base_volume + random.randint(-2, 2),
                    'open_interest': base_volume + random.randint(-1, 1),
                    'theta': -0.2163 + (random.random() - 0.5) * 0.1,
                    'gamma': 0.0098 + (random.random() - 0.5) * 0.005,
                    'delta': 0.0300 + (random.random() - 0.5) * 0.01,
                    'vega': 0.0232 + (random.random() - 0.5) * 0.01,
                    'high': base_price + random.random() * 0.03,
                    'low': base_price - random.random() * 0.03,
                    'timestamp': datetime.now() - timedelta(seconds=20-i)
                }
                
                tracker.add_data_point(test_data)
            
            self.log(f"🧪 Added 20 test data points to {contract_key}")
            self.update_live_charts(contract_key)
            self.log(f"✅ Test data charts updated for {contract_key}")
            
        except Exception as e:
            self.log(f"❌ Error adding test data to {contract_key}: {e}")

def launch_calls_terminal():
    """Launch calls terminal - defined at module level for multiprocessing."""
    terminal = SPYExpandedTerminal('call')
    terminal.show()

def launch_puts_terminal():
    """Launch puts terminal - defined at module level for multiprocessing."""
    terminal = SPYExpandedTerminal('put')
    terminal.show()

def main():
    """Main function."""
    print("🚀 SPY Expanded Contract Tracker")
    print("=" * 50)
    print("Choose which option type to track:")
    print("1. CALLS (expanded contracts)")
    print("2. PUTS (expanded contracts)")
    print("3. Both (separate windows)")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == '1':
        terminal = SPYExpandedTerminal('call')
        terminal.show()
    elif choice == '2':
        terminal = SPYExpandedTerminal('put')
        terminal.show()
    elif choice == '3':
        import multiprocessing
        
        # Set start method to spawn to avoid issues on macOS
        multiprocessing.set_start_method('spawn', force=True)
        
        # Launch both using module-level functions
        calls_process = multiprocessing.Process(target=launch_calls_terminal)
        puts_process = multiprocessing.Process(target=launch_puts_terminal)
        
        calls_process.start()
        puts_process.start()
        
        print("✅ Both expanded terminals launched!")
        print("📱 CALLS terminal: Left window")
        print("📱 PUTS terminal: Right window")
        
        calls_process.join()
        puts_process.join()
    else:
        print("Invalid choice. Launching CALLS terminal.")
        terminal = SPYExpandedTerminal('call')
        terminal.show()

if __name__ == "__main__":
    # Required for multiprocessing on macOS
    import multiprocessing
    multiprocessing.freeze_support()
    main()