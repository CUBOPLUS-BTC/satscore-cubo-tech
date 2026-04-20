"""Tests for ``Retry-After`` handling in :class:`HTTPTransport`."""

from __future__ import annotations

from email.utils import format_datetime
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import List

import pytest

from magma_sdk._transport import HTTPTransport, MAX_RETRY_AFTER, TransportConfig
from magma_sdk.exceptions import RateLimitError


class _FakeHeaders:
    def __init__(self, headers: dict):
        self._headers = headers

    def items(self):
        return self._headers.items()


class _FakeResp:
    def __init__(self, status: int, body: bytes, headers=None):
        self.status = status
        self._buf = BytesIO(body)
        self.headers = _FakeHeaders(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getcode(self):
        return self.status

    def read(self):
        return self._buf.read()


def _transport(responses, *, now=1_700_000_000.0, max_retries=2, respect=True):
    it = iter(responses)
    sleeps: List[float] = []

    def fake_opener(req, timeout):
        nxt = next(it)
        if isinstance(nxt, BaseException):
            raise nxt
        return nxt

    cfg = TransportConfig(
        base_url="https://api.test",
        max_retries=max_retries,
        backoff=1.0,
        respect_retry_after=respect,
    )
    t = HTTPTransport(
        cfg, opener=fake_opener, sleep=sleeps.append, now=lambda: now
    )
    return t, sleeps


class TestRetryAfterSeconds:
    def test_honors_numeric_seconds(self):
        t, sleeps = _transport(
            [
                _FakeResp(429, b"{}", {"Retry-After": "2"}),
                _FakeResp(200, b'{"ok": true}'),
            ]
        )
        assert t.request("GET", "/x") == {"ok": True}
        assert sleeps == [2.0]

    def test_clamps_to_max(self):
        t, sleeps = _transport(
            [
                _FakeResp(429, b"{}", {"Retry-After": "9999"}),
                _FakeResp(200, b"{}"),
            ]
        )
        t.request("GET", "/x")
        assert sleeps == [MAX_RETRY_AFTER]

    def test_negative_clamped_to_zero(self):
        t, sleeps = _transport(
            [
                _FakeResp(503, b"{}", {"Retry-After": "-5"}),
                _FakeResp(200, b"{}"),
            ]
        )
        t.request("GET", "/x")
        assert sleeps == [0.0]

    def test_disabled_falls_back_to_backoff(self):
        t, sleeps = _transport(
            [
                _FakeResp(429, b"{}", {"Retry-After": "2"}),
                _FakeResp(200, b"{}"),
            ],
            respect=False,
        )
        t.request("GET", "/x")
        # Exponential backoff (1.0 * 2**0).
        assert sleeps == [1.0]


class TestRetryAfterDate:
    def test_http_date_in_future(self):
        now = 1_700_000_000.0
        future = datetime.fromtimestamp(now, tz=timezone.utc) + timedelta(seconds=5)
        header = format_datetime(future, usegmt=True)
        t, sleeps = _transport(
            [
                _FakeResp(429, b"{}", {"Retry-After": header}),
                _FakeResp(200, b"{}"),
            ],
            now=now,
        )
        t.request("GET", "/x")
        assert sleeps == [5.0]

    def test_http_date_in_past_clamped(self):
        now = 1_700_000_000.0
        past = datetime.fromtimestamp(now, tz=timezone.utc) - timedelta(seconds=60)
        header = format_datetime(past, usegmt=True)
        t, sleeps = _transport(
            [
                _FakeResp(429, b"{}", {"Retry-After": header}),
                _FakeResp(200, b"{}"),
            ],
            now=now,
        )
        t.request("GET", "/x")
        assert sleeps == [0.0]

    def test_invalid_header_falls_back(self):
        t, sleeps = _transport(
            [
                _FakeResp(429, b"{}", {"Retry-After": "tomorrow"}),
                _FakeResp(200, b"{}"),
            ]
        )
        t.request("GET", "/x")
        # Invalid Retry-After → exponential backoff (1.0 * 2**0).
        assert sleeps == [1.0]


class TestRetryAfterOnHTTPError:
    def test_http_error_respects_header(self):
        import urllib.error

        err = urllib.error.HTTPError(
            "https://api.test/x",
            429,
            "Too Many Requests",
            {"Retry-After": "3"},
            BytesIO(b"{}"),
        )
        t, sleeps = _transport([err, _FakeResp(200, b'{"ok": 1}')])
        assert t.request("GET", "/x") == {"ok": 1}
        assert sleeps == [3.0]

    def test_exhausted_retries_raises_rate_limit(self):
        t, sleeps = _transport(
            [
                _FakeResp(429, b'{"detail": "slow"}', {"Retry-After": "1"}),
                _FakeResp(429, b'{"detail": "slow"}', {"Retry-After": "1"}),
                _FakeResp(429, b'{"detail": "slow"}', {"Retry-After": "1"}),
            ],
            max_retries=2,
        )
        with pytest.raises(RateLimitError):
            t.request("GET", "/x")
        assert sleeps == [1.0, 1.0]
