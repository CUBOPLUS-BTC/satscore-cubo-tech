"""Tests for service clients.

Covers:
- PriceAggregator.get_verified_price() median logic
- PriceUnavailableError when no sources respond
- Cache behavior of CoinGeckoClient
- MockHTTPResponse helper class
- Error handling paths
"""

import sys
import os
import json
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import MockHTTPResponse


# ---------------------------------------------------------------------------
# MockHTTPResponse self-tests
# ---------------------------------------------------------------------------


class TestMockHTTPResponse(unittest.TestCase):

    def test_read_returns_body(self):
        body = b'{"price": 60000}'
        mock = MockHTTPResponse(body)
        self.assertEqual(mock.read(), body)

    def test_status_code(self):
        mock = MockHTTPResponse(b"", status=404)
        self.assertEqual(mock.getcode(), 404)

    def test_context_manager(self):
        mock = MockHTTPResponse(b"ok")
        with mock as resp:
            self.assertEqual(resp.read(), b"ok")

    def test_getheader(self):
        mock = MockHTTPResponse(b"", headers={"X-Custom": "value"})
        self.assertEqual(mock.getheader("X-Custom"), "value")

    def test_getheader_default(self):
        mock = MockHTTPResponse(b"")
        self.assertIsNone(mock.getheader("X-Missing"))


# ---------------------------------------------------------------------------
# PriceAggregator
# ---------------------------------------------------------------------------


class TestPriceAggregatorMedian(unittest.TestCase):

    def _build(self, cg_price=None, kraken_price=None):
        from app.services.price_aggregator import PriceAggregator
        agg = PriceAggregator.__new__(PriceAggregator)
        mock_cg = MagicMock()
        mock_kraken = MagicMock()

        if cg_price is not None:
            mock_cg.get_price.return_value = cg_price
        else:
            mock_cg.get_price.side_effect = Exception("timeout")

        if kraken_price is not None:
            mock_kraken.get_price.return_value = kraken_price
        else:
            mock_kraken.get_price.side_effect = Exception("timeout")

        agg.coingecko = mock_cg
        agg.kraken = mock_kraken
        return agg

    def test_returns_dict(self):
        agg = self._build(cg_price=60000.0, kraken_price=60100.0)
        result = agg.get_verified_price()
        self.assertIsInstance(result, dict)

    def test_has_price_usd(self):
        agg = self._build(cg_price=60000.0, kraken_price=60000.0)
        result = agg.get_verified_price()
        self.assertIn("price_usd", result)

    def test_median_two_prices(self):
        agg = self._build(cg_price=60000.0, kraken_price=62000.0)
        result = agg.get_verified_price()
        # median of sorted [60000, 62000] -> 62000 (upper median, index len//2)
        self.assertIn(result["price_usd"], [60000.0, 62000.0])

    def test_single_source_returns_price(self):
        agg = self._build(cg_price=60000.0, kraken_price=None)
        result = agg.get_verified_price()
        self.assertAlmostEqual(result["price_usd"], 60000.0)

    def test_single_source_has_warning(self):
        agg = self._build(cg_price=60000.0, kraken_price=None)
        result = agg.get_verified_price()
        self.assertTrue(result["has_warning"])

    def test_two_sources_no_warning(self):
        agg = self._build(cg_price=60000.0, kraken_price=60000.0)
        result = agg.get_verified_price()
        self.assertFalse(result["has_warning"])

    def test_no_sources_raises(self):
        from app.services.price_aggregator import PriceUnavailableError
        agg = self._build(cg_price=None, kraken_price=None)
        with self.assertRaises(PriceUnavailableError):
            agg.get_verified_price()

    def test_sources_count_two(self):
        agg = self._build(cg_price=60000.0, kraken_price=61000.0)
        result = agg.get_verified_price()
        self.assertEqual(result["sources_count"], 2)

    def test_sources_count_one(self):
        agg = self._build(cg_price=60000.0, kraken_price=None)
        result = agg.get_verified_price()
        self.assertEqual(result["sources_count"], 1)

    def test_deviation_zero_when_same_price(self):
        agg = self._build(cg_price=60000.0, kraken_price=60000.0)
        result = agg.get_verified_price()
        self.assertAlmostEqual(result["deviation"], 0.0)

    def test_deviation_positive_when_different(self):
        agg = self._build(cg_price=60000.0, kraken_price=61200.0)
        result = agg.get_verified_price()
        self.assertGreater(result["deviation"], 0.0)


# ---------------------------------------------------------------------------
# CoinGeckoClient caching
# ---------------------------------------------------------------------------


class TestCoinGeckoClientCache(unittest.TestCase):

    def setUp(self):
        # Clear shared cache before each test
        from app.services.coingecko_client import CoinGeckoClient
        CoinGeckoClient._shared_cache.clear()

    def test_cache_hit_does_not_call_network_twice(self):
        from app.services.coingecko_client import CoinGeckoClient
        client = CoinGeckoClient()
        price_data = {"bitcoin": {"usd": 65000.0}}
        response_body = json.dumps(price_data).encode()
        mock_response = MockHTTPResponse(response_body)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            p1 = client.get_price()
            p2 = client.get_price()

        # urlopen should only be called once (second call hits cache)
        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertAlmostEqual(p1, 65000.0)
        self.assertAlmostEqual(p2, 65000.0)

    def test_expired_cache_refetches(self):
        from app.services.coingecko_client import CoinGeckoClient
        client = CoinGeckoClient()
        key = "btc_price"
        # Manually put an expired entry
        CoinGeckoClient._shared_cache[key] = ({"bitcoin": {"usd": 50000.0}}, time.time() - 10)

        price_data = {"bitcoin": {"usd": 70000.0}}
        mock_response = MockHTTPResponse(json.dumps(price_data).encode())

        with patch("urllib.request.urlopen", return_value=mock_response):
            price = client.get_price()

        self.assertAlmostEqual(price, 70000.0)

    def test_get_price_returns_float(self):
        from app.services.coingecko_client import CoinGeckoClient
        client = CoinGeckoClient()
        price_data = {"bitcoin": {"usd": 55000.0}}
        mock_response = MockHTTPResponse(json.dumps(price_data).encode())

        with patch("urllib.request.urlopen", return_value=mock_response):
            price = client.get_price()

        self.assertIsInstance(price, float)

    def test_get_historical_prices_returns_list(self):
        from app.services.coingecko_client import CoinGeckoClient
        client = CoinGeckoClient()
        hist_data = {"prices": [[1000000, 50000.0], [2000000, 55000.0]]}
        mock_response = MockHTTPResponse(json.dumps(hist_data).encode())

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.get_historical_prices(days=7)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_network_error_propagates(self):
        from app.services.coingecko_client import CoinGeckoClient
        import urllib.error
        client = CoinGeckoClient()
        CoinGeckoClient._shared_cache.clear()

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            with self.assertRaises(urllib.error.URLError):
                client.get_price()


if __name__ == "__main__":
    unittest.main()
