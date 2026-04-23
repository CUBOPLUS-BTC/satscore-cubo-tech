"""
TTL (Time-To-Live) cache implementations.

Entries automatically expire after their configured TTL.  Cleanup of
expired entries is lazy-on-access plus an explicit :meth:`cleanup` method.

Classes:
  - TTLCache            — base TTL cache
  - ThreadSafeTTLCache  — thread-safe version
  - NamespacedCache     — cache with namespace isolation
"""

import threading
import time
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal entry
# ---------------------------------------------------------------------------

class _TTLEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def remaining_ttl(self) -> float:
        """Seconds until expiry (may be negative if already expired)."""
        return self.expires_at - time.time()


# ---------------------------------------------------------------------------
# TTLCache
# ---------------------------------------------------------------------------

class TTLCache:
    """
    Dictionary-backed cache where every entry has a time-to-live.

    Expired entries are **not** automatically evicted in the background;
    they are removed lazily on access or via an explicit :meth:`cleanup` call.

    Args:
        default_ttl: Default TTL in seconds (default 300 = 5 minutes).

    Example::

        cache = TTLCache(default_ttl=60)
        cache.set("btc_price", 65000.0)
        cache.set("fee_estimate", 20, ttl=10)

        price = cache.get("btc_price")   # 65000.0 for up to 60s
    """

    def __init__(self, default_ttl: int = 300):
        self._default_ttl = default_ttl
        self._store: Dict[str, _TTLEntry] = {}
        self._hits = 0
        self._misses = 0
        self._expirations = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value.  Returns ``None`` if the key is absent or expired.

        Args:
            key: Cache key.

        Returns:
            Cached value or ``None``.
        """
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired():
            del self._store[key]
            self._expirations += 1
            self._misses += 1
            return None
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value with an optional TTL override.

        Args:
            key:   Cache key.
            value: Value to store.
            ttl:   TTL in seconds; uses ``default_ttl`` when omitted.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl
        self._store[key] = _TTLEntry(value, expires_at)

    def delete(self, key: str) -> bool:
        """
        Remove an entry.

        Returns:
            True if the key existed, False otherwise.
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries and reset statistics."""
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._expirations = 0

    def cleanup(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        now = time.time()
        expired_keys = [k for k, e in self._store.items() if now > e.expires_at]
        for k in expired_keys:
            del self._store[k]
            self._expirations += 1
        return len(expired_keys)

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining TTL of an entry in seconds.

        Args:
            key: Cache key.

        Returns:
            Remaining TTL in seconds, or ``None`` if key is absent or expired.
        """
        entry = self._store.get(key)
        if entry is None or entry.is_expired():
            return None
        return max(0, int(entry.remaining_ttl()))

    def extend_ttl(self, key: str, additional: int) -> bool:
        """
        Extend the TTL of an existing entry.

        Args:
            key:        Cache key.
            additional: Seconds to add to the current expiry time.

        Returns:
            True if extended, False if the key was absent or expired.
        """
        entry = self._store.get(key)
        if entry is None or entry.is_expired():
            return False
        entry.expires_at += additional
        return True

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Return the cached value if present, otherwise compute and cache it.

        Args:
            key:     Cache key.
            factory: Zero-argument callable that produces the value.
            ttl:     TTL override for the newly computed value.

        Returns:
            Cached or freshly computed value.
        """
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value, ttl=ttl)
        return value

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple keys at once.

        Args:
            keys: List of cache keys.

        Returns:
            Dict of ``{key: value}`` for all found, non-expired keys.
        """
        result = {}
        for key in keys:
            val = self.get(key)
            if val is not None:
                result[key] = val
        return result

    def mset(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Store multiple key-value pairs at once.

        Args:
            items: Dict of ``{key: value}`` pairs.
            ttl:   TTL override applied to all items.
        """
        for key, value in items.items():
            self.set(key, value, ttl=ttl)

    def get_stats(self) -> Dict:
        """Return cache statistics."""
        # Count non-expired active entries
        now = time.time()
        active = sum(1 for e in self._store.values() if now <= e.expires_at)
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total if total else 0.0, 4),
            "expirations": self._expirations,
            "active_entries": active,
            "total_stored_entries": len(self._store),
            "default_ttl": self._default_ttl,
        }

    def keys(self) -> List[str]:
        """Return all non-expired keys."""
        now = time.time()
        return [k for k, e in self._store.items() if now <= e.expires_at]

    def __len__(self):
        return len(self.keys())

    def __contains__(self, key):
        return self.get(key) is not None

    def __repr__(self):
        stats = self.get_stats()
        return (
            f"<TTLCache default_ttl={self._default_ttl}s "
            f"active={stats['active_entries']} "
            f"hit_rate={stats['hit_rate']:.2%}>"
        )


# ---------------------------------------------------------------------------
# ThreadSafeTTLCache
# ---------------------------------------------------------------------------

class ThreadSafeTTLCache:
    """
    Thread-safe version of :class:`TTLCache` using a reentrant lock.

    All public methods acquire the lock before delegating.

    Args:
        default_ttl: Default TTL in seconds.

    Example::

        cache = ThreadSafeTTLCache(default_ttl=120)
    """

    def __init__(self, default_ttl: int = 300):
        self._cache = TTLCache(default_ttl)
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._cache.set(key, value, ttl=ttl)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._cache.delete(key)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def cleanup(self) -> int:
        with self._lock:
            return self._cache.cleanup()

    def get_ttl(self, key: str) -> Optional[int]:
        with self._lock:
            return self._cache.get_ttl(key)

    def extend_ttl(self, key: str, additional: int) -> bool:
        with self._lock:
            return self._cache.extend_ttl(key, additional)

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        with self._lock:
            return self._cache.get_or_set(key, factory, ttl=ttl)

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        with self._lock:
            return self._cache.mget(keys)

    def mset(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        with self._lock:
            self._cache.mset(items, ttl=ttl)

    def get_stats(self) -> Dict:
        with self._lock:
            return self._cache.get_stats()

    def keys(self) -> List[str]:
        with self._lock:
            return self._cache.keys()

    def __len__(self):
        with self._lock:
            return len(self._cache)

    def __contains__(self, key):
        with self._lock:
            return key in self._cache

    def __repr__(self):
        with self._lock:
            return f"<ThreadSafeTTLCache {self._cache!r}>"


# ---------------------------------------------------------------------------
# NamespacedCache
# ---------------------------------------------------------------------------

class NamespacedCache:
    """
    A TTL cache partitioned into named namespaces.

    Each namespace can have its own default TTL.  Keys are isolated per
    namespace so the same key can exist in multiple namespaces without
    collision.

    This is useful for separating different data types (e.g., ``"prices"``,
    ``"sessions"``, ``"api_responses"``) while sharing a single backing store.

    Args:
        default_ttl: Global default TTL in seconds.

    Example::

        ns = NamespacedCache(default_ttl=60)
        ns.set("prices", "btc_usd", 65000.0, ttl=10)
        ns.set("sessions", "user_abc", {...}, ttl=3600)

        btc = ns.get("prices", "btc_usd")
        ns.invalidate_namespace("prices")
    """

    def __init__(self, default_ttl: int = 300):
        self._default_ttl = default_ttl
        self._store: Dict[str, Dict[str, _TTLEntry]] = {}
        self._lock = threading.RLock()
        self._stats: Dict[str, Dict] = {}

    def _ensure_namespace(self, namespace: str):
        if namespace not in self._store:
            self._store[namespace] = {}
            self._stats[namespace] = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Retrieve a value from a specific namespace.

        Args:
            namespace: Namespace name.
            key:       Cache key.

        Returns:
            Cached value or ``None``.
        """
        with self._lock:
            self._ensure_namespace(namespace)
            ns_store = self._store[namespace]
            entry = ns_store.get(key)
            if entry is None:
                self._stats[namespace]["misses"] += 1
                return None
            if entry.is_expired():
                del ns_store[key]
                self._stats[namespace]["evictions"] += 1
                self._stats[namespace]["misses"] += 1
                return None
            self._stats[namespace]["hits"] += 1
            return entry.value

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Store a value in a specific namespace.

        Args:
            namespace: Namespace name.
            key:       Cache key.
            value:     Value to store.
            ttl:       TTL override; uses ``default_ttl`` if omitted.
        """
        with self._lock:
            self._ensure_namespace(namespace)
            effective_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = time.time() + effective_ttl
            self._store[namespace][key] = _TTLEntry(value, expires_at)
            self._stats[namespace]["sets"] += 1

    def delete(self, namespace: str, key: str) -> bool:
        """Remove a specific key from a namespace."""
        with self._lock:
            ns_store = self._store.get(namespace)
            if ns_store is None or key not in ns_store:
                return False
            del ns_store[key]
            return True

    def invalidate_namespace(self, namespace: str) -> int:
        """
        Remove all entries in a namespace.

        Args:
            namespace: Namespace to clear.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            ns_store = self._store.get(namespace)
            if ns_store is None:
                return 0
            count = len(ns_store)
            ns_store.clear()
            return count

    def cleanup_namespace(self, namespace: str) -> int:
        """Remove expired entries from a namespace."""
        with self._lock:
            ns_store = self._store.get(namespace)
            if ns_store is None:
                return 0
            now = time.time()
            expired = [k for k, e in ns_store.items() if now > e.expires_at]
            for k in expired:
                del ns_store[k]
            return len(expired)

    def cleanup_all(self) -> Dict[str, int]:
        """Remove expired entries from all namespaces."""
        with self._lock:
            result = {}
            for ns in list(self._store.keys()):
                result[ns] = self.cleanup_namespace(ns)
            return result

    def get_namespace_stats(self, namespace: str) -> Dict:
        """Return statistics for a specific namespace."""
        with self._lock:
            self._ensure_namespace(namespace)
            stats = dict(self._stats[namespace])
            ns_store = self._store[namespace]
            now = time.time()
            active = sum(1 for e in ns_store.values() if now <= e.expires_at)
            stats["active_entries"] = active
            stats["total_entries"] = len(ns_store)
            total = stats["hits"] + stats["misses"]
            stats["hit_rate"] = round(stats["hits"] / total if total else 0.0, 4)
            return stats

    def get_all_stats(self) -> Dict:
        """Return stats for every namespace."""
        with self._lock:
            return {ns: self.get_namespace_stats(ns) for ns in self._store}

    def namespaces(self) -> List[str]:
        """List all known namespaces."""
        with self._lock:
            return list(self._store.keys())

    def __repr__(self):
        with self._lock:
            total = sum(len(v) for v in self._store.values())
            return (
                f"<NamespacedCache namespaces={list(self._store.keys())} "
                f"total_entries={total}>"
            )
