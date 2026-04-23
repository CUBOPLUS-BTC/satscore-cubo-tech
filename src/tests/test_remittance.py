"""Tests for the remittance module.

Covers:
- ChannelComparison / RemittanceResponse / SendTimeRecommendation schemas
- Fee calculation and best-send-time logic (FeeTracker)
- Optimizer comparison logic (RemittanceOptimizer) with mocked external calls
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from dataclasses import asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.remittance.schemas import (
    ChannelComparison,
    RemittanceResponse,
    SendTimeRecommendation,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestChannelComparison(unittest.TestCase):

    def _make(self, **kwargs) -> ChannelComparison:
        defaults = dict(
            name="Western Union",
            fee_percent=7.5,
            fee_usd=15.0,
            amount_received=185.0,
            estimated_time="1-3 days",
            is_recommended=False,
            is_live=False,
        )
        defaults.update(kwargs)
        return ChannelComparison(**defaults)

    def test_to_dict_has_all_keys(self):
        ch = self._make()
        d = ch.to_dict()
        for key in ["name", "fee_percent", "fee_usd", "amount_received", "estimated_time",
                    "is_recommended", "is_live"]:
            self.assertIn(key, d)

    def test_to_dict_name_correct(self):
        ch = self._make(name="Strike")
        self.assertEqual(ch.to_dict()["name"], "Strike")

    def test_to_dict_fee_percent_correct(self):
        ch = self._make(fee_percent=0.1)
        self.assertAlmostEqual(ch.to_dict()["fee_percent"], 0.1)

    def test_to_dict_is_recommended_false(self):
        ch = self._make(is_recommended=False)
        self.assertFalse(ch.to_dict()["is_recommended"])

    def test_to_dict_is_recommended_true(self):
        ch = self._make(is_recommended=True)
        self.assertTrue(ch.to_dict()["is_recommended"])

    def test_is_live_flag_defaults_false(self):
        ch = self._make()
        self.assertFalse(ch.is_live)

    def test_is_live_flag_can_be_true(self):
        ch = self._make(is_live=True)
        self.assertTrue(ch.is_live)


class TestSendTimeRecommendation(unittest.TestCase):

    def _make(self) -> SendTimeRecommendation:
        return SendTimeRecommendation(
            best_time="Weekends 2-6 AM UTC",
            current_fee_sat_vb=25,
            estimated_low_fee_sat_vb=10,
            savings_percent=60.0,
        )

    def test_to_dict_has_all_keys(self):
        rec = self._make()
        d = rec.to_dict()
        for key in ["best_time", "current_fee_sat_vb", "estimated_low_fee_sat_vb", "savings_percent"]:
            self.assertIn(key, d)

    def test_to_dict_values_correct(self):
        rec = self._make()
        d = rec.to_dict()
        self.assertEqual(d["current_fee_sat_vb"], 25)
        self.assertEqual(d["estimated_low_fee_sat_vb"], 10)
        self.assertAlmostEqual(d["savings_percent"], 60.0)


class TestRemittanceResponse(unittest.TestCase):

    def _channels(self):
        return [
            ChannelComparison("WU", 7.5, 15.0, 185.0, "1-3 days", False, False),
            ChannelComparison("Lightning", 0.3, 0.60, 199.40, "Seconds", True, True),
        ]

    def test_to_dict_channels_list(self):
        resp = RemittanceResponse(
            channels=self._channels(),
            annual_savings=172.80,
            best_channel="Lightning Network",
        )
        d = resp.to_dict()
        self.assertIsInstance(d["channels"], list)
        self.assertEqual(len(d["channels"]), 2)

    def test_to_dict_annual_savings(self):
        resp = RemittanceResponse(
            channels=self._channels(),
            annual_savings=172.80,
            best_channel="Lightning Network",
        )
        self.assertAlmostEqual(resp.to_dict()["annual_savings"], 172.80)

    def test_to_dict_best_time_none(self):
        resp = RemittanceResponse(
            channels=self._channels(),
            annual_savings=0,
            best_channel="Lightning",
        )
        self.assertIsNone(resp.to_dict()["best_time"])

    def test_to_dict_best_time_populated(self):
        st = SendTimeRecommendation("Weekends", 20, 8, 60.0)
        resp = RemittanceResponse(
            channels=self._channels(),
            annual_savings=100,
            best_channel="Lightning",
            best_time=st,
        )
        d = resp.to_dict()
        self.assertIsNotNone(d["best_time"])
        self.assertIn("best_time", d["best_time"])


# ---------------------------------------------------------------------------
# FeeTracker tests
# ---------------------------------------------------------------------------


class TestFeeTracker(unittest.TestCase):

    def _make_tracker(self, fees: dict):
        """Create a FeeTracker with a mocked MempoolClient."""
        from app.remittance.fees import FeeTracker
        tracker = FeeTracker.__new__(FeeTracker)
        mock_mempool = MagicMock()
        mock_mempool.get_recommended_fees.return_value = fees
        tracker.mempool = mock_mempool
        return tracker

    def test_get_current_fees_returns_dict(self):
        tracker = self._make_tracker({"halfHourFee": 15, "economyFee": 6})
        result = tracker.get_current_fees()
        self.assertIsInstance(result, dict)

    def test_get_best_send_time_has_keys(self):
        tracker = self._make_tracker({"halfHourFee": 20, "economyFee": 8})
        result = tracker.get_best_send_time()
        for key in ["best_time", "current_fee_sat_vb", "estimated_low_fee_sat_vb"]:
            self.assertIn(key, result)

    def test_estimated_low_fee_at_least_one(self):
        # Even when economy fee is very low, min is 1
        tracker = self._make_tracker({"halfHourFee": 1, "economyFee": 1})
        result = tracker.get_best_send_time()
        self.assertGreaterEqual(result["estimated_low_fee_sat_vb"], 1)

    def test_best_send_time_current_fee_matches(self):
        tracker = self._make_tracker({"halfHourFee": 30, "economyFee": 12})
        result = tracker.get_best_send_time()
        self.assertEqual(result["current_fee_sat_vb"], 30)

    def test_best_send_time_fallback_on_missing_fees(self):
        # When fees dict is empty, fallback to 10
        tracker = self._make_tracker({})
        result = tracker.get_best_send_time()
        self.assertEqual(result["current_fee_sat_vb"], 10)


# ---------------------------------------------------------------------------
# Optimizer comparison logic
# ---------------------------------------------------------------------------


class TestRemittanceOptimizerLogic(unittest.TestCase):
    """Test the optimizer using mocked external service calls."""

    def _build_optimizer(self, btc_price=60000.0, fees=None, wise_data=None):
        from app.remittance.optimizer import RemittanceOptimizer
        opt = RemittanceOptimizer.__new__(RemittanceOptimizer)

        mock_cg = MagicMock()
        mock_cg.get_price.return_value = btc_price

        mock_mempool = MagicMock()
        mock_mempool.get_recommended_fees.return_value = fees or {"halfHourFee": 20, "economyFee": 8}

        mock_fee_tracker = MagicMock()
        mock_fee_tracker.get_best_send_time.return_value = {
            "best_time": "Weekends 2-6 AM UTC",
            "current_fee_sat_vb": 20,
            "estimated_low_fee_sat_vb": 8,
        }

        mock_wise = MagicMock()
        mock_wise.get_comparison.return_value = wise_data or []

        opt.coingecko = mock_cg
        opt.mempool = mock_mempool
        opt.fee_tracker = mock_fee_tracker
        opt.wise = mock_wise
        return opt

    def test_compare_returns_remittance_response(self):
        from app.remittance.schemas import RemittanceResponse
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        self.assertIsInstance(result, RemittanceResponse)

    def test_compare_has_channels(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        self.assertGreater(len(result.channels), 0)

    def test_lightning_always_in_channels(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        names = [ch.name for ch in result.channels]
        self.assertIn("Lightning Network", names)

    def test_lightning_is_recommended(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        lightning = next(ch for ch in result.channels if ch.name == "Lightning Network")
        self.assertTrue(lightning.is_recommended)

    def test_annual_savings_positive(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        self.assertGreater(result.annual_savings, 0)

    def test_best_channel_is_lightning(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        self.assertEqual(result.best_channel, "Lightning Network")

    def test_best_time_populated(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        self.assertIsNotNone(result.best_time)

    def test_compare_zero_amount(self):
        opt = self._build_optimizer()
        result = opt.compare(0.0)
        # Should not crash; channels still present
        self.assertIsNotNone(result)

    def test_channel_amounts_received(self):
        opt = self._build_optimizer()
        result = opt.compare(200.0)
        for ch in result.channels:
            # amount_received should be less than or equal to sent amount
            self.assertLessEqual(ch.amount_received, 200.0)


if __name__ == "__main__":
    unittest.main()
