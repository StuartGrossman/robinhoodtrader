#!/usr/bin/env python3
"""
SPY Options Analyzer with GUI - Fixed Version
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

class SPYOptionsAnalyzer:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.options_data = []
        self.spy_data = None
        
    async def connect_to_chrome(self):
        """Connect to existing Chrome browser."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            contexts = self.browser.contexts
            if not contexts:
                print("❌ No browser contexts found")
                return False
            
            context = contexts[0]
            pages = context.pages
            
            if not pages:
                self.page = await context.new_page()
            else:
                self.page = pages[0]
            
            print("✅ Connected to Chrome!")
            return True
            
        except Exception as e:
            print(f"❌ Could not connect to Chrome: {e}")
            return False

    async def navigate_to_spy_options(self):
        """Navigate to SPY options chain."""
        try:
            print("📊 Navigating to SPY options...")
            await self.page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            current_url = self.page.url
            if "login" in current_url:
                print("🔐 Please log into Robinhood first")
                return False
            
            print("✅ SPY options page loaded")
            
            # Take screenshot for debugging
            await self.page.screenshot(path="logs/screenshots/spy_options_page.png")
            print("📸 Screenshot saved for debugging")
            
            return True
            
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False

    def get_spy_rsi_data(self):
        """Fetch SPY data and calculate RSI."""
        try:
            print("📈 Fetching SPY RSI data...")
            
            # Get data
            spy_1m = yf.download("SPY", period="5d", interval="1m", progress=False)
            spy_5m = yf.download("SPY", period="5d", interval="5m", progress=False)
            
            if spy_1m.empty or spy_5m.empty:
                print("❌ Could not fetch SPY data")
                return None
            
            # Calculate RSI
            rsi_1m = talib.RSI(spy_1m['Close'].values, timeperiod=14)
            rsi_5m = talib.RSI(spy_5m['Close'].values, timeperiod=14)
            
            current_price = spy_1m['Close'].iloc[-1]
            current_rsi_1m = rsi_1m[-1] if not np.isnan(rsi_1m[-1]) else None
            current_rsi_5m = rsi_5m[-1] if not np.isnan(rsi_5m[-1]) else None
            
            self.spy_data = {
                'current_price': float(current_price),
                'rsi_1m': float(current_rsi_1m) if current_rsi_1m else None,
                'rsi_5m': float(current_rsi_5m) if current_rsi_5m else None,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📊 SPY: ${current_price:.2f}")
            print(f"📊 RSI 1m: {current_rsi_1m:.1f}" if current_rsi_1m else "📊 RSI 1m: N/A")
            print(f"📊 RSI 5m: {current_rsi_5m:.1f}" if current_rsi_5m else "📊 RSI 5m: N/A")
            
            return self.spy_data
            
        except Exception as e:
            print(f"❌ Error fetching SPY data: {e}")
            return None

    async def scan_options_improved(self):
        """Improved options scanning with better selectors."""
        try:
            print("🔍 Scanning for options contracts...")
            
            # Wait for page to fully load
            await asyncio.sleep(3)
            
            # Try to scroll down to load more options
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Take screenshot to see what we're working with
            await self.page.screenshot(path="logs/screenshots/options_chain.png")
            
            found_options = []
            
            # More comprehensive selectors for Robinhood options
            option_selectors = [
                # Generic option price selectors
                'text=/\\$0\\.(0[8-9]|1[0-6])/',  # $0.08 to $0.16
                '[data-testid*="option"] text=/\\$0\\.(0[8-9]|1[0-6])/',
                'tr:has-text("$0.") td:has-text("$0.")',
                'div:has-text("$0.0") span:has-text("$0.")',
                # Table cell selectors
                'td:has-text("$0.")',
                'span:has-text("$0.")',
                # More specific Robinhood selectors
                '[data-rh-test-id*="option"]',
                '[role="gridcell"]:has-text("$0.")',
                'button:has-text("$0.")'
            ]
            
            print("🔎 Trying different selectors...")
            
            for i, selector in enumerate(option_selectors):
                print(f"Trying selector {i+1}: {selector}")
                
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    
                    if count > 0:
                        print(f"✅ Found {count} elements with selector: {selector}")
                        
                        # Get all text content from elements
                        for j in range(min(count, 20)):  # Limit to first 20
                            try:
                                element = elements.nth(j)
                                text = await element.text_content()
                                
                                if text and '$0.' in text:
                                    # Extract all price matches
                                    price_matches = re.findall(r'\$0\.(\d{2})', text)
                                    
                                    for price_match in price_matches:
                                        price_cents = int(price_match)
                                        if 8 <= price_cents <= 16:
                                            print(f"🎯 Found option in range: $0.{price_match}")
                                            
                                            # Create basic option data
                                            option_data = {
                                                'price_cents': price_cents,
                                                'price_text': f"$0.{price_match}",
                                                'element_text': text.strip(),
                                                'timestamp': datetime.now().isoformat(),
                                                'type': 'unknown',  # Will try to determine
                                                'strike': 'unknown',
                                                'expiration': 'unknown'
                                            }
                                            
                                            # Try to click and get more details
                                            try:
                                                print(f"  🖱️ Attempting to click option...")
                                                await element.click()
                                                await asyncio.sleep(2)
                                                
                                                # Try to extract more details after click
                                                details = await self.extract_option_details_simple()
                                                if details:
                                                    option_data.update(details)
                                                
                                                # Take screenshot after click
                                                await self.page.screenshot(path=f"logs/screenshots/option_clicked_{len(found_options)}.png")
                                                
                                                found_options.append(option_data)
                                                
                                                # Go back or close modal if needed
                                                await self.page.keyboard.press('Escape')
                                                await asyncio.sleep(1)
                                                
                                            except Exception as click_error:
                                                print(f"  ⚠️ Click failed: {click_error}")
                                                # Still add the option even if click failed
                                                found_options.append(option_data)
                                            
                            except Exception as element_error:
                                print(f"  ⚠️ Element error: {element_error}")
                                continue
                        
                        if found_options:
                            break  # Found options with this selector, stop trying others
                            
                except Exception as selector_error:
                    print(f"  ❌ Selector failed: {selector_error}")
                    continue
            
            # If no options found with specific selectors, try a more general approach
            if not found_options:
                print("🔄 Trying general text search...")
                page_content = await self.page.content()
                
                # Search for price patterns in page content
                price_matches = re.findall(r'\$0\.(\d{2})', page_content)
                
                for price_match in price_matches:
                    price_cents = int(price_match)
                    if 8 <= price_cents <= 16:
                        found_options.append({
                            'price_cents': price_cents,
                            'price_text': f"$0.{price_match}",
                            'element_text': f"Found in page content: $0.{price_match}",
                            'timestamp': datetime.now().isoformat(),
                            'type': 'unknown',
                            'strike': 'unknown',
                            'expiration': 'unknown'
                        })
            
            self.options_data = found_options
            print(f"📋 Total options found in 8-16¢ range: {len(found_options)}")
            
            return found_options
            
        except Exception as e:
            print(f"❌ Error scanning options: {e}")
            return []

    async def extract_option_details_simple(self):
        """Simple option details extraction."""
        try:
            details = {}
            
            # Wait a moment for details to load
            await asyncio.sleep(1)
            
            # Get current page content
            content = await self.page.content()
            
            # Look for call/put indicators
            if re.search(r'\bcall\b', content, re.IGNORECASE):
                details['type'] = 'call'
            elif re.search(r'\bput\b', content, re.IGNORECASE):
                details['type'] = 'put'
            
            # Look for strike prices
            strike_matches = re.findall(r'\$(\d{3,4})', content)
            if strike_matches:
                details['strike'] = f"${strike_matches[0]}"
            
            # Look for expiration dates
            exp_matches = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', content)
            if exp_matches:
                details['expiration'] = exp_matches[0]
            
            return details
            
        except Exception as e:
            print(f"❌ Error extracting details: {e}")
            return {}

    def analyze_trade_opportunities(self):
        """Analyze options and provide recommendations."""
        if not self.options_data or not self.spy_data:
            print("❌ Missing data for analysis")
            return []
        
        recommendations = []
        
        rsi_1m = self.spy_data.get('rsi_1m')
        rsi_5m = self.spy_data.get('rsi_5m')
        
        # Determine market bias
        if rsi_1m and rsi_5m:
            if rsi_1m < 30 and rsi_5m < 30:
                bias = "STRONG_BULLISH"
                preferred_type = "call"
            elif rsi_1m > 70 and rsi_5m > 70:
                bias = "STRONG_BEARISH"
                preferred_type = "put"
            elif rsi_1m < 30:
                bias = "MILD_BULLISH"
                preferred_type = "call"
            elif rsi_1m > 70:
                bias = "MILD_BEARISH"
                preferred_type = "put"
            else:
                bias = "NEUTRAL"
                preferred_type = None
        else:
            bias = "UNKNOWN"
            preferred_type = None
        
        # Analyze each option
        for option in self.options_data:
            price_cents = option.get('price_cents', 0)
            option_type = option.get('type', 'unknown')
            
            score = 0
            analysis = []
            
            # Price scoring
            if price_cents <= 10:
                score += 3
                analysis.append("Very cheap premium")
            elif price_cents <= 13:
                score += 2
                analysis.append("Reasonable premium")
            else:
                score += 1
                analysis.append("Higher premium")
            
            # Bias alignment
            if preferred_type and option_type == preferred_type:
                score += 5
                analysis.append(f"Aligns with {bias} bias")
            elif preferred_type and option_type != preferred_type:
                score -= 2
                analysis.append(f"Contrarian to {bias} bias")
            
            recommendation = {
                'option': option,
                'score': score,
                'analysis': analysis,
                'recommendation': 'BUY' if score >= 4 else 'CONSIDER' if score >= 2 else 'AVOID'
            }
            
            recommendations.append(recommendation)
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations

class SPYAnalyzerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SPY Options Analyzer Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        self.spy_data = None
        self.options_data = []
        self.recommendations = []
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup GUI components."""
        # Main frame
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="🚀 SPY Options Analyzer Dashboard", 
                              font=('Arial', 20, 'bold'), fg='#00ff88', bg='#1e1e1e')
        title_label.pack(pady=(0, 20))
        
        # Control panel
        control_frame = tk.Frame(main_frame, bg='#2d2d2d', relief=tk.RAISED, bd=2)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.refresh_btn = tk.Button(control_frame, text="🔄 Start Analysis", 
                                    command=self.start_analysis, font=('Arial', 12, 'bold'),
                                    bg='#0066cc', fg='white', pady=10)
        self.refresh_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.status_label = tk.Label(control_frame, text="Status: Ready to start", 
                                    font=('Arial', 12), fg='#00ff88', bg='#2d2d2d')
        self.status_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Results display
        results_frame = tk.Frame(main_frame, bg='#1e1e1e')
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=30, width=100,
                                                     bg='#1a1a1a', fg='#ffffff', 
                                                     font=('Courier', 10))
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def update_status(self, status):
        """Update status display."""
        self.status_label.config(text=f"Status: {status}")
        self.root.update()
        
    def log_message(self, message):
        """Add message to results display."""
        self.results_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.results_text.see(tk.END)
        self.root.update()
        
    def start_analysis(self):
        """Start analysis in background thread."""
        self.refresh_btn.config(state='disabled', text='🔄 Running...')
        self.results_text.delete('1.0', tk.END)
        
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
        
    def run_analysis(self):
        """Run the complete analysis."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run analysis
            loop.run_until_complete(self.async_analysis())
            
        except Exception as e:
            self.log_message(f"❌ Analysis error: {e}")
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state='normal', text='🔄 Start Analysis'))
            
    async def async_analysis(self):
        """Async analysis function."""
        analyzer = SPYOptionsAnalyzer()
        
        try:
            # Connect to browser
            self.root.after(0, lambda: self.update_status("Connecting to Chrome..."))
            self.root.after(0, lambda: self.log_message("🔗 Connecting to Chrome browser..."))
            
            if not await analyzer.connect_to_chrome():
                self.root.after(0, lambda: self.log_message("❌ Failed to connect to Chrome"))
                return
            
            # Navigate to options
            self.root.after(0, lambda: self.update_status("Navigating to options..."))
            self.root.after(0, lambda: self.log_message("📊 Navigating to SPY options page..."))
            
            if not await analyzer.navigate_to_spy_options():
                self.root.after(0, lambda: self.log_message("❌ Failed to navigate to options"))
                return
            
            # Get SPY data
            self.root.after(0, lambda: self.update_status("Fetching SPY data..."))
            self.root.after(0, lambda: self.log_message("📈 Fetching SPY RSI data..."))
            
            spy_data = analyzer.get_spy_rsi_data()
            if spy_data:
                price = spy_data.get('current_price', 0)
                rsi_1m = spy_data.get('rsi_1m')
                rsi_5m = spy_data.get('rsi_5m')
                
                self.root.after(0, lambda: self.log_message(f"💰 SPY Price: ${price:.2f}"))
                if rsi_1m: self.root.after(0, lambda: self.log_message(f"📊 RSI 1m: {rsi_1m:.1f}"))
                if rsi_5m: self.root.after(0, lambda: self.log_message(f"📊 RSI 5m: {rsi_5m:.1f}"))
            
            # Scan options
            self.root.after(0, lambda: self.update_status("Scanning options contracts..."))
            self.root.after(0, lambda: self.log_message("🔍 Scanning for options in 8-16¢ range..."))
            
            options = await analyzer.scan_options_improved()
            
            self.root.after(0, lambda: self.log_message(f"📋 Found {len(options)} options in price range"))
            
            # Display found options
            for i, option in enumerate(options, 1):
                price_text = option.get('price_text', 'N/A')
                option_type = option.get('type', 'unknown')
                strike = option.get('strike', 'unknown')
                
                self.root.after(0, lambda i=i, pt=price_text, ot=option_type, s=strike: 
                              self.log_message(f"  #{i}: {pt} - {ot.upper()} - Strike: {s}"))
            
            # Generate recommendations
            if options:
                self.root.after(0, lambda: self.update_status("Generating recommendations..."))
                self.root.after(0, lambda: self.log_message("🎯 Analyzing trade opportunities..."))
                
                recommendations = analyzer.analyze_trade_opportunities()
                
                self.root.after(0, lambda: self.log_message("\n🎯 TRADE RECOMMENDATIONS:"))
                self.root.after(0, lambda: self.log_message("=" * 50))
                
                for i, rec in enumerate(recommendations[:5], 1):
                    option = rec['option']
                    score = rec['score']
                    recommendation = rec['recommendation']
                    analysis = rec['analysis']
                    
                    self.root.after(0, lambda i=i, r=recommendation, s=score: 
                                  self.log_message(f"\n#{i} - {r} (Score: {s})"))
                    
                    price_text = option.get('price_text', 'N/A')
                    option_type = option.get('type', 'unknown')
                    
                    self.root.after(0, lambda pt=price_text, ot=option_type: 
                                  self.log_message(f"  Price: {pt} | Type: {ot.upper()}"))
                    
                    for point in analysis:
                        self.root.after(0, lambda p=point: self.log_message(f"  • {p}"))
            
            else:
                self.root.after(0, lambda: self.log_message("❌ No options found in the specified price range"))
                self.root.after(0, lambda: self.log_message("💡 Try checking if you're logged into Robinhood"))
            
            self.root.after(0, lambda: self.update_status("Analysis complete!"))
            self.root.after(0, lambda: self.log_message("\n✅ Analysis complete!"))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Error during analysis: {e}"))
        finally:
            if analyzer.playwright:
                await analyzer.playwright.stop()

def main():
    """Main function."""
    print("🚀 Starting SPY Options Analyzer GUI...")
    app = SPYAnalyzerGUI()
    app.root.mainloop()

if __name__ == "__main__":
    main()