"""Async wrappers around the sync resources.

Each method delegates to its sync counterpart via :func:`asyncio.to_thread`,
so the SDK works naturally from ``async def`` code (FastAPI, aiohttp
handlers, trio via ``anyio``) without pulling in an async HTTP library.

Blocking I/O runs on the default thread pool — fine for the typical
SDK use case (a handful of outbound calls per request). If you need
true non-blocking throughput at scale, swap in ``httpx.AsyncClient``.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, List, Optional

from .models import (
    Alert,
    LiquidAsset,
    LiquidNetworkStatus,
    PensionProjection,
    PriceQuote,
    RemittanceComparison,
    SavingsProgress,
    SavingsProjection,
)
from .resources.auth import (
    AuthSession,
    Challenge,
    LnurlChallenge,
    LnurlStatus,
)

if TYPE_CHECKING:
    from .async_client import AsyncMagmaClient


class _AsyncBase:
    def __init__(self, client: "AsyncMagmaClient") -> None:
        self._client = client

    def _sync(self):
        return self._client._sync


class AsyncAuthResource(_AsyncBase):
    async def create_challenge(self, pubkey: str) -> Challenge:
        return await asyncio.to_thread(
            self._sync().auth.create_challenge, pubkey
        )

    async def verify(self, signed_event: dict, challenge: str) -> AuthSession:
        session = await asyncio.to_thread(
            self._sync().auth.verify, signed_event, challenge
        )
        self._client._sync_token_from_inner()
        return session

    async def me(self) -> dict:
        return await asyncio.to_thread(self._sync().auth.me)

    async def create_lnurl(self) -> LnurlChallenge:
        return await asyncio.to_thread(self._sync().auth.create_lnurl)

    async def lnurl_status(self, k1: str) -> LnurlStatus:
        status = await asyncio.to_thread(self._sync().auth.lnurl_status, k1)
        self._client._sync_token_from_inner()
        return status


class AsyncSavingsResource(_AsyncBase):
    async def project(
        self, monthly_usd: float, years: int = 10
    ) -> SavingsProjection:
        return await asyncio.to_thread(
            self._sync().savings.project, monthly_usd, years
        )

    async def create_goal(
        self, monthly_target_usd: float, target_years: int = 10
    ) -> dict:
        return await asyncio.to_thread(
            self._sync().savings.create_goal, monthly_target_usd, target_years
        )

    async def record_deposit(self, amount_usd: float) -> dict:
        return await asyncio.to_thread(
            self._sync().savings.record_deposit, amount_usd
        )

    async def progress(self) -> SavingsProgress:
        return await asyncio.to_thread(self._sync().savings.progress)


class AsyncPensionResource(_AsyncBase):
    async def project(
        self, monthly_saving_usd: float, years: int
    ) -> PensionProjection:
        return await asyncio.to_thread(
            self._sync().pension.project, monthly_saving_usd, years
        )


class AsyncRemittanceResource(_AsyncBase):
    async def compare(
        self, amount_usd: float, frequency: str = "monthly"
    ) -> RemittanceComparison:
        return await asyncio.to_thread(
            self._sync().remittance.compare, amount_usd, frequency
        )

    async def fees(self) -> dict:
        return await asyncio.to_thread(self._sync().remittance.fees)


class AsyncAlertsResource(_AsyncBase):
    async def list(self, limit: int = 20) -> List[Alert]:
        return await asyncio.to_thread(self._sync().alerts.list, limit)

    async def status(self) -> dict:
        return await asyncio.to_thread(self._sync().alerts.status)

    async def stream(
        self,
        *,
        since: Optional[int] = None,
        poll_interval: float = 5.0,
        limit: int = 50,
        max_iterations: Optional[int] = None,
    ):
        """Async generator yielding alerts as the monitor surfaces them.

        Parameters mirror :meth:`AlertsResource.iter_new`, but the loop
        sleeps via :func:`asyncio.sleep` so the event loop keeps running.
        """
        if poll_interval < 0:
            raise ValueError("poll_interval must be >= 0")

        cursor = since
        seen: set = set()
        iteration = 0

        from .resources.alerts import _alert_key  # local import to avoid cycles

        while True:
            iteration += 1
            alerts = await self.list(limit=limit)
            alerts.sort(key=lambda a: (a.created_at or 0))
            for alert in alerts:
                ts = alert.created_at
                key = _alert_key(alert)
                if cursor is not None and ts is not None and ts <= cursor:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                yield alert
                if ts is not None:
                    cursor = ts if cursor is None else max(cursor, ts)

            if max_iterations is not None and iteration >= max_iterations:
                return
            if poll_interval > 0:
                await asyncio.sleep(poll_interval)


class AsyncGamificationResource(_AsyncBase):
    async def achievements(self) -> dict:
        return await asyncio.to_thread(self._sync().gamification.achievements)


class AsyncNetworkResource(_AsyncBase):
    async def status(self) -> dict:
        return await asyncio.to_thread(self._sync().network.status)


class AsyncPriceResource(_AsyncBase):
    async def get(self) -> PriceQuote:
        return await asyncio.to_thread(self._sync().price.get)


class AsyncLiquidResource(_AsyncBase):
    async def status(self) -> LiquidNetworkStatus:
        return await asyncio.to_thread(self._sync().liquid.status)

    async def lbtc(self) -> LiquidAsset:
        return await asyncio.to_thread(self._sync().liquid.lbtc)

    async def usdt(self) -> LiquidAsset:
        return await asyncio.to_thread(self._sync().liquid.usdt)

    async def asset(self, asset_id: str) -> LiquidAsset:
        return await asyncio.to_thread(self._sync().liquid.asset, asset_id)
