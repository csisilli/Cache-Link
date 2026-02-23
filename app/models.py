"""
Database Models for URL Shortening Service

This module defines SQLAlchemy ORM models for data persistence:
- URLRecord: Core model for shortened URLs and metadata
- ClickRecord: Analytics data for tracking URL access patterns
- RateLimitRecord: Rate limiting state tracking per IP address

Key Features:
- Automatic timestamps for audit trails
- Efficient indexing on frequently queried fields
- Relationship support for normalized data structure
- Connection pooling for high-concurrency scenarios
- Session factory for FastAPI dependency injection

Database URL Format:
- MySQL: mysql+pymysql://user:password@host/database
- PostgreSQL: postgresql://user:password@host/database
"""

from sqlalchemy import (
    create_engine, Column, BigInteger, String, DateTime, Integer, Boolean, 
    Index, ForeignKey, Text, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Base class for all ORM models - provides declarative mapping
Base = declarative_base()


class URLRecord(Base):
    """
    Core model for storing shortened URL mappings.
    
    Stores the relationship between short codes and original long URLs,
    along with metadata about creation, expiration, and access patterns.
    
    This is the central record in the system - every shortened URL creates
    one URLRecord instance that persists in the database.
    
    Attributes:
        id: Primary key - unique auto-incremented identifier
        short_code: Unique short code (Base62 encoded or custom)
                   Indexed for O(1) lookup during redirects
                   This is the most frequently queried field
        long_url: Original URL being shortened (max 2048 chars)
        user_id: Optional user ID if authentication is implemented
                 Allows tracking URLs created by specific users
        created_at: Timestamp when URL was shortened
                   Indexed for sorting and time-range queries
        expires_at: Optional expiration datetime
                   If set, URL becomes inactive after this time
                   Indexed for cleanup queries
        clicks: Total number of times URL was accessed
               Denormalized counter (incremented on each redirect)
               Much faster than counting ClickRecord rows
        is_custom: Boolean flag indicating custom alias was used
                  True if user provided custom short_code
    
    Relationships:
        click_records: One-to-many relationship with ClickRecord
                      When URLRecord is deleted, all ClickRecords are deleted
                      (cascade="all, delete-orphan")
    
    Indexes:
        - idx_short_code: Primary lookup index for redirects
        - idx_user_id: Find all URLs by specific user
        - idx_created_at: Sort/filter by creation time
        - idx_expires_at: Find expired URLs for cleanup
    
    Examples:
        >>> record = URLRecord(
        ...     short_code='abc123',
        ...     long_url='https://example.com/very/long/url',
        ...     user_id=42,
        ...     is_custom=False
        ... )
        >>> session.add(record)
        >>> session.commit()
    """
    __tablename__ = "urls"
    
    # ========== PRIMARY KEY ==========
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # ========== CORE FIELDS ==========
    # Short code - the key part of short URL (e.g., "abc123" in short.url/abc123)
    # UNIQUE constraint prevents duplicate short codes
    # INDEX for fast lookups (most common operation)
    short_code = Column(String(10), unique=True, nullable=False, index=True)
    
    # Original long URL being shortened
    # VARCHAR(2048) max to support long URLs but prevent abuse
    long_url = Column(String(2048), nullable=False)
    
    # ========== OPTIONAL FIELDS ==========
    # User ID for multi-tenant support or user analytics
    # NULL if not using authentication
    # INDEXED for finding all URLs by user
    user_id = Column(BigInteger, index=True)
    
    # ========== TIMESTAMP FIELDS ==========
    # When was this URL shortened (creation time)
    # INDEXED for time-range queries and sorting
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # When does this URL expire (optional)
    # NULL = never expires
    # INDEXED for cleanup queries (find expired URLs)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # ========== ANALYTICS FIELDS ==========
    # Total click count - denormalized for performance
    # Incremented on each redirect rather than counting clicks table
    clicks = Column(Integer, default=0)
    
    # Whether this URL uses custom alias
    # True = user provided custom short_code
    # False = auto-generated short_code
    is_custom = Column(Boolean, default=False)
    
    # ========== RELATIONSHIPS ==========
    # One URLRecord can have many ClickRecords
    # cascade="all, delete-orphan" ensures click records are deleted with URL
    click_records = relationship("ClickRecord", back_populates="url", cascade="all, delete-orphan")
    
    # ========== INDEXES ==========
    # Multi-field and single-field indexes for common query patterns
    __table_args__ = (
        # Primary index for redirect lookups (GET /{short_code})
        Index('idx_short_code', 'short_code'),
        # Find all URLs by specific user (user analytics)
        Index('idx_user_id', 'user_id'),
        # Time-series queries (newest URLs, date filtering)
        Index('idx_created_at', 'created_at'),
        # Cleanup queries (find and delete expired URLs)
        Index('idx_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        """String representation for logging and debugging"""
        return f"<URLRecord(short_code='{self.short_code}', long_url='{self.long_url[:50]}...')>"
    
    def to_dict(self) -> dict:
        """
        Convert URLRecord to dictionary (JSON serializable).
        
        Used when returning URL data in API responses.
        Converts datetime objects to ISO format strings.
        
        Returns:
            Dictionary with all URL information
        """
        return {
            'id': self.id,
            'short_code': self.short_code,
            'long_url': self.long_url,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'clicks': self.clicks,
            'is_custom': self.is_custom
        }


class ClickRecord(Base):
    """
    Analytics model for tracking individual URL access events.
    
    Records detailed information about each time a shortened URL is accessed.
    These records enable:
    - Analytics dashboards (clicks over time, referrers, devices)
    - User behavior analysis
    - Bot detection and spam prevention
    - Geographic/device distribution reporting
    
    With 1M+ daily clicks, this table can grow large.
    Consider:
    - Time-based partitioning in production
    - Archiving old records (>6 months) to cold storage
    - Aggregating to ClickStats table for faster queries
    
    Attributes:
        id: Primary key - unique auto-incremented ID
        short_code: Foreign key reference to URLRecord.short_code
                   Links click event to specific shortened URL
                   Indexed for fast lookup of all clicks for a URL
        ip_address: Client IP address (IPv4 or IPv6)
                   Supports full IPv6 addresses (45 chars max)
                   Can be hashed/anonymized for privacy
        user_agent: Full User-Agent HTTP header
                   Identifies browser, OS, device
                   Can be parsed to extract browser/device info
        referrer: HTTP Referer header
                 Shows what page/site led user to short URL
                 Useful for traffic source analysis
        clicked_at: Timestamp when click occurred
                   Indexed for time-range queries and sorting
    
    Relationships:
        url: Many-to-one relationship with URLRecord
            When URLRecord is deleted, this record is also deleted
    
    Indexes:
        - idx_short_code_click: Find all clicks for a specific URL
        - idx_clicked_at: Time-series queries (last 24 hours, etc.)
        - idx_short_code_clicked_at: Combined index for analytics queries
    
    Examples:
        >>> record = ClickRecord(
        ...     short_code='abc123',
        ...     ip_address='192.168.1.1',
        ...     user_agent='Mozilla/5.0...',
        ...     referrer='https://twitter.com',
        ... )
        >>> session.add(record)
        >>> session.commit()
    """
    __tablename__ = "clicks"
    
    # ========== PRIMARY KEY ==========
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # ========== FOREIGN KEY ==========
    # Reference to URLRecord that was accessed
    # ON CASCADE DELETE ensures clicks are removed if URL is deleted
    # VARCHAR(10) matches URLRecord.short_code field
    short_code = Column(String(10), ForeignKey('urls.short_code'), nullable=False, index=True)
    
    # ========== CLIENT INFORMATION ==========
    # Client IP address (either IPv4 or IPv6)
    # VARCHAR(45) supports full IPv6 address length
    # Can be NULL if client IP not captured
    ip_address = Column(String(45))
    
    # User-Agent HTTP header from browser/client
    # Identifies browser type, version, OS
    # Examples: 
    #   - "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
    #   - "Mobile Safari 14.1.1..."
    # Can be parsed to extract device type, browser, etc.
    user_agent = Column(String(500))
    
    # HTTP Referer header (note: "Referer" is correct per HTTP spec)
    # Shows which website/page linked to the short URL
    # Examples: "https://twitter.com", "https://reddit.com/r/python"
    # Useful for understanding traffic sources
    referrer = Column(String(2048))
    
    # ========== TIMESTAMP ==========
    # When this click event occurred
    # INDEXED for time-series queries
    # Used to find clicks in specific time windows
    clicked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # ========== RELATIONSHIPS ==========
    # Many ClickRecords belong to one URLRecord
    # This relationship links back to the URL that was accessed
    url = relationship("URLRecord", back_populates="click_records")
    
    # ========== INDEXES ==========
    # Optimized for common analytics queries
    __table_args__ = (
        # Find all clicks for a specific URL
        # Query: session.query(ClickRecord).filter_by(short_code='abc123')
        Index('idx_short_code_click', 'short_code'),
        # Time-series queries (clicks in last 24 hours, specific date range)
        # Query: session.query(ClickRecord).filter(ClickRecord.clicked_at >= start_time)
        Index('idx_clicked_at', 'clicked_at'),
        # Combined index for analytics (all clicks for URL in time range)
        # Query: ...filter_by(short_code='abc123').filter(clicked_at >= start)
        Index('idx_short_code_clicked_at', 'short_code', 'clicked_at'),
    )
    
    def __repr__(self) -> str:
        """String representation for logging and debugging"""
        return f"<ClickRecord(short_code='{self.short_code}', clicked_at='{self.clicked_at}')>"
    
    def to_dict(self) -> dict:
        """
        Convert ClickRecord to dictionary (JSON serializable).
        
        Used when returning click analytics in API responses.
        Converts datetime objects to ISO format strings.
        
        Returns:
            Dictionary with click information
        """
        return {
            'id': self.id,
            'short_code': self.short_code,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'referrer': self.referrer,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None
        }


class RateLimitRecord(Base):
    """
    Rate limiting state model for tracking API usage per IP address.
    
    Implements token bucket rate limiting algorithm:
    - Each IP address gets a bucket with maximum tokens
    - Each API request consumes tokens
    - Tokens regenerate over time at fixed rate
    - When bucket is empty, requests are rejected (HTTP 429)
    
    Token Bucket Algorithm Explanation:
    1. Max tokens = 1000 per IP address per window
    2. Requests consume 1 token each
    3. At 1000 req/min max rate, tokens = 1000 * (time_elapsed / 60)
    4. When new request arrives, calculate refill and check if tokens available
    5. If tokens > 0: allow request, tokens -= 1
    6. If tokens <= 0: reject request, return 429 Too Many Requests
    
    Advantages over fixed window:
    - Smooth rate limiting (not burst-based)
    - Prevents traffic spikes
    - Fair to long-running clients
    
    Attributes:
        id: Primary key
        ip_address: Client IP address being rate limited
                   UNIQUE constraint ensures one record per IP
        request_count: Total requests from this IP (all-time counter)
        window_start: When current token bucket window started
                     Used to calculate token regeneration
    
    Indexes:
        - idx_ip_address: Fast lookup of rate limit state for IP
        - idx_window_start: Find and cleanup old windows
    
    Examples:
        >>> record = RateLimitRecord(
        ...     ip_address='192.168.1.1',
        ...     request_count=100,
        ...     window_start=datetime.utcnow()
        ... )
        >>> session.add(record)
        >>> session.commit()
    """
    __tablename__ = "rate_limits"
    
    # ========== PRIMARY KEY ==========
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # ========== RATE LIMIT STATE ==========
    # IP address being rate limited (IPv4 or IPv6)
    # UNIQUE constraint ensures one rate limit record per IP
    # INDEXED for O(1) lookup when checking rate limits
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    
    # Total number of requests from this IP (all-time counter)
    # Used for analytics and detecting repeat offenders
    # Incremented on each API request
    request_count = Column(Integer, default=0)
    
    # When did current token bucket window start?
    # Used to calculate how many tokens to add
    # Example: If window_start = now-30sec and rate = 1000req/min:
    #   tokens_to_add = (30 / 60) * 1000 = 500
    # INDEXED for batch cleanup queries
    window_start = Column(DateTime, default=datetime.utcnow)
    
    # ========== INDEXES ==========
    # Optimized for rate limit checks and cleanup
    __table_args__ = (
        # Primary index - check rate limit on each API request
        # Query: session.query(RateLimitRecord).filter_by(ip_address='192.168.1.1')
        Index('idx_ip_address', 'ip_address'),
        # Cleanup index - find and reset old windows
        # Query: session.query(RateLimitRecord).filter(window_start < cutoff_time)
        Index('idx_window_start', 'window_start'),
    )
    
    def __repr__(self) -> str:
        """String representation for logging and debugging"""
        return f"<RateLimitRecord(ip_address='{self.ip_address}', count={self.request_count})>"



# ==================== DATABASE INITIALIZATION & SESSION MANAGEMENT ====================

def init_db(database_url: str) -> tuple:
    """
    Initialize database connection and session factory.
    
    Sets up SQLAlchemy engine with connection pooling and
    creates database tables if they don't exist.
    
    Connection Pooling:
    - pool_size=20: Keep 20 connections open in pool
    - max_overflow=40: Allow up to 40 extra connections when needed
    - pool_recycle=3600: Recycle connections every 1 hour
      (prevents stale connections to cloud databases)
    
    Args:
        database_url: SQLAlchemy database connection URL
                     Examples:
                       - mysql+pymysql://user:pass@localhost/dbname
                       - postgresql://user:pass@localhost/dbname
        
    Returns:
        Tuple of (engine, SessionLocal)
        - engine: SQLAlchemy engine for direct queries if needed
        - SessionLocal: Session factory for creating new sessions
        
    Examples:
        >>> engine, SessionLocal = init_db('mysql+pymysql://root:pass@localhost/urls')
        >>> session = SessionLocal()
        >>> urls = session.query(URLRecord).all()
        >>> session.close()
    """
    # Create engine with connection pooling
    # pool_size: minimum number of connections to keep open
    # max_overflow: additional connections if pool depleted
    # pool_recycle: seconds before connection is recycled (for cloud DBs)
    engine = create_engine(
        database_url,
        pool_size=20,           # Keep 20 connections in pool
        max_overflow=40,        # Allow 40 extra if needed
        pool_recycle=3600,      # Recycle connections every 1 hour
        echo=False              # Set to True to log all SQL queries
    )
    
    # Create session factory
    # expire_on_commit=False: Objects stay attached after commit
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    
    # Create all table schemas if they don't exist
    # Idempotent - safe to call multiple times
    Base.metadata.create_all(bind=engine)
    
    return engine, SessionLocal


def get_db_session(SessionLocal):
    """
    FastAPI dependency for getting database session.
    
    Creates a new session for each request and ensures
    proper cleanup (connection return to pool).
    
    Usage in FastAPI:
        @app.get('/urls')
        def get_urls(db: Session = Depends(get_db_session)):
            return db.query(URLRecord).all()
    
    How it works:
    1. FastAPI calls this function for each request
    2. Session is created and provided to route handler
    3. Route handler uses session for database operations
    4. After route completes, session is closed and conn returned
    5. Prevents connection leaks
    
    Args:
        SessionLocal: Session factory (from init_db)
        
    Yields:
        Database session for this request
        
    Examples:
        >>> db = get_db_session(SessionLocal)
        >>> urls = db.query(URLRecord).filter_by(user_id=42).all()
        >>> db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
