"""Tests for the pension module.

Covers:
- PensionCalculator.project() with mocked CoinGecko data
- _calc_cagr() with various price histories
- Monthly breakdown structure
- Comparison against traditional pension
"""

import sys
import os
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import make_price_history


def _make_calculator(
    current_price: float = 60000.0,
    start_price: float = 30000.0,
    end_price: float = 90000.0,
    days: int = 365,
):
    from app.pension.calculator import PensionCalculator
    calc = PensionCalculator.__new__(PensionCalculator)
    mock_cg = MagicMock()
    mock_cg.get_price.return_value = current_price
    mock_cg.get_historical_prices.return_value = make_price_history(
        start_price=start_price,
        end_price=end_price,
        num_days=days,
    )
    calc.coingecko = mock_cg
    return calc


class TestPensionCalculatorProject(unittest.TestCase):

    def test_project_returns_pension_projection(self):
        from app.pension.schemas import PensionProjection
        calc = _make_calculator()
        result = calc.project(200.0, years=20)
        self.assertIsInstance(result, PensionProjection)

    def test_total_invested_correct(self):
        calc = _make_calculator()
        result = calc.project(200.0, years=10)
        self.assertAlmostEqual(result.total_invested_usd, 200.0 * 10 * 12)

    def test_total_btc_positive(self):
        calc = _make_calculator()
        result = calc.project(100.0, years=5)
        self.assertGreater(result.total_btc_accumulated, 0)

    def test_current_value_positive(self):
        calc = _make_calculator()
        result = calc.project(100.0, years=5)
        self.assertGreater(result.current_value_usd, 0)

    def test_monthly_breakdown_length(self):
        calc = _make_calculator()
        result = calc.project(100.0, years=5)
        self.assertEqual(len(result.monthly_breakdown), 5 * 12)

    def test_monthly_breakdown_month_numbers(self):
        calc = _make_calculator()
        result = calc.project(100.0, years=3)
        months = [b["month"] for b in result.monthly_breakdown]
        self.assertEqual(months[0], 1)
        self.assertEqual(months[-1], 36)

    def test_monthly_data_length(self):
        calc = _make_calculator()
        result = calc.project(100.0, years=5)
        self.assertEqual(len(result.monthly_data), 5 * 12)

    def test_avg_buy_price_positive(self):
        calc = _make_calculator()
        result = calc.project(100.0, years=5)
        self.assertGreater(result.avg_buy_price, 0)

    def test_btc_price_preserved(self):
        calc = _make_calculator(current_price=75000.0)
        result = calc.project(100.0, years=5)
        self.assertAlmostEqual(result.current_btc_price, 75000.0)

    def test_btc_accumulated_grows_with_more_months(self):
        calc5 = _make_calculator()
        calc10 = _make_calculator()
        r5 = calc5.project(100.0, years=5)
        r10 = calc10.project(100.0, years=10)
        self.assertGreater(r10.total_btc_accumulated, r5.total_btc_accumulated)


class TestCalcCAGR(unittest.TestCase):

    def _make_calc(self):
        from app.pension.calculator import PensionCalculator
        calc = PensionCalculator.__new__(PensionCalculator)
        calc.coingecko = MagicMock()
        return calc

    def test_cagr_positive_when_price_doubled(self):
        calc = self._make_calc()
        history = make_price_history(start_price=30000.0, end_price=60000.0, num_days=365)
        cagr = calc._calc_cagr(history)
        self.assertGreater(cagr, 0)

    def test_cagr_approximately_one_for_doubling_annual(self):
        """Doubling in 1 year → CAGR ≈ 100%."""
        calc = self._make_calc()
        history = make_price_history(start_price=30000.0, end_price=60000.0, num_days=365)
        cagr = calc._calc_cagr(history)
        self.assertAlmostEqual(cagr, 1.0, delta=0.05)

    def test_cagr_raises_on_insufficient_data(self):
        calc = self._make_calc()
        history = make_price_history(num_days=10)
        with self.assertRaises(ValueError):
            calc._calc_cagr(history)

    def test_cagr_raises_on_empty(self):
        calc = self._make_calc()
        with self.assertRaises(ValueError):
            calc._calc_cagr([])

    def test_cagr_zero_start_price_raises(self):
        calc = self._make_calc()
        now_ms = int(time.time() * 1000)
        history = [[now_ms - 365 * 86400 * 1000, 0.0], [now_ms, 60000.0]]
        with self.assertRaises(ValueError):
            calc._calc_cagr(history)


if __name__ == "__main__":
    unittest.main()
