from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.remittance import fees as fees_module
from app.remittance.fees import FeeTracker


class _FakeMempool:
    def __init__(self, fees_value):
        self._fees = fees_value

    def get_recommended_fees(self):
        return self._fees


@pytest.fixture
def tracker():
    t = FeeTracker()
    t.mempool = _FakeMempool({"halfHourFee": 20, "economyFee": 5})
    return t


class TestEstimatedLowFee:
    def test_uses_economy_when_lower(self, tracker):
        result = tracker.get_best_send_time()
        # 60% of 20 = 12, economy is 5 → 5 wins.
        assert result["estimated_low_fee_sat_vb"] == 5

    def test_uses_60_pct_when_no_economy(self):
        t = FeeTracker()
        t.mempool = _FakeMempool({"halfHourFee": 10})
        r = t.get_best_send_time()
        # economy defaults to 5 → min(5, 6) = 5.
        assert r["estimated_low_fee_sat_vb"] == 5

    def test_minimum_is_one(self):
        t = FeeTracker()
        t.mempool = _FakeMempool({"halfHourFee": 1, "economyFee": 0})
        r = t.get_best_send_time()
        assert r["estimated_low_fee_sat_vb"] == 1

    def test_non_dict_mempool_response(self):
        t = FeeTracker()
        t.mempool = _FakeMempool(None)
        r = t.get_best_send_time()
        assert r["current_fee_sat_vb"] == 10
        assert r["estimated_low_fee_sat_vb"] >= 1


class TestBestTimeMessage:
    def _patch_now(self, dt):
        fake = datetime(*dt, tzinfo=timezone.utc)

        class _FakeDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return fake

        return patch.object(fees_module, "datetime", _FakeDT)

    def test_weekend_low_hour_is_now(self, tracker):
        # Saturday 2026-04-18, 03:00 UTC
        with self._patch_now((2026, 4, 18, 3, 0, 0)):
            msg = tracker.get_best_send_time()["best_time"]
        assert "Now" in msg

    def test_weekend_outside_hour(self, tracker):
        # Sunday 2026-04-19, 12:00 UTC
        with self._patch_now((2026, 4, 19, 12, 0, 0)):
            msg = tracker.get_best_send_time()["best_time"]
        assert "Today" in msg

    def test_weekday(self, tracker):
        # Wednesday 2026-04-15, 10:00 UTC
        with self._patch_now((2026, 4, 15, 10, 0, 0)):
            msg = tracker.get_best_send_time()["best_time"]
        assert "Saturday" in msg or "Sunday" in msg
