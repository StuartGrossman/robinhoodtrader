#!/usr/bin/env python3
"""
Working SPY Options Analyzer - Based on debug findings
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
            print("🔗 Connecting to Chrome...")
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
        """Navigate to SPY options and wait for full load."""
        try:
            print("📊 Navigating to SPY options...")
            await self.page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
            
            # Wait for the page to load completely
            await asyncio.sleep(5)
            
            current_url = self.page.url
            if "login" in current_url:
                print("🔐 Please log into Robinhood first")
                return False
            
            print("✅ SPY options page loaded")
            
            # Wait for options chain to load (look for Call/Put tabs)
            try:
                await self.page.wait_for_selector('button:has-text("Call")', timeout=10000)
                print("✅ Options interface loaded")
            except:
                print("⚠️ Options interface may still be loading...")
            
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
            
            # Handle multi-level columns from yfinance
            if isinstance(spy_1m.columns, pd.MultiIndex):
                close_1m = spy_1m['Close'].iloc[:, 0].values.astype(float)  # Get first column
                current_price = spy_1m['Close'].iloc[-1, 0]
            else:
                close_1m = spy_1m['Close'].values.astype(float)
                current_price = spy_1m['Close'].iloc[-1]
            
            if isinstance(spy_5m.columns, pd.MultiIndex):
                close_5m = spy_5m['Close'].iloc[:, 0].values.astype(float)  # Get first column
            else:
                close_5m = spy_5m['Close'].values.astype(float)
            
            # Ensure we have enough data for RSI calculation
            if len(close_1m) < 15:
                print("⚠️ Not enough 1m data for RSI calculation")
                rsi_1m = np.array([np.nan])
            else:
                rsi_1m = talib.RSI(close_1m, timeperiod=14)
            
            if len(close_5m) < 15:
                print("⚠️ Not enough 5m data for RSI calculation")
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
            
            print(f"📊 SPY: ${current_price:.2f}")
            if current_rsi_1m: print(f"📊 RSI 1m: {current_rsi_1m:.1f}")
            if current_rsi_5m: print(f"📊 RSI 5m: {current_rsi_5m:.1f}")
            
            return self.spy_data
            
        except Exception as e:
            print(f"❌ Error fetching SPY data: {e}")
            return None

    async def scan_robinhood_options(self):
        """Scan Robinhood options using proper interface interaction."""
        try:
            print("🔍 Scanning Robinhood options interface...")
            all_options = []
            
            # First, ensure we're on the options page
            await asyncio.sleep(3)
            
            # Take initial screenshot
            await self.page.screenshot(path="logs/screenshots/options_initial.png")
            
            # Try both Call and Put tabs
            option_types = ['Call', 'Put']
            
            for option_type in option_types:
                print(f"\n📈 Scanning {option_type} options...")
                
                try:
                    # Click on the Call/Put tab
                    tab_button = self.page.locator(f'button:has-text("{option_type}")')
                    if await tab_button.count() > 0:
                        print(f"🖱️ Clicking {option_type} tab...")
                        await tab_button.click()
                        await asyncio.sleep(3)
                        
                        # Take screenshot after clicking tab
                        await self.page.screenshot(path=f"logs/screenshots/{option_type.lower()}_tab.png")
                        
                        # Look for options in this tab
                        options_found = await self.extract_options_from_current_view(option_type.lower())
                        all_options.extend(options_found)
                        
                    else:
                        print(f"⚠️ Could not find {option_type} tab")
                        
                except Exception as tab_error:
                    print(f"❌ Error with {option_type} tab: {tab_error}")
                    continue
            
            # Also try scrolling to find more options
            print("\n📜 Scrolling to find more options...")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Look for any additional options after scrolling
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
            print(f"\n📋 Total unique options found: {len(unique_options)}")
            
            return unique_options
            
        except Exception as e:
            print(f"❌ Error scanning options: {e}")
            return []

    async def extract_options_from_current_view(self, option_type):
        """Extract options data from current page view."""
        try:
            found_options = []
            
            # Get all text content from the page
            page_content = await self.page.content()
            
            # Look for price patterns in various formats
            price_patterns = [
                r'\$0\.(\d{2})',  # $0.XX format
                r'0\.(\d{2})',   # 0.XX format
                r'\.(\d{2})¢',   # .XXc format
                r'(\d{1,2})¢',   # XXc format
                r'(\d{1,2})\s*cents',  # XX cents format
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
            
            # Remove duplicates and sort
            unique_prices = sorted(list(set(all_prices)))
            print(f"  💰 Found prices in range: {unique_prices}")
            
            # Try to find more detailed information using selectors
            option_selectors = [
                '[data-testid*="option"]',
                '[data-rh-test-id*="option"]',
                'tr[role="row"]',
                'div[role="button"]',
                'button',
                'td',
                'span'
            ]
            
            for price_cents in unique_prices:
                # Look for elements containing this price
                price_text = f"$0.{price_cents:02d}"
                
                for selector in option_selectors:
                    try:
                        elements = self.page.locator(f'{selector}:has-text("{price_text}")')
                        count = await elements.count()
                        
                        if count > 0:
                            print(f"  🎯 Found {count} elements with {price_text}")
                            
                            # Try to extract details from the first few elements
                            for i in range(min(count, 3)):
                                try:
                                    element = elements.nth(i)
                                    element_text = await element.text_content()
                                    
                                    option_data = {
                                        'price_cents': price_cents,
                                        'price_text': price_text,
                                        'type': option_type if option_type != 'unknown' else self.guess_option_type(element_text),
                                        'element_text': element_text.strip() if element_text else '',
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    
                                    # Try to extract strike and expiration
                                    strike_match = re.search(r'\$(\d{3,4})', element_text or '')
                                    if strike_match:
                                        option_data['strike'] = f"${strike_match.group(1)}"
                                    
                                    exp_match = re.search(r'(\d{1,2}/\d{1,2})', element_text or '')
                                    if exp_match:
                                        option_data['expiration'] = exp_match.group(1)
                                    
                                    found_options.append(option_data)
                                    break  # Found one with this price, move to next
                                    
                                except Exception as element_error:
                                    continue
                            
                            break  # Found elements with this selector, move to next price
                            
                    except Exception as selector_error:
                        continue
                
                # If we couldn't find detailed info, still add basic price info
                if not any(opt['price_cents'] == price_cents for opt in found_options):
                    found_options.append({
                        'price_cents': price_cents,
                        'price_text': price_text,
                        'type': option_type,
                        'element_text': f'Found {price_text} on page',
                        'timestamp': datetime.now().isoformat()
                    })
            
            print(f"  📊 Extracted {len(found_options)} options for {option_type}")
            return found_options
            
        except Exception as e:
            print(f"❌ Error extracting options: {e}")
            return []

    def guess_option_type(self, text):
        """Guess if option is call or put from text."""
        if not text:
            return 'unknown'
        
        text_lower = text.lower()
        if 'call' in text_lower:
            return 'call'
        elif 'put' in text_lower:
            return 'put'
        else:
            return 'unknown'

    def analyze_and_recommend(self):
        """Analyze options and provide recommendations."""
        if not self.options_data or not self.spy_data:
            print("❌ Missing data for analysis")
            return []
        
        print("\n🎯 ANALYZING TRADE OPPORTUNITIES")
        print("=" * 50)
        
        rsi_1m = self.spy_data.get('rsi_1m')
        rsi_5m = self.spy_data.get('rsi_5m')
        
        # Determine market bias
        if rsi_1m and rsi_5m:
            if rsi_1m < 30 and rsi_5m < 30:
                bias = "STRONG_BULLISH"
                preferred_type = "call"
                print(f"📈 Market Bias: {bias} (Both RSI oversold)")
            elif rsi_1m > 70 and rsi_5m > 70:
                bias = "STRONG_BEARISH"
                preferred_type = "put"
                print(f"📉 Market Bias: {bias} (Both RSI overbought)")
            elif rsi_1m < 30:
                bias = "MILD_BULLISH"
                preferred_type = "call"
                print(f"📈 Market Bias: {bias} (1m RSI oversold)")
            elif rsi_1m > 70:
                bias = "MILD_BEARISH"
                preferred_type = "put"
                print(f"📉 Market Bias: {bias} (1m RSI overbought)")
            else:
                bias = "NEUTRAL"
                preferred_type = None
                print(f"⚖️ Market Bias: {bias} (RSI in normal range)")
        else:
            bias = "UNKNOWN"
            preferred_type = None
            print(f"❓ Market Bias: {bias} (Insufficient RSI data)")
        
        # Analyze each option
        recommendations = []
        
        for option in self.options_data:
            price_cents = option.get('price_cents', 0)
            option_type = option.get('type', 'unknown')
            
            score = 0
            analysis = []
            
            # Price scoring (cheaper = better for short-term plays)
            if price_cents <= 10:
                score += 3
                analysis.append("Very cheap premium")
            elif price_cents <= 13:
                score += 2
                analysis.append("Reasonable premium")
            else:
                score += 1
                analysis.append("Higher premium")
            
            # Bias alignment scoring
            if preferred_type and option_type == preferred_type:
                score += 5
                analysis.append(f"Aligns with {bias} bias")
            elif preferred_type and option_type != preferred_type:
                score -= 2
                analysis.append(f"Contrarian to {bias} bias")
            elif option_type == 'unknown':
                analysis.append("Option type unclear")
            
            # Determine recommendation
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
                'recommendation': recommendation
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations

    def print_recommendations(self, recommendations):
        """Print detailed recommendations."""
        if not recommendations:
            print("❌ No recommendations available")
            return
        
        print(f"\n🎯 TOP {min(5, len(recommendations))} RECOMMENDATIONS")
        print("=" * 60)
        
        for i, rec in enumerate(recommendations[:5], 1):
            option = rec['option']
            score = rec['score']
            recommendation = rec['recommendation']
            analysis = rec['analysis']
            
            # Emoji based on recommendation
            if recommendation == 'STRONG BUY':
                emoji = '🟢🟢'
            elif recommendation == 'BUY':
                emoji = '🟢'
            elif recommendation == 'CONSIDER':
                emoji = '🟡'
            else:
                emoji = '🔴'
            
            print(f"\n#{i} {emoji} {recommendation} (Score: {score})")
            print(f"   💰 Price: {option.get('price_text', 'N/A')}")
            print(f"   📊 Type: {option.get('type', 'unknown').upper()}")
            
            if 'strike' in option:
                print(f"   🎯 Strike: {option['strike']}")
            if 'expiration' in option:
                print(f"   📅 Expiration: {option['expiration']}")
            
            print(f"   📝 Analysis:")
            for point in analysis:
                print(f"      • {point}")

async def main():
    """Main function."""
    print("🚀 SPY Options Analyzer - Enhanced Version")
    print("=" * 60)
    
    analyzer = SPYOptionsAnalyzer()
    
    try:
        # Connect to browser
        if not await analyzer.connect_to_chrome():
            print("❌ Failed to connect to Chrome")
            return
        
        # Navigate to options
        if not await analyzer.navigate_to_spy_options():
            print("❌ Failed to navigate to options")
            return
        
        # Get SPY RSI data
        spy_data = analyzer.get_spy_rsi_data()
        if not spy_data:
            print("❌ Failed to get SPY data")
            return
        
        # Scan options
        options = await analyzer.scan_robinhood_options()
        if not options:
            print("❌ No options found in price range")
            print("💡 This might be normal if no options are currently priced 8-16¢")
            return
        
        # Analyze and recommend
        recommendations = analyzer.analyze_and_recommend()
        analyzer.print_recommendations(recommendations)
        
        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {
            'timestamp': datetime.now().isoformat(),
            'spy_data': spy_data,
            'options_data': options,
            'recommendations': recommendations
        }
        
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        filename = f"spy_analysis_{timestamp}.json"
        with open(data_dir / filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n💾 Data saved to: data/{filename}")
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if analyzer.playwright:
            await analyzer.playwright.stop()
    
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    asyncio.run(main())