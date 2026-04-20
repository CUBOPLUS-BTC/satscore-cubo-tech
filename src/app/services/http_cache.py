"""Shared HTTP cache + GET helper with bounded size and retry.

Service clients use ``cached_http_get`` so the cache cannot grow without
bound and transient network errors don't immediately surface to callers.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional


class BoundedCache:
    """Thread-safe TTL cache with a hard size limit (LRU eviction)."""

    def __init__(self, max_size: int = 512):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._data: "OrderedDict[str, tuple[Any, float]]" = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if now >= expiry:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        if ttl <= 0:
            return
        expiry = time.time() + ttl
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (value, expiry)
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


def cached_http_get(
    cache: BoundedCache,
    key: str,
    url: str,
    ttl: int,
    *,
    timeout: float = 8.0,
    headers: Optional[dict] = None,
    retries: int = 1,
    backoff: float = 0.25,
) -> Any:
    """GET url, decode JSON, cache with TTL. Retries transient failures."""
    cached = cache.get(key)
    if cached is not None:
        return cached

    req_headers = {"User-Agent": "Magma/1.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    attempt = 0
    last_exc: Optional[BaseException] = None
    while attempt <= retries:
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            cache.set(key, data, ttl)
            return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            attempt += 1
            if attempt > retries:
                break
            time.sleep(backoff * attempt)

    assert last_exc is not None
    raise last_exc
