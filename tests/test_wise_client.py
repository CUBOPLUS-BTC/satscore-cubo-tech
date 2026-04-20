from unittest.mock import patch

import pytest

from app.services.wise_client import WiseClient


def _fetch(data):
    def fake_get(self, key, url, ttl):
        return data

    return fake_get


@pytest.fixture
def client():
    c = WiseClient()
    c._shared_cache.clear()
    return c


class TestParseDelivery:
    def test_empty(self, client):
        assert client._parse_delivery({}) == "Unknown"
        assert client._parse_delivery({"duration": None}) == "Unknown"

    def test_minutes(self, client):
        assert client._parse_delivery({"duration": {"max": "PT30M"}}) == "Minutes"

    def test_hours(self, client):
        assert client._parse_delivery({"duration": {"max": "PT6H"}}) == "6 hours"

    def test_one_day(self, client):
        assert client._parse_delivery({"duration": {"max": "PT24H"}}) == "1 day"

    def test_multiple_days(self, client):
        assert client._parse_delivery({"duration": {"max": "PT72H"}}) == "3 days"

    def test_invalid_duration_string(self, client):
        assert client._parse_delivery({"duration": {"max": "garbage"}}) == "Unknown"


class TestIsoToHours:
    def test_none(self, client):
        assert client._iso_to_hours("") is None
        assert client._iso_to_hours("invalid") is None

    def test_hours_only(self, client):
        assert client._iso_to_hours("PT5H") == 5.0

    def test_hours_and_minutes(self, client):
        assert client._iso_to_hours("PT1H30M") == pytest.approx(1.5)

    def test_with_seconds(self, client):
        assert client._iso_to_hours("PT0H0M3600S") == pytest.approx(1.0)

    def test_empty_rest_after_pt(self, client):
        assert client._iso_to_hours("PT") == 0.0


class TestGetComparison:
    def test_rejects_non_positive_amount(self, client):
        assert client.get_comparison(0) is None
        assert client.get_comparison(-5) is None

    def test_rejects_nan_amount(self, client):
        assert client.get_comparison(float("nan")) is None
        assert client.get_comparison(float("inf")) is None

    def test_empty_providers(self, client):
        with patch.object(WiseClient, "_get", _fetch({"providers": []})):
            assert client.get_comparison(100) is None

    def test_non_dict_response(self, client):
        with patch.object(WiseClient, "_get", _fetch("not-a-dict")):
            assert client.get_comparison(100) is None

    def test_missing_providers_key(self, client):
        with patch.object(WiseClient, "_get", _fetch({})):
            assert client.get_comparison(100) is None

    def test_network_error_returns_none(self, client):
        def boom(self, key, url, ttl):
            raise TimeoutError("down")

        with patch.object(WiseClient, "_get", boom):
            assert client.get_comparison(100) is None

    def test_provider_without_quotes_skipped(self, client):
        payload = {
            "providers": [
                {"name": "NoQuotes", "quotes": []},
                {"name": "BadShape"},
            ]
        }
        with patch.object(WiseClient, "_get", _fetch(payload)):
            assert client.get_comparison(100) is None

    def test_happy_path(self, client):
        payload = {
            "providers": [
                {
                    "name": "Remitly",
                    "quotes": [
                        {
                            "fee": 3.99,
                            "receivedAmount": 96.01,
                            "deliveryEstimation": {"duration": {"max": "PT2H"}},
                        }
                    ],
                }
            ]
        }
        with patch.object(WiseClient, "_get", _fetch(payload)):
            result = client.get_comparison(100)
        assert result is not None
        assert len(result) == 1
        r = result[0]
        assert r["name"] == "Remitly"
        assert r["fee_usd"] == 3.99
        assert r["fee_percent"] == pytest.approx(3.99)
        assert r["amount_received"] == 96.01
        assert r["estimated_time"] == "2 hours"
        assert r["is_live"] is True

    def test_non_numeric_fee_skipped(self, client):
        payload = {
            "providers": [
                {
                    "name": "Bad",
                    "quotes": [{"fee": "oops", "receivedAmount": 95}],
                },
                {
                    "name": "Good",
                    "quotes": [{"fee": 5, "receivedAmount": 95}],
                },
            ]
        }
        with patch.object(WiseClient, "_get", _fetch(payload)):
            result = client.get_comparison(100)
        assert result is not None
        assert [r["name"] for r in result] == ["Good"]

    def test_negative_fee_skipped(self, client):
        payload = {
            "providers": [
                {"name": "Bad", "quotes": [{"fee": -5, "receivedAmount": 105}]}
            ]
        }
        with patch.object(WiseClient, "_get", _fetch(payload)):
            assert client.get_comparison(100) is None

    def test_bool_fee_rejected(self, client):
        payload = {
            "providers": [
                {"name": "Bool", "quotes": [{"fee": True, "receivedAmount": 99}]}
            ]
        }
        with patch.object(WiseClient, "_get", _fetch(payload)):
            assert client.get_comparison(100) is None
