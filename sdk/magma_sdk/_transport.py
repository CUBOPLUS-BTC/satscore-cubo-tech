"""HTTP transport used by the SDK.

Stdlib-only (``urllib.request``) to avoid pulling in a dependency on
``requests``. Supports per-request timeout, bounded retries with
exponential backoff on transient failures (connection / 5xx / 429),
bearer-token auth, structured error decoding, ``Retry-After``,
``X-Request-Id`` propagation, idempotency keys, and an observable
``on_retry`` callback.
"""

from __future__ import annotations

import email.utils
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from .exceptions import TransportError, api_error_for


DEFAULT_USER_AGENT = "magma-sdk-python/0.4.0"
_RETRIABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
# Upper bound enforced on any Retry-After value (seconds) so a
# misbehaving server can't stall the client indefinitely.
MAX_RETRY_AFTER = 60.0

REQUEST_ID_HEADER = "X-Request-Id"
IDEMPOTENCY_HEADER = "Idempotency-Key"


@dataclass(frozen=True)
class RetryEvent:
    """Passed to ``on_retry`` callbacks on each retry decision."""

    attempt: int
    method: str
    path: str
    status: Optional[int]
    delay: float
    error: Optional[BaseException]
    request_id: Optional[str]


OnRetry = Callable[[RetryEvent], None]


@dataclass(frozen=True)
class TransportConfig:
    base_url: str
    timeout: float = 10.0
    max_retries: int = 2
    backoff: float = 0.25
    user_agent: str = DEFAULT_USER_AGENT
    respect_retry_after: bool = True
    on_retry: Optional[OnRetry] = field(default=None, compare=False)


def generate_request_id() -> str:
    """Return a new request id (UUID4 hex, 32 chars)."""
    return uuid.uuid4().hex


class HTTPTransport:
    """Thin wrapper around :mod:`urllib.request` with retries and errors."""

    def __init__(
        self,
        config: TransportConfig,
        *,
        opener: Optional[Callable[..., Any]] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.time,
        request_id_factory: Callable[[], str] = generate_request_id,
    ) -> None:
        self._config = config
        self._opener = opener or urllib.request.urlopen
        self._sleep = sleep
        self._now = now
        self._request_id_factory = request_id_factory

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
        idempotency_key: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Any:
        url = self._build_url(path, query)
        data: Optional[bytes] = None
        req_id = request_id or self._request_id_factory()
        headers = {
            "Accept": "application/json",
            "User-Agent": self._config.user_agent,
            REQUEST_ID_HEADER: req_id,
        }
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if idempotency_key:
            headers[IDEMPOTENCY_HEADER] = idempotency_key
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
                    delay = self._compute_delay(attempt, response_headers)
                    self._notify_retry(attempt, method, path, status, delay, None, req_id)
                    self._sleep(delay)
                    continue
                detail = body.get("detail") if isinstance(body, dict) else None
                raise api_error_for(status, detail, body)
            except urllib.error.HTTPError as exc:
                raw = exc.read() if hasattr(exc, "read") else b""
                body = self._decode(raw)
                status = exc.code
                response_headers = _headers_to_dict(getattr(exc, "headers", None))
                if status in _RETRIABLE_STATUS and attempt <= self._config.max_retries:
                    delay = self._compute_delay(attempt, response_headers)
                    self._notify_retry(attempt, method, path, status, delay, exc, req_id)
                    self._sleep(delay)
                    continue
                detail = body.get("detail") if isinstance(body, dict) else None
                raise api_error_for(status, detail, body) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                if attempt <= self._config.max_retries:
                    delay = self._compute_delay(attempt, None)
                    self._notify_retry(attempt, method, path, None, delay, exc, req_id)
                    self._sleep(delay)
                    continue
                raise TransportError(f"Request to {url} failed: {exc}") from exc

    def _compute_delay(
        self, attempt: int, headers: Optional[Mapping[str, str]]
    ) -> float:
        """Return the backoff to sleep before ``attempt``'s retry."""
        retry_after = (
            _parse_retry_after(headers, self._now())
            if headers and self._config.respect_retry_after
            else None
        )
        if retry_after is not None:
            return max(0.0, min(retry_after, MAX_RETRY_AFTER))
        return self._config.backoff * (2 ** (attempt - 1))

    def _notify_retry(
        self,
        attempt: int,
        method: str,
        path: str,
        status: Optional[int],
        delay: float,
        error: Optional[BaseException],
        request_id: str,
    ) -> None:
        hook = self._config.on_retry
        if hook is None:
            return
        event = RetryEvent(
            attempt=attempt,
            method=method,
            path=path,
            status=status,
            delay=delay,
            error=error,
            request_id=request_id,
        )
        try:
            hook(event)
        except Exception:
            # Observability hooks must never break the request pipeline.
            pass

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
    """Parse ``Retry-After`` as seconds (int) or HTTP-date."""
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
