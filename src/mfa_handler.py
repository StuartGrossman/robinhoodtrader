"""
Enhanced Multi-Factor Authentication Handler for Robinhood Automation

This module provides multiple 2FA solutions:
1. TOTP (Time-based One-Time Password) using authenticator apps
2. SMS parsing capabilities 
3. Email parsing capabilities
4. Manual input fallback

SECURITY NOTE: This is for defensive automation purposes only.
"""

import os
import re
import time
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import pyotp
import imaplib
import email
from email.mime.text import MIMEText
import smtplib

@dataclass
class MFAConfig:
    """Configuration for MFA handling."""
    totp_secret: Optional[str] = None
    sms_email: Optional[str] = None  # Email where SMS forwards go
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_server: str = "imap.gmail.com"
    email_port: int = 993
    backup_codes: Optional[list] = None


class MFAHandler:
    """Handles various 2FA methods for Robinhood automation."""
    
    def __init__(self, config: MFAConfig):
        """Initialize MFA handler with configuration."""
        self.config = config
        self.logger = logging.getLogger("MFAHandler")
        
    async def get_mfa_code(self, method: str = "auto") -> Optional[str]:
        """
        Get MFA code using specified method.
        
        Args:
            method: "totp", "sms", "email", "manual", or "auto"
            
        Returns:
            MFA code string or None if failed
        """
        if method == "auto":
            # Try methods in order of reliability
            methods = ["totp", "sms", "email", "manual"]
            for auto_method in methods:
                if await self._is_method_available(auto_method):
                    code = await self._get_code_by_method(auto_method)
                    if code:
                        return code
            return None
        else:
            return await self._get_code_by_method(method)
    
    async def _is_method_available(self, method: str) -> bool:
        """Check if a specific MFA method is available."""
        if method == "totp":
            return bool(self.config.totp_secret)
        elif method == "sms":
            return bool(self.config.sms_email and self.config.email_username and self.config.email_password)
        elif method == "email":
            return bool(self.config.email_username and self.config.email_password)
        elif method == "manual":
            return True
        return False
    
    async def _get_code_by_method(self, method: str) -> Optional[str]:
        """Get MFA code using specific method."""
        try:
            if method == "totp":
                return self._get_totp_code()
            elif method == "sms":
                return await self._get_sms_code()
            elif method == "email":
                return await self._get_email_code()
            elif method == "manual":
                return self._get_manual_code()
            else:
                self.logger.error(f"Unknown MFA method: {method}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get {method} MFA code: {e}")
            return None
    
    def _get_totp_code(self) -> Optional[str]:
        """Generate TOTP code from secret."""
        if not self.config.totp_secret:
            return None
            
        try:
            totp = pyotp.TOTP(self.config.totp_secret)
            code = totp.now()
            self.logger.info("Generated TOTP code")
            return code
        except Exception as e:
            self.logger.error(f"TOTP generation failed: {e}")
            return None
    
    async def _get_sms_code(self) -> Optional[str]:
        """Parse MFA code from SMS forwarded to email."""
        if not all([self.config.sms_email, self.config.email_username, self.config.email_password]):
            return None
            
        try:
            # Connect to email server
            mail = imaplib.IMAP4_SSL(self.config.email_server, self.config.email_port)
            mail.login(self.config.email_username, self.config.email_password)
            mail.select('inbox')
            
            # Search for recent SMS messages
            search_criteria = f'(FROM "{self.config.sms_email}" UNSEEN)'
            result, message_ids = mail.search(None, search_criteria)
            
            if result != 'OK' or not message_ids[0]:
                self.logger.info("No new SMS messages found")
                mail.logout()
                return None
            
            # Get the most recent message
            latest_message_id = message_ids[0].split()[-1]
            result, message_data = mail.fetch(latest_message_id, '(RFC822)')
            
            if result != 'OK':
                mail.logout()
                return None
            
            # Parse email content
            email_message = email.message_from_bytes(message_data[0][1])
            body = self._get_email_body(email_message)
            
            # Extract MFA code from message
            code = self._extract_mfa_code_from_text(body)
            
            mail.logout()
            
            if code:
                self.logger.info("Successfully extracted MFA code from SMS")
                return code
            else:
                self.logger.warning("Could not extract MFA code from SMS")
                return None
                
        except Exception as e:
            self.logger.error(f"SMS code retrieval failed: {e}")
            return None
    
    async def _get_email_code(self) -> Optional[str]:
        """Parse MFA code from email."""
        if not all([self.config.email_username, self.config.email_password]):
            return None
            
        try:
            # Connect to email server
            mail = imaplib.IMAP4_SSL(self.config.email_server, self.config.email_port)
            mail.login(self.config.email_username, self.config.email_password)
            mail.select('inbox')
            
            # Search for Robinhood verification emails
            search_criteria = '(FROM "noreply@robinhood.com" SUBJECT "verification" UNSEEN)'
            result, message_ids = mail.search(None, search_criteria)
            
            if result != 'OK' or not message_ids[0]:
                self.logger.info("No new Robinhood verification emails found")
                mail.logout()
                return None
            
            # Get the most recent message
            latest_message_id = message_ids[0].split()[-1]
            result, message_data = mail.fetch(latest_message_id, '(RFC822)')
            
            if result != 'OK':
                mail.logout()
                return None
            
            # Parse email content
            email_message = email.message_from_bytes(message_data[0][1])
            body = self._get_email_body(email_message)
            
            # Extract MFA code from message
            code = self._extract_mfa_code_from_text(body)
            
            mail.logout()
            
            if code:
                self.logger.info("Successfully extracted MFA code from email")
                return code
            else:
                self.logger.warning("Could not extract MFA code from email")
                return None
                
        except Exception as e:
            self.logger.error(f"Email code retrieval failed: {e}")
            return None
    
    def _get_manual_code(self) -> Optional[str]:
        """Get MFA code via manual user input."""
        try:
            print("\n🔐 Multi-Factor Authentication Required")
            print("Please check your phone or email for the verification code.")
            
            # Give user some time to receive the code
            for i in range(30, 0, -1):
                print(f"\rWaiting for code... ({i}s) Press Enter when ready.", end="", flush=True)
                time.sleep(1)
            
            print("\n")
            code = input("Enter MFA code: ").strip()
            
            if code and len(code) >= 4:
                return code
            else:
                print("Invalid code format.")
                return None
                
        except Exception as e:
            self.logger.error(f"Manual code input failed: {e}")
            return None
    
    def _get_email_body(self, email_message) -> str:
        """Extract body text from email message."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8')
                    break
        else:
            body = email_message.get_payload(decode=True).decode('utf-8')
        
        return body
    
    def _extract_mfa_code_from_text(self, text: str) -> Optional[str]:
        """Extract MFA code from text using regex patterns."""
        # Common patterns for MFA codes
        patterns = [
            r'\b(\d{6})\b',  # 6-digit code
            r'\b(\d{5})\b',  # 5-digit code
            r'\b(\d{4})\b',  # 4-digit code
            r'code[:\s]+(\d{4,6})',  # "code: 123456"
            r'verification[:\s]+(\d{4,6})',  # "verification: 123456"
            r'your code is[:\s]*(\d{4,6})',  # "your code is 123456"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first match that looks like an MFA code
                for match in matches:
                    if 4 <= len(match) <= 6 and match.isdigit():
                        return match
        
        return None


def create_mfa_config() -> MFAConfig:
    """Create MFAConfig from environment variables."""
    return MFAConfig(
        totp_secret=os.getenv("ROBINHOOD_TOTP_SECRET"),
        sms_email=os.getenv("SMS_FORWARD_EMAIL"),
        email_username=os.getenv("EMAIL_USERNAME"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_server=os.getenv("EMAIL_SERVER", "imap.gmail.com"),
        email_port=int(os.getenv("EMAIL_PORT", "993")),
        backup_codes=os.getenv("ROBINHOOD_BACKUP_CODES", "").split(",") if os.getenv("ROBINHOOD_BACKUP_CODES") else None
    )


# Example usage
async def main():
    """Example usage of MFA handler."""
    config = create_mfa_config()
    handler = MFAHandler(config)
    
    print("Testing MFA handler...")
    
    # Try to get MFA code using automatic method selection
    code = await handler.get_mfa_code("auto")
    
    if code:
        print(f"✅ Got MFA code: {code}")
    else:
        print("❌ Failed to get MFA code")


if __name__ == "__main__":
    asyncio.run(main())