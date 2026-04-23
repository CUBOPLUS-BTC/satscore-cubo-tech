"""
Multi-tier caching and application-level cache management.

Provides:
  - CacheTier       — descriptor for a single tier
  - MultiTierCache  — cache that checks multiple tiers (L1, L2, …)
  - CacheManager    — application-level singleton with named caches
  - Factory helpers: create_price_cache, create_api_cache, etc.

All pure Python stdlib; no third-party libraries.
"""

import fnmatch
import functools
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .lru import ThreadSafeLRUCache
from .ttl import ThreadSafeTTLCache

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CacheTier
# ---------------------------------------------------------------------------

class CacheTier:
    """
    Descriptor for a single cache tier within a :class:`MultiTierCache`.

    Args:
        name:     Human-readable tier label (e.g. ``"L1"``, ``"L2"``).
        cache:    A ``ThreadSafeLRUCache`` or ``ThreadSafeTTLCache`` instance.
        ttl:      Default TTL for writes to this tier (seconds).
        priority: Lower number = checked first.
    """

    def __init__(
        self,
        name: str,
        cache: Any,
        ttl: int = 60,
        priority: int = 0,
    ):
        self.name = name
        self.cache = cache
        self.ttl = ttl
        self.priority = priority

    def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        effective_ttl = ttl if ttl is not None else self.ttl
        if hasattr(self.cache, "set"):
            self.cache.set(key, value, ttl=effective_ttl)
        else:
            self.cache.put(key, value)

    def delete(self, key: str) -> bool:
        if hasattr(self.cache, "delete"):
            return self.cache.delete(key)
        return False

    def get_stats(self) -> Dict:
        return {
            "tier": self.name,
            "priority": self.priority,
            "ttl": self.ttl,
            "stats": self.cache.get_stats(),
        }

    def contains(self, key: str) -> bool:
        if hasattr(self.cache, "contains"):
            return self.cache.contains(key)
        return self.cache.get(key) is not None

    def keys(self) -> List[str]:
        if hasattr(self.cache, "keys"):
            return self.cache.keys()
        if hasattr(self.cache, "get_keys"):
            return [str(k) for k in self.cache.get_keys()]
        return []

    def __repr__(self):
        return f"<CacheTier name='{self.name}' priority={self.priority} ttl={self.ttl}s>"


# ---------------------------------------------------------------------------
# MultiTierCache
# ---------------------------------------------------------------------------

class MultiTierCache:
    """
    Cache that checks multiple tiers in priority order.

    On a **get**:
      - Tiers are checked from lowest to highest priority number.
      - If found in a lower-priority tier, the value is **promoted**
        (written) into all higher-priority tiers.

    On a **set**:
      - Value is written to *all* tiers simultaneously.

    Args:
        tiers: List of :class:`CacheTier` instances (order by priority).

    Example::

        cache = MultiTierCache([
            CacheTier("L1", ThreadSafeTTLCache(10),  ttl=10,  priority=0),
            CacheTier("L2", ThreadSafeTTLCache(60),  ttl=60,  priority=1),
        ])
        cache.set("btc_price", 65000.0)
        price = cache.get("btc_price")   # hits L1, then L2
    """

    def __init__(self, tiers: List[CacheTier]):
        if not tiers:
            raise ValueError("MultiTierCache requires at least one tier")
        self._tiers = sorted(tiers, key=lambda t: t.priority)
        self._lock = threading.RLock()
        self._hits_per_tier: Dict[str, int] = {t.name: 0 for t in self._tiers}
        self._misses = 0
        self._total_gets = 0
        self._total_sets = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value, checking tiers from highest to lowest priority.

        On a cache miss in a higher-priority tier but hit in a lower one,
        the value is promoted to all higher-priority tiers.

        Args:
            key: Cache key.

        Returns:
            Cached value or ``None``.
        """
        with self._lock:
            self._total_gets += 1
            for idx, tier in enumerate(self._tiers):
                value = tier.get(key)
                if value is not None:
                    self._hits_per_tier[tier.name] += 1
                    # Promote to higher-priority tiers
                    for upper_tier in self._tiers[:idx]:
                        upper_tier.set(key, value)
                    return value
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Write value to all tiers."""
        with self._lock:
            self._total_sets += 1
            for tier in self._tiers:
                tier.set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        """Delete key from all tiers."""
        with self._lock:
            for tier in self._tiers:
                tier.delete(key)

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob ``pattern`` from all tiers.

        Args:
            pattern: Glob pattern (e.g. ``"price:*"``).

        Returns:
            Number of unique keys deleted.
        """
        with self._lock:
            deleted_keys = set()
            for tier in self._tiers:
                for key in tier.keys():
                    if fnmatch.fnmatch(key, pattern):
                        tier.delete(key)
                        deleted_keys.add(key)
            return len(deleted_keys)

    def warmup(self, keys: List[str], loader: Callable[[str], Any]) -> int:
        """
        Pre-populate the cache by calling ``loader(key)`` for each key.

        Args:
            keys:   List of keys to warm up.
            loader: Callable ``(key) -> value``; ``None`` return is ignored.

        Returns:
            Number of keys successfully loaded.
        """
        count = 0
        for key in keys:
            try:
                value = loader(key)
                if value is not None:
                    self.set(key, value)
                    count += 1
            except Exception as exc:
                logger.warning("MultiTierCache warmup error for key '%s': %s", key, exc)
        logger.info("MultiTierCache warmup complete: %d/%d keys loaded", count, len(keys))
        return count

    def get_tier_stats(self) -> List[Dict]:
        """Return per-tier statistics including hit counts."""
        with self._lock:
            stats = []
            for tier in self._tiers:
                s = tier.get_stats()
                s["tier_hits"] = self._hits_per_tier.get(tier.name, 0)
                stats.append(s)
            return stats

    def get_stats(self) -> Dict:
        """Return aggregate statistics."""
        with self._lock:
            total_hits = sum(self._hits_per_tier.values())
            total = total_hits + self._misses
            return {
                "total_gets": self._total_gets,
                "total_sets": self._total_sets,
                "hits": total_hits,
                "misses": self._misses,
                "hit_rate": round(total_hits / total if total else 0.0, 4),
                "tiers": len(self._tiers),
                "hits_per_tier": dict(self._hits_per_tier),
            }

    def __repr__(self):
        tier_names = [t.name for t in self._tiers]
        return f"<MultiTierCache tiers={tier_names}>"


# ---------------------------------------------------------------------------
# CacheManager
# ---------------------------------------------------------------------------

class CacheManager:
    """
    Application-level cache registry.

    Maintains named :class:`MultiTierCache` instances and provides
    convenience methods for get-or-compute, group invalidation, and a
    caching decorator.

    Usage::

        manager = CacheManager()
        manager.register("prices", create_price_cache())

        btc = manager.get_or_compute(
            "btc_price",
            lambda: fetch_btc_price(),
            ttl=10,
            cache_name="prices",
        )
    """

    def __init__(self):
        self._caches: Dict[str, MultiTierCache] = {}
        self._groups: Dict[str, List[str]] = {}  # group -> list of keys
        self._lock = threading.RLock()
        self._started_at = time.time()

    def register(self, name: str, cache: MultiTierCache) -> None:
        """Register a named cache."""
        with self._lock:
            self._caches[name] = cache
            logger.info("CacheManager: registered cache '%s'", name)

    def _get_cache(self, cache_name: Optional[str]) -> MultiTierCache:
        if cache_name is None:
            if not self._caches:
                raise RuntimeError("No caches registered in CacheManager")
            return next(iter(self._caches.values()))
        cache = self._caches.get(cache_name)
        if cache is None:
            raise KeyError(f"Unknown cache: '{cache_name}'")
        return cache

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: Optional[int] = None,
        cache_name: Optional[str] = None,
        group: Optional[str] = None,
    ) -> Any:
        """
        Return the cached value for ``key``, or compute and cache it.

        Args:
            key:         Cache key.
            compute_fn:  Zero-argument callable that produces the value.
            ttl:         TTL override.
            cache_name:  Named cache to use; defaults to first registered.
            group:       Optional group label for bulk invalidation.

        Returns:
            Cached or freshly computed value.
        """
        cache = self._get_cache(cache_name)
        value = cache.get(key)
        if value is not None:
            return value
        value = compute_fn()
        if value is not None:
            cache.set(key, value, ttl=ttl)
            if group:
                with self._lock:
                    self._groups.setdefault(group, [])
                    if key not in self._groups[group]:
                        self._groups[group].append(key)
        return value

    def invalidate(self, key: str, cache_name: Optional[str] = None) -> None:
        """Invalidate a single key from a specific (or all) caches."""
        with self._lock:
            if cache_name:
                self._get_cache(cache_name).delete(key)
            else:
                for cache in self._caches.values():
                    cache.delete(key)

    def invalidate_group(self, group: str) -> int:
        """
        Invalidate all keys registered under ``group``.

        Args:
            group: Group label.

        Returns:
            Number of keys invalidated.
        """
        with self._lock:
            keys = self._groups.pop(group, [])
            for key in keys:
                for cache in self._caches.values():
                    cache.delete(key)
            return len(keys)

    def get_stats(self) -> Dict:
        """Return stats for all registered caches."""
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self._started_at, 1),
                "registered_caches": list(self._caches.keys()),
                "tracked_groups": {g: len(k) for g, k in self._groups.items()},
                "per_cache": {
                    name: cache.get_stats()
                    for name, cache in self._caches.items()
                },
            }

    def cache_decorator(
        self,
        ttl: Optional[int] = None,
        key_fn: Optional[Callable] = None,
        cache_name: Optional[str] = None,
    ):
        """
        Decorator factory that caches function return values.

        Args:
            ttl:        TTL in seconds.
            key_fn:     Optional callable ``(*args, **kwargs) -> str`` for
                        the cache key.  Defaults to ``func.__name__:args:kwargs``.
            cache_name: Named cache to use.

        Example::

            @manager.cache_decorator(ttl=30, cache_name="prices")
            def get_btc_price():
                return fetch_from_api()
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if key_fn:
                    key = key_fn(*args, **kwargs)
                else:
                    key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                return self.get_or_compute(
                    key,
                    lambda: func(*args, **kwargs),
                    ttl=ttl,
                    cache_name=cache_name,
                )
            return wrapper
        return decorator

    def __repr__(self):
        return f"<CacheManager caches={list(self._caches.keys())}>"


# ---------------------------------------------------------------------------
# Predefined cache configurations
# ---------------------------------------------------------------------------

def create_price_cache() -> MultiTierCache:
    """
    Create a two-tier cache for Bitcoin price data.

    - L1: very hot, 10-second TTL, 500-entry LRU
    - L2: warm,     60-second TTL, 2 000-entry LRU

    Returns:
        Configured :class:`MultiTierCache`.
    """
    l1 = CacheTier(
        name="L1-hot",
        cache=ThreadSafeTTLCache(default_ttl=10),
        ttl=10,
        priority=0,
    )
    l2 = CacheTier(
        name="L2-warm",
        cache=ThreadSafeTTLCache(default_ttl=60),
        ttl=60,
        priority=1,
    )
    return MultiTierCache([l1, l2])


def create_api_cache() -> MultiTierCache:
    """
    Create a cache suited for external API responses.

    - L1: 30-second TTL, LRU 1 000 entries
    - L2: 300-second TTL, LRU 5 000 entries

    Returns:
        Configured :class:`MultiTierCache`.
    """
    l1 = CacheTier(
        name="L1-api-hot",
        cache=ThreadSafeTTLCache(default_ttl=30),
        ttl=30,
        priority=0,
    )
    l2 = CacheTier(
        name="L2-api-warm",
        cache=ThreadSafeTTLCache(default_ttl=300),
        ttl=300,
        priority=1,
    )
    return MultiTierCache([l1, l2])


def create_session_cache() -> MultiTierCache:
    """
    Create a cache for authenticated user sessions.

    - L1: 5-minute TTL (memory, fast access), LRU 10 000 entries
    - L2: 30-minute TTL (slower tier), LRU 50 000 entries

    Returns:
        Configured :class:`MultiTierCache`.
    """
    l1 = CacheTier(
        name="L1-session",
        cache=ThreadSafeTTLCache(default_ttl=300),
        ttl=300,
        priority=0,
    )
    l2 = CacheTier(
        name="L2-session",
        cache=ThreadSafeTTLCache(default_ttl=1800),
        ttl=1800,
        priority=1,
    )
    return MultiTierCache([l1, l2])


def create_computation_cache() -> MultiTierCache:
    """
    Create a cache for the results of expensive computations.

    - L1:  2-minute TTL
    - L2: 15-minute TTL

    Returns:
        Configured :class:`MultiTierCache`.
    """
    l1 = CacheTier(
        name="L1-compute",
        cache=ThreadSafeTTLCache(default_ttl=120),
        ttl=120,
        priority=0,
    )
    l2 = CacheTier(
        name="L2-compute",
        cache=ThreadSafeTTLCache(default_ttl=900),
        ttl=900,
        priority=1,
    )
    return MultiTierCache([l1, l2])
