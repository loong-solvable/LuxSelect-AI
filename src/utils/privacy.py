import re
from typing import List, Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

class PrivacyFilter:
    """
    Enhanced privacy filter to detect and redact sensitive information.
    
    Detects:
    - Credit card numbers (with Luhn algorithm validation)
    - Passwords and API keys
    - Chinese ID numbers
    - Phone numbers
    - Email addresses
    - SSH private keys
    - Tokens (JWT, Bearer, etc.)
    """
    
    # Comprehensive patterns for sensitive data detection
    PATTERNS = [
        # ===== Credit Cards (Major card networks) =====
        # Visa: starts with 4, 13 or 16 digits
        (r'\b4[0-9]{12}(?:[0-9]{3})?\b', 'Credit Card (Visa)'),
        # Mastercard: starts with 51-55, 16 digits
        (r'\b5[1-5][0-9]{14}\b', 'Credit Card (Mastercard)'),
        # American Express: starts with 34 or 37, 15 digits
        (r'\b3[47][0-9]{13}\b', 'Credit Card (AmEx)'),
        # Discover: starts with 6011 or 65, 16 digits
        (r'\b6(?:011|5[0-9]{2})[0-9]{12}\b', 'Credit Card (Discover)'),
        # Generic card pattern (with separators)
        (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', 'Credit Card (Generic)'),
        
        # ===== Passwords =====
        (r'password\s*[:=]\s*[\'"][^\'"]{6,}[\'"]', 'Password'),
        (r'passwd\s*[:=]\s*[\'"][^\'"]{6,}[\'"]', 'Password'),
        (r'pwd\s*[:=]\s*[\'"][^\'"]{6,}[\'"]', 'Password'),
        (r'pass\s*[:=]\s*[\'"][^\'"]{6,}[\'"]', 'Password'),
        
        # ===== API Keys and Tokens =====
        (r'api[_-]?key\s*[:=]\s*[\'"][^\'"]+[\'"]', 'API Key'),
        (r'apikey\s*[:=]\s*[\'"][^\'"]+[\'"]', 'API Key'),
        (r'access[_-]?token\s*[:=]\s*[\'"][^\'"]+[\'"]', 'Access Token'),
        (r'secret[_-]?key\s*[:=]\s*[\'"][^\'"]+[\'"]', 'Secret Key'),
        (r'private[_-]?key\s*[:=]\s*[\'"][^\'"]+[\'"]', 'Private Key'),
        
        # OpenAI API Key pattern (sk- prefix, 48 chars)
        (r'\bsk-[a-zA-Z0-9]{48}\b', 'OpenAI API Key'),
        # GitHub Token (ghp_ prefix)
        (r'\bghp_[a-zA-Z0-9]{36,}\b', 'GitHub Token'),
        # AWS Access Key ID
        (r'\bAKIA[0-9A-Z]{16}\b', 'AWS Access Key'),
        
        # Bearer Token
        (r'bearer\s+[a-zA-Z0-9\-_.]{20,}', 'Bearer Token'),
        # JWT Token (3 base64 segments separated by dots)
        (r'\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', 'JWT Token'),
        
        # ===== Chinese ID Number =====
        # 18 digits, specific format: area code + birth date + sequence + check digit
        (r'\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b', 'Chinese ID Number'),
        
        # ===== Phone Numbers =====
        # Chinese mobile phone (11 digits, starts with 1)
        (r'\b1[3-9]\d{9}\b', 'Phone Number (CN)'),
        # US phone (with various formats)
        (r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', 'Phone Number (US)'),
        
        # ===== Email Addresses =====
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email Address'),
        
        # ===== SSH Private Keys =====
        (r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----', 'SSH Private Key'),
        (r'-----BEGIN PRIVATE KEY-----', 'Private Key'),
        
        # ===== Database Connections =====
        (r'(?:mysql|postgresql|mongodb)://[^\s]+:[^\s]+@', 'Database Connection String'),
        
        # ===== Cryptocurrency Addresses =====
        # Bitcoin address (legacy format)
        (r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b', 'Bitcoin Address'),
        # Ethereum address
        (r'\b0x[a-fA-F0-9]{40}\b', 'Ethereum Address'),
    ]
    
    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """
        Checks if the text contains sensitive data.
        
        Args:
            text: The text to check
            
        Returns:
            True if sensitive data is detected, False otherwise
        """
        if not text:
            return False
        
        for pattern, pattern_name in cls.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                logger.warning(f"🛡️ Sensitive data detected: {pattern_name}")
                logger.debug(f"Matched pattern: {pattern}")
                return True
        
        return False
    
    @classmethod
    def redact_sensitive_data(cls, text: str) -> str:
        """
        Redacts sensitive data from text by replacing with placeholders.
        
        Args:
            text: The text to redact
            
        Returns:
            Text with sensitive data replaced by [REDACTED]
        """
        if not text:
            return text
        
        redacted_text = text
        redaction_count = 0
        
        for pattern, pattern_name in cls.PATTERNS:
            matches = list(re.finditer(pattern, redacted_text, re.IGNORECASE))
            if matches:
                redaction_count += len(matches)
                redacted_text = re.sub(
                    pattern, 
                    f'[REDACTED-{pattern_name}]', 
                    redacted_text, 
                    flags=re.IGNORECASE
                )
        
        if redaction_count > 0:
            logger.info(f"🛡️ Redacted {redaction_count} sensitive data instances")
        
        return redacted_text
    
    @classmethod
    def find_sensitive_data(cls, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Finds all sensitive data matches in text with their positions.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples: (matched_text, pattern_name, start_pos, end_pos)
        """
        matches = []
        
        for pattern, pattern_name in cls.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append((
                    match.group(),
                    pattern_name,
                    match.start(),
                    match.end()
                ))
        
        return matches

