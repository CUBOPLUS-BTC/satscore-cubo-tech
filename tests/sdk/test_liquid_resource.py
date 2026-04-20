"""Tests for :class:`LiquidResource` (sync + async)."""

from __future__ import annotations

import asyncio

import pytest

from magma_sdk import MagmaError


LBTC = "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d"


class TestStatus:
    def test_parses_status(self, transport, client):
        transport.set_response(
            {
                "available": True,
                "block_height": 3242517,
                "recommended_fee_sat_vb": 0.1,
                "fee_estimates": {"1": 0.1, "6": 0.1},
                "network": "liquid",
            }
        )
        status = client.liquid.status()
        assert transport.calls[-1]["path"] == "/liquid/status"
        assert status.available is True
        assert status.block_height == 3242517
        assert status.recommended_fee_sat_vb == 0.1
        assert status.fee_estimates == {"1": 0.1, "6": 0.1}

    def test_handles_unavailable(self, transport, client):
        transport.set_response({"available": False, "detail": "blockstream down"})
        status = client.liquid.status()
        assert status.available is False
        assert status.block_height is None

    def test_handles_non_dict(self, transport, client):
        transport.set_response(None)
        status = client.liquid.status()
        assert status.available is False
        assert status.network == "liquid"


class TestAssets:
    def test_lbtc(self, transport, client):
        transport.set_response(
            {
                "asset_id": LBTC,
                "name": "Liquid Bitcoin",
                "ticker": "L-BTC",
                "precision": 8,
                "issued_amount": 450_000_000,
                "burned_amount": 10_000_000,
            }
        )
        asset = client.liquid.lbtc()
        assert transport.calls[-1]["path"] == "/liquid/lbtc"
        assert asset.asset_id == LBTC
        assert asset.ticker == "L-BTC"
        assert asset.precision == 8
        assert asset.issued_amount == 450_000_000

    def test_usdt(self, transport, client):
        transport.set_response({"ticker": "USDt", "precision": 8})
        asset = client.liquid.usdt()
        assert transport.calls[-1]["path"] == "/liquid/usdt"
        assert asset.ticker == "USDt"

    def test_asset_passthrough(self, transport, client):
        transport.set_response({"asset_id": LBTC, "name": "L-BTC"})
        asset = client.liquid.asset(LBTC)
        assert transport.calls[-1]["path"] == f"/liquid/asset/{LBTC}"
        assert asset.name == "L-BTC"

    def test_asset_rejects_bad_id(self, client):
        with pytest.raises(MagmaError):
            client.liquid.asset("not-hex")
        with pytest.raises(MagmaError):
            client.liquid.asset("")
        with pytest.raises(MagmaError):
            client.liquid.asset(123)  # type: ignore[arg-type]

    def test_handles_missing_fields(self, transport, client):
        transport.set_response({})
        asset = client.liquid.lbtc()
        assert asset.asset_id is None
        assert asset.name is None
        assert asset.precision is None


class TestAsyncLiquid:
    def _client(self, transport):
        from magma_sdk import AsyncMagmaClient, MagmaClient

        sync = MagmaClient("https://stub.local", transport=transport)
        return AsyncMagmaClient("https://stub.local", sync_client=sync)

    def test_async_status(self, transport):
        transport.set_response(
            {"available": True, "block_height": 1, "network": "liquid"}
        )
        async_client = self._client(transport)

        async def go():
            return await async_client.liquid.status()

        status = asyncio.run(go())
        assert status.available is True
        assert status.block_height == 1

    def test_async_lbtc(self, transport):
        transport.set_response({"ticker": "L-BTC"})
        async_client = self._client(transport)

        async def go():
            return await async_client.liquid.lbtc()

        asset = asyncio.run(go())
        assert asset.ticker == "L-BTC"

    def test_async_asset_passes_id(self, transport):
        transport.set_response({"asset_id": LBTC})
        async_client = self._client(transport)

        async def go():
            return await async_client.liquid.asset(LBTC)

        asyncio.run(go())
        assert transport.calls[-1]["path"] == f"/liquid/asset/{LBTC}"
