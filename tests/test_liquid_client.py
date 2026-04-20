from unittest.mock import patch

import pytest

from app.services.liquid_client import (
    LBTC_ASSET_ID,
    USDT_ASSET_ID,
    LiquidClient,
)


@pytest.fixture
def client():
    c = LiquidClient()
    c._shared_cache.clear()
    return c


class TestFeeEstimates:
    def test_recommended_picks_cheapest_satisfying_target(self, client):
        # Among block targets >= 2 (i.e. 2 and 6), choose the cheapest.
        with patch.object(
            LiquidClient,
            "get_fee_estimates",
            return_value={"1": 0.2, "2": 0.15, "6": 0.12},
        ):
            assert client.recommended_fee_sat_vb(target_blocks=2) == 0.12

    def test_recommended_ignores_faster_targets(self, client):
        # target=3 — only '6' qualifies; '1' and '2' are faster but we asked
        # for 3-block confirmation so we should not pick them.
        with patch.object(
            LiquidClient,
            "get_fee_estimates",
            return_value={"1": 0.5, "2": 0.4, "6": 0.2},
        ):
            assert client.recommended_fee_sat_vb(target_blocks=3) == 0.2

    def test_recommended_floors_at_minimum(self, client):
        with patch.object(
            LiquidClient, "get_fee_estimates", return_value={"2": 0.05}
        ):
            # Floor at 0.1 sat/vB.
            assert client.recommended_fee_sat_vb(target_blocks=2) == 0.1

    def test_recommended_falls_back_to_cheapest(self, client):
        # Nothing satisfies target=10, so return the cheapest present.
        with patch.object(
            LiquidClient, "get_fee_estimates", return_value={"1": 0.5, "2": 0.4}
        ):
            # min(0.5, 0.4) = 0.4 (>= 0.1 floor)
            assert client.recommended_fee_sat_vb(target_blocks=10) == 0.4

    def test_recommended_default_on_failure(self, client):
        with patch.object(LiquidClient, "get_fee_estimates", return_value={}):
            assert client.recommended_fee_sat_vb() == 0.1

    def test_estimates_filters_non_numeric(self, client):
        with patch(
            "app.services.liquid_client.cached_http_get",
            return_value={"1": 0.1, "bad": "nope", "2": "no"},
        ):
            estimates = client.get_fee_estimates()
            assert estimates == {"1": 0.1}

    def test_estimates_returns_empty_on_non_dict(self, client):
        with patch(
            "app.services.liquid_client.cached_http_get",
            return_value="not a dict",
        ):
            assert client.get_fee_estimates() == {}

    def test_estimates_returns_empty_on_exception(self, client):
        def boom(*a, **kw):
            raise TimeoutError("down")

        with patch("app.services.liquid_client.cached_http_get", side_effect=boom):
            assert client.get_fee_estimates() == {}


class TestBlockTip:
    def test_height_parses(self, client):
        with patch.object(LiquidClient, "_get_text", return_value="3242517"):
            assert client.get_block_tip_height() == 3242517

    def test_height_missing_raises(self, client):
        with patch.object(LiquidClient, "_get_text", return_value=None):
            with pytest.raises(ValueError):
                client.get_block_tip_height()

    def test_height_non_numeric_raises(self, client):
        with patch.object(LiquidClient, "_get_text", return_value="nope"):
            with pytest.raises(ValueError):
                client.get_block_tip_height()

    def test_tip_hash_valid(self, client):
        hex_hash = "a" * 64
        with patch.object(LiquidClient, "_get_text", return_value=hex_hash):
            assert client.get_block_tip_hash() == hex_hash

    def test_tip_hash_invalid(self, client):
        with patch.object(LiquidClient, "_get_text", return_value="short"):
            with pytest.raises(ValueError):
                client.get_block_tip_hash()


class TestAssetInfo:
    def test_validates_asset_id(self, client):
        with pytest.raises(ValueError):
            client.get_asset_info("not-hex")
        with pytest.raises(ValueError):
            client.get_asset_info("abc")

    def test_returns_dict_on_success(self, client):
        with patch(
            "app.services.liquid_client.cached_http_get",
            return_value={"asset_id": LBTC_ASSET_ID, "name": "Liquid Bitcoin"},
        ):
            info = client.get_asset_info(LBTC_ASSET_ID)
            assert info["name"] == "Liquid Bitcoin"

    def test_returns_empty_on_non_dict(self, client):
        with patch(
            "app.services.liquid_client.cached_http_get",
            return_value="nope",
        ):
            assert client.get_asset_info(LBTC_ASSET_ID) == {}

    def test_lbtc_shortcut(self, client):
        captured = {}

        def fake(cache, key, url, ttl, **kw):
            captured["key"] = key
            return {"asset_id": LBTC_ASSET_ID}

        with patch("app.services.liquid_client.cached_http_get", side_effect=fake):
            client.get_lbtc_info()
        assert LBTC_ASSET_ID in captured["key"]

    def test_usdt_shortcut(self, client):
        captured = {}

        def fake(cache, key, url, ttl, **kw):
            captured["key"] = key
            return {}

        with patch("app.services.liquid_client.cached_http_get", side_effect=fake):
            client.get_usdt_info()
        assert USDT_ASSET_ID in captured["key"]
