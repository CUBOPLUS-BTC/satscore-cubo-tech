"""Tests for :class:`AsyncMagmaClient`."""

from __future__ import annotations

import asyncio

import pytest

from magma_sdk import AsyncMagmaClient, MagmaClient
from magma_sdk.exceptions import AuthenticationError, MagmaError


@pytest.fixture
def async_client(transport) -> AsyncMagmaClient:
    sync = MagmaClient("https://stub.local", transport=transport)
    return AsyncMagmaClient("https://stub.local", sync_client=sync)


def _run(coro):
    return asyncio.run(coro)


class TestAsyncBasics:
    def test_shares_sync_token(self, async_client):
        async_client.set_token("abc")
        assert async_client.token == "abc"
        assert async_client.is_authenticated()
        async_client.clear_token()
        assert async_client.token is None

    def test_set_token_validation(self, async_client):
        with pytest.raises(MagmaError):
            async_client.set_token("")

    def test_context_manager(self, transport, async_client):
        transport.set_response({"price_usd": 1, "sources_count": 1, "deviation": 0, "has_warning": False})

        async def go():
            async with async_client as c:
                return await c.price.get()

        quote = _run(go())
        assert quote.price_usd == 1


class TestAsyncResources:
    def test_price(self, transport, async_client):
        transport.set_response(
            {"price_usd": 70000, "sources_count": 2, "deviation": 0.1, "has_warning": False}
        )
        quote = _run(async_client.price.get())
        assert quote.price_usd == 70000
        assert transport.calls[-1]["path"] == "/price"

    def test_savings_project(self, transport, async_client):
        transport.set_response(
            {
                "monthly_usd": 100,
                "years": 5,
                "total_invested": 6000,
                "current_btc_price": 50000,
                "scenarios": [],
                "traditional_value": 6500,
                "monthly_data": [],
            }
        )
        res = _run(async_client.savings.project(monthly_usd=100, years=5))
        assert res.total_invested == 6000

    def test_pension_project(self, transport, async_client):
        transport.set_response(
            {
                "total_invested_usd": 24000,
                "total_btc_accumulated": 0.4,
                "current_value_usd": 48000,
                "avg_buy_price": 60000,
                "current_btc_price": 70000,
                "monthly_breakdown": [],
                "monthly_data": [],
            }
        )
        res = _run(async_client.pension.project(monthly_saving_usd=100, years=20))
        assert res.current_value_usd == 48000

    def test_remittance(self, transport, async_client):
        transport.set_response(
            {
                "channels": [],
                "annual_savings": 0,
                "best_channel": "",
                "savings_vs_worst": 0,
                "worst_channel_name": "",
                "best_time": None,
            }
        )
        res = _run(async_client.remittance.compare(amount_usd=100))
        assert res.best_channel == ""

    def test_fees(self, transport, async_client):
        transport.set_response({"halfHourFee": 7})
        assert _run(async_client.remittance.fees()) == {"halfHourFee": 7}

    def test_alerts_list(self, transport, async_client):
        transport.set_response(
            {"alerts": [{"type": "fee_low", "message": "m", "created_at": 1}]}
        )
        alerts = _run(async_client.alerts.list(limit=10))
        assert alerts[0].type == "fee_low"

    def test_alerts_status(self, transport, async_client):
        transport.set_response({"running": True})
        assert _run(async_client.alerts.status()) == {"running": True}

    def test_network(self, transport, async_client):
        transport.set_response({"height": 900000})
        assert _run(async_client.network.status()) == {"height": 900000}


class TestAsyncAuth:
    def test_requires_token_for_authed(self, async_client):
        with pytest.raises(AuthenticationError):
            _run(async_client.savings.progress())

    def test_verify_stores_token(self, transport, async_client):
        transport.set_response({"token": "t", "pubkey": "a" * 64})
        session = _run(
            async_client.auth.verify(
                signed_event={"pubkey": "a" * 64}, challenge="c"
            )
        )
        assert session.token == "t"
        assert async_client.token == "t"

    def test_lnurl_status_stores_token(self, transport, async_client):
        transport.set_response({"token": "tok", "pubkey": "b" * 64})
        status = _run(async_client.auth.lnurl_status("k1x"))
        assert status.authenticated is True
        assert async_client.token == "tok"

    def test_achievements_sends_token(self, transport, async_client):
        async_client.set_token("zz")
        transport.set_response({"level": 2})
        assert _run(async_client.gamification.achievements()) == {"level": 2}
        assert transport.calls[-1]["token"] == "zz"
