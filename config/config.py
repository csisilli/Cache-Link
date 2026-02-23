"""
Application Configuration Management

This module handles all application settings using Pydantic BaseSettings.
Settings are loaded from environment variables (.env file) with sensible defaults.

Environment Priority:
1. Environment variables (highest priority)
2. .env file
3. Default values defined here (lowest priority)

Usage:
    from config.config import settings
    db_url = settings.DATABASE_URL
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application configuration settings.
    
    All settings can be overridden via environment variables.
    Example: DATABASE_URL=mysql://... python app/main.py
    """
    
    # ==================== DATABASE CONFIGURATION ====================
    # MySQL/PostgreSQL connection settings
    DATABASE_URL: str = "mysql://root:password@localhost:3306/shortener"
    DB_POOL_SIZE: int = 20  # Number of connections to keep in pool
    DB_MAX_OVERFLOW: int = 40  # Additional connections beyond pool size
    DB_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    
    # ==================== REDIS CACHE CONFIGURATION ====================
    # Redis connection for caching layer
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ==================== APPLICATION SETTINGS ====================
    SECRET_KEY: str = "your_super_secret_key_change_this_in_production"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # ==================== CACHE SETTINGS ====================
    CACHE_TTL: int = 2592000  # 30 days in seconds - default TTL for cached URLs
    HOT_URL_THRESHOLD: int = 100  # URLs with >100 clicks get aggressive caching
    
    # ==================== RATE LIMITING ====================
    # Token bucket algorithm rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 1000  # Max requests per window
    RATE_LIMIT_WINDOW: int = 60  # Time window in seconds (1 minute)
    
    # ==================== URL CONFIGURATION ====================
    DEFAULT_EXPIRY_DAYS: int = 0  # 0 = URLs never expire
    MAX_EXPIRY_DAYS: int = 365  # Maximum expiry allowed
    SHORT_CODE_LENGTH: int = 6  # Default length of generated short codes
    CUSTOM_CODE_MIN_LENGTH: int = 3  # Minimum length for custom aliases
    CUSTOM_CODE_MAX_LENGTH: int = 20  # Maximum length for custom aliases
    
    # ==================== ANALYTICS ====================
    ANALYTICS_BATCH_SIZE: int = 1000  # Batch size for analytics operations
    ANALYTICS_FLUSH_INTERVAL: int = 300  # Flush analytics every 5 minutes
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    class Config:
        # Load settings from .env file in project root
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses LRU cache to avoid re-parsing .env file on every request.
    This is more efficient than creating new Settings instance each time.
    
    Returns:
        Settings instance (cached after first call)
    """
    return Settings()


# Create default settings instance (used throughout the app)
settings = get_settings()

