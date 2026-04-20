"""High-level :class:`MagmaClient` that exposes every API resource."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from ._transport import HTTPTransport, OnRetry, TransportConfig
from .exceptions import AuthenticationError, MagmaError
from .resources import (
    AlertsResource,
    AuthResource,
    GamificationResource,
    LiquidResource,
    NetworkResource,
    PensionResource,
    PriceResource,
    RemittanceResource,
    SavingsResource,
)


class MagmaClient:
    """Main entry point for the Magma SDK.

    Example::

        client = MagmaClient("https://api.magma.example")
        projection = client.savings.project(monthly_usd=100, years=10)

    The client is safe to share across threads: individual requests
    never mutate shared state except for the bearer token, which is
    updated via :meth:`set_token` / :meth:`clear_token`.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff: float = 0.25,
        user_agent: Optional[str] = None,
        respect_retry_after: bool = True,
        on_retry: Optional[OnRetry] = None,
        transport: Optional[HTTPTransport] = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise MagmaError("base_url must be an http(s) URL")

        if transport is None:
            cfg_kwargs: dict[str, Any] = {
                "base_url": base_url,
                "timeout": timeout,
                "max_retries": max_retries,
                "backoff": backoff,
                "respect_retry_after": respect_retry_after,
                "on_retry": on_retry,
            }
            if user_agent:
                cfg_kwargs["user_agent"] = user_agent
            transport = HTTPTransport(TransportConfig(**cfg_kwargs))

        self._transport = transport
        self._token: Optional[str] = token

        # Attach resource clients.
        self.auth = AuthResource(self)
        self.savings = SavingsResource(self)
        self.pension = PensionResource(self)
        self.remittance = RemittanceResource(self)
        self.alerts = AlertsResource(self)
        self.gamification = GamificationResource(self)
        self.liquid = LiquidResource(self)
        self.network = NetworkResource(self)
        self.price = PriceResource(self)

    # ---- session management ----

    @property
    def token(self) -> Optional[str]:
        return self._token

    def set_token(self, token: str) -> None:
        if not isinstance(token, str) or not token:
            raise MagmaError("token must be a non-empty string")
        self._token = token

    def clear_token(self) -> None:
        self._token = None

    def is_authenticated(self) -> bool:
        return bool(self._token)

    # ---- health ----

    def health(self) -> dict:
        """GET /health — liveness check."""
        result = self._request("GET", "/health")
        return result if isinstance(result, dict) else {"status": "ok"}

    def wait_until_ready(
        self,
        timeout: float = 30.0,
        *,
        interval: float = 0.5,
        sleep=None,
        now=None,
    ) -> bool:
        """Poll ``/health`` until it returns 200 or ``timeout`` elapses.

        Returns ``True`` on success, ``False`` on timeout. Handy for
        container startup scripts and integration tests.
        """
        import time as _time

        _sleep = sleep or _time.sleep
        _now = now or _time.time

        if timeout <= 0:
            raise MagmaError("timeout must be positive")

        deadline = _now() + timeout
        while True:
            try:
                self.health()
                return True
            except Exception:
                if _now() >= deadline:
                    return False
                _sleep(max(0.0, min(interval, deadline - _now())))

    # ---- internal request helper ----

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        query: Optional[Mapping[str, Any]] = None,
        auth: bool = False,
        idempotency_key: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Any:
        token = None
        if auth:
            if not self._token:
                raise AuthenticationError(
                    status=401,
                    detail="This endpoint requires authentication. Call set_token() first.",
                )
            token = self._token
        return self._transport.request(
            method,
            path,
            json_body=json_body,
            query=query,
            token=token,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
