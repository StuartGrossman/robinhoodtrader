#!/usr/bin/env python3
"""
SPY Options Navigator for Robinhood
Navigates to SPY options and extracts daily option data
"""
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from src.robinhood_automation import RobinhoodAutomation, AuthConfig

async def navigate_to_spy_options(automation):
    """Navigate to SPY options page and extract option data."""
    try:
        print("🎯 Navigating to SPY options chain...")
        
        # Navigate directly to SPY options chain
        spy_options_url = "https://robinhood.com/options/chains/SPY"
        print(f"🌐 Going to: {spy_options_url}")
        
        await automation.page.goto(spy_options_url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Set zoom to 50% so user can see everything
        print("🔍 Setting zoom to 50% for better visibility...")
        await automation.page.evaluate("document.body.style.zoom = '0.5'")
        await asyncio.sleep(2)
        
        # Check current URL
        current_url = automation.page.url
        print(f"📍 Current URL: {current_url}")
        
        # Wait a bit more for options data to load
        print("⏳ Waiting for options data to load...")
        await asyncio.sleep(5)
        
        # Take screenshot to see current state
        await automation._take_screenshot("spy_options_page")
        
        # Extract options data
        return await extract_spy_options_data(automation)
        
    except Exception as e:
        print(f"❌ Error navigating to SPY options: {e}")
        return {}

async def extract_spy_options_data(automation):
    """Extract SPY options data from the current page."""
    try:
        print("📈 Extracting SPY options data...")
        
        options_data = {
            "symbol": "SPY",
            "timestamp": datetime.now().isoformat(),
            "current_url": automation.page.url,
            "options": []
        }
        
        # Look for option chains or option listings
        option_selectors = [
            '[data-testid="option-chain"]',
            '.option-chain',
            '.options-list',
            'div:has-text("Call"):has-text("Put")',
            'table tr:has-text("$")'
        ]
        
        for selector in option_selectors:
            elements = automation.page.locator(selector)
            count = await elements.count()
            if count > 0:
                print(f"📊 Found {count} option elements with selector: {selector}")
                
                # Extract data from first few elements
                for i in range(min(count, 10)):
                    try:
                        element = elements.nth(i)
                        text = await element.text_content()
                        if text and ("$" in text or "Call" in text or "Put" in text):
                            options_data["options"].append({
                                "text": text.strip(),
                                "index": i
                            })
                    except Exception as e:
                        print(f"⚠️ Error extracting option {i}: {e}")
                
                break
        
        # Also look for current SPY price
        price_selectors = [
            '[data-testid="stock-price"]',
            '.stock-price',
            'span:has-text("$"):has-text(".")',
            'div:has-text("$"):has-text(".")'
        ]
        
        for selector in price_selectors:
            elements = automation.page.locator(selector)
            if await elements.count() > 0:
                try:
                    price_text = await elements.first.text_content()
                    if price_text and "$" in price_text:
                        options_data["current_price"] = price_text.strip()
                        print(f"💰 SPY Current Price: {price_text.strip()}")
                        break
                except Exception as e:
                    continue
        
        return options_data
        
    except Exception as e:
        print(f"⚠️ Error extracting options data: {e}")
        return {}

async def save_spy_options_data(options_data):
    """Save SPY options data to JSON file."""
    try:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to timestamped file
        data_file = data_dir / f"spy_options_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump(options_data, f, indent=2)
        
        # Also save as latest spy options
        latest_file = data_dir / "spy_options_latest.json"
        with open(latest_file, 'w') as f:
            json.dump(options_data, f, indent=2)
        
        print(f"💾 SPY options data saved to: {data_file}")
        print(f"💾 Latest SPY options: {latest_file}")
        
    except Exception as e:
        print(f"⚠️ Error saving SPY options data: {e}")

async def main():
    """Main function for SPY options navigation."""
    print("🚀 SPY Options Navigator")
    print("=" * 40)
    print("This will open a browser window for manual Robinhood trading.")
    print("You can log in manually and navigate as needed.")
    print("The script will go to SPY options and zoom out for better visibility.")
    print("=" * 40)
    
    # Create config 
    config = AuthConfig(
        username="grossman.stuart1@gmail.com",  # Not used for manual login
        password="Alenviper123!",  # Not used for manual login
        headless=False,  # Keep browser visible
        browser_timeout=60000
    )
    
    automation = RobinhoodAutomation(config)
    
    try:
        # Initialize browser
        await automation.initialize_browser()
        print("✅ Browser opened - you can now log in manually")
        
        # Navigate to SPY options
        options_data = await navigate_to_spy_options(automation)
        
        # Save data
        await save_spy_options_data(options_data)
        
        # Summary
        print("\n" + "=" * 40)
        print("📋 SPY OPTIONS SUMMARY")
        print("=" * 40)
        print(f"Symbol: {options_data.get('symbol', 'N/A')}")
        print(f"Current Price: {options_data.get('current_price', 'N/A')}")
        print(f"Options Found: {len(options_data.get('options', []))}")
        print(f"URL: {options_data.get('current_url', 'N/A')}")
        
        # Show first few options
        if options_data.get('options'):
            print("\nSample Options:")
            for i, option in enumerate(options_data['options'][:5]):
                print(f"  {i+1}. {option['text'][:100]}...")
        
        print("\n🌐 Browser will stay open for manual trading!")
        print("🎯 Navigate and perform all your actions in the browser window.")
        print("📊 The page is zoomed to 50% so you can see everything.")
        print("⏸️  Press Enter in this terminal when you want to close the browser...")
        
        # Keep browser open indefinitely until user presses Enter
        input()
        print("👋 Closing browser...")
        
    except KeyboardInterrupt:
        print("\n⏸️  Press Enter when ready to close browser...")
        input()
    finally:
        await automation.close()

if __name__ == "__main__":
    asyncio.run(main())