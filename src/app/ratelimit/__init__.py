"""Rate limiting package for the Magma API.

Provides sliding-window rate limiting with in-memory storage and
standard X-RateLimit-* HTTP response headers.

Quick start
-----------
::

    from app.ratelimit import limiter, storage

    _storage = storage.MemoryStorage()
    _limiter = limiter.RateLimiter(_storage)

    # In an HTTP handler:
    result = _limiter.check_request(ip=client_ip, endpoint="/auth/challenge")
    if not result["allowed"]:
        return {"detail": "Too many requests"}, 429
"""

from .storage import MemoryStorage
from .limiter import RateLimiter, RATE_LIMITS

__all__ = ["MemoryStorage", "RateLimiter", "RATE_LIMITS"]
