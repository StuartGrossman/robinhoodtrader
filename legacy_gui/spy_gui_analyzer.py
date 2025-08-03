#!/usr/bin/env python3
"""
SPY Options Analyzer with GUI Dashboard
Real-time data display and decision tree visualization
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

class SPYAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SPY Options Analyzer Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        # Data storage
        self.spy_data = None
        self.options_data = []
        self.recommendations = []
        self.analyzer = None
        
        # GUI setup
        self.setup_gui()
        
        # Start initial analysis
        self.refresh_analysis()
    
    def setup_gui(self):
        """Setup the GUI layout."""
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="🚀 SPY Options Analyzer Dashboard", 
                              font=('Arial', 20, 'bold'), fg='#00ff88', bg='#1e1e1e')
        title_label.pack(pady=(0, 20))
        
        # Top section - SPY Data and Controls
        top_frame = tk.Frame(main_frame, bg='#2d2d2d', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # SPY Data Frame
        spy_frame = tk.LabelFrame(top_frame, text=" 📊 SPY Market Data ", 
                                 font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        spy_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.spy_price_label = tk.Label(spy_frame, text="Price: Loading...", 
                                       font=('Arial', 14), fg='#ffffff', bg='#2d2d2d')
        self.spy_price_label.pack(anchor=tk.W, padx=10, pady=5)
        
        self.rsi_1m_label = tk.Label(spy_frame, text="RSI 1m: Loading...", 
                                    font=('Arial', 12), fg='#ffaa00', bg='#2d2d2d')
        self.rsi_1m_label.pack(anchor=tk.W, padx=10, pady=2)
        
        self.rsi_5m_label = tk.Label(spy_frame, text="RSI 5m: Loading...", 
                                    font=('Arial', 12), fg='#ffaa00', bg='#2d2d2d')
        self.rsi_5m_label.pack(anchor=tk.W, padx=10, pady=2)
        
        self.market_bias_label = tk.Label(spy_frame, text="Bias: Analyzing...", 
                                         font=('Arial', 12, 'bold'), fg='#00ddff', bg='#2d2d2d')
        self.market_bias_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Controls Frame
        controls_frame = tk.LabelFrame(top_frame, text=" 🔧 Controls ", 
                                      font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        controls_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.Y)
        
        self.refresh_btn = tk.Button(controls_frame, text="🔄 Refresh Analysis", 
                                    command=self.refresh_analysis, font=('Arial', 11, 'bold'),
                                    bg='#0066cc', fg='white', pady=5)
        self.refresh_btn.pack(padx=10, pady=5, fill=tk.X)
        
        self.status_label = tk.Label(controls_frame, text="Status: Ready", 
                                    font=('Arial', 10), fg='#00ff88', bg='#2d2d2d')
        self.status_label.pack(padx=10, pady=5)
        
        # Middle section - Decision Tree
        decision_frame = tk.LabelFrame(main_frame, text=" 🌳 Decision Tree Logic ", 
                                      font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        decision_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.decision_text = scrolledtext.ScrolledText(decision_frame, height=8, width=80,
                                                      bg='#1a1a1a', fg='#ffffff', 
                                                      font=('Courier', 10))
        self.decision_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Bottom section - Options Data and Recommendations
        bottom_frame = tk.Frame(main_frame, bg='#1e1e1e')
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        # Options Data Frame
        options_frame = tk.LabelFrame(bottom_frame, text=" 📈 Options Data (8-16¢ Range) ", 
                                     font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        options_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Options Treeview
        self.options_tree = ttk.Treeview(options_frame, columns=('type', 'strike', 'price', 'exp'), 
                                        show='headings', height=10)
        self.options_tree.heading('#1', text='Type')
        self.options_tree.heading('#2', text='Strike')
        self.options_tree.heading('#3', text='Price')
        self.options_tree.heading('#4', text='Expiration')
        
        self.options_tree.column('#1', width=60)
        self.options_tree.column('#2', width=80)
        self.options_tree.column('#3', width=70)
        self.options_tree.column('#4', width=100)
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background='#2d2d2d', foreground='white', 
                       fieldbackground='#2d2d2d', borderwidth=0)
        style.configure('Treeview.Heading', background='#404040', foreground='white')
        
        self.options_tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Recommendations Frame
        rec_frame = tk.LabelFrame(bottom_frame, text=" 🎯 Trade Recommendations ", 
                                 font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2d2d2d')
        rec_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.recommendations_text = scrolledtext.ScrolledText(rec_frame, height=15, width=50,
                                                             bg='#1a1a1a', fg='#ffffff', 
                                                             font=('Courier', 9))
        self.recommendations_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    def update_spy_data(self, spy_data):
        """Update SPY data display."""
        if not spy_data:
            return
        
        price = spy_data.get('current_price', 0)
        rsi_1m = spy_data.get('rsi_1m')
        rsi_5m = spy_data.get('rsi_5m')
        
        self.spy_price_label.config(text=f"💰 Price: ${price:.2f}")
        
        # Color-code RSI
        if rsi_1m:
            color_1m = '#ff4444' if rsi_1m > 70 else '#44ff44' if rsi_1m < 30 else '#ffaa00'
            self.rsi_1m_label.config(text=f"📊 RSI 1m: {rsi_1m:.1f}", fg=color_1m)
        
        if rsi_5m:
            color_5m = '#ff4444' if rsi_5m > 70 else '#44ff44' if rsi_5m < 30 else '#ffaa00'
            self.rsi_5m_label.config(text=f"📊 RSI 5m: {rsi_5m:.1f}", fg=color_5m)
        
        # Determine bias
        bias, bias_color = self.determine_market_bias(rsi_1m, rsi_5m)
        self.market_bias_label.config(text=f"🎯 Bias: {bias}", fg=bias_color)
    
    def determine_market_bias(self, rsi_1m, rsi_5m):
        """Determine market bias and return color."""
        if rsi_1m and rsi_5m:
            if rsi_1m < 30 and rsi_5m < 30:
                return "STRONG BULLISH", '#00ff00'
            elif rsi_1m > 70 and rsi_5m > 70:
                return "STRONG BEARISH", '#ff0000'
            elif rsi_1m < 30:
                return "MILD BULLISH", '#88ff88'
            elif rsi_1m > 70:
                return "MILD BEARISH", '#ff8888'
            else:
                return "NEUTRAL", '#ffaa00'
        return "UNKNOWN", '#666666'
    
    def update_decision_tree(self, spy_data, recommendations):
        """Update decision tree display."""
        self.decision_text.delete('1.0', tk.END)
        
        tree_text = "🌳 DECISION TREE ANALYSIS\n"
        tree_text += "=" * 60 + "\n\n"
        
        if spy_data:
            rsi_1m = spy_data.get('rsi_1m')
            rsi_5m = spy_data.get('rsi_5m')
            price = spy_data.get('current_price')
            
            tree_text += f"📊 Current SPY Price: ${price:.2f}\n\n"
            
            tree_text += "🔍 RSI Analysis:\n"
            if rsi_1m:
                tree_text += f"   ├─ 1m RSI: {rsi_1m:.1f} "
                if rsi_1m < 30:
                    tree_text += "→ OVERSOLD (Bullish Signal) ✅\n"
                elif rsi_1m > 70:
                    tree_text += "→ OVERBOUGHT (Bearish Signal) ⚠️\n"
                else:
                    tree_text += "→ NEUTRAL ZONE\n"
            
            if rsi_5m:
                tree_text += f"   └─ 5m RSI: {rsi_5m:.1f} "
                if rsi_5m < 30:
                    tree_text += "→ OVERSOLD (Bullish Signal) ✅\n"
                elif rsi_5m > 70:
                    tree_text += "→ OVERBOUGHT (Bearish Signal) ⚠️\n"
                else:
                    tree_text += "→ NEUTRAL ZONE\n"
            
            tree_text += "\n🎯 Trading Logic:\n"
            
            if rsi_1m and rsi_5m:
                if rsi_1m < 30 and rsi_5m < 30:
                    tree_text += "   ├─ Both timeframes oversold\n"
                    tree_text += "   ├─ Strategy: CALLS preferred\n"
                    tree_text += "   └─ Confidence: HIGH\n"
                elif rsi_1m > 70 and rsi_5m > 70:
                    tree_text += "   ├─ Both timeframes overbought\n"
                    tree_text += "   ├─ Strategy: PUTS preferred\n"
                    tree_text += "   └─ Confidence: HIGH\n"
                elif rsi_1m < 30:
                    tree_text += "   ├─ 1m oversold, 5m neutral\n"
                    tree_text += "   ├─ Strategy: CALLS preferred\n"
                    tree_text += "   └─ Confidence: MEDIUM\n"
                elif rsi_1m > 70:
                    tree_text += "   ├─ 1m overbought, 5m neutral\n"
                    tree_text += "   ├─ Strategy: PUTS preferred\n"
                    tree_text += "   └─ Confidence: MEDIUM\n"
                else:
                    tree_text += "   ├─ No clear directional bias\n"
                    tree_text += "   ├─ Strategy: Wait for better setup\n"
                    tree_text += "   └─ Confidence: LOW\n"
            
            tree_text += "\n💰 Price Range Filter: 8-16 cents\n"
            tree_text += "   ├─ 8-10¢: High attractiveness (cheap premium)\n"
            tree_text += "   ├─ 11-13¢: Medium attractiveness\n"
            tree_text += "   └─ 14-16¢: Lower attractiveness (higher premium)\n"
            
            if recommendations:
                tree_text += f"\n📋 Found {len(recommendations)} options in range\n"
                top_rec = recommendations[0] if recommendations else None
                if top_rec:
                    rec_text = top_rec['recommendation']
                    score = top_rec['score']
                    tree_text += f"   └─ Top recommendation: {rec_text} (Score: {score})\n"
        
        self.decision_text.insert(tk.END, tree_text)
    
    def update_options_data(self, options_data):
        """Update options data display."""
        # Clear existing data
        for item in self.options_tree.get_children():
            self.options_tree.delete(item)
        
        # Add new data
        for option in options_data:
            option_type = option.get('type', 'unknown').upper()
            strike = option.get('strike', 'N/A')
            price_cents = option.get('price_cents', 0)
            price = f"$0.{price_cents:02d}"
            expiration = option.get('expiration', 'N/A')
            
            # Color-code by type
            tag = 'call' if option_type == 'CALL' else 'put'
            
            self.options_tree.insert('', tk.END, values=(option_type, strike, price, expiration), 
                                   tags=(tag,))
        
        # Configure tags for colors
        self.options_tree.tag_configure('call', background='#004400', foreground='#88ff88')
        self.options_tree.tag_configure('put', background='#440000', foreground='#ff8888')
    
    def update_recommendations(self, recommendations):
        """Update recommendations display."""
        self.recommendations_text.delete('1.0', tk.END)
        
        if not recommendations:
            self.recommendations_text.insert(tk.END, "No recommendations available.")
            return
        
        rec_text = "🎯 TOP TRADE RECOMMENDATIONS\n"
        rec_text += "=" * 45 + "\n\n"
        
        for i, rec in enumerate(recommendations[:5], 1):
            option = rec['option']
            score = rec['score']
            recommendation = rec['recommendation']
            analysis = rec['analysis']
            
            # Color indicators
            if recommendation == 'BUY':
                indicator = "🟢 BUY"
            elif recommendation == 'CONSIDER':
                indicator = "🟡 CONSIDER"
            else:
                indicator = "🔴 AVOID"
            
            rec_text += f"#{i} {indicator} (Score: {score})\n"
            rec_text += f"├─ Type: {option.get('type', 'unknown').upper()}\n"
            rec_text += f"├─ Price: $0.{option.get('price_cents', 0):02d}\n"
            
            if 'strike' in option:
                rec_text += f"├─ Strike: {option['strike']}\n"
            if 'expiration' in option:
                rec_text += f"├─ Exp: {option['expiration']}\n"
            
            rec_text += "└─ Analysis:\n"
            for point in analysis:
                rec_text += f"   • {point}\n"
            rec_text += "\n"
        
        self.recommendations_text.insert(tk.END, rec_text)
    
    def update_status(self, status):
        """Update status label."""
        self.status_label.config(text=f"Status: {status}")
        self.root.update()
    
    def refresh_analysis(self):
        """Refresh the analysis in a separate thread."""
        self.refresh_btn.config(state='disabled', text='🔄 Analyzing...')
        self.update_status("Starting analysis...")
        
        # Run analysis in thread to prevent GUI blocking
        thread = threading.Thread(target=self._run_analysis_thread)
        thread.daemon = True
        thread.start()
    
    def _run_analysis_thread(self):
        """Run analysis in separate thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the analysis
            from spy_options_analyzer import SPYOptionsAnalyzer
            analyzer = SPYOptionsAnalyzer()
            
            # Schedule updates
            self.root.after(0, lambda: self.update_status("Connecting to browser..."))
            
            # Run async analysis
            loop.run_until_complete(self._async_analysis(analyzer))
            
        except Exception as e:
            print(f"Analysis error: {e}")
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state='normal', text='🔄 Refresh Analysis'))
    
    async def _async_analysis(self, analyzer):
        """Async analysis function."""
        try:
            # Connect to browser
            self.root.after(0, lambda: self.update_status("Connecting to Chrome..."))
            if not await analyzer.connect_to_chrome():
                self.root.after(0, lambda: self.update_status("Failed to connect to Chrome"))
                return
            
            # Navigate to options
            self.root.after(0, lambda: self.update_status("Navigating to options..."))
            if not await analyzer.navigate_to_spy_options():
                self.root.after(0, lambda: self.update_status("Failed to navigate to options"))
                return
            
            # Get RSI data
            self.root.after(0, lambda: self.update_status("Fetching SPY RSI data..."))
            spy_data = analyzer.get_spy_rsi_data()
            if spy_data:
                self.root.after(0, lambda: self.update_spy_data(spy_data))
            
            # Scan options
            self.root.after(0, lambda: self.update_status("Scanning options..."))
            options = await analyzer.scan_options_in_price_range()
            if options:
                self.root.after(0, lambda: self.update_options_data(options))
            
            # Generate recommendations
            self.root.after(0, lambda: self.update_status("Generating recommendations..."))
            recommendations = analyzer.analyze_trade_opportunities()
            
            # Update GUI
            self.root.after(0, lambda: self.update_recommendations(recommendations))
            self.root.after(0, lambda: self.update_decision_tree(spy_data, recommendations))
            
            # Save data
            analyzer.save_analysis_data(recommendations)
            
            self.root.after(0, lambda: self.update_status("Analysis complete!"))
            
        except Exception as e:
            print(f"Async analysis error: {e}")
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}"))
        finally:
            if analyzer.playwright:
                await analyzer.playwright.stop()

def main():
    """Main function."""
    root = tk.Tk()
    app = SPYAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()