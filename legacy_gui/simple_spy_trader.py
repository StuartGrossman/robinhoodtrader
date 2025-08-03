#!/usr/bin/env python3
"""
Simple SPY Trader - Uses persistent browser session
Creates a browser that keeps your login session
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    """Simple SPY options trader."""
    print("🚀 Simple SPY Options Trader")
    print("=" * 40)
    print("🌐 Opening browser with session persistence...")
    
    playwright = await async_playwright().start()
    
    # Use persistent context to save cookies/session
    user_data_dir = Path("/tmp/robinhood_session")
    user_data_dir.mkdir(exist_ok=True)
    
    try:
        # Create persistent context (saves cookies automatically)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run"
            ]
        )
        
        # Get or create page
        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()
        
        # Set zoom to 50%
        await page.evaluate("document.body.style.zoom = '0.5'")
        
        print("✅ Browser opened with persistent session")
        
        # Navigate to SPY options
        print("📊 Navigating to SPY options...")
        await page.goto("https://robinhood.com/options/chains/SPY", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        if "login" in current_url:
            print("🔐 Please log in manually in the browser...")
            print("   The browser will remember your login for next time!")
            
            # Wait for login
            while "login" in page.url:
                await asyncio.sleep(2)
                print("⏳ Still waiting for login...")
            
            print("✅ Login successful! Session saved for next time.")
        else:
            print("🎉 Already logged in! Using saved session.")
        
        # Now on SPY options page
        print("\n🎯 You're now on the SPY options chain!")
        print("📊 Page is zoomed to 50% for better visibility")
        print("🔍 You can manually:")
        print("   • Browse same-day options")  
        print("   • Look for 8-16¢ options")
        print("   • Monitor price movements")
        print("   • Execute trades")
        
        print("\n🌐 Browser will stay open for trading...")
        print("⏸️  Press Enter to close...")
        
        # Keep browser open
        input()
        
    except KeyboardInterrupt:
        print("\n⏸️ Interrupted")
    finally:
        await context.close()
        await playwright.stop()
        print("👋 Browser closed")

if __name__ == "__main__":
    asyncio.run(main())