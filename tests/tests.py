"""
Unit tests for URL shortener service.
Run with: pytest tests/tests.py -v
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from app.models import Base, URLRecord, ClickRecord, get_db_session, SessionLocal
from app.utils import (
    base62_encode, base62_decode, generate_short_code,
    validate_url, validate_custom_alias, calculate_expiry_time,
    is_url_expired, format_short_url
)
from app.cache import RedisCache


# Test client
client = TestClient(app)


class TestBase62Encoding:
    """Test Base62 encoding/decoding functions."""
    
    def test_base62_encode_zero(self):
        assert base62_encode(0) == "0"
    
    def test_base62_encode_single_digit(self):
        assert base62_encode(5) == "5"
    
    def test_base62_encode_two_digits(self):
        result = base62_encode(62)
        assert len(result) == 2
    
    def test_base62_roundtrip(self):
        original = 123456789
        encoded = base62_encode(original)
        decoded = base62_decode(encoded)
        assert decoded == original
    
    def test_base62_large_number(self):
        """Test with 56 billion (max for 6 chars)."""
        original = 56000000000
        encoded = base62_encode(original)
        decoded = base62_decode(encoded)
        assert decoded == original


class TestShortCodeGeneration:
    """Test short code generation."""
    
    def test_generate_short_code_default_length(self):
        code = generate_short_code()
        assert len(code) == 6
    
    def test_generate_short_code_custom_length(self):
        for length in [3, 6, 10, 20]:
            code = generate_short_code(length)
            assert len(code) == length
    
    def test_generate_short_codes_unique(self):
        codes = {generate_short_code() for _ in range(100)}
        assert len(codes) == 100


class TestURLValidation:
    """Test URL validation."""
    
    def test_validate_valid_http_url(self):
        is_valid, msg = validate_url("http://example.com")
        assert is_valid is True
    
    def test_validate_valid_https_url(self):
        is_valid, msg = validate_url("https://example.com/path?query=value")
        assert is_valid is True
    
    def test_validate_empty_url(self):
        is_valid, msg = validate_url("")
        assert is_valid is False
    
    def test_validate_url_without_protocol(self):
        is_valid, msg = validate_url("example.com")
        assert is_valid is False
    
    def test_validate_url_too_long(self):
        long_url = "http://example.com/" + "a" * 2100
        is_valid, msg = validate_url(long_url)
        assert is_valid is False


class TestCustomAliasValidation:
    """Test custom alias validation."""
    
    def test_validate_valid_alias(self):
        is_valid, msg = validate_custom_alias("mylink")
        assert is_valid is True
    
    def test_validate_alias_with_numbers(self):
        is_valid, msg = validate_custom_alias("link123")
        assert is_valid is True
    
    def test_validate_alias_with_hyphens(self):
        is_valid, msg = validate_custom_alias("my-link")
        assert is_valid is True
    
    def test_validate_alias_too_short(self):
        is_valid, msg = validate_custom_alias("ab")
        assert is_valid is False
    
    def test_validate_alias_too_long(self):
        is_valid, msg = validate_custom_alias("a" * 30)
        assert is_valid is False
    
    def test_validate_alias_invalid_chars(self):
        is_valid, msg = validate_custom_alias("my@link!")
        assert is_valid is False


class TestExpiryCalculation:
    """Test expiry time calculation."""
    
    def test_no_expiry(self):
        expiry = calculate_expiry_time(0)
        assert expiry is None
    
    def test_expiry_30_days(self):
        expiry = calculate_expiry_time(30)
        assert expiry is not None
        # Check approximately 30 days in future
        diff = expiry - datetime.utcnow()
        assert 29 * 86400 < diff.total_seconds() < 31 * 86400
    
    def test_is_url_expired_false(self):
        future_date = datetime.utcnow() + timedelta(days=1)
        assert is_url_expired(future_date) is False
    
    def test_is_url_expired_true(self):
        past_date = datetime.utcnow() - timedelta(days=1)
        assert is_url_expired(past_date) is True
    
    def test_is_url_expired_none(self):
        assert is_url_expired(None) is False


class TestAPIEndpoints:
    """Test API endpoints."""
    
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "service" in response.json()
    
    def test_health_check(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "cache" in data
    
    def test_create_short_url(self):
        payload = {
            "long_url": "https://example.com/very/long/path"
        }
        response = client.post("/api/v1/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["long_url"] == payload["long_url"]
    
    def test_create_short_url_with_custom_alias(self):
        payload = {
            "long_url": "https://example.com",
            "custom_alias": f"test_{generate_short_code()}"
        }
        response = client.post("/api/v1/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["short_code"] == payload["custom_alias"]
    
    def test_create_short_url_invalid_url(self):
        payload = {
            "long_url": "invalid_url"
        }
        response = client.post("/api/v1/shorten", json=payload)
        assert response.status_code == 400
    
    def test_create_short_url_with_expiry(self):
        payload = {
            "long_url": "https://example.com",
            "expiry_days": 30
        }
        response = client.post("/api/v1/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None
    
    def test_list_user_urls(self):
        response = client.get("/api/v1/urls?user_id=1")
        assert response.status_code == 200
        data = response.json()
        assert "urls" in data
        assert "count" in data
    
    def test_list_user_urls_pagination(self):
        response = client.get("/api/v1/urls?user_id=1&skip=0&limit=10")
        assert response.status_code == 200
    
    def test_service_stats(self):
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_urls" in data
        assert "total_clicks" in data


class TestRedisCache:
    """Test Redis cache functionality."""
    
    @pytest.fixture
    def cache(self):
        """Create test cache instance."""
        return RedisCache("redis://localhost:6379/1")
    
    def test_cache_set_get_url(self, cache):
        if not cache.is_connected():
            pytest.skip("Redis not available")
        
        cache.set_url("test123", "https://example.com")
        url = cache.get_url("test123")
        assert url == "https://example.com"
    
    def test_cache_delete_url(self, cache):
        if not cache.is_connected():
            pytest.skip("Redis not available")
        
        cache.set_url("delete_test", "https://example.com")
        cache.delete_url("delete_test")
        url = cache.get_url("delete_test")
        assert url is None
    
    def test_rate_limiting(self, cache):
        if not cache.is_connected():
            pytest.skip("Redis not available")
        
        ip = "192.168.1.1"
        # First 10 requests should pass
        for _ in range(10):
            assert cache.check_rate_limit(ip, 10, 60) is True
        
        # 11th should fail
        assert cache.check_rate_limit(ip, 10, 60) is False


class TestDatabaseModels:
    """Test database models."""
    
    def test_url_record_creation(self):
        url = URLRecord(
            short_code="test123",
            long_url="https://example.com"
        )
        assert url.short_code == "test123"
        assert url.long_url == "https://example.com"
        assert url.clicks == 0
    
    def test_url_record_to_dict(self):
        url = URLRecord(
            short_code="test123",
            long_url="https://example.com"
        )
        d = url.to_dict()
        assert d["short_code"] == "test123"
        assert d["long_url"] == "https://example.com"
    
    def test_click_record_creation(self):
        click = ClickRecord(
            short_code="test123",
            ip_address="192.168.1.1"
        )
        assert click.short_code == "test123"
        assert click.ip_address == "192.168.1.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
