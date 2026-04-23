"""
LRU (Least Recently Used) cache implementations.

All operations on ``LRUCache`` are O(1) thanks to a doubly-linked list
combined with a hash map.  No third-party libraries required.

Classes:
  - LRUCache            — base LRU cache
  - ThreadSafeLRUCache  — thread-safe wrapper using threading.Lock
  - SizedLRUCache       — LRU cache with byte-level memory tracking
"""

import sys
import threading
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal doubly-linked-list node
# ---------------------------------------------------------------------------

class _Node:
    """A node in the doubly-linked list used by LRUCache."""
    __slots__ = ("key", "value", "prev", "next", "size_bytes")

    def __init__(self, key: Any, value: Any, size_bytes: int = 0):
        self.key = key
        self.value = value
        self.prev: Optional["_Node"] = None
        self.next: Optional["_Node"] = None
        self.size_bytes = size_bytes


# ---------------------------------------------------------------------------
# LRUCache
# ---------------------------------------------------------------------------

class LRUCache:
    """
    Least Recently Used cache backed by a doubly-linked list + dict.

    All get / put / delete operations run in O(1) time.

    Args:
        capacity: Maximum number of entries before the least-recently-used
                  item is evicted.

    Example::

        cache = LRUCache(capacity=1000)
        cache.put("btc_price", 65000.0)
        price = cache.get("btc_price")   # 65000.0
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("LRUCache capacity must be > 0")
        self._capacity = capacity
        self._map: Dict[Any, _Node] = {}

        # Sentinel head / tail nodes – never hold real data
        self._head = _Node(None, None)
        self._tail = _Node(None, None)
        self._head.next = self._tail
        self._tail.prev = self._head

        # Stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._puts = 0

    # -- linked-list helpers --

    def _remove(self, node: _Node):
        """Detach a node from the list."""
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node

    def _prepend(self, node: _Node):
        """Insert a node right after the sentinel head (most-recent position)."""
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node

    def _move_to_front(self, node: _Node):
        self._remove(node)
        self._prepend(node)

    # -- public API --

    def get(self, key: Any) -> Optional[Any]:
        """
        Retrieve a value by key and mark it as most recently used.

        Returns:
            Cached value, or ``None`` if not present.
        """
        node = self._map.get(key)
        if node is None:
            self._misses += 1
            return None
        self._move_to_front(node)
        self._hits += 1
        return node.value

    def put(self, key: Any, value: Any) -> None:
        """
        Insert or update a cache entry.

        If the cache is at capacity, the least-recently-used entry is evicted.

        Args:
            key:   Cache key.
            value: Value to store.
        """
        self._puts += 1
        if key in self._map:
            node = self._map[key]
            node.value = value
            self._move_to_front(node)
            return

        node = _Node(key, value)
        self._map[key] = node
        self._prepend(node)

        if len(self._map) > self._capacity:
            lru_node = self._tail.prev
            self._remove(lru_node)
            del self._map[lru_node.key]
            self._evictions += 1

    def delete(self, key: Any) -> bool:
        """
        Remove an entry from the cache.

        Returns:
            True if the key existed and was removed, False otherwise.
        """
        node = self._map.get(key)
        if node is None:
            return False
        self._remove(node)
        del self._map[key]
        return True

    def clear(self) -> None:
        """Remove all entries and reset statistics."""
        self._map.clear()
        self._head.next = self._tail
        self._tail.prev = self._head
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._puts = 0

    def contains(self, key: Any) -> bool:
        """Return True if ``key`` is present in the cache."""
        return key in self._map

    def peek(self, key: Any) -> Optional[Any]:
        """
        Retrieve a value without updating LRU order.

        Args:
            key: Cache key.

        Returns:
            Cached value without side effects, or ``None`` if absent.
        """
        node = self._map.get(key)
        return node.value if node is not None else None

    def get_size(self) -> int:
        """Return the current number of entries in the cache."""
        return len(self._map)

    def get_keys(self) -> List[Any]:
        """
        Return all keys ordered from most-recently-used to least.

        Returns:
            Ordered list of keys.
        """
        keys = []
        node = self._head.next
        while node is not self._tail:
            keys.append(node.key)
            node = node.next
        return keys

    def get_stats(self) -> Dict:
        """
        Return cache performance statistics.

        Returns:
            Dict with ``hits``, ``misses``, ``hit_rate``, ``evictions``,
            ``puts``, ``size``, ``capacity`` keys.
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self._evictions,
            "puts": self._puts,
            "size": len(self._map),
            "capacity": self._capacity,
            "utilization": round(len(self._map) / self._capacity, 4),
        }

    def __len__(self):
        return len(self._map)

    def __contains__(self, key):
        return key in self._map

    def __repr__(self):
        return (
            f"<LRUCache capacity={self._capacity} "
            f"size={len(self._map)} "
            f"hit_rate={self.get_stats()['hit_rate']:.2%}>"
        )


# ---------------------------------------------------------------------------
# ThreadSafeLRUCache
# ---------------------------------------------------------------------------

class ThreadSafeLRUCache:
    """
    Thread-safe wrapper around :class:`LRUCache` using a reentrant lock.

    All public methods acquire the lock before delegating to the inner cache.

    Args:
        capacity: Maximum number of entries.

    Example::

        shared_cache = ThreadSafeLRUCache(capacity=5000)
    """

    def __init__(self, capacity: int):
        self._cache = LRUCache(capacity)
        self._lock = threading.RLock()

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            self._cache.put(key, value)

    def delete(self, key: Any) -> bool:
        with self._lock:
            return self._cache.delete(key)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def contains(self, key: Any) -> bool:
        with self._lock:
            return self._cache.contains(key)

    def peek(self, key: Any) -> Optional[Any]:
        with self._lock:
            return self._cache.peek(key)

    def get_size(self) -> int:
        with self._lock:
            return self._cache.get_size()

    def get_keys(self) -> List[Any]:
        with self._lock:
            return self._cache.get_keys()

    def get_stats(self) -> Dict:
        with self._lock:
            return self._cache.get_stats()

    def __len__(self):
        with self._lock:
            return len(self._cache)

    def __contains__(self, key):
        with self._lock:
            return key in self._cache

    def __repr__(self):
        with self._lock:
            return f"<ThreadSafeLRUCache {self._cache!r}>"


# ---------------------------------------------------------------------------
# SizedLRUCache
# ---------------------------------------------------------------------------

class SizedLRUCache:
    """
    LRU cache that also tracks approximate memory usage in bytes.

    Uses ``sys.getsizeof`` for shallow size estimation.  Evicts entries
    both when the count capacity is exceeded *and* when the memory budget
    is exceeded.

    Args:
        capacity:       Maximum number of entries.
        max_memory:     Maximum memory in bytes (default 50 MB).

    Example::

        cache = SizedLRUCache(capacity=10_000, max_memory=50 * 1024 * 1024)
        cache.put("key", large_object)
        print(cache.get_memory_usage())  # bytes used
    """

    def __init__(self, capacity: int, max_memory: int = 50 * 1024 * 1024):
        if capacity <= 0:
            raise ValueError("SizedLRUCache capacity must be > 0")
        self._capacity = capacity
        self._max_memory = max_memory
        self._lock = threading.RLock()
        self._map: Dict[Any, _Node] = {}
        self._head = _Node(None, None)
        self._tail = _Node(None, None)
        self._head.next = self._tail
        self._tail.prev = self._head
        self._memory_used = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @staticmethod
    def _estimate_size(value: Any) -> int:
        try:
            return sys.getsizeof(value)
        except Exception:
            return 64  # conservative fallback

    def _remove(self, node: _Node):
        node.prev.next = node.next
        node.next.prev = node.prev
        self._memory_used -= node.size_bytes

    def _prepend(self, node: _Node):
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node
        self._memory_used += node.size_bytes

    def _evict_lru(self):
        lru = self._tail.prev
        if lru is self._head:
            return
        self._remove(lru)
        del self._map[lru.key]
        self._evictions += 1

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            node = self._map.get(key)
            if node is None:
                self._misses += 1
                return None
            self._remove(node)
            self._prepend(node)
            self._hits += 1
            return node.value

    def put(self, key: Any, value: Any) -> None:
        size = self._estimate_size(value)
        with self._lock:
            if key in self._map:
                existing = self._map[key]
                self._remove(existing)
                del self._map[key]

            node = _Node(key, value, size_bytes=size)
            self._map[key] = node
            self._prepend(node)

            # Evict by count
            while len(self._map) > self._capacity:
                self._evict_lru()

            # Evict by memory
            while self._memory_used > self._max_memory and len(self._map) > 1:
                self._evict_lru()

    def delete(self, key: Any) -> bool:
        with self._lock:
            node = self._map.get(key)
            if node is None:
                return False
            self._remove(node)
            del self._map[key]
            return True

    def clear(self) -> None:
        with self._lock:
            self._map.clear()
            self._head.next = self._tail
            self._tail.prev = self._head
            self._memory_used = 0
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def get_memory_usage(self) -> int:
        """Return approximate memory used by cached values in bytes."""
        with self._lock:
            return self._memory_used

    def set_max_memory(self, bytes_limit: int) -> None:
        """Update the memory budget and immediately evict if needed."""
        with self._lock:
            self._max_memory = bytes_limit
            while self._memory_used > self._max_memory and len(self._map) > 1:
                self._evict_lru()

    def get_stats(self) -> Dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total if total else 0.0, 4),
                "evictions": self._evictions,
                "size": len(self._map),
                "capacity": self._capacity,
                "memory_used_bytes": self._memory_used,
                "max_memory_bytes": self._max_memory,
                "memory_utilization": round(
                    self._memory_used / self._max_memory if self._max_memory else 0.0, 4
                ),
            }

    def __len__(self):
        with self._lock:
            return len(self._map)

    def __contains__(self, key):
        with self._lock:
            return key in self._map

    def __repr__(self):
        stats = self.get_stats()
        return (
            f"<SizedLRUCache size={stats['size']} "
            f"memory={stats['memory_used_bytes']:,}B "
            f"hit_rate={stats['hit_rate']:.2%}>"
        )
