"""
Utility Functions for URL Shortening Service

This module provides essential utility functions for:
- Base62 encoding/decoding for compact URL codes
- URL and alias validation
- Expiry time management
- Analytics data preparation
- IP address hashing for privacy

Base62 Encoding:
- Supports 62 characters (0-9, a-z, A-Z)
- 6-character code supports ~56 billion unique URLs
- More compact than Base64 (which includes +, /, =)
"""

import string
import random
from datetime import datetime, timedelta
from typing import Tuple
import hashlib
import re


# ==================== BASE62 CONFIGURATION ====================
# Base62 alphabet for encoding: digits + lowercase + uppercase
BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


# ==================== BASE62 ENCODING/DECODING ====================
def base62_encode(num: int) -> str:
    """
    Encode an integer to Base62 string.
    
    Base62 supports 62^6 = ~56 billion unique URLs with 6 characters.
    Used to convert sequential IDs into compact, user-friendly short codes.
    
    Algorithm:
    1. Repeatedly divide number by 62
    2. Map remainder to Base62 character
    3. Reverse the result
    
    Args:
        num: Integer to encode (typically a database ID)
        
    Returns:
        Base62 encoded string (compact and URL-safe)
        
    Examples:
        >>> base62_encode(0)
        '0'
        >>> base62_encode(62)
        '10'
        >>> base62_encode(3843)
        'zz'
    """
    if num == 0:
        return BASE62_ALPHABET[0]
    
    encoded = []
    while num > 0:
        encoded.append(BASE62_ALPHABET[num % 62])
        num //= 62
    
    return ''.join(reversed(encoded))


def base62_decode(code: str) -> int:
    """
    Decode a Base62 string to integer.
    
    Reverse of base62_encode - converts compact short code back to ID.
    
    Algorithm:
    1. For each character, find its value in alphabet
    2. Shift previous result by 62 and add character value
    
    Args:
        code: Base62 encoded string
        
    Returns:
        Decoded integer (original ID)
        
    Examples:
        >>> base62_decode('0')
        0
        >>> base62_decode('10')
        62
        >>> base62_decode('zz')
        3843
    """
    num = 0
    for char in code:
        num = num * 62 + BASE62_ALPHABET.index(char)
    return num


# ==================== SHORT CODE GENERATION ====================
def generate_short_code(length: int = 6) -> str:
    """
    Generate a random short code using Base62 alphabet.
    
    Unlike sequential encoding, this generates random codes directly.
    Useful for non-sequential short codes or fallback generation.
    
    Args:
        length: Length of the short code (default: 6)
        
    Returns:
        Random short code of specified length
        
    Note:
        With 6 characters and 62 options per character:
        62^6 = 56,800,235,584 possible combinations
        At 10M new URLs/day, would take ~15,589 years to exhaust
    """
    return ''.join(random.choices(BASE62_ALPHABET, k=length))


# ==================== URL VALIDATION ====================
def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate if a URL is properly formatted.
    
    Checks for:
    - Non-empty URL
    - Reasonable length (2048 chars max)
    - Valid HTTP/HTTPS protocol
    - Proper URL structure
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - If valid: (True, "")
        - If invalid: (False, error message explaining why)
        
    Examples:
        >>> validate_url("https://example.com")
        (True, '')
        >>> validate_url("invalid")
        (False, 'Invalid URL format. Must start with http:// or https://')
    """
    # Check if URL is empty
    if not url:
        return False, "URL cannot be empty"
    
    # Check maximum length (prevent extremely long URLs)
    if len(url) > 2048:
        return False, "URL exceeds maximum length of 2048 characters"
    
    # Validate URL format using regex pattern
    # Requires: http:// or https:// followed by valid URL characters
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(url_pattern, url):
        return False, "Invalid URL format. Must start with http:// or https://"
    
    return True, ""


# ==================== CUSTOM ALIAS VALIDATION ====================
def validate_custom_alias(alias: str, min_length: int = 3, max_length: int = 20) -> Tuple[bool, str]:
    """
    Validate custom short code alias.
    
    Ensures custom aliases meet requirements:
    - Length constraints
    - Only alphanumeric + hyphens + underscores
    - No special characters or spaces
    
    Args:
        alias: Custom alias string to validate
        min_length: Minimum allowed length (default: 3)
        max_length: Maximum allowed length (default: 20)
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        
    Examples:
        >>> validate_custom_alias("mylink")
        (True, '')
        >>> validate_custom_alias("my@link")
        (False, 'Alias can only contain alphanumeric characters...')
    """
    # Check if alias is empty
    if not alias:
        return False, "Alias cannot be empty"
    
    # Check minimum length
    if len(alias) < min_length:
        return False, f"Alias must be at least {min_length} characters"
    
    # Check maximum length
    if len(alias) > max_length:
        return False, f"Alias must not exceed {max_length} characters"
    
    # Check allowed characters (alphanumeric, hyphens, underscores only)
    if not re.match(r'^[a-zA-Z0-9_-]+$', alias):
        return False, "Alias can only contain alphanumeric characters, hyphens, and underscores"
    
    return True, ""


# ==================== EXPIRY & TTL MANAGEMENT ====================
def is_url_expired(expires_at: datetime) -> bool:
    """
    Check if a URL has expired.
    
    Compares expiration datetime with current time to determine
    if a short URL should still be accessible.
    
    Args:
        expires_at: Expiration datetime (None means never expires)
        
    Returns:
        True if expired and should be rejected, False otherwise
        
    Note:
        URLs with expires_at=None are treated as permanent
    """
    if expires_at is None:
        return False  # No expiry = never expires
    
    return datetime.utcnow() > expires_at


def calculate_expiry_time(expiry_days: int = 0) -> datetime:
    """
    Calculate expiration datetime from days offset.
    
    Converts number of days into an absolute expiration timestamp.
    Used when creating URLs with TTL.
    
    Args:
        expiry_days: Number of days until expiration (0 = never expires)
        
    Returns:
        Expiration datetime or None if never expires
        
    Examples:
        >>> calc = calculate_expiry_time(30)  # 30 days from now
        >>> calc > datetime.utcnow()
        True
    """
    if expiry_days <= 0:
        return None  # No expiry
    
    return datetime.utcnow() + timedelta(days=expiry_days)


# ==================== ANALYTICS DATA PREPARATION ====================
def hash_ip_address(ip_address: str) -> str:
    """
    Hash IP address for privacy protection.
    
    One-way hashing allows tracking patterns without storing
    actual IP addresses, improving user privacy.
    
    Args:
        ip_address: IP address string to hash
        
    Returns:
        SHA256 hash of IP address (truncated to 16 chars)
    """
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]


def get_user_agent_summary(user_agent: str, max_length: int = 200) -> str:
    """
    Truncate user agent string for storage.
    
    User agent strings can be very long (500+ characters).
    Truncate to reasonable length while preserving essential info.
    
    Args:
        user_agent: Full user agent string
        max_length: Maximum length to store (default: 200)
        
    Returns:
        Truncated user agent
    """
    if not user_agent:
        return "Unknown"
    
    return user_agent[:max_length]


# ==================== URL FORMATTING ====================
def format_short_url(short_code: str, domain: str = "https://short.url") -> str:
    """
    Format complete short URL from code and domain.
    
    Combines the domain with the short code to create the full URL
    that will be returned to users.
    
    Args:
        short_code: Short code part (e.g., "abc123")
        domain: Domain name (e.g., "https://short.url")
        
    Returns:
        Complete short URL (e.g., "https://short.url/abc123")
    """
    return f"{domain}/{short_code}"

