"""Tests for the Liquid HTTP route handlers."""

from __future__ import annotations

from unittest.mock import patch

from app.liquid import routes
from app.services.liquid_client import LBTC_ASSET_ID


class TestNetworkStatus:
    def test_happy_path(self):
        with patch.object(
            routes._client, "get_block_tip_height", return_value=3_242_517
        ), patch.object(
            routes._client, "recommended_fee_sat_vb", return_value=0.1
        ), patch.object(
            routes._client,
            "get_fee_estimates",
            return_value={"1": 0.1, "6": 0.1},
        ):
            body, status = routes.handle_network_status({})
        assert status == 200
        assert body["available"] is True
        assert body["block_height"] == 3_242_517
        assert body["recommended_fee_sat_vb"] == 0.1
        assert body["network"] == "liquid"

    def test_returns_unavailable_on_failure(self):
        with patch.object(
            routes._client,
            "get_block_tip_height",
            side_effect=TimeoutError("down"),
        ):
            body, status = routes.handle_network_status({})
        assert status == 200
        assert body["available"] is False
        assert "detail" in body


class TestAssetInfo:
    def test_rejects_invalid_id(self):
        body, status = routes.handle_asset_info({}, "not-hex")
        assert status == 400
        assert "detail" in body

    def test_returns_summary(self):
        with patch.object(
            routes._client,
            "get_asset_info",
            return_value={
                "asset_id": LBTC_ASSET_ID,
                "name": "Liquid Bitcoin",
                "ticker": "L-BTC",
                "precision": 8,
                "chain_stats": {
                    "issued_amount": 100_000_000,
                    "burned_amount": 1_000_000,
                },
            },
        ):
            body, status = routes.handle_asset_info({}, LBTC_ASSET_ID)
        assert status == 200
        assert body["ticker"] == "L-BTC"
        assert body["issued_amount"] == 100_000_000
        assert body["burned_amount"] == 1_000_000

    def test_handles_missing_chain_stats(self):
        with patch.object(
            routes._client,
            "get_asset_info",
            return_value={"asset_id": LBTC_ASSET_ID, "name": "X"},
        ):
            body, status = routes.handle_asset_info({}, LBTC_ASSET_ID)
        assert status == 200
        assert body["issued_amount"] is None

    def test_returns_502_on_upstream_failure(self):
        with patch.object(
            routes._client,
            "get_asset_info",
            side_effect=TimeoutError("down"),
        ):
            body, status = routes.handle_asset_info({}, LBTC_ASSET_ID)
        assert status == 502


class TestShortcuts:
    def test_lbtc_returns_summary(self):
        with patch.object(
            routes._client,
            "get_lbtc_info",
            return_value={
                "asset_id": LBTC_ASSET_ID,
                "ticker": "L-BTC",
            },
        ):
            body, status = routes.handle_lbtc({})
        assert status == 200
        assert body["ticker"] == "L-BTC"

    def test_lbtc_returns_fallback_on_failure(self):
        with patch.object(
            routes._client,
            "get_lbtc_info",
            side_effect=TimeoutError("down"),
        ):
            body, status = routes.handle_lbtc({})
        assert status == 200
        assert body["asset_id"] == LBTC_ASSET_ID

    def test_usdt_returns_summary(self):
        with patch.object(
            routes._client,
            "get_usdt_info",
            return_value={"ticker": "USDt", "precision": 8},
        ):
            body, status = routes.handle_usdt({})
        assert status == 200
        assert body["ticker"] == "USDt"
