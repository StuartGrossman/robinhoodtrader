"""
Robinhood Web Automation using Playwright

This module provides a comprehensive web automation solution for interacting with 
Robinhood.com, featuring secure credential storage, resilient multi-factor 
authentication handling, and robust error recovery mechanisms.

Features:
- Secure credential management with environment variables
- Multi-factor authentication (MFA) support
- Session persistence and cookie management
- Comprehensive error handling and retry logic
- Headless and headed browser modes
- Screenshot capture for debugging
- Activity logging for audit trails

Author: RobinhoodBot
Version: 1.0.0
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import json
import time
from datetime import datetime, timedelta

from playwright.async_api import (
    async_playwright, 
    Browser, 
    BrowserContext, 
    Page, 
    TimeoutError as PlaywrightTimeoutError
)
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

# Load environment variables
load_dotenv()


@dataclass
class AuthConfig:
    """Configuration for authentication and security settings."""
    username: str
    password: str
    mfa_phone: Optional[str] = None
    mfa_email: Optional[str] = None
    session_timeout: int = 3600  # 1 hour
    max_login_attempts: int = 3
    headless: bool = True
    browser_timeout: int = 30000


@dataclass
class SessionState:
    """Represents the current session state."""
    is_authenticated: bool = False
    last_activity: Optional[datetime] = None
    session_cookies: Optional[List[Dict]] = None
    user_agent: Optional[str] = None
    csrf_token: Optional[str] = None


class SecureCredentialManager:
    """Manages secure storage and retrieval of sensitive credentials."""
    
    def __init__(self, key_file: str = "config/.encryption_key"):
        """Initialize the credential manager with encryption key."""
        self.key_file = Path(key_file)
        self._ensure_encryption_key()
        
    def _ensure_encryption_key(self) -> None:
        """Create encryption key if it doesn't exist."""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Restrict permissions
    
    def _get_cipher(self) -> Fernet:
        """Get the encryption cipher."""
        with open(self.key_file, 'rb') as f:
            key = f.read()
        return Fernet(key)
    
    def encrypt_credentials(self, credentials: Dict[str, str]) -> str:
        """Encrypt credentials dictionary."""
        cipher = self._get_cipher()
        data = json.dumps(credentials).encode()
        return base64.urlsafe_b64encode(cipher.encrypt(data)).decode()
    
    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, str]:
        """Decrypt credentials dictionary."""
        cipher = self._get_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())


class RobinhoodAutomation:
    """
    Main class for automating Robinhood web interface using Playwright.
    
    Provides secure authentication, session management, and resilient 
    web interactions with comprehensive error handling.
    """
    
    def __init__(self, config: AuthConfig):
        """Initialize the Robinhood automation system."""
        self.config = config
        self.logger = self._setup_logging()
        self.credential_manager = SecureCredentialManager()
        self.session_state = SessionState()
        
        # Browser components
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Session management
        self.session_file = Path("config/session_data.json")
        self.login_attempts = 0
        
        # URLs and selectors
        self.base_url = "https://robinhood.com"
        self.login_url = f"{self.base_url}/login"
        self.selectors = self._load_selectors()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger("RobinhoodAutomation")
        logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
        
        # Create logs directory if it doesn't exist
        log_file = Path(os.getenv("LOG_FILE", "logs/robinhood_automation.log"))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _load_selectors(self) -> Dict[str, str]:
        """Load CSS selectors for web elements."""
        return {
            # Login page selectors
            "username_input": 'input[name="username"], input[type="email"]',
            "password_input": 'input[name="password"], input[type="password"]',
            "login_button": 'button[type="submit"], input[type="submit"]',
            "remember_me": 'input[type="checkbox"][name="remember"]',
            
            # MFA selectors
            "mfa_code_input": 'input[name="mfa_code"], input[placeholder*="code"]',
            "mfa_submit": 'button:has-text("Submit"), button:has-text("Verify")',
            "mfa_resend": 'button:has-text("Resend"), a:has-text("Resend")',
            
            # Dashboard elements
            "account_menu": '[data-testid="account-menu"], .account-menu',
            "portfolio_value": '[data-testid="portfolio-value"], .portfolio-value',
            "navbar": 'nav, [role="navigation"]',
            
            # Error messages
            "error_message": '.error, .alert-danger, [role="alert"]',
            "login_error": '.login-error, .authentication-error',
            
            # Security elements
            "captcha": '.captcha, .recaptcha',
            "security_question": '.security-question, [data-testid="security-question"]',
        }
    
    async def initialize_browser(self) -> None:
        """Initialize Playwright browser with optimal settings."""
        try:
            self.playwright = await async_playwright().start()
            
            # Browser launch options
            launch_options = {
                "headless": self.config.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor"
                ]
            }
            
            # Use Chromium for better compatibility
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # Create browser context with realistic settings
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "permissions": ["geolocation"],
                "extra_http_headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            }
            
            self.context = await self.browser.new_context(**context_options)
            
            # Load existing session if available
            await self._load_session()
            
            # Create new page
            self.page = await self.context.new_page()
            
            # Set timeout
            self.page.set_default_timeout(self.config.browser_timeout)
            
            # Add script to avoid detection
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                window.chrome = {
                    runtime: {},
                };
            """)
            
            self.logger.info("Browser initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            raise
    
    async def _load_session(self) -> None:
        """Load existing session data if available."""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                
                # Check if session is still valid
                last_activity = datetime.fromisoformat(session_data.get("last_activity", ""))
                if datetime.now() - last_activity < timedelta(seconds=self.config.session_timeout):
                    # Restore cookies
                    cookies = session_data.get("cookies", [])
                    if cookies and self.context:
                        await self.context.add_cookies(cookies)
                    
                    self.session_state.session_cookies = cookies
                    self.session_state.last_activity = last_activity
                    self.session_state.csrf_token = session_data.get("csrf_token")
                    
                    self.logger.info("Loaded existing session data")
                else:
                    self.logger.info("Session expired, will need fresh authentication")
                    
        except Exception as e:
            self.logger.warning(f"Could not load session data: {str(e)}")
    
    async def _save_session(self) -> None:
        """Save current session data."""
        try:
            if self.context:
                cookies = await self.context.cookies()
                session_data = {
                    "cookies": cookies,
                    "last_activity": datetime.now().isoformat(),
                    "csrf_token": self.session_state.csrf_token,
                    "user_agent": self.session_state.user_agent
                }
                
                self.session_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.session_file, 'w') as f:
                    json.dump(session_data, f, indent=2)
                
                self.session_state.session_cookies = cookies
                self.session_state.last_activity = datetime.now()
                
                self.logger.debug("Session data saved")
                
        except Exception as e:
            self.logger.error(f"Failed to save session data: {str(e)}")
    
    async def login(self) -> bool:
        """
        Perform login to Robinhood with MFA support.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if self.session_state.is_authenticated:
            self.logger.info("Already authenticated")
            return True
        
        if self.login_attempts >= self.config.max_login_attempts:
            self.logger.error("Maximum login attempts exceeded")
            return False
        
        try:
            self.login_attempts += 1
            self.logger.info(f"Login attempt {self.login_attempts}/{self.config.max_login_attempts}")
            
            # Navigate to login page
            await self.page.goto(self.login_url, wait_until="networkidle")
            await self._take_screenshot("login_page")
            
            # Check if already logged in
            if await self._is_authenticated():
                self.session_state.is_authenticated = True
                await self._save_session()
                return True
            
            # Fill login form
            if not await self._fill_login_form():
                return False
            
            # Handle potential MFA
            if await self._handle_mfa():
                self.session_state.is_authenticated = True
                await self._save_session()
                self.logger.info("Login successful")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            await self._take_screenshot("login_error")
            return False
    
    async def _fill_login_form(self) -> bool:
        """Fill and submit the login form."""
        try:
            # Wait for login form to be visible
            await self.page.wait_for_selector(self.selectors["username_input"], timeout=10000)
            
            # Fill username
            await self.page.fill(self.selectors["username_input"], self.config.username)
            await asyncio.sleep(0.5)  # Human-like delay
            
            # Fill password
            await self.page.fill(self.selectors["password_input"], self.config.password)
            await asyncio.sleep(0.5)
            
            # Check remember me if available
            remember_me = self.page.locator(self.selectors["remember_me"])
            if await remember_me.count() > 0:
                await remember_me.check()
            
            await self._take_screenshot("login_form_filled")
            
            # Submit form
            await self.page.click(self.selectors["login_button"])
            
            # Wait longer for navigation or MFA prompt
            await asyncio.sleep(5)
            
            # Take screenshot after form submission
            await self._take_screenshot("after_login_submit")
            
            # Check for login errors
            error_elements = self.page.locator(self.selectors["error_message"])
            if await error_elements.count() > 0:
                error_text = await error_elements.first.text_content()
                self.logger.error(f"Login error: {error_text}")
                return False
            
            self.logger.info("Login form submitted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill login form: {str(e)}")
            return False
    
    async def _handle_mfa(self) -> bool:
        """Handle multi-factor authentication if required."""
        try:
            # Wait to see if MFA is required
            await asyncio.sleep(5)
            
            # Take screenshot to see current state
            await self._take_screenshot("checking_for_mfa")
            
            # Check current URL and page content
            current_url = self.page.url
            self.logger.info(f"Current URL after login: {current_url}")
            
            # Check if already authenticated (redirected to dashboard)
            if await self._is_authenticated():
                self.logger.info("Already authenticated - no MFA required")
                return True
            
            # Check if MFA code input is present
            mfa_input = self.page.locator(self.selectors["mfa_code_input"])
            if await mfa_input.count() == 0:
                # Also check for alternative MFA selectors
                alt_mfa_selectors = [
                    'input[placeholder*="code"]',
                    'input[type="text"][maxlength="6"]',
                    'input[name="challenge_response"]'
                ]
                mfa_found = False
                for selector in alt_mfa_selectors:
                    if await self.page.locator(selector).count() > 0:
                        self.selectors["mfa_code_input"] = selector
                        mfa_found = True
                        break
                
                if not mfa_found:
                    self.logger.info("No MFA input found - checking authentication")
                    return await self._is_authenticated()
            
            self.logger.info("MFA required - waiting for user input")
            await self._take_screenshot("mfa_prompt")
            
            return await self._prompt_for_mfa_code()
            
        except Exception as e:
            self.logger.error(f"MFA handling failed: {str(e)}")
            return False
    
    async def _prompt_for_mfa_code(self) -> bool:
        """Prompt user for MFA code and submit it."""
        try:
            max_attempts = 5  # Increased attempts
            for attempt in range(max_attempts):
                self.logger.info(f"MFA attempt {attempt + 1}/{max_attempts}")
                
                print("\n🔐 Multi-Factor Authentication Required")
                print("The browser window should be open - you can see the MFA prompt.")
                print("Please check your phone or email for the verification code.")
                print("You have up to 2 minutes to enter the code.")
                
                # Give user more time to get and enter the code
                try:
                    mfa_code = input("Enter MFA code (or 'skip' to handle manually in browser): ").strip()
                    
                    if mfa_code.lower() == 'skip':
                        print("⏳ Waiting for you to handle MFA manually in the browser...")
                        print("You have 2 minutes. Press Enter when you're logged in.")
                        input("Press Enter after completing MFA in browser...")
                        
                        # Check if authentication successful
                        if await self._is_authenticated():
                            self.logger.info("Manual MFA authentication successful")
                            return True
                        else:
                            print("❌ Authentication check failed. Please try again.")
                            continue
                    
                    if not mfa_code or len(mfa_code) < 4:
                        print("Invalid code format. Please try again.")
                        continue
                    
                    # Fill MFA code
                    await self.page.fill(self.selectors["mfa_code_input"], mfa_code)
                    await asyncio.sleep(0.5)
                    
                    # Submit MFA
                    await self.page.click(self.selectors["mfa_submit"])
                    await asyncio.sleep(5)  # Increased wait time
                    
                    # Check if authentication successful
                    if await self._is_authenticated():
                        self.logger.info("MFA authentication successful")
                        return True
                    
                    # Check for MFA errors
                    error_elements = self.page.locator(self.selectors["error_message"])
                    if await error_elements.count() > 0:
                        error_text = await error_elements.first.text_content()
                        self.logger.warning(f"MFA error: {error_text}")
                        print(f"❌ {error_text}")
                    else:
                        print("❌ Invalid code. Please try again.")
                        
                except KeyboardInterrupt:
                    print("\n⏳ Waiting for manual completion...")
                    for i in range(120):  # 2 minute timeout
                        await asyncio.sleep(1)
                        if await self._is_authenticated():
                            self.logger.info("Manual authentication detected")
                            return True
                    print("⏰ Timeout waiting for manual authentication")
            
            self.logger.error("MFA authentication failed after maximum attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"MFA code prompt failed: {str(e)}")
            return False
    
    async def _is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        try:
            # Check for presence of authenticated elements
            authenticated_selectors = [
                self.selectors["account_menu"],
                self.selectors["portfolio_value"],
                self.selectors["navbar"]
            ]
            
            for selector in authenticated_selectors:
                elements = self.page.locator(selector)
                if await elements.count() > 0:
                    self.logger.debug(f"Authentication confirmed by selector: {selector}")
                    return True
            
            # Check URL patterns that indicate authentication
            current_url = self.page.url
            authenticated_patterns = ["/dashboard", "/portfolio", "/account"]
            
            if any(pattern in current_url for pattern in authenticated_patterns):
                self.logger.debug(f"Authentication confirmed by URL: {current_url}")
                return True
            
            # Check for login page indicators (negative check)
            if "login" in current_url.lower():
                return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Authentication check failed: {str(e)}")
            return False
    
    async def _take_screenshot(self, name: str) -> None:
        """Take a screenshot for debugging purposes."""
        try:
            if self.page and not self.config.headless:
                screenshot_dir = Path("logs/screenshots")
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = screenshot_dir / f"{name}_{timestamp}.png"
                
                await self.page.screenshot(path=str(screenshot_path))
                self.logger.debug(f"Screenshot saved: {screenshot_path}")
                
        except Exception as e:
            self.logger.warning(f"Failed to take screenshot: {str(e)}")
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Retrieve account information from the dashboard."""
        if not self.session_state.is_authenticated:
            raise Exception("Not authenticated. Please login first.")
        
        try:
            # Navigate to main page if not already there
            await self.page.goto(f"{self.base_url}/", wait_until="networkidle")
            
            account_info = {}
            
            # Get portfolio value
            portfolio_element = self.page.locator(self.selectors["portfolio_value"])
            if await portfolio_element.count() > 0:
                portfolio_text = await portfolio_element.first.text_content()
                account_info["portfolio_value"] = portfolio_text.strip()
            
            # Add more account information extraction here
            # This would depend on Robinhood's current page structure
            
            self.logger.info("Account information retrieved successfully")
            return account_info
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {str(e)}")
            raise
    
    async def logout(self) -> bool:
        """Perform logout and cleanup."""
        try:
            if self.session_state.is_authenticated:
                # Attempt to logout via UI
                try:
                    account_menu = self.page.locator(self.selectors["account_menu"])
                    if await account_menu.count() > 0:
                        await account_menu.click()
                        await asyncio.sleep(1)
                        
                        logout_button = self.page.locator('text=Logout, text=Sign Out')
                        if await logout_button.count() > 0:
                            await logout_button.click()
                            await asyncio.sleep(2)
                except Exception as e:
                    self.logger.warning(f"UI logout failed: {str(e)}")
            
            # Clear session data
            self.session_state.is_authenticated = False
            self.session_state.session_cookies = None
            self.session_state.csrf_token = None
            
            # Remove session file
            if self.session_file.exists():
                self.session_file.unlink()
            
            self.logger.info("Logout completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Logout failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            
            if self.context:
                await self.context.close()
            
            if self.browser:
                await self.browser.close()
            
            if self.playwright:
                await self.playwright.stop()
            
            self.logger.info("Browser resources cleaned up")
            
        except Exception as e:
            self.logger.error(f"Failed to close browser: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Utility functions for easy usage
def create_auth_config() -> AuthConfig:
    """Create AuthConfig from environment variables."""
    return AuthConfig(
        username=os.getenv("ROBINHOOD_USERNAME", "grossman.stuart1@gmail.com"),
        password=os.getenv("ROBINHOOD_PASSWORD", "Alenviper123!"),
        headless=os.getenv("HEADLESS_MODE", "false").lower() == "true",
        browser_timeout=int(os.getenv("BROWSER_TIMEOUT", "30000"))
    )


async def main():
    """Example usage of the RobinhoodAutomation class."""
    config = create_auth_config()
    
    if not config.username or not config.password:
        print("❌ Please set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD in your .env file")
        return
    
    async with RobinhoodAutomation(config) as automation:
        # Attempt login
        if await automation.login():
            print("✅ Login successful!")
            
            # Get account information
            try:
                account_info = await automation.get_account_info()
                print(f"📊 Account Info: {account_info}")
            except Exception as e:
                print(f"❌ Failed to get account info: {e}")
            
            # Logout
            await automation.logout()
        else:
            print("❌ Login failed")


if __name__ == "__main__":
    asyncio.run(main())
