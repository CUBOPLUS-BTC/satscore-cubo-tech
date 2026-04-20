"""Async facade: :class:`AsyncMagmaClient`.

Mirrors the sync :class:`~magma_sdk.client.MagmaClient` API but exposes
every endpoint as an ``async def`` method, delegating the blocking
I/O to :func:`asyncio.to_thread`.

Usage::

    async with AsyncMagmaClient("https://api.magma.example") as client:
        quote = await client.price.get()
        projection = await client.savings.project(monthly_usd=100, years=10)
"""

from __future__ import annotations

from typing import Optional

from .async_resources import (
    AsyncAlertsResource,
    AsyncAuthResource,
    AsyncGamificationResource,
    AsyncNetworkResource,
    AsyncPensionResource,
    AsyncPriceResource,
    AsyncRemittanceResource,
    AsyncSavingsResource,
)
from .client import MagmaClient


class AsyncMagmaClient:
    """Async-compatible counterpart to :class:`MagmaClient`."""

    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff: float = 0.25,
        user_agent: Optional[str] = None,
        sync_client: Optional[MagmaClient] = None,
    ) -> None:
        if sync_client is not None:
            self._sync = sync_client
        else:
            kwargs = {
                "token": token,
                "timeout": timeout,
                "max_retries": max_retries,
                "backoff": backoff,
            }
            if user_agent:
                kwargs["user_agent"] = user_agent
            self._sync = MagmaClient(base_url, **kwargs)

        self.auth = AsyncAuthResource(self)
        self.savings = AsyncSavingsResource(self)
        self.pension = AsyncPensionResource(self)
        self.remittance = AsyncRemittanceResource(self)
        self.alerts = AsyncAlertsResource(self)
        self.gamification = AsyncGamificationResource(self)
        self.network = AsyncNetworkResource(self)
        self.price = AsyncPriceResource(self)

    @property
    def token(self) -> Optional[str]:
        return self._sync.token

    def set_token(self, token: str) -> None:
        self._sync.set_token(token)

    def clear_token(self) -> None:
        self._sync.clear_token()

    def is_authenticated(self) -> bool:
        return self._sync.is_authenticated()

    def _sync_token_from_inner(self) -> None:
        """Hook so async resources can re-read the token after auth flows.

        The sync client mutates its own token inside ``auth.verify`` /
        ``auth.lnurl_status``; since we delegate to it, nothing else is
        needed today. This method exists as a documented extension point
        for future session backends.
        """
        return None

    async def __aenter__(self) -> "AsyncMagmaClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None
