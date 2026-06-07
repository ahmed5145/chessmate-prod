"""Unit tests for core.rate_limiting.RateLimiter."""

from unittest.mock import MagicMock

from core.rate_limiting import RateLimiter


def _limiter_with_cache(cache):
    limiter = RateLimiter.__new__(RateLimiter)
    limiter.backend = "default"
    limiter.cache = cache
    return limiter


def test_parse_rate_valid_and_default_fallback():
    limiter = _limiter_with_cache(MagicMock())
    assert limiter._parse_rate("10/60") == (10, 60)
    assert limiter._parse_rate("") == (100, 3600)
    assert limiter._parse_rate("bad-format") == (100, 3600)


def test_is_rate_limited_at_threshold():
    cache = MagicMock()
    cache.get.return_value = "5"
    limiter = _limiter_with_cache(cache)

    assert limiter.is_rate_limited("login", "user-1", "5/300") is True
    cache.get.assert_called_with("ratelimit:login:user-1")


def test_is_rate_limited_allows_under_threshold():
    cache = MagicMock()
    cache.get.return_value = "2"
    limiter = _limiter_with_cache(cache)

    assert limiter.is_rate_limited("login", "user-1", "5/300") is False


def test_increment_sets_ttl_window():
    cache = MagicMock()
    cache.get.return_value = "2"
    limiter = _limiter_with_cache(cache)

    limiter.increment("api", "ip-1", "5/120")

    cache.set.assert_called_once_with("ratelimit:api:ip-1", "3", 120)


def test_get_remaining_decrements_correctly():
    cache = MagicMock()
    cache.get.return_value = "3"
    limiter = _limiter_with_cache(cache)

    assert limiter.get_remaining("api", "ip-1", "5/120") == 2


def test_corrupt_cache_value_returns_safe_defaults():
    cache = MagicMock()
    cache.get.return_value = "not-a-number"
    limiter = _limiter_with_cache(cache)

    assert limiter.is_rate_limited("api", "ip-1", "5/120") is False
    assert limiter.get_remaining("api", "ip-1", "5/120") == 0
