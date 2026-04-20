"""HTTP transport used by the SDK.

Stdlib-only (``urllib.request``) to avoid pulling in a dependency on
``requests``. Supports per-request timeout, bounded retries with
exponential backoff on transient failures (connection / 5xx / 429),
bearer-token auth, structured error decoding, and honours ``Retry-After``.
"""

from __future__ import annotations

import email.utils
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .exceptions import TransportError, api_error_for


DEFAULT_USER_AGENT = "magma-sdk-python/0.2.0"
_RETRIABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
# Upper bound enforced on any Retry-After value (seconds) so a
# misbehaving server can't stall the client indefinitely.
MAX_RETRY_AFTER = 60.0


@dataclass(frozen=True)
class TransportConfig:
    base_url: str
    timeout: float = 10.0
    max_retries: int = 2
    backoff: float = 0.25
    user_agent: str = DEFAULT_USER_AGENT
    respect_retry_after: bool = True


class HTTPTransport:
    """Thin wrapper around :mod:`urllib.request` with retries and errors."""

    def __init__(
        self,
        config: TransportConfig,
        *,
        opener: Optional[Callable[..., Any]] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._opener = opener or urllib.request.urlopen
        self._sleep = sleep
        self._now = now

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        query: Optional[Mapping[str, Any]] = None,
        token: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        url = self._build_url(path, query)
        data: Optional[bytes] = None
        headers = {
            "Accept": "application/json",
            "User-Agent": self._config.user_agent,
        }
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(
            url, data=data, method=method.upper(), headers=headers
        )

        attempt = 0
        while True:
            attempt += 1
            try:
                with self._opener(req, timeout=self._config.timeout) as response:
                    status = getattr(response, "status", None) or response.getcode()
                    response_headers = _headers_to_dict(
                        getattr(response, "headers", None)
                    )
                    raw = response.read()
                body = self._decode(raw)
                if 200 <= status < 300:
                    return body
                if status in _RETRIABLE_STATUS and attempt <= self._config.max_retries:
                    self._sleep(self._compute_delay(attempt, response_headers))
                    continue
                detail = body.get("detail") if isinstance(body, dict) else None
                raise api_error_for(status, detail, body)
            except urllib.error.HTTPError as exc:
                raw = exc.read() if hasattr(exc, "read") else b""
                body = self._decode(raw)
                status = exc.code
                response_headers = _headers_to_dict(getattr(exc, "headers", None))
                if status in _RETRIABLE_STATUS and attempt <= self._config.max_retries:
                    self._sleep(self._compute_delay(attempt, response_headers))
                    continue
                detail = body.get("detail") if isinstance(body, dict) else None
                raise api_error_for(status, detail, body) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                if attempt <= self._config.max_retries:
                    self._sleep(self._compute_delay(attempt, None))
                    continue
                raise TransportError(f"Request to {url} failed: {exc}") from exc

    def _compute_delay(
        self, attempt: int, headers: Optional[Mapping[str, str]]
    ) -> float:
        """Return the backoff to sleep before ``attempt``'s retry.

        Honours an upstream ``Retry-After`` header (seconds or HTTP-date)
        when ``respect_retry_after`` is on; otherwise falls back to
        exponential backoff.
        """
        retry_after = (
            _parse_retry_after(headers, self._now())
            if headers and self._config.respect_retry_after
            else None
        )
        if retry_after is not None:
            return max(0.0, min(retry_after, MAX_RETRY_AFTER))
        return self._config.backoff * (2 ** (attempt - 1))

    def _build_url(self, path: str, query: Optional[Mapping[str, Any]]) -> str:
        base = self._config.base_url.rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        url = f"{base}{path}"
        if query:
            cleaned = {k: v for k, v in query.items() if v is not None}
            if cleaned:
                url = f"{url}?{urllib.parse.urlencode(cleaned)}"
        return url

    @staticmethod
    def _decode(raw: bytes) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise TransportError("Server returned non-JSON response") from exc


def _headers_to_dict(headers: Any) -> Optional[dict]:
    if headers is None:
        return None
    try:
        items = headers.items()
    except AttributeError:
        return None
    return {str(k).lower(): str(v) for k, v in items}


def _parse_retry_after(headers: Mapping[str, str], now: float) -> Optional[float]:
    """Parse ``Retry-After`` as seconds (int) or HTTP-date.

    Returns seconds until the retry, or ``None`` if the header is absent
    or cannot be parsed.
    """
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if parsed is None:
            return None
        target = parsed.timestamp()
        delta = target - now
        return delta if delta >= 0 else 0.0
    return seconds if seconds >= 0 else 0.0
