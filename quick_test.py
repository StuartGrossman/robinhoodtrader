#!/usr/bin/env python3
"""
Quick test to check existing Robinhood session
"""
import asyncio
import os
from src.robinhood_automation import RobinhoodAutomation, AuthConfig

async def test_existing_session():
    """Test if we can connect to existing Robinhood session."""
    config = AuthConfig(
        username="dummy",  # Won't be used if already logged in
        password="dummy",  # Won't be used if already logged in
        headless=False,    # Show browser to see existing session
        browser_timeout=30000
    )
    
    print("🔍 Testing connection to existing Robinhood session...")
    
    async with RobinhoodAutomation(config) as automation:
        # Navigate to Robinhood and check if already authenticated
        await automation.page.goto("https://robinhood.com/dashboard", wait_until="networkidle")
        
        # Check if we're already authenticated
        if await automation._is_authenticated():
            print("✅ Already authenticated! Found existing session.")
            automation.session_state.is_authenticated = True
            
            # Try to get account information
            try:
                account_info = await automation.get_account_info()
                print(f"📊 Account Info: {account_info}")
                return True
            except Exception as e:
                print(f"⚠️ Could get session but failed to get account info: {e}")
                return True
        else:
            print("❌ No existing authenticated session found.")
            print("Current URL:", automation.page.url)
            
            # Take a screenshot to see what's on the page
            await automation._take_screenshot("current_state")
            return False

if __name__ == "__main__":
    asyncio.run(test_existing_session())