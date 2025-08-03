#!/usr/bin/env python3
"""
Simple SPY Options GUI that actually works and clicks contracts
"""
import asyncio
import tkinter as tk
from tkinter import scrolledtext
import threading
from datetime import datetime
from playwright.async_api import async_playwright
import yfinance as yf
import pandas as pd
import numpy as np
import talib
import re
import time

class SPYOptionsGUI:
    def __init__(self):
        # Force GUI to show
        self.root = tk.Tk()
        self.root.title("SPY Options Live Data")
        self.root.geometry("800x600")
        self.root.configure(bg='#1e1e1e')
        
        # Force window to appear
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        
        self.setup_gui()
        print("✅ GUI created and should be visible!")
        
    def setup_gui(self):
        """Setup simple GUI."""
        # Title
        title = tk.Label(self.root, text="🚀 SPY Options Live Contract Data", 
                        font=('Arial', 16, 'bold'), fg='#00ff88', bg='#1e1e1e')
        title.pack(pady=10)
        
        # Start button
        self.start_btn = tk.Button(self.root, text="🔄 Start Live Analysis", 
                                  command=self.start_analysis,
                                  font=('Arial', 12, 'bold'),
                                  bg='#0066cc', fg='white', pady=10)
        self.start_btn.pack(pady=10)
        
        # Status
        self.status = tk.Label(self.root, text="Status: Ready to start", 
                              font=('Arial', 11), fg='#00ff88', bg='#1e1e1e')
        self.status.pack(pady=5)
        
        # Output area
        self.output = scrolledtext.ScrolledText(self.root, height=30, width=100,
                                               bg='#2d2d2d', fg='#ffffff', 
                                               font=('Courier', 10))
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add initial message
        self.log("🎯 Ready to analyze SPY options contracts!")
        self.log("📋 Click 'Start Live Analysis' to begin")
        
    def log(self, message):
        """Add message to output."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{timestamp}] {message}\n")
        self.output.see(tk.END)
        self.root.update()
        
    def update_status(self, status):
        """Update status."""
        self.status.config(text=f"Status: {status}")
        self.root.update()
        
    def start_analysis(self):
        """Start analysis in background."""
        self.start_btn.config(state='disabled', text='🔄 Analyzing...')
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
        
    def run_analysis(self):
        """Run the analysis."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.analyze_options())
        except Exception as e:
            self.log(f"❌ Error: {e}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state='normal', text='🔄 Start Live Analysis'))
            
    async def analyze_options(self):
        """Main analysis function."""
        playwright = None
        try:
            # Step 1: Get SPY data first
            self.root.after(0, lambda: self.update_status("Getting SPY data..."))
            self.root.after(0, lambda: self.log("📈 Getting SPY price and RSI data..."))
            
            spy_data = self.get_spy_data()
            if spy_data:
                price = spy_data['price']
                rsi_1m = spy_data.get('rsi_1m', 'N/A')
                rsi_5m = spy_data.get('rsi_5m', 'N/A')
                
                self.root.after(0, lambda: self.log(f"💰 SPY Price: ${price:.2f}"))
                self.root.after(0, lambda: self.log(f"📊 RSI 1m: {rsi_1m}"))
                self.root.after(0, lambda: self.log(f"📊 RSI 5m: {rsi_5m}"))
                
                # Determine bias
                bias = self.determine_bias(rsi_1m, rsi_5m)
                self.root.after(0, lambda: self.log(f"🎯 Market Bias: {bias}"))
            
            # Step 2: Connect to browser
            self.root.after(0, lambda: self.update_status("Connecting to Chrome..."))
            self.root.after(0, lambda: self.log("🔗 Connecting to Chrome browser..."))
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            contexts = browser.contexts
            if not contexts:
                self.root.after(0, lambda: self.log("❌ No browser contexts found"))
                return
                
            context = contexts[0]
            pages = context.pages
            page = pages[0] if pages else await context.new_page()
            
            self.root.after(0, lambda: self.log("✅ Connected to Chrome"))
            
            # Step 3: Navigate to options
            self.root.after(0, lambda: self.update_status("Loading SPY options..."))
            self.root.after(0, lambda: self.log("📊 Loading SPY options page..."))
            
            await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            if "login" in page.url:
                self.root.after(0, lambda: self.log("🔐 Please log into Robinhood first"))
                return
                
            self.root.after(0, lambda: self.log("✅ SPY options page loaded"))
            
            # Step 4: Actually click on contracts and examine them
            self.root.after(0, lambda: self.update_status("Examining option contracts..."))
            self.root.after(0, lambda: self.log("🔍 Looking for option contracts to click..."))
            
            # Try to find clickable option elements
            await self.examine_option_contracts(page)
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Analysis error: {e}"))
        finally:
            if playwright:
                await playwright.stop()
            self.root.after(0, lambda: self.update_status("Analysis complete"))
            
    async def examine_option_contracts(self, page):
        """Actually click on option contracts to examine their data."""
        try:
            # Wait for options to load
            await asyncio.sleep(3)
            
            # Take screenshot to see what we're working with
            await page.screenshot(path="current_options_page.png")
            self.root.after(0, lambda: self.log("📸 Screenshot saved: current_options_page.png"))
            
            # Look for clickable option elements with various selectors
            selectors_to_try = [
                'button[data-testid*="option"]',
                'div[role="button"]',
                'tr[role="row"]',
                'button:has-text("$")',
                'div:has-text("$0.")',
                '[data-rh-test-id*="option"]',
                'a[href*="option"]',
                'span:has-text("$0.")',
                'td:has-text("$0.")'
            ]
            
            contracts_found = 0
            
            for selector in selectors_to_try:
                try:
                    self.root.after(0, lambda s=selector: self.log(f"🔍 Trying selector: {s}"))
                    
                    elements = page.locator(selector)
                    count = await elements.count()
                    
                    if count > 0:
                        self.root.after(0, lambda c=count, s=selector: self.log(f"✅ Found {c} elements with {s}"))
                        
                        # Try to click on first few elements
                        for i in range(min(count, 5)):
                            try:
                                element = elements.nth(i)
                                
                                # Get element text first
                                element_text = await element.text_content()
                                if element_text:
                                    self.root.after(0, lambda txt=element_text: self.log(f"📋 Element text: {txt[:100]}"))
                                
                                # Look for price patterns in the text
                                if element_text and ('$0.' in element_text or '$' in element_text):
                                    self.root.after(0, lambda: self.log(f"🎯 Found potential option contract, clicking..."))
                                    
                                    # Click the element
                                    await element.click()
                                    await asyncio.sleep(3)
                                    
                                    # Take screenshot after click
                                    await page.screenshot(path=f"contract_clicked_{contracts_found}.png")
                                    
                                    # Try to extract contract data
                                    contract_data = await self.extract_contract_data(page)
                                    if contract_data:
                                        self.root.after(0, lambda data=contract_data: self.display_contract_data(data))
                                        contracts_found += 1
                                    
                                    # Go back or close modal
                                    await page.keyboard.press('Escape')
                                    await asyncio.sleep(2)
                                    
                                    if contracts_found >= 3:  # Limit to 3 contracts for now
                                        break
                                        
                            except Exception as click_error:
                                self.root.after(0, lambda e=click_error: self.log(f"⚠️ Click failed: {e}"))
                                continue
                        
                        if contracts_found > 0:
                            break  # Found some contracts, stop trying other selectors
                            
                except Exception as selector_error:
                    continue
            
            if contracts_found == 0:
                self.root.after(0, lambda: self.log("❌ No clickable option contracts found"))
                self.root.after(0, lambda: self.log("💡 Try scrolling on the page or check if options are visible"))
                
                # Try scrolling and looking again
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                # Get page content and look for any price patterns
                content = await page.content()
                prices = re.findall(r'\$0\.(\d{2})', content)
                if prices:
                    self.root.after(0, lambda p=prices: self.log(f"💰 Found price patterns on page: {p[:10]}"))
                else:
                    self.root.after(0, lambda: self.log("❌ No price patterns found on page"))
            else:
                self.root.after(0, lambda c=contracts_found: self.log(f"✅ Successfully examined {c} option contracts"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Error examining contracts: {e}"))
            
    async def extract_contract_data(self, page):
        """Extract data from a clicked contract."""
        try:
            # Wait for contract details to load
            await asyncio.sleep(2)
            
            # Get current page content
            content = await page.content()
            
            contract_data = {
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            
            # Look for various data points
            price_match = re.search(r'\$(\d+\.\d{2})', content)
            if price_match:
                contract_data['current_price'] = price_match.group(1)
            
            # Look for bid/ask
            bid_match = re.search(r'Bid[:\s]+\$?(\d+\.\d{2})', content, re.IGNORECASE)
            if bid_match:
                contract_data['bid'] = bid_match.group(1)
                
            ask_match = re.search(r'Ask[:\s]+\$?(\d+\.\d{2})', content, re.IGNORECASE)
            if ask_match:
                contract_data['ask'] = ask_match.group(1)
            
            # Look for volume
            volume_match = re.search(r'Volume[:\s]+(\d+)', content, re.IGNORECASE)
            if volume_match:
                contract_data['volume'] = volume_match.group(1)
            
            # Look for open interest
            oi_match = re.search(r'Open Interest[:\s]+(\d+)', content, re.IGNORECASE)
            if oi_match:
                contract_data['open_interest'] = oi_match.group(1)
            
            # Look for strike
            strike_match = re.search(r'Strike[:\s]+\$?(\d+)', content, re.IGNORECASE)
            if strike_match:
                contract_data['strike'] = strike_match.group(1)
            
            return contract_data if len(contract_data) > 1 else None
            
        except Exception as e:
            return None
            
    def display_contract_data(self, data):
        """Display extracted contract data."""
        self.log("=" * 50)
        self.log(f"🎯 CONTRACT DATA [{data.get('timestamp', 'N/A')}]")
        self.log("=" * 50)
        
        for key, value in data.items():
            if key != 'timestamp':
                self.log(f"   {key.replace('_', ' ').title()}: {value}")
        
        self.log("=" * 50)
    
    def get_spy_data(self):
        """Get SPY price and RSI data."""
        try:
            # Get SPY data
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
        """Determine market bias from RSI."""
        try:
            if rsi_1m == "N/A" or rsi_5m == "N/A":
                return "UNKNOWN (insufficient data)"
            
            rsi_1m_val = float(rsi_1m)
            rsi_5m_val = float(rsi_5m)
            
            if rsi_1m_val < 30 and rsi_5m_val < 30:
                return "STRONG BULLISH (both oversold)"
            elif rsi_1m_val > 70 and rsi_5m_val > 70:
                return "STRONG BEARISH (both overbought)"
            elif rsi_1m_val < 30:
                return "MILD BULLISH (1m oversold)"
            elif rsi_1m_val > 70:
                return "MILD BEARISH (1m overbought)"
            else:
                return "NEUTRAL (no clear bias)"
                
        except:
            return "UNKNOWN"
    
    def show(self):
        """Show the GUI."""
        self.root.mainloop()

def main():
    """Main function."""
    print("🚀 Starting SPY Options GUI...")
    print("✅ GUI should open in a new window")
    
    app = SPYOptionsGUI()
    app.show()

if __name__ == "__main__":
    main()