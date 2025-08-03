"""
Security Utilities for Robinhood Automation

This module provides advanced security features including:
- Multi-factor authentication handlers
- CAPTCHA detection and handling
- Device fingerprinting
- Rate limiting and retry logic
- Security question handling
- Session validation and security checks

Author: RobinhoodBot
Version: 1.0.0
"""

import asyncio
import logging
import re
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
import random
import hashlib
import base64

from playwright.async_api import Page, Locator
import cv2
import numpy as np
from PIL import Image
import io


@dataclass
class SecurityConfig:
    """Configuration for security features."""
    enable_captcha_solving: bool = True
    max_captcha_attempts: int = 3
    enable_device_fingerprint: bool = True
    rate_limit_delay: float = 1.0
    max_retry_attempts: int = 5
    security_question_answers: Optional[Dict[str, str]] = None


@dataclass
class MFAMethod:
    """Represents a multi-factor authentication method."""
    method_type: str  # 'sms', 'email', 'app', 'call'
    identifier: str  # phone number, email, or app name
    is_preferred: bool = False
    last_used: Optional[datetime] = None


class DeviceFingerprint:
    """Generates and manages device fingerprinting."""
    
    def __init__(self):
        """Initialize device fingerprinting."""
        self.fingerprint_file = Path("config/device_fingerprint.json")
        self.fingerprint_data = self._load_or_create_fingerprint()
    
    def _load_or_create_fingerprint(self) -> Dict[str, Any]:
        """Load existing fingerprint or create new one."""
        if self.fingerprint_file.exists():
            with open(self.fingerprint_file, 'r') as f:
                return json.load(f)
        
        # Create new fingerprint
        fingerprint = {
            "screen_resolution": "1920x1080",
            "timezone": -300,  # EST
            "language": "en-US",
            "platform": "MacIntel",
            "user_agent_hash": self._generate_ua_hash(),
            "canvas_fingerprint": self._generate_canvas_fingerprint(),
            "webgl_fingerprint": self._generate_webgl_fingerprint(),
            "audio_fingerprint": self._generate_audio_fingerprint(),
            "created_at": datetime.now().isoformat()
        }
        
        # Save fingerprint
        self.fingerprint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fingerprint_file, 'w') as f:
            json.dump(fingerprint, f, indent=2)
        
        return fingerprint
    
    def _generate_ua_hash(self) -> str:
        """Generate user agent hash."""
        base_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        return hashlib.sha256(base_ua.encode()).hexdigest()[:16]
    
    def _generate_canvas_fingerprint(self) -> str:
        """Generate canvas fingerprint."""
        # Simulate canvas rendering characteristics
        canvas_data = f"canvas_{random.randint(1000, 9999)}_{int(time.time())}"
        return hashlib.md5(canvas_data.encode()).hexdigest()
    
    def _generate_webgl_fingerprint(self) -> str:
        """Generate WebGL fingerprint."""
        webgl_data = f"webgl_{random.randint(1000, 9999)}_{int(time.time())}"
        return hashlib.md5(webgl_data.encode()).hexdigest()
    
    def _generate_audio_fingerprint(self) -> str:
        """Generate audio context fingerprint."""
        audio_data = f"audio_{random.randint(1000, 9999)}_{int(time.time())}"
        return hashlib.md5(audio_data.encode()).hexdigest()
    
    async def inject_fingerprint(self, page: Page) -> None:
        """Inject fingerprint data into page."""
        fingerprint_script = f"""
        // Override screen properties
        Object.defineProperty(screen, 'width', {{
            get: () => {self.fingerprint_data['screen_resolution'].split('x')[0]}
        }});
        Object.defineProperty(screen, 'height', {{
            get: () => {self.fingerprint_data['screen_resolution'].split('x')[1]}
        }});
        
        // Override timezone
        Date.prototype.getTimezoneOffset = function() {{
            return {self.fingerprint_data['timezone']};
        }};
        
        // Override navigator properties
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{self.fingerprint_data['platform']}'
        }});
        
        Object.defineProperty(navigator, 'language', {{
            get: () => '{self.fingerprint_data['language']}'
        }});
        
        // Canvas fingerprinting protection
        HTMLCanvasElement.prototype.getContext = function(contextType) {{
            if (contextType === '2d' || contextType === 'webgl') {{
                const originalGetContext = HTMLCanvasElement.prototype.getContext;
                const context = originalGetContext.call(this, contextType);
                
                if (contextType === '2d' && context) {{
                    const originalToDataURL = this.toDataURL;
                    this.toDataURL = function() {{
                        const imageData = originalToDataURL.apply(this, arguments);
                        return imageData + '{self.fingerprint_data['canvas_fingerprint']}';
                    }};
                }}
                
                return context;
            }}
            return HTMLCanvasElement.prototype.getContext.call(this, contextType);
        }};
        
        // WebGL fingerprinting
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{ // UNMASKED_VENDOR_WEBGL
                return 'Intel Inc.';
            }}
            if (parameter === 37446) {{ // UNMASKED_RENDERER_WEBGL
                return 'Intel Iris Pro OpenGL Engine';
            }}
            return WebGLRenderingContext.prototype.getParameter.call(this, parameter);
        }};
        """
        
        await page.add_init_script(fingerprint_script)


class CaptchaSolver:
    """Handles CAPTCHA detection and solving."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize CAPTCHA solver."""
        self.config = config
        self.logger = logging.getLogger("CaptchaSolver")
    
    async def detect_captcha(self, page: Page) -> Optional[Dict[str, Any]]:
        """Detect if CAPTCHA is present on the page."""
        captcha_selectors = [
            '.captcha',
            '.recaptcha',
            '[data-sitekey]',
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '#captcha',
            '.g-recaptcha'
        ]
        
        for selector in captcha_selectors:
            elements = page.locator(selector)
            if await elements.count() > 0:
                captcha_type = await self._determine_captcha_type(page, selector)
                return {
                    "type": captcha_type,
                    "selector": selector,
                    "element": elements.first
                }
        
        return None
    
    async def _determine_captcha_type(self, page: Page, selector: str) -> str:
        """Determine the type of CAPTCHA."""
        if "recaptcha" in selector.lower():
            return "recaptcha"
        elif "hcaptcha" in selector.lower():
            return "hcaptcha"
        elif "captcha" in selector.lower():
            return "image_captcha"
        else:
            return "unknown"
    
    async def solve_captcha(self, page: Page, captcha_info: Dict[str, Any]) -> bool:
        """Attempt to solve CAPTCHA."""
        captcha_type = captcha_info["type"]
        
        if captcha_type == "recaptcha":
            return await self._solve_recaptcha(page, captcha_info)
        elif captcha_type == "image_captcha":
            return await self._solve_image_captcha(page, captcha_info)
        else:
            self.logger.warning(f"Unsupported CAPTCHA type: {captcha_type}")
            return False
    
    async def _solve_recaptcha(self, page: Page, captcha_info: Dict[str, Any]) -> bool:
        """Handle reCAPTCHA."""
        try:
            # Wait for user to solve CAPTCHA manually
            print("\n🤖 reCAPTCHA detected!")
            print("Please solve the CAPTCHA manually in the browser window.")
            print("Press Enter when you've completed the CAPTCHA...")
            
            input("Waiting for manual CAPTCHA completion...")
            
            # Verify CAPTCHA was solved
            await asyncio.sleep(2)
            captcha_element = page.locator(captcha_info["selector"])
            
            # Check if CAPTCHA is still present
            if await captcha_element.count() == 0:
                self.logger.info("reCAPTCHA solved successfully")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to handle reCAPTCHA: {str(e)}")
            return False
    
    async def _solve_image_captcha(self, page: Page, captcha_info: Dict[str, Any]) -> bool:
        """Handle image-based CAPTCHA."""
        try:
            # Take screenshot of CAPTCHA
            captcha_element = captcha_info["element"]
            captcha_screenshot = await captcha_element.screenshot()
            
            # For now, prompt user to solve manually
            print("\n🖼️ Image CAPTCHA detected!")
            print("Please solve the CAPTCHA manually in the browser window.")
            captcha_solution = input("Enter CAPTCHA text: ").strip()
            
            if captcha_solution:
                # Find and fill CAPTCHA input
                captcha_input = page.locator('input[name*="captcha"], input[placeholder*="captcha"]')
                if await captcha_input.count() > 0:
                    await captcha_input.fill(captcha_solution)
                    
                    # Submit CAPTCHA
                    submit_button = page.locator('button:has-text("Submit"), input[type="submit"]')
                    if await submit_button.count() > 0:
                        await submit_button.click()
                        await asyncio.sleep(2)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to solve image CAPTCHA: {str(e)}")
            return False


class AdvancedMFAHandler:
    """Advanced multi-factor authentication handler."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize MFA handler."""
        self.config = config
        self.logger = logging.getLogger("AdvancedMFAHandler")
        self.available_methods: List[MFAMethod] = []
    
    async def detect_mfa_methods(self, page: Page) -> List[MFAMethod]:
        """Detect available MFA methods on the page."""
        methods = []
        
        # Check for SMS option
        sms_elements = page.locator('text=SMS, text=Text, text=Phone')
        if await sms_elements.count() > 0:
            methods.append(MFAMethod("sms", "phone", is_preferred=True))
        
        # Check for email option
        email_elements = page.locator('text=Email')
        if await email_elements.count() > 0:
            methods.append(MFAMethod("email", "email"))
        
        # Check for authenticator app
        app_elements = page.locator('text=Authenticator, text=Google Authenticator, text=App')
        if await app_elements.count() > 0:
            methods.append(MFAMethod("app", "authenticator"))
        
        # Check for phone call option
        call_elements = page.locator('text=Call, text=Phone call')
        if await call_elements.count() > 0:
            methods.append(MFAMethod("call", "phone"))
        
        self.available_methods = methods
        self.logger.info(f"Detected {len(methods)} MFA methods")
        
        return methods
    
    async def select_mfa_method(self, page: Page, preferred_method: str = "sms") -> Optional[MFAMethod]:
        """Select the preferred MFA method."""
        if not self.available_methods:
            await self.detect_mfa_methods(page)
        
        # Find preferred method
        for method in self.available_methods:
            if method.method_type == preferred_method:
                await self._click_mfa_option(page, method)
                return method
        
        # Fall back to first available method
        if self.available_methods:
            method = self.available_methods[0]
            await self._click_mfa_option(page, method)
            return method
        
        return None
    
    async def _click_mfa_option(self, page: Page, method: MFAMethod) -> None:
        """Click on the selected MFA option."""
        method_selectors = {
            "sms": 'text=SMS, text=Text, label:has-text("SMS")',
            "email": 'text=Email, label:has-text("Email")',
            "app": 'text=Authenticator, text=App, label:has-text("App")',
            "call": 'text=Call, label:has-text("Call")'
        }
        
        selector = method_selectors.get(method.method_type)
        if selector:
            element = page.locator(selector)
            if await element.count() > 0:
                await element.click()
                await asyncio.sleep(1)
    
    async def handle_mfa_with_retry(self, page: Page, max_attempts: int = 3) -> bool:
        """Handle MFA with retry logic."""
        for attempt in range(max_attempts):
            self.logger.info(f"MFA attempt {attempt + 1}/{max_attempts}")
            
            # Detect and select MFA method
            selected_method = await self.select_mfa_method(page)
            if not selected_method:
                self.logger.error("No MFA method available")
                return False
            
            # Handle the selected method
            if await self._handle_method(page, selected_method):
                return True
            
            # Wait before retry
            if attempt < max_attempts - 1:
                await asyncio.sleep(2)
        
        return False
    
    async def _handle_method(self, page: Page, method: MFAMethod) -> bool:
        """Handle specific MFA method."""
        if method.method_type == "sms":
            return await self._handle_sms_mfa(page)
        elif method.method_type == "email":
            return await self._handle_email_mfa(page)
        elif method.method_type == "app":
            return await self._handle_app_mfa(page)
        elif method.method_type == "call":
            return await self._handle_call_mfa(page)
        else:
            return False
    
    async def _handle_sms_mfa(self, page: Page) -> bool:
        """Handle SMS-based MFA."""
        try:
            # Wait for code input field
            code_input = page.locator('input[name*="code"], input[placeholder*="code"]')
            await code_input.wait_for(timeout=10000)
            
            print("\n📱 SMS code requested!")
            print("Please check your phone for the verification code.")
            
            # In a production system, you might:
            # 1. Parse SMS messages automatically
            # 2. Use SMS gateway APIs
            # 3. Integrate with SMS forwarding services
            
            code = input("Enter SMS code: ").strip()
            
            if code and len(code) >= 4:
                await code_input.fill(code)
                
                # Submit code
                submit_button = page.locator('button:has-text("Submit"), button:has-text("Verify")')
                if await submit_button.count() > 0:
                    await submit_button.click()
                    await asyncio.sleep(3)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"SMS MFA failed: {str(e)}")
            return False
    
    async def _handle_email_mfa(self, page: Page) -> bool:
        """Handle email-based MFA."""
        try:
            print("\n📧 Email verification required!")
            print("Please check your email for the verification code.")
            
            code = input("Enter email code: ").strip()
            
            if code:
                code_input = page.locator('input[name*="code"], input[placeholder*="code"]')
                await code_input.fill(code)
                
                submit_button = page.locator('button:has-text("Submit"), button:has-text("Verify")')
                if await submit_button.count() > 0:
                    await submit_button.click()
                    await asyncio.sleep(3)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Email MFA failed: {str(e)}")
            return False
    
    async def _handle_app_mfa(self, page: Page) -> bool:
        """Handle authenticator app MFA."""
        try:
            print("\n📱 Authenticator app verification required!")
            print("Please open your authenticator app and enter the 6-digit code.")
            
            code = input("Enter authenticator code: ").strip()
            
            if code and len(code) == 6 and code.isdigit():
                code_input = page.locator('input[name*="code"], input[placeholder*="code"]')
                await code_input.fill(code)
                
                submit_button = page.locator('button:has-text("Submit"), button:has-text("Verify")')
                if await submit_button.count() > 0:
                    await submit_button.click()
                    await asyncio.sleep(3)
                    return True
            else:
                print("❌ Invalid code format. Authenticator codes are 6 digits.")
            
            return False
            
        except Exception as e:
            self.logger.error(f"App MFA failed: {str(e)}")
            return False
    
    async def _handle_call_mfa(self, page: Page) -> bool:
        """Handle phone call MFA."""
        try:
            print("\n📞 Phone call verification initiated!")
            print("You should receive a phone call with the verification code.")
            
            code = input("Enter the code from the phone call: ").strip()
            
            if code:
                code_input = page.locator('input[name*="code"], input[placeholder*="code"]')
                await code_input.fill(code)
                
                submit_button = page.locator('button:has-text("Submit"), button:has-text("Verify")')
                if await submit_button.count() > 0:
                    await submit_button.click()
                    await asyncio.sleep(3)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Call MFA failed: {str(e)}")
            return False


class SecurityQuestionHandler:
    """Handles security questions during authentication."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize security question handler."""
        self.config = config
        self.logger = logging.getLogger("SecurityQuestionHandler")
        self.known_answers = config.security_question_answers or {}
    
    async def detect_security_question(self, page: Page) -> Optional[str]:
        """Detect if a security question is present."""
        question_selectors = [
            '.security-question',
            '[data-testid="security-question"]',
            'label:has-text("What"), label:has-text("Where"), label:has-text("Who")',
            '.question-text'
        ]
        
        for selector in question_selectors:
            elements = page.locator(selector)
            if await elements.count() > 0:
                question_text = await elements.first.text_content()
                return question_text.strip() if question_text else None
        
        return None
    
    async def answer_security_question(self, page: Page, question: str) -> bool:
        """Answer security question if possible."""
        try:
            # Check if we have a known answer
            answer = self._find_answer(question)
            
            if not answer:
                print(f"\n🔐 Security Question: {question}")
                answer = input("Enter your answer: ").strip()
            
            if answer:
                # Find answer input field
                answer_input = page.locator(
                    'input[name*="answer"], input[placeholder*="answer"], '
                    'input[type="text"]:near(.security-question)'
                )
                
                if await answer_input.count() > 0:
                    await answer_input.fill(answer)
                    
                    # Submit answer
                    submit_button = page.locator('button:has-text("Submit"), button:has-text("Continue")')
                    if await submit_button.count() > 0:
                        await submit_button.click()
                        await asyncio.sleep(2)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to answer security question: {str(e)}")
            return False
    
    def _find_answer(self, question: str) -> Optional[str]:
        """Find answer for known security question."""
        question_lower = question.lower()
        
        for known_question, answer in self.known_answers.items():
            if known_question.lower() in question_lower:
                return answer
        
        # Try partial matching
        for known_question, answer in self.known_answers.items():
            if any(word in question_lower for word in known_question.lower().split()):
                return answer
        
        return None


class RateLimiter:
    """Implements rate limiting for requests."""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """Initialize rate limiter."""
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.logger = logging.getLogger("RateLimiter")
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request)
            
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.requests.append(now)


class RetryHandler:
    """Implements retry logic with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """Initialize retry handler."""
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger("RetryHandler")
    
    async def retry_with_backoff(self, 
                               func: Callable, 
                               *args, 
                               exceptions: tuple = (Exception,),
                               **kwargs) -> Any:
        """Retry function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception
