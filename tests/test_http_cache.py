import json
import time
from io import BytesIO
from unittest.mock import patch

import pytest

from app.services.http_cache import BoundedCache, cached_http_get


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._body = BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body.read()


class TestBoundedCache:
    def test_set_and_get(self):
        cache = BoundedCache(max_size=4)
        cache.set("k", {"v": 1}, ttl=10)
        assert cache.get("k") == {"v": 1}

    def test_missing_key_returns_none(self):
        cache = BoundedCache(max_size=4)
        assert cache.get("missing") is None

    def test_ttl_expiry(self):
        cache = BoundedCache(max_size=4)
        cache.set("k", 1, ttl=60)
        with patch(
            "app.services.http_cache.time.time",
            return_value=time.time() + 120,
        ):
            assert cache.get("k") is None

    def test_eviction_by_size(self):
        cache = BoundedCache(max_size=2)
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        cache.set("c", 3, ttl=60)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert len(cache) == 2

    def test_get_refreshes_lru_order(self):
        cache = BoundedCache(max_size=2)
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        # Touch "a" so "b" becomes the oldest.
        assert cache.get("a") == 1
        cache.set("c", 3, ttl=60)
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3

    def test_zero_ttl_is_not_stored(self):
        cache = BoundedCache(max_size=4)
        cache.set("k", 1, ttl=0)
        assert cache.get("k") is None

    def test_invalid_max_size(self):
        with pytest.raises(ValueError):
            BoundedCache(max_size=0)

    def test_clear(self):
        cache = BoundedCache(max_size=4)
        cache.set("a", 1, ttl=60)
        cache.clear()
        assert cache.get("a") is None


class TestCachedHttpGet:
    def test_returns_cached_value(self):
        cache = BoundedCache(max_size=4)
        cache.set("k", {"hit": True}, ttl=60)
        with patch("app.services.http_cache.urllib.request.urlopen") as urlopen:
            result = cached_http_get(cache, "k", "http://x", ttl=60)
        assert result == {"hit": True}
        urlopen.assert_not_called()

    def test_fetches_and_caches(self):
        cache = BoundedCache(max_size=4)
        payload = json.dumps({"ok": 1}).encode()
        with patch(
            "app.services.http_cache.urllib.request.urlopen",
            return_value=_FakeResponse(payload),
        ):
            data = cached_http_get(cache, "k", "http://x", ttl=60)
        assert data == {"ok": 1}
        assert cache.get("k") == {"ok": 1}

    def test_retries_then_succeeds(self):
        cache = BoundedCache(max_size=4)
        payload = json.dumps({"ok": 1}).encode()
        responses = iter([TimeoutError("boom"), _FakeResponse(payload)])

        def fake_urlopen(req, timeout):
            nxt = next(responses)
            if isinstance(nxt, BaseException):
                raise nxt
            return nxt

        with patch("app.services.http_cache.time.sleep"), patch(
            "app.services.http_cache.urllib.request.urlopen",
            side_effect=fake_urlopen,
        ):
            data = cached_http_get(cache, "k", "http://x", ttl=60, retries=1)
        assert data == {"ok": 1}

    def test_retries_exhausted_raises(self):
        cache = BoundedCache(max_size=4)

        def always_fail(*a, **kw):
            raise TimeoutError("still down")

        with patch("app.services.http_cache.time.sleep"), patch(
            "app.services.http_cache.urllib.request.urlopen",
            side_effect=always_fail,
        ), pytest.raises(TimeoutError):
            cached_http_get(cache, "k", "http://x", ttl=60, retries=2)

    def test_malformed_json_raises(self):
        cache = BoundedCache(max_size=4)
        with patch("app.services.http_cache.time.sleep"), patch(
            "app.services.http_cache.urllib.request.urlopen",
            return_value=_FakeResponse(b"not json"),
        ), pytest.raises(json.JSONDecodeError):
            cached_http_get(cache, "k", "http://x", ttl=60, retries=0)
