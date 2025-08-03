#!/usr/bin/env python3
"""
SPY Options Analyzer - Enhanced with RSI analysis and trade recommendations
"""
import asyncio
import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright
import talib

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
            return True
            
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False

    def get_spy_rsi_data(self):
        """Fetch SPY data and calculate RSI for 1m and 5m timeframes."""
        try:
            print("📈 Fetching SPY RSI data...")
            
            # Get 1-minute data for last 5 days
            spy_1m = yf.download("SPY", period="5d", interval="1m", progress=False)
            # Get 5-minute data for last 5 days  
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

    async def scan_options_in_price_range(self):
        """Scan for options in the 8-16 cent price range."""
        try:
            print("🔍 Scanning options in 8-16 cent range...")
            
            # Wait for options chain to load
            await asyncio.sleep(2)
            
            # Look for option rows/cells
            option_selectors = [
                '[data-testid*="option"]',
                '.option-chain-row',
                'tr:has-text("$0.")',
                'div:has-text("$0.0")',
                'span:has-text("$0.")'
            ]
            
            found_options = []
            
            for selector in option_selectors:
                elements = self.page.locator(selector)
                count = await elements.count()
                
                if count > 0:
                    print(f"Found {count} elements with selector: {selector}")
                    
                    for i in range(min(count, 50)):  # Limit to first 50 elements
                        try:
                            element = elements.nth(i)
                            text = await element.text_content()
                            
                            if text and '$0.' in text:
                                # Extract price using regex
                                import re
                                price_matches = re.findall(r'\$0\.(\d{2})', text)
                                
                                for price_match in price_matches:
                                    price_cents = int(price_match)
                                    if 8 <= price_cents <= 16:
                                        print(f"🎯 Found option in range: $0.{price_match}")
                                        
                                        # Try to click and get more details
                                        try:
                                            await element.click()
                                            await asyncio.sleep(1)
                                            
                                            # Extract option details
                                            option_data = await self.extract_option_details()
                                            if option_data:
                                                option_data['price_cents'] = price_cents
                                                found_options.append(option_data)
                                                
                                        except Exception as click_error:
                                            print(f"  ⚠️ Could not click option: {click_error}")
                                            
                        except Exception as e:
                            continue
                    
                    if found_options:
                        break  # Found options, don't try other selectors
            
            self.options_data = found_options
            print(f"📋 Found {len(found_options)} options in price range")
            return found_options
            
        except Exception as e:
            print(f"❌ Error scanning options: {e}")
            return []

    async def extract_option_details(self):
        """Extract detailed information from a clicked option."""
        try:
            await asyncio.sleep(1)  # Wait for details to load
            
            # Look for option details
            details = {}
            
            # Try to extract strike price
            strike_selectors = [
                '[data-testid*="strike"]',
                '.strike-price',
                'text=/\\$\\d+/'
            ]
            
            for selector in strike_selectors:
                elements = self.page.locator(selector)
                if await elements.count() > 0:
                    try:
                        text = await elements.first.text_content()
                        if text and '$' in text:
                            details['strike'] = text.strip()
                            break
                    except:
                        continue
            
            # Try to extract expiration
            exp_selectors = [
                '[data-testid*="expiration"]',
                '.expiration',
                'text=/\\d{1,2}\\/\\d{1,2}/'
            ]
            
            for selector in exp_selectors:
                elements = self.page.locator(selector)
                if await elements.count() > 0:
                    try:
                        text = await elements.first.text_content()
                        if text and '/' in text:
                            details['expiration'] = text.strip()
                            break
                    except:
                        continue
            
            # Try to extract option type (call/put)
            if 'call' in self.page.url.lower() or 'Call' in await self.page.text_content():
                details['type'] = 'call'
            elif 'put' in self.page.url.lower() or 'Put' in await self.page.text_content():
                details['type'] = 'put'
            
            # Try to extract Greeks
            greek_selectors = [
                '[data-testid*="delta"]',
                '[data-testid*="gamma"]',
                '[data-testid*="theta"]',
                'text=/Delta|Gamma|Theta/'
            ]
            
            for selector in greek_selectors:
                elements = self.page.locator(selector)
                if await elements.count() > 0:
                    try:
                        text = await elements.first.text_content()
                        if 'Delta' in text:
                            details['delta'] = text.strip()
                        elif 'Gamma' in text:
                            details['gamma'] = text.strip()
                        elif 'Theta' in text:
                            details['theta'] = text.strip()
                    except:
                        continue
            
            details['timestamp'] = datetime.now().isoformat()
            return details if details else None
            
        except Exception as e:
            print(f"❌ Error extracting option details: {e}")
            return None

    def analyze_trade_opportunities(self):
        """Analyze options and RSI data to recommend trades."""
        if not self.options_data or not self.spy_data:
            print("❌ Missing data for analysis")
            return []
        
        recommendations = []
        
        rsi_1m = self.spy_data.get('rsi_1m')
        rsi_5m = self.spy_data.get('rsi_5m')
        current_price = self.spy_data.get('current_price')
        
        print("\n🎯 TRADE ANALYSIS")
        print("=" * 40)
        
        # RSI Analysis
        if rsi_1m and rsi_5m:
            if rsi_1m < 30 and rsi_5m < 30:
                bias = "BULLISH"
                reason = "Both 1m and 5m RSI oversold"
                preferred_type = "call"
            elif rsi_1m > 70 and rsi_5m > 70:
                bias = "BEARISH" 
                reason = "Both 1m and 5m RSI overbought"
                preferred_type = "put"
            elif rsi_1m < 30:
                bias = "MILD_BULLISH"
                reason = "1m RSI oversold"
                preferred_type = "call"
            elif rsi_1m > 70:
                bias = "MILD_BEARISH"
                reason = "1m RSI overbought"
                preferred_type = "put"
            else:
                bias = "NEUTRAL"
                reason = "RSI in normal range"
                preferred_type = None
        else:
            bias = "UNKNOWN"
            reason = "Insufficient RSI data"
            preferred_type = None
        
        print(f"📊 Market Bias: {bias}")
        print(f"📝 Reason: {reason}")
        if preferred_type:
            print(f"🎯 Preferred: {preferred_type.upper()}S")
        
        # Analyze individual options
        for option in self.options_data:
            price_cents = option.get('price_cents', 0)
            option_type = option.get('type', 'unknown')
            
            score = 0
            analysis = []
            
            # Price attractiveness (cheaper = higher score for short-term plays)
            if price_cents <= 10:
                score += 3
                analysis.append("Very cheap premium")
            elif price_cents <= 13:
                score += 2
                analysis.append("Reasonable premium")
            else:
                score += 1
                analysis.append("Higher premium")
            
            # RSI alignment
            if preferred_type and option_type == preferred_type:
                score += 5
                analysis.append(f"Aligns with {bias} bias")
            elif preferred_type and option_type != preferred_type:
                score -= 2
                analysis.append(f"Contrarian to {bias} bias")
            
            # Delta consideration (if available)
            if 'delta' in option:
                analysis.append(f"Delta: {option['delta']}")
            
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

    def save_analysis_data(self, recommendations):
        """Save analysis data to file."""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            analysis_data = {
                'timestamp': datetime.now().isoformat(),
                'spy_data': self.spy_data,
                'options_data': self.options_data,
                'recommendations': recommendations,
                'analysis_method': 'rsi_based_options_analysis'
            }
            
            # Save timestamped file
            filename = f"spy_options_analysis_{timestamp}.json"
            filepath = data_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            
            # Save as latest
            latest_path = data_dir / "spy_options_latest.json"
            with open(latest_path, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            
            print(f"💾 Analysis saved: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return None

    def print_recommendations(self, recommendations):
        """Print formatted trade recommendations."""
        if not recommendations:
            print("❌ No recommendations generated")
            return
        
        print("\n🎯 TRADE RECOMMENDATIONS")
        print("=" * 50)
        
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5
            option = rec['option']
            score = rec['score']
            analysis = rec['analysis']
            recommendation = rec['recommendation']
            
            print(f"\n#{i} - {recommendation} (Score: {score})")
            print(f"Type: {option.get('type', 'unknown').upper()}")
            print(f"Price: $0.{option.get('price_cents', 0):02d}")
            if 'strike' in option:
                print(f"Strike: {option['strike']}")
            if 'expiration' in option:
                print(f"Expiration: {option['expiration']}")
            
            print("Analysis:")
            for point in analysis:
                print(f"  • {point}")

    async def run_analysis(self):
        """Run complete options analysis."""
        try:
            # Connect to browser
            if not await self.connect_to_chrome():
                return
            
            # Navigate to options
            if not await self.navigate_to_spy_options():
                return
            
            # Get RSI data
            if not self.get_spy_rsi_data():
                return
            
            # Scan options in price range
            options = await self.scan_options_in_price_range()
            if not options:
                print("❌ No options found in price range")
                return
            
            # Analyze and recommend
            recommendations = self.analyze_trade_opportunities()
            
            # Print results
            self.print_recommendations(recommendations)
            
            # Save data
            self.save_analysis_data(recommendations)
            
        except Exception as e:
            print(f"❌ Analysis error: {e}")
        finally:
            if self.playwright:
                await self.playwright.stop()

async def main():
    """Main function."""
    print("🚀 SPY Options Analyzer with RSI")
    print("=" * 40)
    
    analyzer = SPYOptionsAnalyzer()
    await analyzer.run_analysis()

if __name__ == "__main__":
    asyncio.run(main())