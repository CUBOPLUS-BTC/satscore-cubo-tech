"""Rate limit storage backends for the Magma API.

Implements an in-memory sliding-window rate limiter that is fully
thread-safe. A database-backed backend can be added later by
implementing the same interface.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple


class MemoryStorage:
    """Thread-safe, sliding-window rate limit store.

    Each request timestamp is stored in a deque per ``key``.  When
    ``record_request`` is called the deque is pruned to the current
    window so the length always reflects the true count for that window.

    Additionally a separate ``_blocked`` dict holds keys that have been
    explicitly blocked (e.g. after abuse detection) until a timestamp.

    Data structures
    ---------------
    _requests : dict[str, deque[float]]
        Sliding window of UNIX timestamps for every rate-limit key.
    _blocked  : dict[str, float]
        Mapping of key → unblock_at UNIX timestamp.
    _lock     : threading.Lock
        Single coarse-grained lock protecting both dicts.  Fine-grained
        per-key locking would be faster at scale but adds complexity;
        this is sufficient for the expected request volume.
    """

    def __init__(self) -> None:
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._blocked: Dict[str, float] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_request(self, key: str, window: int) -> int:
        """Record an incoming request for *key* and return the count
        within the current *window* (seconds).

        The call is side-effect free with respect to blocking: it does
        *not* check whether the key is blocked – callers should call
        :meth:`is_blocked` first.

        Parameters
        ----------
        key:
            Opaque string identifying the rate-limit subject (IP,
            pubkey, endpoint combination, etc.).
        window:
            Length of the sliding window in seconds.

        Returns
        -------
        int
            Number of recorded requests in the current window
            *including* the one just added.
        """
        now = time.time()
        cutoff = now - window
        with self._lock:
            dq = self._requests[key]
            # Prune expired timestamps from the left end of the deque.
            while dq and dq[0] < cutoff:
                dq.popleft()
            dq.append(now)
            return len(dq)

    def get_remaining(self, key: str, window: int, limit: int) -> Tuple[int, int]:
        """Return (remaining, reset_at) for the given *key* and *limit*.

        *remaining* is the number of requests the caller may still make
        before hitting the limit.  *reset_at* is the UNIX timestamp at
        which the oldest in-window request expires, i.e. when the
        window slides past it and at least one slot is freed.

        If there are no recorded requests the reset_at is the current
        time plus the full window length.

        Parameters
        ----------
        key:
            Rate-limit subject key.
        window:
            Sliding window length in seconds.
        limit:
            Maximum number of requests allowed per window.

        Returns
        -------
        tuple[int, int]
            ``(remaining, reset_at)``
        """
        now = time.time()
        cutoff = now - window
        with self._lock:
            dq = self._requests.get(key)
            if not dq:
                return limit, int(now + window)
            # Peek at oldest live request (after pruning).
            oldest = next((ts for ts in dq if ts >= cutoff), None)
            count = sum(1 for ts in dq if ts >= cutoff)
            remaining = max(0, limit - count)
            reset_at = int(oldest + window) if oldest is not None else int(now + window)
            return remaining, reset_at

    def is_blocked(self, key: str) -> bool:
        """Return ``True`` if *key* is currently in the blocked list.

        Expired blocks are removed lazily during this call.
        """
        now = time.time()
        with self._lock:
            unblock_at = self._blocked.get(key)
            if unblock_at is None:
                return False
            if now >= unblock_at:
                del self._blocked[key]
                return False
            return True

    def block(self, key: str, duration: int) -> None:
        """Block *key* for *duration* seconds.

        If the key is already blocked, the block is extended to
        ``max(existing_unblock_at, now + duration)``.
        """
        now = time.time()
        unblock_at = now + duration
        with self._lock:
            existing = self._blocked.get(key, 0.0)
            self._blocked[key] = max(existing, unblock_at)

    def unblock(self, key: str) -> None:
        """Remove a manual block on *key* immediately."""
        with self._lock:
            self._blocked.pop(key, None)

    def get_block_remaining(self, key: str) -> int:
        """Return seconds until *key* is unblocked, or 0 if not blocked."""
        now = time.time()
        with self._lock:
            unblock_at = self._blocked.get(key, 0.0)
            if unblock_at <= now:
                return 0
            return int(unblock_at - now)

    def cleanup(self) -> int:
        """Remove all expired entries from both dicts.

        This should be called periodically (e.g. every 5 minutes) to
        prevent unbounded memory growth for high-cardinality key spaces.

        Returns
        -------
        int
            Total number of stale entries removed.
        """
        now = time.time()
        removed = 0
        with self._lock:
            # Clean request deques – remove keys whose newest timestamp
            # is older than the maximum possible window (1 hour).
            max_window = 3600
            cutoff = now - max_window
            stale_keys: List[str] = [
                k for k, dq in self._requests.items()
                if not dq or dq[-1] < cutoff
            ]
            for k in stale_keys:
                del self._requests[k]
                removed += 1

            # Clean expired blocks.
            stale_blocks: List[str] = [
                k for k, unblock_at in self._blocked.items()
                if unblock_at <= now
            ]
            for k in stale_blocks:
                del self._blocked[k]
                removed += 1

        return removed

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return a snapshot of current storage usage."""
        now = time.time()
        with self._lock:
            total_keys = len(self._requests)
            active_blocks = sum(
                1 for unblock_at in self._blocked.values() if unblock_at > now
            )
            total_timestamps = sum(len(dq) for dq in self._requests.values())
        return {
            "tracked_keys": total_keys,
            "active_blocks": active_blocks,
            "total_timestamps": total_timestamps,
            "timestamp": int(now),
        }

    def get_key_info(self, key: str, window: int, limit: int) -> dict:
        """Return detailed info for a single key (useful for debugging)."""
        now = time.time()
        cutoff = now - window
        with self._lock:
            dq = self._requests.get(key, deque())
            timestamps = [ts for ts in dq if ts >= cutoff]
            count = len(timestamps)
            blocked = self._blocked.get(key, 0.0) > now
            unblock_at = self._blocked.get(key, 0.0)
        return {
            "key": key,
            "count": count,
            "remaining": max(0, limit - count),
            "blocked": blocked,
            "unblock_at": int(unblock_at) if blocked else None,
            "oldest_request": int(min(timestamps)) if timestamps else None,
            "newest_request": int(max(timestamps)) if timestamps else None,
        }

    def reset_key(self, key: str) -> None:
        """Completely clear all rate-limit data for *key*."""
        with self._lock:
            self._requests.pop(key, None)
            self._blocked.pop(key, None)
