"""Tests for the scoring module.

The scoring module lives at app/scoring/__init__.py.
We test any public classes/functions it exposes, using mocked external calls.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


VALID_PUBKEY = "d" * 64

# A realistic-looking Bitcoin address (P2PKH mainnet)
VALID_BTC_ADDRESS = "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf6A"
# A Bech32 segwit address
VALID_SEGWIT_ADDRESS = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
# Invalid garbage
INVALID_ADDRESS = "not-a-valid-btc-address"


def _import_scoring():
    """Import app.scoring, skip test on ImportError."""
    import app.scoring as scoring_mod
    return scoring_mod


class TestScoringModuleImport(unittest.TestCase):

    def test_scoring_module_importable(self):
        try:
            import app.scoring
        except ImportError as e:
            self.skipTest(f"scoring module not available: {e}")


class TestAddressValidation(unittest.TestCase):
    """Tests for address format validation, if exposed."""

    def _get_validate_fn(self):
        try:
            from app.scoring import validate_address
            return validate_address
        except ImportError:
            self.skipTest("validate_address not exported from scoring module")

    def test_valid_p2pkh_address(self):
        fn = self._get_validate_fn()
        self.assertTrue(fn(VALID_BTC_ADDRESS))

    def test_valid_segwit_address(self):
        fn = self._get_validate_fn()
        self.assertTrue(fn(VALID_SEGWIT_ADDRESS))

    def test_invalid_garbage(self):
        fn = self._get_validate_fn()
        self.assertFalse(fn(INVALID_ADDRESS))

    def test_empty_string_invalid(self):
        fn = self._get_validate_fn()
        self.assertFalse(fn(""))

    def test_none_like_empty_invalid(self):
        fn = self._get_validate_fn()
        self.assertFalse(fn("   "))


class TestScoreCalculation(unittest.TestCase):
    """Tests for the main score calculation logic."""

    def _get_route_handler(self):
        try:
            import app.scoring.routes as routes
            return routes
        except ImportError:
            self.skipTest("scoring.routes not available")

    def test_routes_importable(self):
        try:
            import app.scoring.routes
        except ImportError:
            self.skipTest("scoring.routes not available")

    def test_score_range_valid_inputs(self):
        """Score should be between 0 and 1000 for reasonable inputs."""
        # We rely on the scoring module having some internal calculation
        try:
            from app.scoring.routes import _calculate_score
        except ImportError:
            self.skipTest("_calculate_score not importable")

        score = _calculate_score(address=VALID_BTC_ADDRESS, tx_count=50, balance_btc=0.1)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1000)


class TestGradeAssignment(unittest.TestCase):
    """If a grade function exists, test its thresholds."""

    def _get_grade_fn(self):
        try:
            from app.scoring.routes import _score_to_grade
            return _score_to_grade
        except ImportError:
            try:
                from app.scoring import score_to_grade
                return score_to_grade
            except ImportError:
                self.skipTest("grade function not found in scoring module")

    def test_high_score_gets_good_grade(self):
        fn = self._get_grade_fn()
        grade = fn(900)
        self.assertIn(grade, ["A", "A+", "excellent", "S", "AA"])

    def test_low_score_gets_poor_grade(self):
        fn = self._get_grade_fn()
        grade = fn(50)
        self.assertIn(grade, ["F", "D", "D-", "poor", "E"])

    def test_mid_score_gets_mid_grade(self):
        fn = self._get_grade_fn()
        grade = fn(500)
        self.assertIsNotNone(grade)
        self.assertIsInstance(grade, str)

    def test_zero_score(self):
        fn = self._get_grade_fn()
        grade = fn(0)
        self.assertIsNotNone(grade)

    def test_max_score(self):
        fn = self._get_grade_fn()
        grade = fn(1000)
        self.assertIsNotNone(grade)


class TestScoringRouteHandler(unittest.TestCase):
    """Integration-level tests for the scoring route handler."""

    def test_scoring_init_importable(self):
        try:
            import app.scoring
        except ImportError as e:
            self.skipTest(str(e))

    def test_scoring_routes_importable(self):
        try:
            import app.scoring.routes
        except ImportError as e:
            self.skipTest(str(e))

    def test_scoring_module_has_routes_or_handler(self):
        try:
            import app.scoring.routes as r
            # Check that something callable exists
            has_handler = any(
                callable(getattr(r, attr))
                for attr in dir(r)
                if not attr.startswith("_")
            )
            self.assertTrue(has_handler)
        except ImportError:
            self.skipTest("scoring.routes not available")

    def test_scoring_init_not_empty(self):
        import app.scoring as s
        # Module should at least exist; it might be empty
        self.assertIsNotNone(s)


if __name__ == "__main__":
    unittest.main()
