#!/usr/bin/env python3
"""
SPY Options Analyzer with Working GUI
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
                return False
            
            context = contexts[0]
            pages = context.pages
            
            if not pages:
                self.page = await context.new_page()
            else:
                self.page = pages[0]
            
            return True
            
        except Exception as e:
            print(f"❌ Could not connect to Chrome: {e}")
            return False

    async def navigate_to_spy_options(self):
        """Navigate to SPY options and wait for full load."""
        try:
            await self.page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            current_url = self.page.url
            if "login" in current_url:
                return False
            
            try:
                await self.page.wait_for_selector('button:has-text("Call")', timeout=10000)
            except:
                pass
            
            return True
            
        except Exception as e:
            return False

    def get_spy_rsi_data(self):
        """Fetch SPY data and calculate RSI."""
        try:
            # Get data
            spy_1m = yf.download("SPY", period="5d", interval="1m", progress=False)
            spy_5m = yf.download("SPY", period="5d", interval="5m", progress=False)
            
            if spy_1m.empty or spy_5m.empty:
                return None
            
            # Handle multi-level columns from yfinance
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
            if len(close_1m) < 15:
                rsi_1m = np.array([np.nan])
            else:
                rsi_1m = talib.RSI(close_1m, timeperiod=14)
            
            if len(close_5m) < 15:
                rsi_5m = np.array([np.nan])
            else:
                rsi_5m = talib.RSI(close_5m, timeperiod=14)
            
            current_rsi_1m = rsi_1m[-1] if not np.isnan(rsi_1m[-1]) else None
            current_rsi_5m = rsi_5m[-1] if not np.isnan(rsi_5m[-1]) else None
            
            self.spy_data = {
                'current_price': float(current_price),
                'rsi_1m': float(current_rsi_1m) if current_rsi_1m else None,
                'rsi_5m': float(current_rsi_5m) if current_rsi_5m else None,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.spy_data
            
        except Exception as e:
            return None

    async def scan_robinhood_options(self):
        """Scan Robinhood options using proper interface interaction."""
        try:
            all_options = []
            await asyncio.sleep(3)
            
            # Try both Call and Put tabs
            option_types = ['Call', 'Put']
            
            for option_type in option_types:
                try:
                    tab_button = self.page.locator(f'button:has-text("{option_type}")')
                    if await tab_button.count() > 0:
                        await tab_button.click()
                        await asyncio.sleep(3)
                        
                        options_found = await self.extract_options_from_current_view(option_type.lower())
                        all_options.extend(options_found)
                        
                except Exception as tab_error:
                    continue
            
            # Also try scrolling
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            additional_options = await self.extract_options_from_current_view("unknown")
            all_options.extend(additional_options)
            
            # Remove duplicates
            seen = set()
            unique_options = []
            for option in all_options:
                key = f"{option.get('price_cents', 0)}_{option.get('type', 'unknown')}"
                if key not in seen:
                    seen.add(key)
                    unique_options.append(option)
            
            self.options_data = unique_options
            return unique_options
            
        except Exception as e:
            return []

    async def extract_options_from_current_view(self, option_type):
        """Extract options data from current page view."""
        try:
            found_options = []
            page_content = await self.page.content()
            
            # Look for price patterns
            price_patterns = [
                r'\$0\.(\d{2})',
                r'0\.(\d{2})',
                r'\.(\d{2})¢',
                r'(\d{1,2})¢',
                r'(\d{1,2})\s*cents',
            ]
            
            all_prices = []
            for pattern in price_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    try:
                        price_cents = int(match)
                        if 8 <= price_cents <= 16:
                            all_prices.append(price_cents)
                    except:
                        continue
            
            unique_prices = sorted(list(set(all_prices)))
            
            for price_cents in unique_prices:
                price_text = f"$0.{price_cents:02d}"
                
                option_data = {
                    'price_cents': price_cents,
                    'price_text': price_text,
                    'type': option_type,
                    'element_text': f'Found {price_text} on page',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Try to extract more details
                strike_match = re.search(rf'\${price_text}.*?\$(\d{{3,4}})', page_content)
                if strike_match:
                    option_data['strike'] = f"${strike_match.group(1)}"
                
                exp_match = re.search(rf'\${price_text}.*?(\d{{1,2}}/\d{{1,2}})', page_content)
                if exp_match:
                    option_data['expiration'] = exp_match.group(1)
                
                found_options.append(option_data)
            
            return found_options
            
        except Exception as e:
            return []

    def analyze_and_recommend(self):
        """Analyze options and provide recommendations."""
        if not self.options_data or not self.spy_data:
            return []
        
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
        
        recommendations = []
        
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
            elif option_type == 'unknown':
                analysis.append("Option type unclear")
            
            if score >= 5:
                recommendation = 'STRONG BUY'
            elif score >= 3:
                recommendation = 'BUY'
            elif score >= 1:
                recommendation = 'CONSIDER'
            else:
                recommendation = 'AVOID'
            
            recommendations.append({
                'option': option,
                'score': score,
                'analysis': analysis,
                'recommendation': recommendation,
                'bias': bias,
                'preferred_type': preferred_type
            })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations

class SPYAnalyzerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚀 SPY Options Analyzer Dashboard")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#0d1117')  # GitHub dark theme
        
        # Data storage
        self.spy_data = None
        self.options_data = []
        self.recommendations = []
        self.analyzer = None
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the GUI layout."""
        # Main container with padding
        main_frame = tk.Frame(self.root, bg='#0d1117')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title with gradient-like effect
        title_frame = tk.Frame(main_frame, bg='#0d1117')
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="🚀 SPY OPTIONS ANALYZER DASHBOARD", 
                              font=('SF Pro Display', 24, 'bold'), 
                              fg='#58a6ff', bg='#0d1117')
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Real-time Options Analysis with RSI Decision Tree", 
                                 font=('SF Pro Display', 12), 
                                 fg='#8b949e', bg='#0d1117')
        subtitle_label.pack(pady=(5, 0))
        
        # Top dashboard section
        dashboard_frame = tk.Frame(main_frame, bg='#161b22', relief=tk.RAISED, bd=1)
        dashboard_frame.pack(fill=tk.X, pady=(0, 15))
        
        # SPY Data Panel
        spy_panel = tk.LabelFrame(dashboard_frame, text=" 📊 SPY MARKET DATA ", 
                                 font=('SF Pro Display', 14, 'bold'), 
                                 fg='#58a6ff', bg='#161b22', bd=2)
        spy_panel.pack(side=tk.LEFT, padx=15, pady=15, fill=tk.BOTH, expand=True)
        
        self.spy_price_label = tk.Label(spy_panel, text="💰 Price: Loading...", 
                                       font=('SF Mono', 16, 'bold'), 
                                       fg='#f0f6fc', bg='#161b22')
        self.spy_price_label.pack(anchor=tk.W, padx=15, pady=8)
        
        self.rsi_1m_label = tk.Label(spy_panel, text="📊 RSI 1m: Loading...", 
                                    font=('SF Mono', 14), 
                                    fg='#ffa657', bg='#161b22')
        self.rsi_1m_label.pack(anchor=tk.W, padx=15, pady=4)
        
        self.rsi_5m_label = tk.Label(spy_panel, text="📊 RSI 5m: Loading...", 
                                    font=('SF Mono', 14), 
                                    fg='#ffa657', bg='#161b22')
        self.rsi_5m_label.pack(anchor=tk.W, padx=15, pady=4)
        
        self.bias_label = tk.Label(spy_panel, text="🎯 Bias: Analyzing...", 
                                  font=('SF Mono', 14, 'bold'), 
                                  fg='#7ee787', bg='#161b22')
        self.bias_label.pack(anchor=tk.W, padx=15, pady=8)
        
        # Control Panel
        control_panel = tk.LabelFrame(dashboard_frame, text=" 🎮 CONTROLS ", 
                                     font=('SF Pro Display', 14, 'bold'), 
                                     fg='#58a6ff', bg='#161b22', bd=2)
        control_panel.pack(side=tk.RIGHT, padx=15, pady=15, fill=tk.Y)
        
        self.analyze_btn = tk.Button(control_panel, text="🔄 START ANALYSIS", 
                                    command=self.start_analysis, 
                                    font=('SF Pro Display', 12, 'bold'),
                                    bg='#238636', fg='white', 
                                    activebackground='#2ea043',
                                    pady=10, padx=20, cursor='hand2')
        self.analyze_btn.pack(padx=15, pady=10, fill=tk.X)
        
        self.status_label = tk.Label(control_panel, text="⚡ Status: Ready", 
                                    font=('SF Mono', 11), 
                                    fg='#7ee787', bg='#161b22')
        self.status_label.pack(padx=15, pady=5)
        
        self.timestamp_label = tk.Label(control_panel, text="🕐 Last Update: Never", 
                                       font=('SF Mono', 10), 
                                       fg='#8b949e', bg='#161b22')
        self.timestamp_label.pack(padx=15, pady=5)
        
        # Main content area
        content_frame = tk.Frame(main_frame, bg='#0d1117')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Decision Tree
        left_frame = tk.LabelFrame(content_frame, text=" 🌳 DECISION TREE ANALYSIS ", 
                                  font=('SF Pro Display', 14, 'bold'), 
                                  fg='#58a6ff', bg='#161b22', bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        
        self.decision_text = scrolledtext.ScrolledText(left_frame, height=20, width=60,
                                                      bg='#0d1117', fg='#f0f6fc', 
                                                      font=('SF Mono', 11),
                                                      insertbackground='#58a6ff',
                                                      selectbackground='#264f78')
        self.decision_text.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)
        
        # Right side - Options & Recommendations
        right_frame = tk.Frame(content_frame, bg='#0d1117')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        
        # Options Table
        options_frame = tk.LabelFrame(right_frame, text=" 📈 OPTIONS DATA (8-16¢ Range) ", 
                                     font=('SF Pro Display', 12, 'bold'), 
                                     fg='#58a6ff', bg='#161b22', bd=2)
        options_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Configure treeview style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.Treeview', 
                       background='#161b22', 
                       foreground='#f0f6fc',
                       fieldbackground='#161b22',
                       borderwidth=0,
                       font=('SF Mono', 10))
        style.configure('Custom.Treeview.Heading', 
                       background='#21262d', 
                       foreground='#58a6ff',
                       font=('SF Pro Display', 11, 'bold'))
        
        self.options_tree = ttk.Treeview(options_frame, 
                                        columns=('type', 'strike', 'price', 'exp'), 
                                        show='headings', height=8,
                                        style='Custom.Treeview')
        
        self.options_tree.heading('#1', text='TYPE')
        self.options_tree.heading('#2', text='STRIKE')
        self.options_tree.heading('#3', text='PRICE')
        self.options_tree.heading('#4', text='EXPIRATION')
        
        self.options_tree.column('#1', width=80, anchor='center')
        self.options_tree.column('#2', width=100, anchor='center')
        self.options_tree.column('#3', width=80, anchor='center')
        self.options_tree.column('#4', width=120, anchor='center')
        
        self.options_tree.pack(padx=15, pady=10, fill=tk.BOTH)
        
        # Recommendations
        rec_frame = tk.LabelFrame(right_frame, text=" 🎯 TRADE RECOMMENDATIONS ", 
                                 font=('SF Pro Display', 12, 'bold'), 
                                 fg='#58a6ff', bg='#161b22', bd=2)
        rec_frame.pack(fill=tk.BOTH, expand=True)
        
        self.recommendations_text = scrolledtext.ScrolledText(rec_frame, height=12, width=50,
                                                             bg='#0d1117', fg='#f0f6fc', 
                                                             font=('SF Mono', 10),
                                                             insertbackground='#58a6ff',
                                                             selectbackground='#264f78')
        self.recommendations_text.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)
    
    def update_status(self, status):
        """Update status display."""
        self.status_label.config(text=f"⚡ Status: {status}")
        self.root.update()
        
    def update_timestamp(self):
        """Update timestamp display."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.timestamp_label.config(text=f"🕐 Last Update: {current_time}")
        
    def log_to_decision_tree(self, message):
        """Add message to decision tree display."""
        self.decision_text.insert(tk.END, f"{message}\n")
        self.decision_text.see(tk.END)
        self.root.update()
        
    def update_spy_data_display(self, spy_data):
        """Update SPY data display."""
        if not spy_data:
            return
        
        price = spy_data.get('current_price', 0)
        rsi_1m = spy_data.get('rsi_1m')
        rsi_5m = spy_data.get('rsi_5m')
        
        self.spy_price_label.config(text=f"💰 Price: ${price:.2f}")
        
        # Color-code RSI
        if rsi_1m:
            if rsi_1m > 70:
                color_1m, status_1m = '#f85149', 'OVERBOUGHT'
            elif rsi_1m < 30:
                color_1m, status_1m = '#7ee787', 'OVERSOLD'
            else:
                color_1m, status_1m = '#ffa657', 'NEUTRAL'
            
            self.rsi_1m_label.config(text=f"📊 RSI 1m: {rsi_1m:.1f} ({status_1m})", fg=color_1m)
        
        if rsi_5m:
            if rsi_5m > 70:
                color_5m, status_5m = '#f85149', 'OVERBOUGHT'
            elif rsi_5m < 30:
                color_5m, status_5m = '#7ee787', 'OVERSOLD'
            else:
                color_5m, status_5m = '#ffa657', 'NEUTRAL'
            
            self.rsi_5m_label.config(text=f"📊 RSI 5m: {rsi_5m:.1f} ({status_5m})", fg=color_5m)
    
    def update_bias_display(self, bias):
        """Update market bias display."""
        bias_colors = {
            'STRONG_BULLISH': '#7ee787',
            'MILD_BULLISH': '#a5f3fc',
            'NEUTRAL': '#ffa657',
            'MILD_BEARISH': '#fbb6ce',
            'STRONG_BEARISH': '#f85149',
            'UNKNOWN': '#8b949e'
        }
        
        color = bias_colors.get(bias, '#8b949e')
        self.bias_label.config(text=f"🎯 Bias: {bias}", fg=color)
    
    def update_options_table(self, options_data):
        """Update options table."""
        # Clear existing data
        for item in self.options_tree.get_children():
            self.options_tree.delete(item)
        
        # Add new data
        for option in options_data:
            option_type = option.get('type', 'unknown').upper()
            strike = option.get('strike', 'N/A')
            price = option.get('price_text', 'N/A')
            expiration = option.get('expiration', 'N/A')
            
            # Color-code by type
            tag = 'call' if option_type == 'CALL' else 'put' if option_type == 'PUT' else 'unknown'
            
            self.options_tree.insert('', tk.END, 
                                   values=(option_type, strike, price, expiration), 
                                   tags=(tag,))
        
        # Configure row colors
        self.options_tree.tag_configure('call', background='#1a2332', foreground='#7ee787')
        self.options_tree.tag_configure('put', background='#2d1b1f', foreground='#fbb6ce')
        self.options_tree.tag_configure('unknown', background='#21262d', foreground='#8b949e')
    
    def update_recommendations_display(self, recommendations):
        """Update recommendations display."""
        self.recommendations_text.delete('1.0', tk.END)
        
        if not recommendations:
            self.recommendations_text.insert(tk.END, "No recommendations available.\nRun analysis to generate recommendations.")
            return
        
        rec_text = "🎯 TOP TRADE RECOMMENDATIONS\n"
        rec_text += "=" * 45 + "\n\n"
        
        emoji_map = {
            'STRONG BUY': '🟢🟢',
            'BUY': '🟢',
            'CONSIDER': '🟡',
            'AVOID': '🔴'
        }
        
        for i, rec in enumerate(recommendations[:5], 1):
            option = rec['option']
            score = rec['score']
            recommendation = rec['recommendation']
            analysis = rec['analysis']
            
            emoji = emoji_map.get(recommendation, '⚪')
            
            rec_text += f"#{i} {emoji} {recommendation} (Score: {score})\n"
            rec_text += f"├─ Type: {option.get('type', 'unknown').upper()}\n"
            rec_text += f"├─ Price: {option.get('price_text', 'N/A')}\n"
            
            if 'strike' in option:
                rec_text += f"├─ Strike: {option['strike']}\n"
            if 'expiration' in option:
                rec_text += f"├─ Exp: {option['expiration']}\n"
            
            rec_text += "└─ Analysis:\n"
            for point in analysis:
                rec_text += f"   • {point}\n"
            rec_text += "\n"
        
        self.recommendations_text.insert(tk.END, rec_text)
    
    def start_analysis(self):
        """Start analysis in background thread."""
        self.analyze_btn.config(state='disabled', text='🔄 ANALYZING...')
        self.decision_text.delete('1.0', tk.END)
        
        # Start analysis thread
        thread = threading.Thread(target=self.run_analysis_thread)
        thread.daemon = True
        thread.start()
    
    def run_analysis_thread(self):
        """Run analysis in separate thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run analysis
            loop.run_until_complete(self.async_analysis())
            
        except Exception as e:
            self.root.after(0, lambda: self.log_to_decision_tree(f"❌ Analysis error: {e}"))
        finally:
            self.root.after(0, lambda: self.analyze_btn.config(state='normal', text='🔄 START ANALYSIS'))
    
    async def async_analysis(self):
        """Run the complete analysis."""
        analyzer = SPYOptionsAnalyzer()
        
        try:
            # Step 1: Connect to browser
            self.root.after(0, lambda: self.update_status("Connecting to Chrome..."))
            self.root.after(0, lambda: self.log_to_decision_tree("🔗 STEP 1: Connecting to Chrome browser..."))
            
            if not await analyzer.connect_to_chrome():
                self.root.after(0, lambda: self.log_to_decision_tree("❌ Failed to connect to Chrome browser"))
                self.root.after(0, lambda: self.log_to_decision_tree("💡 Make sure Chrome is running with debugging enabled"))
                return
            
            self.root.after(0, lambda: self.log_to_decision_tree("✅ Connected to Chrome successfully"))
            
            # Step 2: Navigate to options
            self.root.after(0, lambda: self.update_status("Navigating to SPY options..."))
            self.root.after(0, lambda: self.log_to_decision_tree("\n📊 STEP 2: Navigating to SPY options page..."))
            
            if not await analyzer.navigate_to_spy_options():
                self.root.after(0, lambda: self.log_to_decision_tree("❌ Failed to navigate to options page"))
                self.root.after(0, lambda: self.log_to_decision_tree("🔐 Please ensure you're logged into Robinhood"))
                return
            
            self.root.after(0, lambda: self.log_to_decision_tree("✅ SPY options page loaded successfully"))
            
            # Step 3: Get RSI data
            self.root.after(0, lambda: self.update_status("Fetching SPY RSI data..."))
            self.root.after(0, lambda: self.log_to_decision_tree("\n📈 STEP 3: Fetching SPY market data..."))
            
            spy_data = analyzer.get_spy_rsi_data()
            if not spy_data:
                self.root.after(0, lambda: self.log_to_decision_tree("❌ Failed to fetch SPY data"))
                return
            
            price = spy_data.get('current_price', 0)
            rsi_1m = spy_data.get('rsi_1m')
            rsi_5m = spy_data.get('rsi_5m')
            
            self.root.after(0, lambda: self.log_to_decision_tree(f"✅ SPY Price: ${price:.2f}"))
            if rsi_1m: self.root.after(0, lambda: self.log_to_decision_tree(f"✅ RSI 1m: {rsi_1m:.1f}"))
            if rsi_5m: self.root.after(0, lambda: self.log_to_decision_tree(f"✅ RSI 5m: {rsi_5m:.1f}"))
            
            # Update GUI with SPY data
            self.root.after(0, lambda: self.update_spy_data_display(spy_data))
            
            # Step 4: Scan options
            self.root.after(0, lambda: self.update_status("Scanning options contracts..."))
            self.root.after(0, lambda: self.log_to_decision_tree("\n🔍 STEP 4: Scanning options in 8-16¢ range..."))
            
            options = await analyzer.scan_robinhood_options()
            
            self.root.after(0, lambda: self.log_to_decision_tree(f"✅ Found {len(options)} options in price range"))
            
            # Update options table
            self.root.after(0, lambda: self.update_options_table(options))
            
            # Step 5: Generate recommendations
            if options:
                self.root.after(0, lambda: self.update_status("Generating recommendations..."))
                self.root.after(0, lambda: self.log_to_decision_tree("\n🎯 STEP 5: Analyzing trade opportunities..."))
                
                recommendations = analyzer.analyze_and_recommend()
                
                if recommendations:
                    bias = recommendations[0].get('bias', 'UNKNOWN')
                    self.root.after(0, lambda: self.update_bias_display(bias))
                    self.root.after(0, lambda: self.log_to_decision_tree(f"📊 Market Bias: {bias}"))
                    
                    # Show decision tree logic
                    if rsi_1m and rsi_5m:
                        self.root.after(0, lambda: self.log_to_decision_tree("\n🌳 DECISION TREE LOGIC:"))
                        
                        if rsi_1m < 30 and rsi_5m < 30:
                            self.root.after(0, lambda: self.log_to_decision_tree("├─ Both RSI oversold → CALLS preferred"))
                        elif rsi_1m > 70 and rsi_5m > 70:
                            self.root.after(0, lambda: self.log_to_decision_tree("├─ Both RSI overbought → PUTS preferred"))
                        elif rsi_1m < 30:
                            self.root.after(0, lambda: self.log_to_decision_tree("├─ 1m RSI oversold → CALLS preferred"))
                        elif rsi_1m > 70:
                            self.root.after(0, lambda: self.log_to_decision_tree("├─ 1m RSI overbought → PUTS preferred"))
                        else:
                            self.root.after(0, lambda: self.log_to_decision_tree("├─ RSI neutral → No directional bias"))
                        
                        self.root.after(0, lambda: self.log_to_decision_tree("├─ 8-10¢ options: High score (cheap premium)"))
                        self.root.after(0, lambda: self.log_to_decision_tree("├─ 11-13¢ options: Medium score"))
                        self.root.after(0, lambda: self.log_to_decision_tree("└─ 14-16¢ options: Lower score (expensive premium)"))
                    
                    # Update recommendations display
                    self.root.after(0, lambda: self.update_recommendations_display(recommendations))
                    
                    # Show top recommendation
                    top_rec = recommendations[0]
                    top_option = top_rec['option']
                    self.root.after(0, lambda: self.log_to_decision_tree(f"\n🏆 TOP RECOMMENDATION: {top_rec['recommendation']}"))
                    self.root.after(0, lambda: self.log_to_decision_tree(f"   {top_option.get('price_text', 'N/A')} {top_option.get('type', 'unknown').upper()} (Score: {top_rec['score']})"))
            
            else:
                self.root.after(0, lambda: self.log_to_decision_tree("❌ No options found in the 8-16¢ price range"))
                self.root.after(0, lambda: self.log_to_decision_tree("💡 This is normal if no options are currently priced in this range"))
            
            # Update timestamp and status
            self.root.after(0, lambda: self.update_timestamp())
            self.root.after(0, lambda: self.update_status("Analysis complete!"))
            self.root.after(0, lambda: self.log_to_decision_tree("\n✅ ANALYSIS COMPLETE!"))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_to_decision_tree(f"❌ Error during analysis: {e}"))
        finally:
            if analyzer.playwright:
                await analyzer.playwright.stop()
    
    def show(self):
        """Show the GUI."""
        self.root.mainloop()

def main():
    """Main function."""
    print("🚀 Starting SPY Options Analyzer GUI...")
    
    app = SPYAnalyzerGUI()
    app.show()

if __name__ == "__main__":
    main()