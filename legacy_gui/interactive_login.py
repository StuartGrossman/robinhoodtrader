#!/usr/bin/env python3
"""
Interactive Robinhood Login for Manual 2FA Handling
This version keeps the browser open for you to see and handle authentication manually.
"""
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from src.robinhood_automation import RobinhoodAutomation, AuthConfig

async def interactive_login():
    """Interactive login that keeps browser open for manual handling."""
    print("🚀 RobinhoodBot - Interactive Login Mode")
    print("=" * 50)
    print("This will open a browser window that stays open.")
    print("You can watch the login process and handle 2FA manually if needed.")
    print("=" * 50)
    
    # Create config with actual credentials
    config = AuthConfig(
        username="grossman.stuart1@gmail.com",
        password="Alenviper123!", 
        headless=False,  # Keep browser visible
        browser_timeout=60000  # 1 minute timeout
    )
    
    automation = RobinhoodAutomation(config)
    
    try:
        # Initialize browser
        await automation.initialize_browser()
        print("✅ Browser opened - you should see a Chrome window")
        
        # Navigate to login page
        print("🌐 Navigating to Robinhood login page...")
        await automation.page.goto("https://robinhood.com/login", wait_until="networkidle")
        await asyncio.sleep(2)
        
        # Fill in credentials
        print("📝 Filling in your credentials...")
        try:
            # Wait for and fill username
            await automation.page.wait_for_selector('input[name="username"], input[type="email"]', timeout=10000)
            await automation.page.fill('input[name="username"], input[type="email"]', config.username)
            await asyncio.sleep(1)
            
            # Fill password
            await automation.page.fill('input[name="password"], input[type="password"]', config.password)
            await asyncio.sleep(1)
            
            print("✅ Credentials filled in")
            
            # Submit form
            print("🔄 Submitting login form...")
            await automation.page.click('button[type="submit"], input[type="submit"]')
            await asyncio.sleep(5)
            
            print("⏳ Login submitted - checking what happens next...")
            
            # Check current state
            current_url = automation.page.url
            print(f"📍 Current URL: {current_url}")
            
            # Wait and see what happens
            for i in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                new_url = automation.page.url
                
                if new_url != current_url:
                    print(f"🔄 Page changed to: {new_url}")
                    current_url = new_url
                
                # Check if we're authenticated
                if await automation._is_authenticated():
                    print("✅ Login successful! You're now authenticated.")
                    return automation
                    
                # Check for MFA prompt
                mfa_selectors = [
                    'input[placeholder*="code"]',
                    'input[type="text"][maxlength="6"]',
                    'input[name="challenge_response"]',
                    'input[name="mfa_code"]'
                ]
                
                mfa_found = False
                for selector in mfa_selectors:
                    if await automation.page.locator(selector).count() > 0:
                        print(f"🔐 2FA prompt detected! Please handle it manually in the browser.")
                        print(f"   MFA input selector: {selector}")
                        mfa_found = True
                        break
                
                if mfa_found:
                    print("⏳ Waiting for you to complete 2FA...")
                    print("   Enter your 2FA code in the browser window and submit.")
                    print("   This script will detect when you're logged in.")
                    
                    # Wait for authentication to complete
                    for j in range(120):  # Wait up to 2 minutes for 2FA
                        await asyncio.sleep(1)
                        if await automation._is_authenticated():
                            print("✅ 2FA completed successfully! You're now authenticated.")
                            print("🎉 Keeping browser open to extract your data...")
                            return automation
                    
                    print("⏰ Timeout waiting for 2FA completion")
                    break
            
            print("❌ Login process did not complete successfully")
            
            # Keep browser open for manual inspection
            print("\n" + "=" * 50)
            print("🔍 MANUAL INSPECTION MODE")
            print("=" * 50)
            print("The browser will stay open for you to inspect what happened.")
            print("You can:")
            print("1. Check for error messages")
            print("2. Try logging in manually")
            print("3. Handle 2FA if needed")
            print("4. Navigate to the dashboard if successful")
            print("\nPress Enter when you want to continue with data extraction...")
            input()
            
            # Check if now authenticated
            if await automation._is_authenticated():
                print("✅ Authentication detected! Proceeding with data extraction.")
                return automation
            else:
                print("❌ Still not authenticated. Cannot proceed with data extraction.")
                return None
        
        except Exception as e:
            print(f"❌ Error during login process: {e}")
            print("The browser window is still open for manual inspection.")
            input("Press Enter to close...")
            return None
            
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return None

async def extract_portfolio_data(automation):
    """Extract comprehensive portfolio data from the dashboard."""
    try:
        print("📊 Extracting portfolio data...")
        
        # Navigate to main page after login
        await automation.page.goto("https://robinhood.com/", wait_until="networkidle")
        await asyncio.sleep(3)
        
        portfolio_data = {}
        
        # Try various selectors for portfolio value
        value_selectors = [
            '[data-testid="portfolio-value"]',
            '.portfolio-value',
            '[data-rh-test-id="portfolio-value"]',
            'div:has-text("$"):has-text(",")',
            'span:has-text("$"):has-text(",")',
            '[data-testid="total-value"]'
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
        
        return portfolio_data
        
    except Exception as e:
        print(f"⚠️ Error extracting portfolio data: {e}")
        return {}

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
            'extraction_method': 'interactive_login'
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
    """Main function with interactive login."""
    automation = await interactive_login()
    
    if automation:
        try:
            print("🎯 Now extracting your portfolio data...")
            await asyncio.sleep(2)  # Give time to see the message
            
            # Extract data
            portfolio_data = await extract_portfolio_data(automation)
            holdings = []  # We'll add holdings extraction later
            
            # Save data
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
            
            print("\n✅ Data extraction completed successfully!")
            print("📁 Check the 'data' folder for your portfolio data files.")
            print("🌐 Browser will stay open for 30 more seconds for you to review.")
            
            # Keep browser open for review
            for i in range(30, 0, -1):
                print(f"\rClosing in {i} seconds... (Press Ctrl+C to keep open longer)", end="", flush=True)
                await asyncio.sleep(1)
            
            print("\n👋 Closing browser...")
            
        except KeyboardInterrupt:
            print("\n⏸️  Browser staying open - Press Enter when ready to close...")
            input()
        finally:
            await automation.close()
    else:
        print("❌ Could not establish authenticated session")

if __name__ == "__main__":
    asyncio.run(main())