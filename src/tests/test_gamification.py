"""Tests for the gamification module.

Covers:
- ACHIEVEMENT_DEFS definitions and structure
- LEVEL_THRESHOLDS ordering
- AchievementEngine.check_and_award()
- AchievementEngine.get_user_achievements()
- XP and level calculation
- _get_candidates() event routing
"""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import TestDatabase

VALID_PUBKEY = "c" * 64


class TestAchievementDefs(unittest.TestCase):

    def setUp(self):
        from app.gamification.achievements import ACHIEVEMENT_DEFS, LEVEL_THRESHOLDS
        self.defs = ACHIEVEMENT_DEFS
        self.thresholds = LEVEL_THRESHOLDS

    def test_defs_is_list(self):
        self.assertIsInstance(self.defs, list)

    def test_defs_not_empty(self):
        self.assertGreater(len(self.defs), 0)

    def test_each_def_has_id(self):
        for d in self.defs:
            self.assertIn("id", d)

    def test_each_def_has_name(self):
        for d in self.defs:
            self.assertIn("name", d)

    def test_each_def_has_xp(self):
        for d in self.defs:
            self.assertIn("xp", d)
            self.assertGreater(d["xp"], 0)

    def test_each_def_has_desc(self):
        for d in self.defs:
            self.assertIn("desc", d)

    def test_all_ids_unique(self):
        ids = [d["id"] for d in self.defs]
        self.assertEqual(len(ids), len(set(ids)))

    def test_level_thresholds_sorted(self):
        for i in range(len(self.thresholds) - 1):
            self.assertLessEqual(self.thresholds[i], self.thresholds[i + 1])

    def test_level_thresholds_start_with_zero(self):
        self.assertEqual(self.thresholds[0], 0)

    def test_expected_achievements_present(self):
        ids = {d["id"] for d in self.defs}
        for expected_id in ["first_score", "first_save", "first_remittance",
                            "streak_3", "streak_6", "streak_12"]:
            self.assertIn(expected_id, ids)


class TestAchievementEngine(unittest.TestCase):

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()

    def tearDown(self):
        self.db.teardown()

    def _engine(self):
        from app.gamification.achievements import AchievementEngine
        engine = AchievementEngine()
        return engine

    def _award_check(self, engine, pubkey, event_type, event_data):
        with patch("app.gamification.achievements.get_conn", return_value=self.conn):
            with patch("app.gamification.achievements._is_postgres", return_value=False):
                return engine.check_and_award(pubkey, event_type, event_data)

    def _get_achievements(self, engine, pubkey):
        with patch("app.gamification.achievements.get_conn", return_value=self.conn):
            with patch("app.gamification.achievements._is_postgres", return_value=False):
                return engine.get_user_achievements(pubkey)

    def test_check_and_award_returns_list(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 600})
        self.assertIsInstance(result, list)

    def test_first_score_awarded_on_score_event(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 100})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("first_score", awarded_ids)

    def test_score_500_awarded_when_score_gte_500(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 550})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("score_500", awarded_ids)

    def test_score_700_awarded_when_score_gte_700(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 750})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("score_700", awarded_ids)

    def test_score_500_not_awarded_below_threshold(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 400})
        awarded_ids = [a["id"] for a in result]
        self.assertNotIn("score_500", awarded_ids)

    def test_first_save_awarded_on_deposit(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "deposit", {"total_invested_usd": 50})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("first_save", awarded_ids)

    def test_saved_100_awarded_when_total_gte_100(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "deposit", {"total_invested_usd": 150})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("saved_100", awarded_ids)

    def test_first_remittance_awarded_on_remittance_event(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "remittance", {})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("first_remittance", awarded_ids)

    def test_achievement_not_awarded_twice(self):
        engine = self._engine()
        self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 100})
        result2 = self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 100})
        awarded_ids = [a["id"] for a in result2]
        self.assertNotIn("first_score", awarded_ids)

    def test_streak_3_awarded(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "deposit",
                                   {"streak_months": 3, "total_invested_usd": 10})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("streak_3", awarded_ids)

    def test_streak_6_awarded(self):
        engine = self._engine()
        result = self._award_check(engine, VALID_PUBKEY, "deposit",
                                   {"streak_months": 6, "total_invested_usd": 10})
        awarded_ids = [a["id"] for a in result]
        self.assertIn("streak_6", awarded_ids)

    def test_get_user_achievements_structure(self):
        engine = self._engine()
        result = self._get_achievements(engine, VALID_PUBKEY)
        self.assertIn("achievements", result)
        self.assertIn("total_xp", result)
        self.assertIn("level", result)

    def test_get_user_achievements_xp_zero_before_earning(self):
        engine = self._engine()
        result = self._get_achievements(engine, VALID_PUBKEY)
        self.assertEqual(result["total_xp"], 0)

    def test_get_user_achievements_level_increases_with_xp(self):
        engine = self._engine()
        # Award first_score (10 xp)
        self._award_check(engine, VALID_PUBKEY, "score", {"total_score": 100})
        r1 = self._get_achievements(engine, VALID_PUBKEY)
        self.assertGreater(r1["level"], 0)

    def test_earned_count_increases_after_award(self):
        engine = self._engine()
        r1 = self._get_achievements(engine, VALID_PUBKEY)
        self._award_check(engine, VALID_PUBKEY, "remittance", {})
        r2 = self._get_achievements(engine, VALID_PUBKEY)
        self.assertGreater(r2["earned_count"], r1["earned_count"])


class TestGetCandidates(unittest.TestCase):
    """Unit tests for _get_candidates without DB."""

    def setUp(self):
        from app.gamification.achievements import AchievementEngine
        self.engine = AchievementEngine()

    def test_score_event_includes_first_score(self):
        result = self.engine._get_candidates("score", {"total_score": 100})
        self.assertIn("first_score", result)

    def test_deposit_event_includes_first_save(self):
        result = self.engine._get_candidates("deposit", {"total_invested_usd": 10})
        self.assertIn("first_save", result)

    def test_unknown_event_returns_empty(self):
        result = self.engine._get_candidates("unknown_event", {})
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
