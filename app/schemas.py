"""
Pydantic Request/Response Schemas for URL Shortening API

This module defines data validation schemas for:
- API request bodies (what clients send)
- API response bodies (what server returns)
- Error responses
- Internal data transfer objects

Pydantic provides:
- Automatic request validation (400 Bad Request on validation failure)
- Automatic JSON serialization (models → JSON)
- Automatic OpenAPI/Swagger documentation
- Runtime type checking
- JSON schema generation

All schemas include:
- Field descriptions for API documentation
- Validation rules (min/max length, ranges, patterns)
- Example data for API docs
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, List
from datetime import datetime


# ==================== URL SHORTENING REQUEST/RESPONSE ====================

class CreateURLRequest(BaseModel):
    """
    Request model for creating shortened URLs.
    
    Clients POST this JSON to /api/v1/shorten endpoint
    with URL to shorten and optional customization.
    
    Validation Rules:
    - long_url: 10-2048 characters, must be valid URL format
    - custom_alias: 3-20 alphanumeric chars, optional
    - expiry_days: 0-365 days (0 = never expire), optional
    - user_id: Optional for tracking user quotas
    
    Attributes:
        long_url: Original URL to shorten (required)
                 Must be valid HTTP/HTTPS URL
                 Max 2048 chars to prevent abuse
        custom_alias: User-provided short code (optional)
                     If provided, used as short_code instead of generated one
                     3-20 characters, alphanumeric + hyphen/underscore
        expiry_days: How many days until URL expires (optional)
                    0 or None = URL never expires
                    Default is None (permanent)
        user_id: Optional user identifier (optional)
                Allows tracking which user created URL
                Useful for rate limiting per user
    
    Examples:
        >>> # Basic URL shortening
        >>> request = CreateURLRequest(long_url="https://example.com/very/long/path")
        
        >>> # With custom alias
        >>> request = CreateURLRequest(
        ...     long_url="https://example.com/path",
        ...     custom_alias="mylink"
        ... )
        
        >>> # With expiration
        >>> request = CreateURLRequest(
        ...     long_url="https://example.com/path",
        ...     expiry_days=30  # Expires in 30 days
        ... )
    """
    
    # URL to be shortened - REQUIRED
    long_url: str = Field(
        ...,  # ... means required (no default value)
        description="URL to shorten",
        min_length=10,      # e.g., "http://a.c" (minimum valid URL)
        max_length=2048     # Prevent extremely long URLs
    )
    
    # Custom short code - OPTIONAL
    custom_alias: Optional[str] = Field(
        None,               # None = not provided
        description="Custom short code (optional)",
        min_length=3,       # e.g., "abc"
        max_length=20       # e.g., "my-very-long-alias"
    )
    
    # Expiration time - OPTIONAL
    expiry_days: Optional[int] = Field(
        None,               # None = never expires
        description="Days until URL expires (optional, 0=never)",
        ge=0,               # >= 0
        le=365              # <= 365 (max 1 year)
    )
    
    # User identification - OPTIONAL
    user_id: Optional[int] = Field(
        None,               # None = anonymous
        description="User ID (optional)"
    )
    
    class Config:
        # Example data shown in Swagger/OpenAPI documentation
        json_schema_extra = {
            "example": {
                "long_url": "https://example.com/very/long/path?param=value",
                "custom_alias": "mylink",
                "expiry_days": 30,
                "user_id": 123
            }
        }


class URLResponse(BaseModel):
    """
    Response model for successfully created short URL.
    
    Server returns this JSON after POST /api/v1/shorten
    with all details about the newly shortened URL.
    
    Attributes:
        short_code: Generated short code (Base62 encoded)
                   Unique identifier for this URL
                   Format: 6-10 alphanumeric characters
        short_url: Full short URL (domain + code)
                  Format: "https://short.url/abc123"
                  What the user actually shares
        long_url: Original URL being shortened
                 What users get redirected to
        created_at: ISO 8601 timestamp when URL was created
                   Format: "2026-02-22T10:30:00"
        expires_at: ISO 8601 expiration timestamp (if applicable)
                   None/null = never expires
    
    Examples:
        >>> response = URLResponse(
        ...     short_code="abc123",
        ...     short_url="https://short.url/abc123",
        ...     long_url="https://example.com/very/long/path",
        ...     created_at="2026-02-22T10:30:00",
        ...     expires_at="2026-03-24T10:30:00"  # 30 days later
        ... )
    """
    
    short_code: str = Field(
        ...,
        description="Generated short code"
    )
    
    short_url: str = Field(
        ...,
        description="Full short URL"
    )
    
    long_url: str = Field(
        ...,
        description="Original long URL"
    )
    
    created_at: str = Field(
        ...,
        description="Creation timestamp (ISO 8601)"
    )
    
    expires_at: Optional[str] = Field(
        None,
        description="Expiration timestamp (ISO 8601, null if never)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "short_code": "abc123",
                "short_url": "https://short.url/abc123",
                "long_url": "https://example.com/very/long/path",
                "created_at": "2026-02-22T10:30:00",
                "expires_at": "2026-03-24T10:30:00"
            }
        }


# ==================== ANALYTICS & STATISTICS ====================

class ClickStats(BaseModel):
    """
    Click statistics summary for a URL.
    
    Shows high-level click metrics useful for quick dashboard views.
    
    Attributes:
        total_clicks: All-time total clicks on this URL
        clicks_today: Clicks in current calendar day (UTC)
        clicks_by_day: Dictionary mapping date → click count
                      Format: {"2026-02-22": 250, "2026-02-21": 350}
    """
    
    total_clicks: int = Field(
        ...,
        description="Total number of clicks (all-time)"
    )
    
    clicks_today: int = Field(
        ...,
        description="Clicks in current day (UTC)"
    )
    
    # Dictionary with date strings as keys, counts as values
    # Example: {"2026-02-22": 250, "2026-02-21": 350}
    clicks_by_day: Dict[str, int] = Field(
        ...,
        description="Clicks grouped by date"
    )


class URLStatsResponse(BaseModel):
    """
    Complete statistics response for a single URL.
    
    Server returns this JSON from GET /api/v1/stats/{short_code}
    with full URL details and click analytics.
    
    Attributes:
        short_code: The short code for this URL
        long_url: Original URL being tracked
        created_at: When URL was shortened
        total_clicks: All-time click count
        clicks_today: Clicks in current day
        clicks_by_day: Click breakdown by date
        is_custom: Whether user provided custom alias
        expires_at: Expiration timestamp (null = never)
    
    Examples:
        >>> stats = URLStatsResponse(
        ...     short_code="abc123",
        ...     long_url="https://example.com/path",
        ...     created_at="2026-02-22T10:30:00",
        ...     total_clicks=5000,
        ...     clicks_today=250,
        ...     clicks_by_day={"2026-02-22": 250, "2026-02-21": 350},
        ...     is_custom=False,
        ...     expires_at=None
        ... )
    """
    
    short_code: str = Field(..., description="Short code")
    
    long_url: str = Field(..., description="Original URL")
    
    created_at: str = Field(..., description="Creation timestamp")
    
    total_clicks: int = Field(..., description="Total clicks (all-time)")
    
    clicks_today: int = Field(..., description="Clicks in current day")
    
    # Dictionary breakdown: {"2026-02-22": 250, "2026-02-21": 350, ...}
    clicks_by_day: Dict[str, int] = Field(..., description="Clicks per day")
    
    is_custom: bool = Field(..., description="Custom alias flag")
    
    expires_at: Optional[str] = Field(..., description="Expiration timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "short_code": "abc123",
                "long_url": "https://example.com/path",
                "created_at": "2026-02-22T10:30:00",
                "total_clicks": 5000,
                "clicks_today": 250,
                "clicks_by_day": {
                    "2026-02-22": 250,
                    "2026-02-21": 350,
                    "2026-02-20": 200
                },
                "is_custom": False,
                "expires_at": None
            }
        }


# ==================== URL MANAGEMENT ====================

class URLInfo(BaseModel):
    """
    Compact URL information.
    
    Used in list responses to show summary of each URL.
    Contains essential info without full analytics.
    
    Attributes:
        short_code: The short code
        long_url: Original URL
        total_clicks: Click count
        created_at: Creation timestamp
        expires_at: Expiration timestamp (if any)
        is_custom: Whether custom alias
    """
    
    short_code: str = Field(..., description="Short code")
    
    long_url: str = Field(..., description="Original URL")
    
    total_clicks: int = Field(..., description="Total clicks")
    
    created_at: str = Field(..., description="Creation timestamp")
    
    expires_at: Optional[str] = Field(..., description="Expiration timestamp")
    
    is_custom: bool = Field(..., description="Custom alias flag")


class URLListResponse(BaseModel):
    """
    Response model for listing multiple URLs.
    
    Server returns this JSON from GET /api/v1/urls
    with list of URLs created by user.
    
    Attributes:
        urls: List of URLInfo objects
        count: Number of URLs in response
    
    Examples:
        >>> response = URLListResponse(
        ...     urls=[
        ...         URLInfo(
        ...             short_code="abc123",
        ...             long_url="https://example.com/path1",
        ...             total_clicks=5000,
        ...             created_at="2026-02-22T10:30:00",
        ...             expires_at=None,
        ...             is_custom=False
        ...         )
        ...     ],
        ...     count=1
        ... )
    """
    
    # List of URL summaries
    urls: List[URLInfo] = Field(..., description="List of URLs")
    
    # Number of URLs in this response
    count: int = Field(..., description="Number of URLs returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "urls": [
                    {
                        "short_code": "abc123",
                        "long_url": "https://example.com/path1",
                        "total_clicks": 5000,
                        "created_at": "2026-02-22T10:30:00",
                        "expires_at": None,
                        "is_custom": False
                    }
                ],
                "count": 1
            }
        }


# ==================== SYSTEM MONITORING ====================

class HealthResponse(BaseModel):
    """
    Health check response showing system status.
    
    Server returns this JSON from GET /health endpoint
    indicating if all components are operational.
    
    Component Status Values:
    - "healthy": Component is working normally
    - "degraded": Component working but with issues
    - "unhealthy": Component is down or not working
    
    Attributes:
        status: Overall system status (combining all components)
        database: Database connection status
        cache: Redis/cache connection status
        timestamp: When this check was performed
    """
    
    status: str = Field(
        ...,
        description="Overall status (healthy/degraded/unhealthy)"
    )
    
    database: str = Field(
        ...,
        description="Database status (healthy/unhealthy)"
    )
    
    cache: str = Field(
        ...,
        description="Cache status (healthy/unhealthy)"
    )
    
    timestamp: str = Field(
        ...,
        description="Check timestamp (ISO 8601)"
    )


class StatsResponse(BaseModel):
    """
    Service-level statistics and metrics.
    
    Server returns this JSON from GET /api/v1/stats endpoint
    with overall service metrics and cache info.
    
    Attributes:
        total_urls: Total number of shortened URLs ever created
        total_clicks: Total number of clicks recorded across all URLs
        urls_created_today: URLs created in current day (UTC)
        cache: Dictionary with cache statistics
        timestamp: When stats were collected
    """
    
    total_urls: int = Field(
        ...,
        description="Total URLs created"
    )
    
    total_clicks: int = Field(
        ...,
        description="Total clicks recorded"
    )
    
    urls_created_today: int = Field(
        ...,
        description="URLs created in current day"
    )
    
    # Cache stats: keys, bytes used, hits, misses, etc.
    cache: Dict = Field(
        ...,
        description="Cache statistics (keys, hits, misses, etc.)"
    )
    
    timestamp: str = Field(
        ...,
        description="Stats collection timestamp"
    )


# ==================== ERROR RESPONSES ====================

class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Server returns this JSON on any error with HTTP status code.
    Returned by exception handlers with appropriate status codes.
    
    Attributes:
        detail: Human-readable error message
        status_code: HTTP status code (400, 404, 429, 500, etc.)
    
    Common Status Codes:
    - 400: Bad Request (validation failed)
    - 404: Not Found (URL doesn't exist)
    - 429: Too Many Requests (rate limited)
    - 500: Internal Server Error
    
    Examples:
        >>> error = ErrorResponse(
        ...     detail="Short URL not found",
        ...     status_code=404
        ... )
        
        >>> error = ErrorResponse(
        ...     detail="Rate limit exceeded: 1000 requests per minute",
        ...     status_code=429
        ... )
    """
    
    detail: str = Field(
        ...,
        description="Error message"
    )
    
    status_code: int = Field(
        ...,
        description="HTTP status code"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Short URL not found",
                "status_code": 404
            }
        }

