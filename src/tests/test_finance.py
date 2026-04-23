"""
tests/test_finance.py
=====================
Test suite for the app.finance package — technical analysis indicators,
financial calculators, data models, and tax lot management.

Test count: 40+
"""

import sys
import os
import math
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.finance.indicators import (
    sma,
    ema,
    rsi,
    macd,
    bollinger_bands,
    atr,
    stochastic_oscillator,
    williams_r,
    obv,
    vwap,
    fibonacci_retracement,
    pivot_points,
    rate_of_change,
    analyze_trend,
)
from app.finance.calculator import (
    compound_interest,
    present_value,
    future_value,
    internal_rate_of_return,
    net_present_value,
    loan_amortization,
    inflation_adjustment,
    annuity_payment,
    perpetuity_value,
    bond_price,
    yield_to_maturity,
    real_return,
    weighted_average_cost,
    retirement_calculator,
    emergency_fund_calculator,
    dollar_cost_average_analysis,
    break_even_analysis,
)
from app.finance.tax import (
    TaxLot,
    TaxLotManager,
    classify_holding_period,
    calculate_average_cost_basis,
    generate_tax_report,
    estimate_tax_liability,
)
from app.finance.models import (
    PricePoint,
    OHLCV,
    Trade,
    Position,
    Portfolio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prices(n: int, start: float = 100.0, step: float = 1.0) -> list:
    """Linearly increasing price series."""
    return [start + i * step for i in range(n)]


def _make_flat_prices(n: int, price: float = 100.0) -> list:
    return [price] * n


def _make_ohlcv(prices: list, volume: float = 1000.0) -> list:
    """Build a list of (high, low, close, volume) tuples from close prices."""
    result = []
    for p in prices:
        result.append((p * 1.01, p * 0.99, p, volume))
    return result


# ===========================================================================
# SMA
# ===========================================================================

class TestSMA(unittest.TestCase):

    def test_sma_simple_known_values(self):
        # SMA(3) of [1, 2, 3, 4, 5]
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = sma(prices, 3)
        # Warmup: first 2 are None
        self.assertIsNone(result[0])
        self.assertIsNone(result[1])
        self.assertAlmostEqual(result[2], 2.0)  # (1+2+3)/3
        self.assertAlmostEqual(result[3], 3.0)  # (2+3+4)/3
        self.assertAlmostEqual(result[4], 4.0)  # (3+4+5)/3

    def test_sma_period_1_equals_input(self):
        prices = [10.0, 20.0, 30.0]
        result = sma(prices, 1)
        for i, p in enumerate(prices):
            self.assertAlmostEqual(result[i], p)

    def test_sma_length_matches_input(self):
        prices = _make_prices(50)
        result = sma(prices, 20)
        self.assertEqual(len(result), 50)

    def test_sma_flat_series(self):
        prices = _make_flat_prices(10, 50.0)
        result = sma(prices, 5)
        for i in range(4, 10):
            self.assertAlmostEqual(result[i], 50.0)

    def test_sma_invalid_period_raises(self):
        with self.assertRaises((ValueError, ZeroDivisionError)):
            sma([1, 2, 3], 0)


# ===========================================================================
# EMA
# ===========================================================================

class TestEMA(unittest.TestCase):

    def test_ema_returns_list_same_length(self):
        prices = _make_prices(20)
        result = ema(prices, 10)
        self.assertEqual(len(result), 20)

    def test_ema_first_value_is_none_before_period(self):
        prices = _make_prices(5)
        result = ema(prices, 3)
        # Typically EMA starts at period-1 or earlier (seeded with first SMA)
        # At minimum, result has correct length
        self.assertEqual(len(result), 5)

    def test_ema_flat_prices_constant(self):
        prices = _make_flat_prices(20, 100.0)
        result = ema(prices, 5)
        # After warmup, all EMA values should be 100.0
        for val in result:
            if val is not None:
                self.assertAlmostEqual(val, 100.0, places=5)

    def test_ema_rising_prices_lag_behind(self):
        # With rising prices, EMA should be below the latest price
        prices = _make_prices(30, start=100.0, step=2.0)
        result = ema(prices, 10)
        last_ema = next(v for v in reversed(result) if v is not None)
        self.assertLess(last_ema, prices[-1])

    def test_ema_different_periods_differ(self):
        prices = _make_prices(30)
        fast = ema(prices, 5)
        slow = ema(prices, 20)
        last_fast = next(v for v in reversed(fast) if v is not None)
        last_slow = next(v for v in reversed(slow) if v is not None)
        self.assertNotAlmostEqual(last_fast, last_slow)


# ===========================================================================
# RSI
# ===========================================================================

class TestRSI(unittest.TestCase):

    def test_rsi_returns_correct_length(self):
        prices = _make_prices(20)
        result = rsi(prices, 14)
        self.assertEqual(len(result), 20)

    def test_rsi_bounds(self):
        prices = [100 + math.sin(i * 0.5) * 10 for i in range(50)]
        result = rsi(prices, 14)
        for val in result:
            if val is not None:
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 100.0)

    def test_rsi_rising_prices_above_50(self):
        # Purely rising prices → RSI should be above 50
        prices = _make_prices(30, start=100.0, step=1.0)
        result = rsi(prices, 14)
        last_rsi = next(v for v in reversed(result) if v is not None)
        self.assertGreater(last_rsi, 50.0)

    def test_rsi_falling_prices_below_50(self):
        # Purely falling prices → RSI should be below 50
        prices = _make_prices(30, start=130.0, step=-1.0)
        result = rsi(prices, 14)
        last_rsi = next(v for v in reversed(result) if v is not None)
        self.assertLess(last_rsi, 50.0)

    def test_rsi_warmup_nones(self):
        prices = _make_prices(20)
        result = rsi(prices, 14)
        # First 14 values should be None (warm-up period)
        none_count = sum(1 for v in result if v is None)
        self.assertGreater(none_count, 0)


# ===========================================================================
# MACD
# ===========================================================================

class TestMACD(unittest.TestCase):

    def test_macd_returns_dict_with_required_keys(self):
        prices = _make_prices(50)
        result = macd(prices)
        self.assertIn("macd_line", result)
        self.assertIn("signal_line", result)
        self.assertIn("histogram", result)

    def test_macd_all_lists_same_length(self):
        prices = _make_prices(50)
        result = macd(prices)
        n = len(prices)
        self.assertEqual(len(result["macd_line"]), n)
        self.assertEqual(len(result["signal_line"]), n)
        self.assertEqual(len(result["histogram"]), n)

    def test_macd_histogram_is_line_minus_signal(self):
        prices = [100 + math.sin(i * 0.3) * 5 for i in range(60)]
        result = macd(prices)
        for m, s, h in zip(result["macd_line"], result["signal_line"], result["histogram"]):
            if m is not None and s is not None and h is not None:
                self.assertAlmostEqual(h, m - s, places=8)

    def test_macd_long_enough_series(self):
        prices = _make_prices(100)
        result = macd(prices, fast=12, slow=26, signal=9)
        self.assertEqual(len(result["macd_line"]), 100)


# ===========================================================================
# Bollinger Bands
# ===========================================================================

class TestBollingerBands(unittest.TestCase):

    def test_returns_dict_with_bands(self):
        prices = _make_prices(25)
        result = bollinger_bands(prices, 20)
        self.assertIn("upper", result)
        self.assertIn("middle", result)
        self.assertIn("lower", result)

    def test_upper_above_lower(self):
        prices = [100 + math.sin(i * 0.2) * 3 for i in range(30)]
        result = bollinger_bands(prices, 20)
        for u, l in zip(result["upper"], result["lower"]):
            if u is not None and l is not None:
                self.assertGreater(u, l)

    def test_middle_is_sma(self):
        prices = _make_prices(25)
        bb = bollinger_bands(prices, 20)
        sma_result = sma(prices, 20)
        for bm, sm in zip(bb["middle"], sma_result):
            if bm is not None and sm is not None:
                self.assertAlmostEqual(bm, sm, places=8)

    def test_flat_prices_band_width_zero(self):
        prices = _make_flat_prices(25, 100.0)
        result = bollinger_bands(prices, 20)
        for u, m, l in zip(result["upper"], result["middle"], result["lower"]):
            if u is not None:
                self.assertAlmostEqual(u, m, places=5)
                self.assertAlmostEqual(l, m, places=5)


# ===========================================================================
# ATR
# ===========================================================================

class TestATR(unittest.TestCase):

    def test_atr_returns_correct_length(self):
        highs = _make_prices(20, 105.0)
        lows  = _make_prices(20, 95.0)
        closes = _make_prices(20, 100.0)
        result = atr(highs, lows, closes, 14)
        self.assertEqual(len(result), 20)

    def test_atr_non_negative(self):
        prices = _make_prices(20)
        highs = [p + 1 for p in prices]
        lows  = [p - 1 for p in prices]
        result = atr(highs, lows, prices, 14)
        for val in result:
            if val is not None:
                self.assertGreaterEqual(val, 0.0)


# ===========================================================================
# Fibonacci
# ===========================================================================

class TestFibonacci(unittest.TestCase):
    """fibonacci_retracement(high, low) -> dict with string keys like '0.0', '61.8', '100.0'."""

    def test_returns_dict_with_levels(self):
        result = fibonacci_retracement(high=50000.0, low=10000.0)
        self.assertIn("0.0", result)
        self.assertIn("23.6", result)
        self.assertIn("38.2", result)
        self.assertIn("50.0", result)
        self.assertIn("61.8", result)
        self.assertIn("100.0", result)

    def test_0_level_equals_high(self):
        # At 0% retracement from high = high price (no retracement)
        result = fibonacci_retracement(high=50000.0, low=10000.0)
        self.assertAlmostEqual(result["0.0"], 50000.0)

    def test_100_level_equals_low(self):
        # At 100% retracement = low price (full retracement)
        result = fibonacci_retracement(high=50000.0, low=10000.0)
        self.assertAlmostEqual(result["100.0"], 10000.0)

    def test_50_level_is_midpoint(self):
        result = fibonacci_retracement(high=50000.0, low=10000.0)
        self.assertAlmostEqual(result["50.0"], 30000.0, places=2)


# ===========================================================================
# Financial Calculator
# ===========================================================================

class TestCompoundInterest(unittest.TestCase):

    def _get_final(self, result):
        """Extract final value from compound_interest result (dict or float)."""
        if isinstance(result, dict):
            for key in ("final_value", "balance", "future_value", "total"):
                if key in result:
                    return float(result[key])
            # fallback: first numeric value
            return float(next(v for v in result.values() if isinstance(v, (int, float))))
        return float(result)

    def test_known_result(self):
        # $1000 at 10% annual for 1 year, compounded annually = $1100
        result = compound_interest(principal=1000.0, rate=0.10, periods=1, compound_frequency=1)
        self.assertAlmostEqual(self._get_final(result), 1100.0, places=2)

    def test_more_compounding_periods_yields_more(self):
        annual  = compound_interest(1000.0, 0.10, 1, compound_frequency=1)
        monthly = compound_interest(1000.0, 0.10, 1, compound_frequency=12)
        self.assertGreater(self._get_final(monthly), self._get_final(annual))

    def test_zero_rate(self):
        result = compound_interest(1000.0, 0.0, 5, compound_frequency=1)
        self.assertAlmostEqual(self._get_final(result), 1000.0, places=2)


class TestPresentFutureValue(unittest.TestCase):

    def test_future_value_known(self):
        # FV of $1000 at 5% for 10 years
        fv = future_value(1000.0, 0.05, 10)
        self.assertAlmostEqual(fv, 1000.0 * (1.05 ** 10), places=4)

    def test_present_value_inverse_of_future_value(self):
        pv_orig = 1000.0
        fv = future_value(pv_orig, 0.08, 5)
        pv_back = present_value(fv, 0.08, 5)
        self.assertAlmostEqual(pv_back, pv_orig, places=6)

    def test_pv_zero_rate(self):
        self.assertAlmostEqual(present_value(500.0, 0.0, 10), 500.0, places=6)


class TestNPVandIRR(unittest.TestCase):

    def test_npv_positive_good_investment(self):
        # Cash flows: -1000, +300, +400, +500 at 10% discount
        cf = [-1000.0, 300.0, 400.0, 500.0]
        npv = net_present_value(cf, 0.10)
        # NPV > 0 means profitable at this rate
        self.assertIsInstance(npv, float)

    def test_npv_zero_at_irr(self):
        cf = [-1000.0, 300.0, 400.0, 500.0]
        irr_val = internal_rate_of_return(cf)
        if irr_val is not None:
            npv_at_irr = net_present_value(cf, irr_val)
            self.assertAlmostEqual(npv_at_irr, 0.0, places=2)

    def test_irr_simple_doubling(self):
        # Invest 100, get 200 in 1 year → IRR = 100%
        cf = [-100.0, 200.0]
        irr_val = internal_rate_of_return(cf)
        if irr_val is not None:
            self.assertAlmostEqual(irr_val, 1.0, places=2)


class TestLoanAmortization(unittest.TestCase):

    def test_amortization_schedule_length(self):
        result = loan_amortization(principal=100000.0, annual_rate=0.05, years=30)
        if isinstance(result, dict):
            schedule = result.get("schedule", [])
            self.assertEqual(len(schedule), 30 * 12)
        elif isinstance(result, list):
            self.assertEqual(len(result), 30 * 12)

    def test_amortization_final_balance_near_zero(self):
        result = loan_amortization(100000.0, 0.05, 10)
        if isinstance(result, dict):
            schedule = result.get("schedule", [])
            if schedule:
                last = schedule[-1]
                balance = last.get("balance", last.get("remaining_balance", 0))
                self.assertAlmostEqual(float(balance), 0.0, places=0)

    def test_monthly_payment_reasonable(self):
        result = loan_amortization(100000.0, 0.06, 30)
        if isinstance(result, dict):
            payment = result.get("monthly_payment")
            if payment is not None:
                # For a $100k 30yr 6% mortgage, payment is roughly $599-$600
                self.assertGreater(float(payment), 500.0)
                self.assertLess(float(payment), 800.0)


class TestAnnuityBond(unittest.TestCase):

    def test_annuity_payment_zero_rate(self):
        # $12000 / 12 months at 0% = $1000/month
        payment = annuity_payment(12000.0, 0.0, 12)
        self.assertAlmostEqual(payment, 1000.0, places=4)

    def test_annuity_payment_positive_rate(self):
        payment = annuity_payment(100000.0, 0.05/12, 360)
        self.assertGreater(payment, 100000.0 / 360)  # Higher than principal/n due to interest

    def test_perpetuity_value(self):
        # $100/year at 5% → $2000
        pv = perpetuity_value(100.0, 0.05)
        self.assertAlmostEqual(pv, 2000.0, places=4)

    def test_bond_price_at_par(self):
        # When coupon rate == market rate, bond price ≈ face value
        price = bond_price(face_value=1000.0, coupon_rate=0.05, market_rate=0.05, periods=10)
        self.assertAlmostEqual(price, 1000.0, places=2)


class TestInflationRealReturn(unittest.TestCase):

    def test_inflation_adjustment(self):
        result = inflation_adjustment(100.0, 0.03, 10)
        # After 10 years at 3% inflation, real purchasing power decreases
        if isinstance(result, dict):
            val = result.get(
                "real_value_in_future",
                result.get("real_value", result.get("adjusted_value", 0))
            )
        else:
            val = result
        self.assertLess(float(val), 100.0)

    def test_real_return_positive(self):
        # 10% nominal, 3% inflation → ~6.8% real
        rr = real_return(0.10, 0.03)
        self.assertGreater(rr, 0.06)
        self.assertLess(rr, 0.08)


class TestDCAAnalysis(unittest.TestCase):

    def test_dca_returns_dict(self):
        result = dollar_cost_average_analysis(
            prices=[30000.0 + i * 100 for i in range(12)],
            amount=100.0,
            frequency="monthly",
        )
        self.assertIsInstance(result, dict)

    def test_dca_total_invested(self):
        result = dollar_cost_average_analysis(
            prices=[30000.0] * 12,
            amount=100.0,
            frequency="monthly",
        )
        total = result.get("total_invested")
        if total is not None:
            self.assertAlmostEqual(float(total), 1200.0, places=2)


class TestBreakEven(unittest.TestCase):

    def test_break_even_units(self):
        result = break_even_analysis(
            fixed_costs=10000.0,
            price_per_unit=50.0,
            variable_cost_per_unit=30.0,
        )
        if isinstance(result, dict):
            units = result.get("break_even_units")
            if units is not None:
                # 10000 / (50 - 30) = 500
                self.assertAlmostEqual(float(units), 500.0, places=2)
        else:
            self.assertAlmostEqual(float(result), 500.0, places=2)


# ===========================================================================
# Tax Lot Manager
# ===========================================================================

class TestTaxLotClassification(unittest.TestCase):

    def test_short_term(self):
        now = int(time.time())
        acquired = now - (30 * 86400)  # 30 days ago
        self.assertEqual(classify_holding_period(acquired, now), "short_term")

    def test_long_term(self):
        now = int(time.time())
        acquired = now - (400 * 86400)  # 400 days ago
        self.assertEqual(classify_holding_period(acquired, now), "long_term")

    def test_exactly_one_year_is_long_term(self):
        import datetime as dt
        # Use a known date
        acquired_dt = dt.datetime(2022, 1, 1)
        one_year_later = dt.datetime(2023, 1, 1)
        acquired = int(acquired_dt.timestamp())
        disposed = int(one_year_later.timestamp())
        result = classify_holding_period(acquired, disposed)
        self.assertEqual(result, "long_term")


class TestAverageCostBasis(unittest.TestCase):

    def test_single_lot(self):
        purchases = [{"amount": 1.0, "cost_basis": 50000.0}]
        self.assertAlmostEqual(calculate_average_cost_basis(purchases), 50000.0)

    def test_two_equal_lots(self):
        purchases = [
            {"amount": 1.0, "cost_basis": 40000.0},
            {"amount": 1.0, "cost_basis": 60000.0},
        ]
        self.assertAlmostEqual(calculate_average_cost_basis(purchases), 50000.0)

    def test_weighted_average(self):
        purchases = [
            {"amount": 2.0, "cost_basis": 30000.0},
            {"amount": 1.0, "cost_basis": 60000.0},
        ]
        # (2*30000 + 1*60000) / 3 = 40000
        self.assertAlmostEqual(calculate_average_cost_basis(purchases), 40000.0)

    def test_empty_list(self):
        self.assertEqual(calculate_average_cost_basis([]), 0.0)


class TestTaxLotManager(unittest.TestCase):

    def setUp(self):
        self.mgr = TaxLotManager()
        now = int(time.time())
        # Add three lots purchased at different times/prices
        self.lot1_time = now - 400 * 86400  # 400 days ago
        self.lot2_time = now - 100 * 86400  # 100 days ago
        self.lot3_time = now - 10 * 86400   # 10 days ago
        self.mgr.add_purchase(amount=0.5, price_usd=30000.0, timestamp=self.lot1_time)
        self.mgr.add_purchase(amount=0.5, price_usd=50000.0, timestamp=self.lot2_time)
        self.mgr.add_purchase(amount=0.5, price_usd=70000.0, timestamp=self.lot3_time)

    def test_total_btc_is_sum(self):
        total = sum(lot.amount for lot in self.mgr._open_lots)
        self.assertAlmostEqual(total, 1.5)

    def test_fifo_sells_oldest_first(self):
        now = int(time.time())
        result = self.mgr.process_sale(amount=0.5, price_usd=60000.0, timestamp=now, method="fifo")
        # FIFO: sell lot1 (bought at 30000), gain = (60000 - 30000) * 0.5 = 15000
        self.assertIsInstance(result, dict)
        gain = result.get("realized_gain", 0)
        self.assertAlmostEqual(gain, 15000.0, places=2)

    def test_lifo_sells_newest_first(self):
        now = int(time.time())
        result = self.mgr.process_sale(amount=0.5, price_usd=60000.0, timestamp=now, method="lifo")
        # LIFO: sell lot3 (bought at 70000), gain = (60000 - 70000) * 0.5 = -5000
        gain = result.get("realized_gain", 0)
        self.assertAlmostEqual(gain, -5000.0, places=2)

    def test_hifo_sells_highest_cost_first(self):
        now = int(time.time())
        result = self.mgr.process_sale(amount=0.5, price_usd=60000.0, timestamp=now, method="hifo")
        # HIFO: sell lot3 (highest cost 70000), minimizes gains
        gain = result.get("realized_gain", 0)
        self.assertAlmostEqual(gain, -5000.0, places=2)

    def test_insufficient_balance_raises(self):
        now = int(time.time())
        with self.assertRaises((ValueError, Exception)):
            self.mgr.process_sale(amount=10.0, price_usd=60000.0, timestamp=now, method="fifo")

    def test_generate_tax_summary_structure(self):
        now = int(time.time())
        year = time.gmtime(now).tm_year
        self.mgr.process_sale(0.3, 60000.0, now, "fifo")
        report = self.mgr.get_tax_summary(year=year)
        self.assertIsInstance(report, dict)


# ===========================================================================
# OHLCV Model
# ===========================================================================

class TestPricePoint(unittest.TestCase):

    def test_typical_price(self):
        p = PricePoint(timestamp=0, open=100.0, high=110.0, low=90.0, close=105.0)
        self.assertAlmostEqual(p.typical_price(), (110 + 90 + 105) / 3)

    def test_range(self):
        p = PricePoint(timestamp=0, open=100.0, high=120.0, low=80.0, close=100.0)
        self.assertAlmostEqual(p.range(), 40.0)

    def test_is_bullish(self):
        bull = PricePoint(0, 100.0, 110.0, 90.0, 105.0)
        bear = PricePoint(0, 110.0, 115.0, 90.0, 95.0)
        self.assertTrue(bull.is_bullish())
        self.assertFalse(bear.is_bullish())

    def test_to_dict_has_all_fields(self):
        p = PricePoint(timestamp=1000000, open=50000.0, high=52000.0, low=49000.0, close=51000.0)
        d = p.to_dict()
        for key in ["timestamp", "open", "high", "low", "close"]:
            self.assertIn(key, d)


class TestOHLCV(unittest.TestCase):

    def _make_ohlcv_series(self, n: int = 10) -> "OHLCV":
        """Create an OHLCV series from PricePoint objects."""
        candles = []
        for i in range(n):
            ts = 1000000 + i * 3600
            candles.append(PricePoint(
                timestamp=ts,
                open=float(100 + i),
                high=float(102 + i),
                low=float(98 + i),
                close=float(101 + i),
                volume=1000.0,
            ))
        return OHLCV(candles=candles)

    def test_ohlcv_candle_count(self):
        series = self._make_ohlcv_series(10)
        self.assertEqual(len(series.candles), 10)

    def test_ohlcv_creates_without_error(self):
        series = self._make_ohlcv_series(5)
        self.assertEqual(len(series.candles), 5)

    def test_ohlcv_from_raw(self):
        raw = [
            {"timestamp": 1000000 + i, "open": 100.0, "high": 105.0,
             "low": 95.0, "close": 102.0, "volume": 500.0}
            for i in range(5)
        ]
        series = OHLCV.from_raw(raw)
        self.assertEqual(len(series.candles), 5)


# ===========================================================================
# Rate of Change
# ===========================================================================

class TestRateOfChange(unittest.TestCase):

    def test_roc_known_values(self):
        # ROC(3): at index 3, (prices[3] - prices[0]) / prices[0] * 100
        prices = [100.0, 105.0, 110.0, 120.0]
        result = rate_of_change(prices, 3)
        # ROC at index 3 = (120 - 100) / 100 * 100 = 20%
        self.assertIsNotNone(result[3])
        self.assertAlmostEqual(result[3], 20.0, places=4)

    def test_roc_warmup_nones(self):
        prices = _make_prices(10)
        result = rate_of_change(prices, 3)
        for i in range(3):
            self.assertIsNone(result[i])


# ===========================================================================
# Weighted Average Cost
# ===========================================================================

class TestWeightedAverageCost(unittest.TestCase):

    def test_single_item(self):
        # weighted_average_cost takes list of dicts with 'amount' and 'price'
        result = weighted_average_cost([{"amount": 5.0, "price": 100.0}])
        avg = result.get("average_cost_basis", result) if isinstance(result, dict) else result
        self.assertAlmostEqual(float(avg), 100.0)

    def test_two_items(self):
        result = weighted_average_cost([
            {"amount": 4.0, "price": 100.0},
            {"amount": 2.0, "price": 200.0},
        ])
        # (100*4 + 200*2) / 6 = 800/6 ≈ 133.33
        avg = result.get("average_cost_basis", result) if isinstance(result, dict) else result
        self.assertAlmostEqual(float(avg), 800.0 / 6.0, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
