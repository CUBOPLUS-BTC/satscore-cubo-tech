"""
Cache package for the Magma Bitcoin application.

Provides:
  - LRUCache / ThreadSafeLRUCache / SizedLRUCache
  - TTLCache / ThreadSafeTTLCache / NamespacedCache
  - MultiTierCache / CacheTier / CacheManager
  - Predefined cache factories: create_price_cache, create_api_cache, etc.
"""

from .lru import LRUCache, ThreadSafeLRUCache, SizedLRUCache
from .ttl import TTLCache, ThreadSafeTTLCache, NamespacedCache
from .multi_tier import (
    CacheTier,
    MultiTierCache,
    CacheManager,
    create_price_cache,
    create_api_cache,
    create_session_cache,
    create_computation_cache,
)

__all__ = [
    "LRUCache",
    "ThreadSafeLRUCache",
    "SizedLRUCache",
    "TTLCache",
    "ThreadSafeTTLCache",
    "NamespacedCache",
    "CacheTier",
    "MultiTierCache",
    "CacheManager",
    "create_price_cache",
    "create_api_cache",
    "create_session_cache",
    "create_computation_cache",
]
