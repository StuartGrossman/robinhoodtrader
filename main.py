#!/usr/bin/env python3
"""
RobinhoodBot Main Application
Enhanced to work with existing sessions and extract comprehensive account data
"""
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from src.robinhood_automation import RobinhoodAutomation, AuthConfig
from src.mfa_handler import MFAHandler, create_mfa_config

async def extract_portfolio_data(automation):
    """Extract comprehensive portfolio data from the dashboard."""
    try:
        print("📊 Extracting portfolio data...")
        
        # Navigate to main page after login  
        await automation.page.goto("https://robinhood.com/", wait_until="networkidle")
        await asyncio.sleep(2)
        
        portfolio_data = {}
        
        # Try various selectors for portfolio value
        value_selectors = [
            '[data-testid="portfolio-value"]',
            '.portfolio-value',
            '[data-rh-test-id="portfolio-value"]',
            'div:has-text("$"):has-text(",")',
            'span:has-text("$"):has-text(",")'
        ]
        
        for selector in value_selectors:
            elements = automation.page.locator(selector)
            if await elements.count() > 0:
                try:
                    text = await elements.first.text_content()
                    if text and '$' in text:
                        portfolio_data['portfolio_value'] = text.strip()
                        print(f"💰 Portfolio Value: {text.strip()}")
                        break
                except:
                    continue
        
        # Extract today's change
        change_selectors = [
            '[data-testid="portfolio-change"]',
            '.portfolio-change',
            'div:has-text("+"):has-text("$"), div:has-text("-"):has-text("$")'
        ]
        
        for selector in change_selectors:
            elements = automation.page.locator(selector)
            if await elements.count() > 0:
                try:
                    text = await elements.first.text_content()
                    if text and ('$' in text or '%' in text):
                        portfolio_data['daily_change'] = text.strip()
                        print(f"📈 Daily Change: {text.strip()}")
                        break
                except:
                    continue
        
        # Get buying power
        buying_power_selectors = [
            '[data-testid="buying-power"]',
            '.buying-power',
            'div:has-text("Buying Power")',
            'span:has-text("Available")'
        ]
        
        for selector in buying_power_selectors:
            elements = automation.page.locator(selector)
            if await elements.count() > 0:
                try:
                    # Look for the value near the label
                    parent = elements.first
                    value_element = parent.locator('.. >> text=/\\$.+/')
                    if await value_element.count() > 0:
                        text = await value_element.first.text_content()
                        portfolio_data['buying_power'] = text.strip()
                        print(f"💵 Buying Power: {text.strip()}")
                        break
                except:
                    continue
        
        return portfolio_data
        
    except Exception as e:
        print(f"⚠️ Error extracting portfolio data: {e}")
        return {}

async def extract_holdings(automation):
    """Extract current stock holdings."""
    try:
        print("📈 Extracting stock holdings...")
        
        # Navigate to portfolio positions
        await automation.page.goto("https://robinhood.com/portfolio", wait_until="networkidle")
        await asyncio.sleep(3)
        
        holdings = []
        
        # Look for stock position cards/rows
        position_selectors = [
            '[data-testid="position-card"]',
            '.position-card',
            '[data-rh-test-id="position"]',
            'div[role="button"]:has-text("$")',
            'a:has([data-testid="symbol"])'
        ]
        
        for selector in position_selectors:
            elements = automation.page.locator(selector)
            count = await elements.count()
            
            if count > 0:
                print(f"Found {count} positions using selector: {selector}")
                
                for i in range(min(count, 10)):  # Limit to first 10 positions
                    try:
                        element = elements.nth(i)
                        
                        # Extract symbol
                        symbol_element = element.locator('[data-testid="symbol"], .symbol, text=/^[A-Z]{1,5}$/')
                        symbol = await symbol_element.first.text_content() if await symbol_element.count() > 0 else None
                        
                        # Extract current value
                        value_element = element.locator('text=/\\$[0-9,]+\\.?[0-9]*/')
                        value = await value_element.first.text_content() if await value_element.count() > 0 else None
                        
                        if symbol and value:
                            holdings.append({
                                'symbol': symbol.strip(),
                                'current_value': value.strip(),
                                'extracted_at': datetime.now().isoformat()
                            })
                            print(f"  📊 {symbol.strip()}: {value.strip()}")
                    
                    except Exception as e:
                        print(f"  ⚠️ Error extracting position {i}: {e}")
                        continue
                
                break  # If we found positions with one selector, don't try others
        
        return holdings
        
    except Exception as e:
        print(f"⚠️ Error extracting holdings: {e}")
        return []

async def save_data(portfolio_data, holdings):
    """Save extracted data to JSON file."""
    try:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        combined_data = {
            'timestamp': datetime.now().isoformat(),
            'portfolio': portfolio_data,
            'holdings': holdings,
            'extraction_method': 'automated_web_scraping'
        }
        
        # Save to timestamped file
        data_file = data_dir / f"robinhood_data_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        # Also save as latest.json for easy access
        latest_file = data_dir / "latest.json"
        with open(latest_file, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        print(f"💾 Data saved to: {data_file}")
        print(f"💾 Latest data: {latest_file}")
        
    except Exception as e:
        print(f"⚠️ Error saving data: {e}")

async def main():
    """Main application with existing session support."""
    print("🚀 RobinhoodBot - Enhanced Session Handler")
    print("=" * 50)
    
    # Create config with actual credentials
    config = AuthConfig(
        username="grossman.stuart1@gmail.com",
        password="Alenviper123!", 
        headless=False,  # Show browser to see what's happening
        browser_timeout=30000
    )
    
    async with RobinhoodAutomation(config) as automation:
        # Perform fresh login with your credentials
        print("🔐 Attempting to log in with your credentials...")
        
        if await automation.login():
            print("✅ Login successful!")
            
            # Extract portfolio data
            portfolio_data = await extract_portfolio_data(automation)
            
            # Extract holdings
            holdings = await extract_holdings(automation)
            
            # Save all data
            await save_data(portfolio_data, holdings)
            
            # Summary
            print("\n" + "=" * 50)
            print("📋 EXTRACTION SUMMARY")
            print("=" * 50)
            print(f"Portfolio Data Points: {len(portfolio_data)}")
            print(f"Holdings Found: {len(holdings)}")
            
            if portfolio_data:
                for key, value in portfolio_data.items():
                    print(f"  {key}: {value}")
            
            if holdings:
                print(f"\nTop Holdings:")
                for holding in holdings[:5]:
                    print(f"  {holding['symbol']}: {holding['current_value']}")
            
        else:
            print("❌ Login failed. Please check your credentials or handle 2FA manually.")
            print("Current URL:", automation.page.url)
            
            # Take screenshot to see current state
            await automation._take_screenshot("login_failed")

if __name__ == "__main__":
    asyncio.run(main())