#!/usr/bin/env python3
"""
SPY Options Dual Terminal - Separate windows for Puts and Calls
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

class ContractTracker:
    def __init__(self, contract_key):
        self.contract_key = contract_key  # e.g., "call_09" or "put_12"
        self.data_history = []
        self.current_data = {}
        self.last_update = None
        
    def add_data_point(self, data):
        """Add timestamped data point."""
        data['timestamp'] = datetime.now()
        self.data_history.append(data)
        self.current_data = data
        self.last_update = datetime.now()
        
        # Keep only last 100 data points to prevent memory issues
        if len(self.data_history) > 100:
            self.data_history = self.data_history[-100:]

class SPYTerminal:
    def __init__(self, option_type, window_title):
        self.option_type = option_type.lower()  # 'call' or 'put'
        self.window_title = window_title
        self.contracts = {}  # contract_key -> ContractTracker
        self.contract_tabs = {}
        self.page = None
        self.monitoring_active = True
        
        # Create GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup GUI for this terminal."""
        self.root = tk.Tk()
        self.root.title(f"🚀 SPY {self.option_type.upper()} Options Terminal")
        self.root.geometry("1600x900")
        self.root.configure(bg='#0d1117')
        
        # Force window positioning (calls on left, puts on right)
        if self.option_type == 'call':
            self.root.geometry("1600x900+50+50")
        else:
            self.root.geometry("1600x900+1700+50")
        
        self.root.lift()
        self.root.focus_force()
        
        # Clear screenshots for this type
        self.clear_screenshots()
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#0d1117')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_color = '#7ee787' if self.option_type == 'call' else '#fbb6ce'
        title = tk.Label(main_frame, text=f"📊 SPY {self.option_type.upper()} OPTIONS TRACKER", 
                        font=('SF Pro Display', 18, 'bold'), fg=title_color, bg='#0d1117')
        title.pack(pady=(0, 10))
        
        # Controls
        controls_frame = tk.Frame(main_frame, bg='#161b22', relief=tk.RAISED, bd=1)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = tk.Button(controls_frame, text=f"🔄 Start {self.option_type.upper()} Analysis", 
                                  command=self.start_analysis,
                                  font=('SF Pro Display', 12, 'bold'),
                                  bg='#238636', fg='white', pady=8)
        self.start_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.status_label = tk.Label(controls_frame, text="Status: Ready", 
                                    font=('SF Mono', 11), fg=title_color, bg='#161b22')
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Content area
        content_frame = tk.Frame(main_frame, bg='#0d1117')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Terminal (left side)
        terminal_frame = tk.LabelFrame(content_frame, text=f" 📊 {self.option_type.upper()} Analysis Terminal ",
                                      font=('SF Pro Display', 12, 'bold'), fg=title_color, bg='#161b22')
        terminal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.terminal = scrolledtext.ScrolledText(terminal_frame, height=30, width=60,
                                                 bg='#0d1117', fg='#f0f6fc', 
                                                 font=('SF Mono', 9))
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Contract tabs (right side)
        tabs_frame = tk.LabelFrame(content_frame, text=f" 📈 {self.option_type.upper()} Contract Data ",
                                  font=('SF Pro Display', 12, 'bold'), fg=title_color, bg='#161b22')
        tabs_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Notebook for contract tabs
        style = ttk.Style()
        style.configure('Terminal.TNotebook', background='#161b22')
        style.configure('Terminal.TNotebook.Tab', background='#21262d', foreground='white')
        
        self.notebook = ttk.Notebook(tabs_frame, style='Terminal.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Welcome message
        self.log(f"🎯 {self.option_type.upper()} Options Terminal Ready")
        self.log("📋 Will track contracts in 8-16¢ range")
        self.log("🔍 Click start to begin analysis")
        
    def clear_screenshots(self):
        """Clear screenshots for this option type."""
        try:
            import os
            import glob
            
            pattern = f"screenshots/{self.option_type}_*"
            old_files = glob.glob(pattern)
            for f in old_files:
                try:
                    os.remove(f)
                except:
                    pass
            
            os.makedirs("screenshots", exist_ok=True)
            if old_files:
                self.log(f"🗑️ Cleared {len(old_files)} old {self.option_type} screenshots")
                
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
        """Start contract analysis for this option type."""
        self.start_btn.config(state='disabled', text=f'🔄 Analyzing {self.option_type.upper()}...')
        thread = threading.Thread(target=self.run_analysis_thread)
        thread.daemon = True
        thread.start()
    
    def run_analysis_thread(self):
        """Run analysis in separate thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.analyze_contracts())
        except Exception as e:
            self.log(f"❌ Analysis error: {e}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state='normal', text=f'🔄 Start {self.option_type.upper()} Analysis'))
    
    async def analyze_contracts(self):
        """Main analysis function."""
        playwright = None
        try:
            # Connect to browser
            self.update_status("Connecting to Chrome...")
            self.log("🔗 Connecting to Chrome browser...")
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            contexts = browser.contexts
            if not contexts:
                self.log("❌ No browser contexts found")
                return
                
            context = contexts[0]
            pages = context.pages
            self.page = pages[0] if pages else await context.new_page()
            
            self.log("✅ Connected to Chrome")
            
            # Navigate to options
            self.update_status("Loading SPY options...")
            self.log("📊 Loading SPY options page...")
            
            await self.page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            if "login" in self.page.url:
                self.log("🔐 Please log into Robinhood first")
                return
            
            self.log("✅ SPY options page loaded")
            
            # Click the appropriate tab (Call or Put)
            self.update_status(f"Scanning {self.option_type} options...")
            self.log(f"📈 Scanning {self.option_type.upper()} options...")
            
            tab_button = self.page.locator(f'button:has-text("{self.option_type.title()}")')
            if await tab_button.count() > 0:
                await tab_button.click()
                await asyncio.sleep(3)
                self.log(f"✅ Clicked {self.option_type.upper()} tab")
            else:
                self.log(f"⚠️ Could not find {self.option_type.upper()} tab")
            
            # Find and track contracts
            await self.find_and_track_contracts()
            
        except Exception as e:
            self.log(f"❌ Analysis error: {e}")
        finally:
            if playwright:
                await playwright.stop()
            self.update_status("Analysis complete")
    
    async def find_and_track_contracts(self):
        """Find contracts in price range and create tracking tabs."""
        try:
            # Take screenshot
            await self.page.screenshot(path=f"screenshots/{self.option_type}_options_scan.png")
            self.log(f"📸 Screenshot: {self.option_type}_options_scan.png")
            
            # Find contracts in 8-16¢ range
            contracts_found = {}  # price_cents -> contract_data to avoid duplicates
            
            # Get page content and look for prices
            content = await self.page.content()
            price_matches = re.finditer(r'\$0\.(\d{2})', content)
            
            target_prices = []
            for match in price_matches:
                price_cents = int(match.group(1))
                if 8 <= price_cents <= 16:
                    target_prices.append(price_cents)
            
            unique_prices = sorted(list(set(target_prices)))
            self.log(f"🎯 Found prices in range: {unique_prices}")
            
            # For each unique price, try to find and click the contract
            for price_cents in unique_prices:
                try:
                    contract_key = f"{self.option_type}_{price_cents:02d}"
                    
                    # Skip if we already have this contract
                    if contract_key in self.contracts:
                        continue
                    
                    self.log(f"🔍 Looking for {self.option_type.upper()} $0.{price_cents:02d} contract...")
                    
                    # Try to find and click this specific contract
                    success = await self.find_and_click_contract(price_cents)
                    
                    if success:
                        # Extract data from expanded contract
                        contract_data = await self.extract_contract_data(price_cents)
                        
                        if not contract_data:
                            # Create basic data if extraction failed
                            contract_data = {
                                'type': self.option_type,
                                'price_cents': price_cents,
                                'price_text': f"$0.{price_cents:02d}",
                                'symbol': 'SPY',
                                'status': 'Found but data extraction failed'
                            }
                        
                        # Create contract tracker and tab
                        self.create_contract_tab(contract_key, contract_data)
                        contracts_found[price_cents] = contract_data
                        
                        # Close any expanded views
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(1)
                        
                    else:
                        self.log(f"⚠️ Could not click {self.option_type.upper()} $0.{price_cents:02d}")
                        
                except Exception as contract_error:
                    self.log(f"❌ Error with $0.{price_cents:02d}: {contract_error}")
                    continue
            
            self.log(f"✅ Created {len(contracts_found)} {self.option_type.upper()} contract tabs")
            
            # Start continuous monitoring for all contracts
            if contracts_found:
                self.start_continuous_monitoring()
            
        except Exception as e:
            self.log(f"❌ Error finding contracts: {e}")
    
    async def find_and_click_contract(self, price_cents):
        """Find and click a specific contract by price."""
        try:
            price_text = f"$0.{price_cents:02d}"
            
            # Look for elements containing this exact price
            price_elements = self.page.locator(f'text="{price_text}"')
            count = await price_elements.count()
            
            if count == 0:
                return False
            
            self.log(f"  Found {count} elements with {price_text}")
            
            # Try clicking each element until we find one that expands
            for i in range(min(count, 3)):
                try:
                    element = price_elements.nth(i)
                    
                    # Get bounding box and click 50px to the left
                    box = await element.bounding_box()
                    if box:
                        click_x = box['x'] - 50  # 50px left of price
                        click_y = box['y'] + (box['height'] * 0.5)
                        
                        self.log(f"  🖱️ Clicking at ({click_x:.0f}, {click_y:.0f}) - 50px left of {price_text}")
                        
                        # Take before screenshot
                        await self.page.screenshot(path=f"screenshots/{self.option_type}_before_click_{price_cents:02d}.png")
                        
                        # Click
                        await self.page.mouse.click(click_x, click_y)
                        await asyncio.sleep(3)
                        
                        # Take after screenshot
                        await self.page.screenshot(path=f"screenshots/{self.option_type}_after_click_{price_cents:02d}.png")
                        
                        # Check if contract expanded (look for detailed data)
                        new_content = await self.page.content()
                        expanded_indicators = ['theta', 'gamma', 'delta', 'bid', 'ask', 'volume', 'open interest']
                        
                        if any(indicator.lower() in new_content.lower() for indicator in expanded_indicators):
                            self.log(f"  ✅ Contract expanded successfully!")
                            return True
                        else:
                            self.log(f"  ⚠️ Click {i+1} - no expansion detected")
                    
                except Exception as click_error:
                    self.log(f"  ❌ Click {i+1} failed: {click_error}")
                    continue
            
            return False
            
        except Exception as e:
            self.log(f"❌ Error finding/clicking contract: {e}")
            return False
    
    async def extract_contract_data(self, price_cents):
        """Extract detailed contract data from expanded view."""
        try:
            self.log(f"📊 Extracting data for $0.{price_cents:02d}...")
            
            # Wait for data to load
            await asyncio.sleep(2)
            
            content = await self.page.content()
            
            contract_data = {
                'type': self.option_type,
                'price_cents': price_cents,
                'price_text': f"$0.{price_cents:02d}",
                'symbol': 'SPY',
                'timestamp': datetime.now().isoformat()
            }
            
            # Enhanced data extraction patterns
            patterns = {
                'current_price': r'(?:Last|Price|Mark)[:\s]+\$?(\d+\.\d{2,4})',
                'bid': r'Bid[:\s]+\$?(\d+\.\d{2,4})',
                'ask': r'Ask[:\s]+\$?(\d+\.\d{2,4})',
                'volume': r'Volume[:\s]+(\d+(?:,\d+)*)',
                'open_interest': r'Open Interest[:\s]+(\d+(?:,\d+)*)',
                'strike': r'Strike[:\s]+\$?(\d+)',
                'theta': r'Theta[:\s]+(-?\d+\.\d{2,4})',
                'gamma': r'Gamma[:\s]+(\d+\.\d{2,4})',
                'delta': r'Delta[:\s]+(-?\d+\.\d{2,4})',
                'vega': r'Vega[:\s]+(\d+\.\d{2,4})',
                'high': r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2,4})',
                'low': r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2,4})',
                'iv': r'(?:Implied\s+)?(?:Vol|Volatility)[:\s]+(\d+\.\d+)%?',
                'expiration': r'(?:Exp|Expires?)[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
            }
            
            extracted_count = 0
            for key, pattern in patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Use the first match and clean it
                    value = matches[0].replace(',', '').strip()
                    contract_data[key] = value
                    extracted_count += 1
                    self.log(f"   {key.replace('_', ' ').title()}: {value}")
            
            if extracted_count > 2:  # At least got some data beyond basic info
                self.log(f"✅ Extracted {extracted_count} data points")
                return contract_data
            else:
                self.log(f"⚠️ Only extracted {extracted_count} data points - may need manual verification")
                return contract_data
            
        except Exception as e:
            self.log(f"❌ Error extracting contract data: {e}")
            return None
    
    def create_contract_tab(self, contract_key, contract_data):
        """Create a tab for tracking this contract."""
        try:
            # Create contract tracker
            tracker = ContractTracker(contract_key)
            tracker.add_data_point(contract_data)
            self.contracts[contract_key] = tracker
            
            # Create tab
            tab_frame = tk.Frame(self.notebook, bg='#0d1117')
            price_text = contract_data.get('price_text', 'N/A')
            
            self.notebook.add(tab_frame, text=price_text)
            self.contract_tabs[contract_key] = tab_frame
            
            # Setup tab content
            self.setup_contract_tab_content(tab_frame, contract_key)
            
            # Switch to new tab
            self.notebook.select(tab_frame)
            
            self.log(f"✅ Created tab for {contract_key}")
            
        except Exception as e:
            self.log(f"❌ Error creating contract tab: {e}")
    
    def setup_contract_tab_content(self, tab_frame, contract_key):
        """Setup content for a contract tab."""
        try:
            tracker = self.contracts[contract_key]
            
            # Info section
            info_frame = tk.Frame(tab_frame, bg='#161b22', height=200)
            info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            info_frame.pack_propagate(False)
            
            self.info_text = tk.Text(info_frame, height=10, bg='#0d1117', fg='#f0f6fc',
                                    font=('SF Mono', 10), wrap=tk.WORD)
            self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Update info display
            self.update_contract_info(contract_key)
            
            # Charts section
            charts_frame = tk.Frame(tab_frame, bg='#0d1117')
            charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
            
            # Create real charts with actual data
            self.create_contract_charts(charts_frame, contract_key)
            
        except Exception as e:
            self.log(f"❌ Error setting up tab content: {e}")
    
    def update_contract_info(self, contract_key):
        """Update contract info display."""
        try:
            tracker = self.contracts[contract_key]
            data = tracker.current_data
            
            info = f"""
🎯 CONTRACT: {contract_key.upper()}
{'='*50}
Type: {data.get('type', 'N/A').upper()}
Price: {data.get('price_text', 'N/A')}
Strike: ${data.get('strike', 'N/A')}
Expiration: {data.get('expiration', 'N/A')}

📊 MARKET DATA
Current: ${data.get('current_price', 'N/A')}
Bid: ${data.get('bid', 'N/A')}
Ask: ${data.get('ask', 'N/A')}
Volume: {data.get('volume', 'N/A')}
Open Interest: {data.get('open_interest', 'N/A')}

🏷️ GREEKS
Delta: {data.get('delta', 'N/A')}
Gamma: {data.get('gamma', 'N/A')}
Theta: {data.get('theta', 'N/A')}
Vega: {data.get('vega', 'N/A')}

📈 DAY RANGE
High: ${data.get('high', 'N/A')}
Low: ${data.get('low', 'N/A')}
IV: {data.get('iv', 'N/A')}%

⏰ Last Update: {tracker.last_update.strftime('%H:%M:%S') if tracker.last_update else 'Never'}
📊 Data Points: {len(tracker.data_history)}
            """
            
            # Update the info text widget
            if hasattr(self, 'info_text'):
                self.info_text.delete('1.0', tk.END)
                self.info_text.insert('1.0', info)
            
        except Exception as e:
            pass
    
    def create_contract_charts(self, parent_frame, contract_key):
        """Create charts for contract data."""
        try:
            tracker = self.contracts[contract_key]
            
            # Create matplotlib figure
            fig = Figure(figsize=(12, 8), facecolor='#0d1117')
            
            # Create 4 subplots
            ax1 = fig.add_subplot(2, 2, 1, facecolor='#161b22')
            ax2 = fig.add_subplot(2, 2, 2, facecolor='#161b22')
            ax3 = fig.add_subplot(2, 2, 3, facecolor='#161b22')
            ax4 = fig.add_subplot(2, 2, 4, facecolor='#161b22')
            
            # Style all axes
            for ax in [ax1, ax2, ax3, ax4]:
                ax.tick_params(colors='white', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('white')
            
            # Chart 1: Price over time
            ax1.set_title('Price History', color='white', fontsize=10, pad=10)
            if len(tracker.data_history) > 1:
                timestamps = [d['timestamp'] for d in tracker.data_history]
                prices = [float(d.get('current_price', 0)) for d in tracker.data_history if d.get('current_price')]
                
                if prices:
                    ax1.plot(range(len(prices)), prices, color='#7ee787', linewidth=2)
                    ax1.set_ylabel('Price ($)', color='white', fontsize=8)
                    ax1.grid(True, alpha=0.3)
                else:
                    ax1.text(0.5, 0.5, 'No price data yet', ha='center', va='center', 
                            transform=ax1.transAxes, color='white')
            else:
                ax1.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                        transform=ax1.transAxes, color='white')
            
            # Chart 2: Volume
            ax2.set_title('Volume', color='white', fontsize=10, pad=10)
            if len(tracker.data_history) > 1:
                volumes = [int(d.get('volume', '0').replace(',', '')) for d in tracker.data_history if d.get('volume')]
                
                if volumes:
                    ax2.bar(range(len(volumes)), volumes, color='#58a6ff', alpha=0.7)
                    ax2.set_ylabel('Volume', color='white', fontsize=8)
                    ax2.grid(True, alpha=0.3)
                else:
                    ax2.text(0.5, 0.5, 'No volume data yet', ha='center', va='center', 
                            transform=ax2.transAxes, color='white')
            else:
                ax2.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                        transform=ax2.transAxes, color='white')
            
            # Chart 3: Greeks
            ax3.set_title('Greeks (Theta/Gamma)', color='white', fontsize=10, pad=10)
            if len(tracker.data_history) > 1:
                thetas = [float(d.get('theta', 0)) for d in tracker.data_history if d.get('theta')]
                gammas = [float(d.get('gamma', 0)) for d in tracker.data_history if d.get('gamma')]
                
                if thetas or gammas:
                    if thetas:
                        ax3.plot(range(len(thetas)), thetas, color='#ffa657', label='Theta', linewidth=2)
                    if gammas:
                        # Scale gamma for display (usually much smaller than theta)
                        scaled_gammas = [g * 100 for g in gammas]  # Scale up for visibility
                        ax3.plot(range(len(scaled_gammas)), scaled_gammas, color='#f85149', label='Gamma*100', linewidth=2)
                    
                    ax3.legend(fontsize=8)
                    ax3.grid(True, alpha=0.3)
                else:
                    ax3.text(0.5, 0.5, 'No Greeks data yet', ha='center', va='center', 
                            transform=ax3.transAxes, color='white')
            else:
                ax3.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                        transform=ax3.transAxes, color='white')
            
            # Chart 4: Bid/Ask Spread
            ax4.set_title('Bid/Ask Spread', color='white', fontsize=10, pad=10)
            if len(tracker.data_history) > 1:
                bids = [float(d.get('bid', 0)) for d in tracker.data_history if d.get('bid')]
                asks = [float(d.get('ask', 0)) for d in tracker.data_history if d.get('ask')]
                
                if bids or asks:
                    if bids:
                        ax4.plot(range(len(bids)), bids, color='#7ee787', label='Bid', linewidth=2)
                    if asks:
                        ax4.plot(range(len(asks)), asks, color='#fbb6ce', label='Ask', linewidth=2)
                    
                    ax4.legend(fontsize=8)
                    ax4.set_ylabel('Price ($)', color='white', fontsize=8)
                    ax4.grid(True, alpha=0.3)
                else:
                    ax4.text(0.5, 0.5, 'No bid/ask data yet', ha='center', va='center', 
                            transform=ax4.transAxes, color='white')
            else:
                ax4.text(0.5, 0.5, 'Collecting data...', ha='center', va='center', 
                        transform=ax4.transAxes, color='white')
            
            fig.tight_layout(pad=2.0)
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, parent_frame)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Store references for updates
            tracker.figure = fig
            tracker.axes = [ax1, ax2, ax3, ax4]
            tracker.canvas = canvas
            
        except Exception as e:
            self.log(f"❌ Error creating charts: {e}")
    
    def start_continuous_monitoring(self):
        """Start continuous monitoring and screenshots for all contracts."""
        try:
            self.log("📹 Starting continuous monitoring for all contracts...")
            
            def monitor_all_contracts():
                """Monitor all contracts continuously."""
                import asyncio
                
                async def monitoring_loop():
                    screenshot_count = 0
                    
                    while self.monitoring_active and self.contracts:
                        try:
                            screenshot_count += 1
                            timestamp = datetime.now().strftime("%H%M%S")
                            
                            # Take page screenshot
                            if self.page:
                                screenshot_path = f"screenshots/{self.option_type}_monitor_{timestamp}_{screenshot_count:03d}.png"
                                await self.page.screenshot(path=screenshot_path)
                                
                                # Try to extract current data for all contracts
                                for contract_key, tracker in self.contracts.items():
                                    try:
                                        # Extract current data
                                        current_data = await self.extract_live_data(contract_key)
                                        if current_data:
                                            tracker.add_data_point(current_data)
                                            
                                            # Update GUI
                                            self.root.after(0, lambda k=contract_key: self.update_contract_info(k))
                                            self.root.after(0, lambda k=contract_key: self.refresh_contract_charts(k))
                                    
                                    except Exception as contract_error:
                                        continue
                            
                            await asyncio.sleep(1)  # Screenshot every second
                            
                        except Exception as e:
                            self.log(f"❌ Monitoring error: {e}")
                            await asyncio.sleep(2)
                
                # Run monitoring loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(monitoring_loop())
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=monitor_all_contracts)
            monitor_thread.daemon = True
            monitor_thread.start()
            
        except Exception as e:
            self.log(f"❌ Error starting monitoring: {e}")
    
    async def extract_live_data(self, contract_key):
        """Extract live data for a specific contract."""
        try:
            # Get current page content
            content = await self.page.content()
            
            # Extract current data
            current_data = {
                'timestamp': datetime.now().isoformat()
            }
            
            # Same patterns as before but for live updates
            patterns = {
                'current_price': r'(?:Last|Price|Mark)[:\s]+\$?(\d+\.\d{2,4})',
                'bid': r'Bid[:\s]+\$?(\d+\.\d{2,4})',
                'ask': r'Ask[:\s]+\$?(\d+\.\d{2,4})',
                'volume': r'Volume[:\s]+(\d+(?:,\d+)*)',
                'theta': r'Theta[:\s]+(-?\d+\.\d{2,4})',
                'gamma': r'Gamma[:\s]+(\d+\.\d{2,4})',
                'high': r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2,4})',
                'low': r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2,4})',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    current_data[key] = match.group(1).replace(',', '')
            
            return current_data if len(current_data) > 1 else None
            
        except Exception as e:
            return None
    
    def refresh_contract_charts(self, contract_key):
        """Refresh charts for a specific contract."""
        try:
            if contract_key in self.contracts:
                tracker = self.contracts[contract_key]
                
                if hasattr(tracker, 'figure') and hasattr(tracker, 'axes'):
                    # Clear and redraw charts with new data
                    for ax in tracker.axes:
                        ax.clear()
                    
                    # Recreate charts with updated data
                    self.update_chart_data(tracker)
                    
                    # Refresh canvas
                    tracker.canvas.draw()
                    
        except Exception as e:
            pass
    
    def update_chart_data(self, tracker):
        """Update chart data for a tracker."""
        try:
            ax1, ax2, ax3, ax4 = tracker.axes
            
            # Re-style axes
            for ax in tracker.axes:
                ax.set_facecolor('#161b22')
                ax.tick_params(colors='white', labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color('white')
            
            # Update Price Chart
            ax1.set_title('Price History', color='white', fontsize=10, pad=10)
            prices = [float(d.get('current_price', 0)) for d in tracker.data_history if d.get('current_price')]
            if len(prices) > 1:
                ax1.plot(range(len(prices)), prices, color='#7ee787', linewidth=2)
                ax1.set_ylabel('Price ($)', color='white', fontsize=8)
                ax1.grid(True, alpha=0.3)
            
            # Update Volume Chart
            ax2.set_title('Volume', color='white', fontsize=10, pad=10)
            volumes = [int(d.get('volume', '0').replace(',', '')) for d in tracker.data_history if d.get('volume')]
            if len(volumes) > 1:
                ax2.bar(range(len(volumes)), volumes, color='#58a6ff', alpha=0.7)
                ax2.set_ylabel('Volume', color='white', fontsize=8)
                ax2.grid(True, alpha=0.3)
            
            # Update Greeks Chart
            ax3.set_title('Greeks (Theta/Gamma)', color='white', fontsize=10, pad=10)
            thetas = [float(d.get('theta', 0)) for d in tracker.data_history if d.get('theta')]
            gammas = [float(d.get('gamma', 0)) for d in tracker.data_history if d.get('gamma')]
            
            if thetas:
                ax3.plot(range(len(thetas)), thetas, color='#ffa657', label='Theta', linewidth=2)
            if gammas:
                scaled_gammas = [g * 100 for g in gammas]
                ax3.plot(range(len(scaled_gammas)), scaled_gammas, color='#f85149', label='Gamma*100', linewidth=2)
            
            if thetas or gammas:
                ax3.legend(fontsize=8)
                ax3.grid(True, alpha=0.3)
            
            # Update Bid/Ask Chart
            ax4.set_title('Bid/Ask Spread', color='white', fontsize=10, pad=10)
            bids = [float(d.get('bid', 0)) for d in tracker.data_history if d.get('bid')]
            asks = [float(d.get('ask', 0)) for d in tracker.data_history if d.get('ask')]
            
            if bids:
                ax4.plot(range(len(bids)), bids, color='#7ee787', label='Bid', linewidth=2)
            if asks:
                ax4.plot(range(len(asks)), asks, color='#fbb6ce', label='Ask', linewidth=2)
            
            if bids or asks:
                ax4.legend(fontsize=8)
                ax4.set_ylabel('Price ($)', color='white', fontsize=8)
                ax4.grid(True, alpha=0.3)
            
        except Exception as e:
            pass
    
    def show(self):
        """Show this terminal window."""
        self.root.mainloop()

def launch_calls_terminal():
    """Launch the calls terminal."""
    calls_terminal = SPYTerminal('call', 'SPY Calls Terminal')
    calls_terminal.show()

def launch_puts_terminal():
    """Launch the puts terminal."""
    puts_terminal = SPYTerminal('put', 'SPY Puts Terminal')
    puts_terminal.show()

def main():
    """Main launcher - asks user which terminal to launch."""
    print("🚀 SPY Options Dual Terminal System")
    print("=" * 50)
    print("Choose which terminal to launch:")
    print("1. CALLS Terminal")
    print("2. PUTS Terminal") 
    print("3. Both (launches two separate windows)")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == '1':
        launch_calls_terminal()
    elif choice == '2':
        launch_puts_terminal()
    elif choice == '3':
        # Launch both in separate processes
        import multiprocessing
        
        # Start calls terminal
        calls_process = multiprocessing.Process(target=launch_calls_terminal)
        calls_process.start()
        
        # Start puts terminal  
        puts_process = multiprocessing.Process(target=launch_puts_terminal)
        puts_process.start()
        
        print("✅ Both terminals launched!")
        print("CALLS terminal should appear on the left")
        print("PUTS terminal should appear on the right")
        
        # Wait for both processes
        calls_process.join()
        puts_process.join()
    else:
        print("Invalid choice. Launching CALLS terminal by default.")
        launch_calls_terminal()

if __name__ == "__main__":
    main()