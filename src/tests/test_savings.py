"""Tests for the savings module.

Covers:
- SavingsProjector.project() with synthetic price data
- SavingsTracker.create_goal(), record_deposit(), get_progress(), _calculate_streak()
- Milestone detection logic
- Deposit count-based streak algorithm
"""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import TestDatabase, make_price_history

VALID_PUBKEY = "a" * 64


# ---------------------------------------------------------------------------
# SavingsProjector
# ---------------------------------------------------------------------------


class TestSavingsProjector(unittest.TestCase):

    def _build_projector(self, start_price=30000.0, end_price=90000.0, days=365):
        from app.savings.projector import SavingsProjector
        proj = SavingsProjector.__new__(SavingsProjector)
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = end_price
        mock_cg.get_historical_prices.return_value = make_price_history(
            start_price=start_price,
            end_price=end_price,
            num_days=days,
        )
        proj.coingecko = mock_cg
        return proj

    def test_project_returns_dict(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=5)
        self.assertIsInstance(result, dict)

    def test_project_has_scenarios(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=5)
        self.assertIn("scenarios", result)
        self.assertEqual(len(result["scenarios"]), 3)

    def test_project_scenario_names(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=5)
        names = {s["name"] for s in result["scenarios"]}
        self.assertEqual(names, {"conservative", "moderate", "optimistic"})

    def test_project_total_invested(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=10)
        self.assertAlmostEqual(result["total_invested"], 12000.0)

    def test_project_monthly_usd_preserved(self):
        proj = self._build_projector()
        result = proj.project(250.0, years=5)
        self.assertEqual(result["monthly_usd"], 250.0)

    def test_project_years_preserved(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=7)
        self.assertEqual(result["years"], 7)

    def test_project_optimistic_greater_than_conservative(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=10)
        by_name = {s["name"]: s for s in result["scenarios"]}
        self.assertGreater(
            by_name["optimistic"]["projected_value"],
            by_name["conservative"]["projected_value"],
        )

    def test_project_moderate_between_extremes(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=10)
        by_name = {s["name"]: s for s in result["scenarios"]}
        self.assertGreaterEqual(
            by_name["moderate"]["projected_value"],
            by_name["conservative"]["projected_value"],
        )
        self.assertLessEqual(
            by_name["moderate"]["projected_value"],
            by_name["optimistic"]["projected_value"],
        )

    def test_project_has_monthly_data(self):
        proj = self._build_projector()
        result = proj.project(100.0, years=5)
        self.assertIn("monthly_data", result)
        self.assertGreater(len(result["monthly_data"]), 0)

    def test_project_has_btc_price(self):
        proj = self._build_projector(end_price=80000.0)
        result = proj.project(100.0, years=5)
        self.assertAlmostEqual(result["current_btc_price"], 80000.0)

    def test_project_insufficient_data_raises(self):
        proj = self._build_projector()
        proj.coingecko.get_historical_prices.return_value = make_price_history(
            num_days=10  # too few
        )
        with self.assertRaises(ValueError):
            proj.project(100.0, years=5)

    def test_project_multiplier_positive(self):
        proj = self._build_projector(start_price=30000.0, end_price=150000.0)
        result = proj.project(100.0, years=10)
        for s in result["scenarios"]:
            self.assertGreater(s["multiplier"], 0)


# ---------------------------------------------------------------------------
# SavingsTracker — unit tests with in-memory DB
# ---------------------------------------------------------------------------


def _make_tracker(conn):
    """Build a SavingsTracker that uses our test connection."""
    from app.savings.tracker import SavingsTracker
    tracker = SavingsTracker.__new__(SavingsTracker)
    mock_cg = MagicMock()
    mock_cg.get_price.return_value = 50000.0
    tracker.coingecko = mock_cg

    # Monkey-patch get_conn to return test conn
    import app.savings.tracker as tracker_mod
    tracker_mod._patched_conn = conn  # store for cleanup

    return tracker, mock_cg


class TestSavingsTrackerGoal(unittest.TestCase):

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()

    def tearDown(self):
        self.db.teardown()

    def _tracker(self):
        from app.savings.tracker import SavingsTracker
        tracker = SavingsTracker.__new__(SavingsTracker)
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = 50000.0
        tracker.coingecko = mock_cg
        return tracker, mock_cg

    def _create_goal(self, tracker, pubkey, monthly=100.0, years=10):
        with patch("app.savings.tracker.get_conn", return_value=self.conn):
            with patch("app.savings.tracker._is_postgres", return_value=False):
                return tracker.create_goal(pubkey, monthly, years)

    def _record_deposit(self, tracker, pubkey, amount=100.0):
        with patch("app.savings.tracker.get_conn", return_value=self.conn):
            with patch("app.savings.tracker._is_postgres", return_value=False):
                return tracker.record_deposit(pubkey, amount)

    def _get_progress(self, tracker, pubkey):
        with patch("app.savings.tracker.get_conn", return_value=self.conn):
            with patch("app.savings.tracker._is_postgres", return_value=False):
                return tracker.get_progress(pubkey)

    def test_create_goal_returns_dict(self):
        tracker, _ = self._tracker()
        result = self._create_goal(tracker, VALID_PUBKEY)
        self.assertIsInstance(result, dict)

    def test_create_goal_has_monthly_target(self):
        tracker, _ = self._tracker()
        result = self._create_goal(tracker, VALID_PUBKEY, monthly=250.0)
        self.assertAlmostEqual(result["monthly_target_usd"], 250.0)

    def test_create_goal_has_target_years(self):
        tracker, _ = self._tracker()
        result = self._create_goal(tracker, VALID_PUBKEY, years=15)
        self.assertEqual(result["target_years"], 15)

    def test_create_goal_idempotent_upsert(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY, monthly=100.0)
        self._create_goal(tracker, VALID_PUBKEY, monthly=200.0)
        row = self.conn.execute(
            "SELECT COUNT(*) FROM savings_goals WHERE pubkey = ?", (VALID_PUBKEY,)
        ).fetchone()
        self.assertEqual(row[0], 1)

    def test_create_goal_updates_value(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY, monthly=100.0)
        self._create_goal(tracker, VALID_PUBKEY, monthly=500.0)
        row = self.conn.execute(
            "SELECT monthly_target_usd FROM savings_goals WHERE pubkey = ?",
            (VALID_PUBKEY,),
        ).fetchone()
        self.assertAlmostEqual(row[0], 500.0)

    def test_record_deposit_inserts_row(self):
        tracker, _ = self._tracker()
        self.db.insert_user(VALID_PUBKEY)
        self._record_deposit(tracker, VALID_PUBKEY, amount=150.0)
        count = self.db.count_rows("savings_deposits")
        self.assertEqual(count, 1)

    def test_record_deposit_returns_dict(self):
        tracker, _ = self._tracker()
        result = self._record_deposit(tracker, VALID_PUBKEY, amount=75.0)
        self.assertIsInstance(result, dict)
        self.assertIn("btc_amount", result)
        self.assertIn("btc_price", result)

    def test_record_deposit_calculates_btc_amount(self):
        tracker, mock_cg = self._tracker()
        mock_cg.get_price.return_value = 50000.0
        result = self._record_deposit(tracker, VALID_PUBKEY, amount=100.0)
        self.assertAlmostEqual(result["btc_amount"], 0.002, places=5)

    def test_get_progress_no_goal(self):
        tracker, _ = self._tracker()
        result = self._get_progress(tracker, "b" * 64)
        self.assertFalse(result["has_goal"])

    def test_get_progress_with_goal(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY, monthly=100.0, years=10)
        result = self._get_progress(tracker, VALID_PUBKEY)
        self.assertTrue(result["has_goal"])

    def test_get_progress_milestones_present(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY)
        result = self._get_progress(tracker, VALID_PUBKEY)
        self.assertIn("milestones", result)

    def test_first_deposit_milestone_reached(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY)
        self._record_deposit(tracker, VALID_PUBKEY, amount=50.0)
        result = self._get_progress(tracker, VALID_PUBKEY)
        first = next(m for m in result["milestones"] if m["name"] == "First deposit")
        self.assertTrue(first["reached"])

    def test_milestone_100_not_reached_at_50(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY)
        self._record_deposit(tracker, VALID_PUBKEY, amount=50.0)
        result = self._get_progress(tracker, VALID_PUBKEY)
        m100 = next(m for m in result["milestones"] if m["name"] == "$100 saved")
        self.assertFalse(m100["reached"])

    def test_milestone_100_reached(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY)
        self._record_deposit(tracker, VALID_PUBKEY, amount=100.0)
        result = self._get_progress(tracker, VALID_PUBKEY)
        m100 = next(m for m in result["milestones"] if m["name"] == "$100 saved")
        self.assertTrue(m100["reached"])

    def test_total_invested_accumulated(self):
        tracker, _ = self._tracker()
        self._create_goal(tracker, VALID_PUBKEY)
        for _ in range(3):
            self._record_deposit(tracker, VALID_PUBKEY, amount=100.0)
        result = self._get_progress(tracker, VALID_PUBKEY)
        self.assertAlmostEqual(result["total_invested_usd"], 300.0)


class TestStreakCalculation(unittest.TestCase):
    """Test _calculate_streak in isolation."""

    def _make_tracker(self):
        from app.savings.tracker import SavingsTracker
        tracker = SavingsTracker.__new__(SavingsTracker)
        tracker.coingecko = MagicMock()
        return tracker

    def test_no_deposits_streak_zero(self):
        tracker = self._make_tracker()
        self.assertEqual(tracker._calculate_streak([]), 0)

    def test_single_deposit_this_month_streak_one(self):
        tracker = self._make_tracker()
        now = int(time.time())
        deposits = [(100.0, 50000.0, 0.002, now)]
        self.assertEqual(tracker._calculate_streak(deposits), 1)

    def test_consecutive_months_streak_three(self):
        tracker = self._make_tracker()
        now = int(time.time())
        month_sec = 30 * 86400
        deposits = [
            (100.0, 50000.0, 0.002, now),
            (100.0, 50000.0, 0.002, now - month_sec),
            (100.0, 50000.0, 0.002, now - 2 * month_sec),
        ]
        self.assertGreaterEqual(tracker._calculate_streak(deposits), 3)

    def test_gap_breaks_streak(self):
        tracker = self._make_tracker()
        now = int(time.time())
        month_sec = 30 * 86400
        # Deposit this month and 3 months ago — gap in between
        deposits = [
            (100.0, 50000.0, 0.002, now),
            (100.0, 50000.0, 0.002, now - 3 * month_sec),
        ]
        streak = tracker._calculate_streak(deposits)
        # Streak should be 1 (current month only) due to gap
        self.assertEqual(streak, 1)


if __name__ == "__main__":
    unittest.main()
