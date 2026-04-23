"""
Historical price data management for Magma Bitcoin app.

PriceHistory encapsulates a list of {timestamp, price} dicts and
provides analytical methods covering returns, volatility, drawdown,
seasonality, distribution statistics, support/resistance levels,
trend detection, DCA backtesting, and strategy comparison.

Also exposes BITCOIN_HISTORICAL_EVENTS – a curated timeline of 30+
significant Bitcoin events for overlay on charts and analysis.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Utility maths (pure Python)
# ---------------------------------------------------------------------------

def _mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list, ddof: int = 1) -> float:
    n = len(values)
    if n < ddof + 1:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (n - ddof)
    return math.sqrt(variance)


def _median(values: list) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 != 0 else (s[mid - 1] + s[mid]) / 2


def _percentile(values: list, p: float) -> float:
    """Linear interpolation percentile."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    idx = p / 100 * (n - 1)
    lo = int(idx)
    hi = lo + 1
    frac = idx - lo
    if hi >= n:
        return s[-1]
    return s[lo] * (1 - frac) + s[hi] * frac


def _skewness(values: list) -> float:
    n = len(values)
    if n < 3:
        return 0.0
    m = _mean(values)
    s = _stddev(values)
    if s == 0:
        return 0.0
    return sum(((v - m) / s) ** 3 for v in values) * n / ((n - 1) * (n - 2))


def _kurtosis(values: list) -> float:
    """Excess kurtosis (Fisher definition, normal = 0)."""
    n = len(values)
    if n < 4:
        return 0.0
    m = _mean(values)
    s = _stddev(values)
    if s == 0:
        return 0.0
    raw = sum(((v - m) / s) ** 4 for v in values) / n
    return raw - 3.0


def _log_return(p1: float, p2: float) -> float:
    if p1 <= 0 or p2 <= 0:
        return 0.0
    return math.log(p2 / p1)


def _pct_return(p1: float, p2: float) -> float:
    if p1 == 0:
        return 0.0
    return (p2 - p1) / p1 * 100.0


# ---------------------------------------------------------------------------
# HistoricalEvent dataclass
# ---------------------------------------------------------------------------

@dataclass
class HistoricalEvent:
    """A significant Bitcoin event."""
    timestamp: int       # Unix timestamp
    date: str            # ISO date string
    title: str
    category: str        # halving | crash | ath | regulatory | adoption | hack | macro
    price_usd: float     # approximate BTC price at the time
    description: str
    impact: str          # bullish | bearish | neutral
    price_change_pct: Optional[float] = None  # 30-day after


# ---------------------------------------------------------------------------
# BITCOIN_HISTORICAL_EVENTS
# ---------------------------------------------------------------------------

BITCOIN_HISTORICAL_EVENTS: list[HistoricalEvent] = [
    HistoricalEvent(1231006505, "2009-01-03", "Genesis Block Mined", "adoption",
        0.0, "Satoshi mines the genesis block. 'Chancellor on brink of second bailout for banks.'",
        "bullish"),
    HistoricalEvent(1279065600, "2010-07-14", "First BTC Exchange Rate (Mt. Gox opens)", "adoption",
        0.06, "Mt. Gox exchange launches, providing first liquid market.", "bullish"),
    HistoricalEvent(1281657600, "2010-08-13", "Bitcoin Pizza Day", "adoption",
        0.08, "Laszlo Hanyecz buys two pizzas for 10,000 BTC (~$25).", "neutral"),
    HistoricalEvent(1320969600, "2011-11-10", "First Major Crash -93%", "crash",
        2.0, "BTC falls from $32 to $2 over several months after first bubble.", "bearish",
        -93.0),
    HistoricalEvent(1354320000, "2012-11-28", "First Halving", "halving",
        12.35, "Block reward drops from 50 to 25 BTC. Price later rose ~8000% in 12 months.",
        "bullish"),
    HistoricalEvent(1370563200, "2013-06-07", "$266 ATH Then Crash", "crash",
        70.0, "BTC hits $266 on April 10, then crashes to $50 as speculation peaks.",
        "bearish", -75.0),
    HistoricalEvent(1386201600, "2013-12-05", "China PBOC Ban", "regulatory",
        1100.0, "China's central bank bans financial institutions from using BTC.",
        "bearish", -50.0),
    HistoricalEvent(1391990400, "2014-02-10", "Mt. Gox Collapse", "hack",
        600.0, "Mt. Gox halts withdrawals; 850,000 BTC (~$450M) reported lost.",
        "bearish", -36.0),
    HistoricalEvent(1407715200, "2014-08-11", "Bear Market Low ~$200", "crash",
        200.0, "Extended post-Mt.Gox bear market drags price to $170 low.", "bearish"),
    HistoricalEvent(1468512000, "2016-07-09", "Second Halving", "halving",
        650.0, "Block reward drops from 25 to 12.5 BTC. Bull run follows over 18 months.",
        "bullish"),
    HistoricalEvent(1483228800, "2017-01-01", "BTC Breaks $1,000 Again", "ath",
        1000.0, "BTC reclaims $1,000 for first time since 2013 peak.", "bullish"),
    HistoricalEvent(1513555200, "2017-12-17", "All-Time High $19,783", "ath",
        19783.0, "Bitcoin peaks near $20,000 amid retail frenzy and CME futures launch.",
        "bullish"),
    HistoricalEvent(1514764800, "2018-01-01", "2018 Bear Market Begins", "crash",
        13000.0, "Year-long bear market sends BTC from ~$20k to ~$3k.", "bearish", -85.0),
    HistoricalEvent(1543622400, "2018-11-30", "Hash Wars / BCH Fork Crash", "crash",
        4000.0, "Bitcoin Cash hash war triggers widespread market sell-off.", "bearish"),
    HistoricalEvent(1575158400, "2019-12-01", "BTC $7,000 Range", "adoption",
        7200.0, "Relative stability as institutional interest begins rebuilding.", "neutral"),
    HistoricalEvent(1584662400, "2020-03-12", "COVID Black Thursday -50%", "crash",
        5000.0, "Global pandemic panic selling. BTC drops from $9k to $4,700 in hours.",
        "bearish", -50.0),
    HistoricalEvent(1589168400, "2020-05-11", "Third Halving", "halving",
        8600.0, "Block reward drops from 12.5 to 6.25 BTC. Followed by historic bull run.",
        "bullish"),
    HistoricalEvent(1602979200, "2020-10-07", "PayPal Announces BTC Support", "adoption",
        10700.0, "PayPal enables 300M users to buy/sell/hold Bitcoin.", "bullish", 30.0),
    HistoricalEvent(1610150400, "2021-01-08", "BTC Breaks $40,000", "ath",
        40000.0, "Institutional FOMO drives rapid appreciation.", "bullish"),
    HistoricalEvent(1620691200, "2021-05-11", "Elon Musk / Tesla FUD", "crash",
        55000.0, "Tesla suspends BTC payments citing energy concerns. Price falls 30% in days.",
        "bearish", -35.0),
    HistoricalEvent(1621555200, "2021-05-21", "China Mining Ban", "regulatory",
        35000.0, "China orders Bitcoin miners to shut down. Hashrate drops ~50%.", "bearish", -40.0),
    HistoricalEvent(1635724800, "2021-11-01", "BTC ATH $68,789", "ath",
        68789.0, "All-time high reached on ProShares Bitcoin ETF launch (BITO).", "bullish"),
    HistoricalEvent(1654041600, "2022-06-01", "Luna/UST Collapse", "crash",
        30000.0, "Terra/Luna ecosystem collapses, erasing $40B in value. Contagion follows.",
        "bearish", -45.0),
    HistoricalEvent(1655942400, "2022-06-13", "Celsius Pause / 3AC Crisis", "hack",
        22500.0, "Celsius halts withdrawals; Three Arrows Capital insolvent.", "bearish", -30.0),
    HistoricalEvent(1667433600, "2022-11-03", "FTX Collapse", "hack",
        20400.0, "FTX exchange collapses in 72 hours; Sam Bankman-Fried arrested.",
        "bearish", -25.0),
    HistoricalEvent(1672531200, "2023-01-01", "2023 Recovery Begins", "adoption",
        16500.0, "Bear market lows established at ~$15,500; slow recovery starts.", "bullish"),
    HistoricalEvent(1686096000, "2023-06-07", "BlackRock Bitcoin ETF Filing", "adoption",
        27000.0, "BlackRock files for spot Bitcoin ETF, signalling institutional acceptance.",
        "bullish", 20.0),
    HistoricalEvent(1704672000, "2024-01-08", "Spot Bitcoin ETF Approval (US)", "adoption",
        46000.0, "SEC approves 11 spot Bitcoin ETFs. Record inflows follow.", "bullish", 60.0),
    HistoricalEvent(1713571767, "2024-04-20", "Fourth Halving", "halving",
        63700.0, "Block reward drops from 6.25 to 3.125 BTC at block 840,000.", "bullish"),
    HistoricalEvent(1728518400, "2024-10-10", "BTC Breaks $60,000 Post-Halving", "ath",
        62000.0, "Post-halving price recovery; ETF inflows sustain demand.", "bullish"),
    HistoricalEvent(1732060800, "2024-11-20", "BTC Approaches $100,000", "ath",
        98000.0, "Post-US election rally; Trump administration signals Bitcoin-friendly policy.",
        "bullish"),
    HistoricalEvent(1735689600, "2025-01-01", "BTC Surpasses $100,000", "ath",
        100000.0, "Bitcoin enters six-figure price territory for the first time.", "bullish"),
]


# ---------------------------------------------------------------------------
# PriceHistory
# ---------------------------------------------------------------------------

class PriceHistory:
    """
    Analytical wrapper around a time-ordered list of price observations.

    Parameters
    ----------
    prices : list[dict]
        Each element must have at minimum keys ``timestamp`` (unix ms or s)
        and ``price`` (float). Optional keys: ``volume``.
    """

    def __init__(self, prices: list[dict]):
        # Sort by timestamp ascending
        self._raw = sorted(prices, key=lambda p: p["timestamp"])
        self._prices  = [float(p["price"]) for p in self._raw]
        self._timestamps = [p["timestamp"] for p in self._raw]
        self._volumes = [float(p.get("volume", 0)) for p in self._raw]

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------

    @property
    def prices(self) -> list[float]:
        return self._prices

    @property
    def timestamps(self) -> list:
        return self._timestamps

    def __len__(self) -> int:
        return len(self._prices)

    # ------------------------------------------------------------------
    # Returns
    # ------------------------------------------------------------------

    def get_returns(self, period: str = "daily") -> list[dict]:
        """
        Compute period-over-period returns.

        Parameters
        ----------
        period : str
            'daily', 'weekly', 'monthly', 'yearly'

        Returns
        -------
        list of {timestamp, return_pct, log_return}
        """
        step_map = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}
        step = step_map.get(period, 1)

        results = []
        prices  = self._prices
        timestamps = self._timestamps

        i = step
        while i < len(prices):
            p_curr = prices[i]
            p_prev = prices[i - step]
            results.append({
                "timestamp":    timestamps[i],
                "return_pct":   round(_pct_return(p_prev, p_curr), 4),
                "log_return":   round(_log_return(p_prev, p_curr), 6),
            })
            i += 1
        return results

    # ------------------------------------------------------------------
    # Volatility
    # ------------------------------------------------------------------

    def get_volatility(self, window: int = 30) -> float:
        """
        Annualised historical volatility over a rolling window.

        Parameters
        ----------
        window : int
            Number of periods for the calculation.

        Returns
        -------
        float : annualised standard deviation of log returns (percentage)
        """
        prices = self._prices
        if len(prices) < window + 1:
            window = max(2, len(prices) - 1)

        recent = prices[-(window + 1):]
        log_rets = [_log_return(recent[i - 1], recent[i]) for i in range(1, len(recent))]
        daily_vol = _stddev(log_rets)
        annual_vol = daily_vol * math.sqrt(365) * 100
        return round(annual_vol, 4)

    # ------------------------------------------------------------------
    # Drawdown analysis
    # ------------------------------------------------------------------

    def get_max_drawdown(self) -> dict:
        """
        Compute the maximum peak-to-trough drawdown in the series.

        Returns
        -------
        dict with keys: drawdown_pct, peak_index, trough_index,
        peak_date, trough_date, recovery_index, recovery_date,
        duration_days (peak to trough)
        """
        prices = self._prices
        timestamps = self._timestamps
        if len(prices) < 2:
            return {"drawdown_pct": 0.0}

        max_dd = 0.0
        peak_idx   = 0
        trough_idx = 0
        best_peak  = 0
        best_trough = 0

        running_peak = prices[0]
        running_peak_idx = 0

        for i in range(1, len(prices)):
            if prices[i] > running_peak:
                running_peak = prices[i]
                running_peak_idx = i
            else:
                dd = (prices[i] - running_peak) / running_peak * 100
                if dd < max_dd:
                    max_dd = dd
                    best_peak   = running_peak_idx
                    best_trough = i

        # Find recovery point
        recovery_idx = None
        if best_peak < best_trough < len(prices) - 1:
            peak_price = prices[best_peak]
            for j in range(best_trough + 1, len(prices)):
                if prices[j] >= peak_price:
                    recovery_idx = j
                    break

        def _ts_to_date(ts) -> str:
            try:
                ts_s = ts / 1000 if ts > 1e10 else ts
                import datetime
                return datetime.datetime.utcfromtimestamp(ts_s).strftime("%Y-%m-%d")
            except Exception:
                return str(ts)

        peak_ts    = timestamps[best_peak]   if timestamps else None
        trough_ts  = timestamps[best_trough] if timestamps else None
        rec_ts     = timestamps[recovery_idx] if recovery_idx else None

        peak_ts_s  = (peak_ts / 1000   if peak_ts   and peak_ts   > 1e10 else peak_ts)   or 0
        trough_ts_s= (trough_ts / 1000 if trough_ts and trough_ts > 1e10 else trough_ts) or 0

        duration = round((trough_ts_s - peak_ts_s) / 86400, 1) if (peak_ts_s and trough_ts_s) else 0

        return {
            "drawdown_pct":   round(max_dd, 4),
            "peak_index":     best_peak,
            "trough_index":   best_trough,
            "peak_price":     round(prices[best_peak], 2),
            "trough_price":   round(prices[best_trough], 2),
            "peak_date":      _ts_to_date(peak_ts) if peak_ts else None,
            "trough_date":    _ts_to_date(trough_ts) if trough_ts else None,
            "recovery_index": recovery_idx,
            "recovery_date":  _ts_to_date(rec_ts) if rec_ts else None,
            "duration_days":  duration,
            "recovered":      recovery_idx is not None,
        }

    def get_recovery_time(self, drawdown_threshold: float = 30.0) -> list[dict]:
        """
        Find all drawdowns deeper than the threshold and measure
        how long each took to recover.

        Parameters
        ----------
        drawdown_threshold : float
            Minimum drawdown percentage (positive number, e.g. 30 = 30%).

        Returns
        -------
        list of {peak_date, trough_date, recovery_date,
                 drawdown_pct, days_to_trough, days_to_recovery}
        """
        prices     = self._prices
        timestamps = self._timestamps
        if len(prices) < 2:
            return []

        events = []
        i = 0
        while i < len(prices) - 1:
            peak_price = prices[i]
            peak_ts    = timestamps[i]
            trough_price = peak_price
            trough_idx   = i

            # Find trough
            j = i + 1
            while j < len(prices) and prices[j] < prices[j - 1]:
                if prices[j] < trough_price:
                    trough_price = prices[j]
                    trough_idx   = j
                j += 1

            dd = (trough_price - peak_price) / peak_price * 100  # negative
            if abs(dd) >= drawdown_threshold:
                # Find recovery
                rec_idx = None
                k = trough_idx + 1
                while k < len(prices):
                    if prices[k] >= peak_price:
                        rec_idx = k
                        break
                    k += 1

                def _ts_s(ts) -> float:
                    return ts / 1000 if ts > 1e10 else ts

                peak_s   = _ts_s(peak_ts)
                trough_s = _ts_s(timestamps[trough_idx])
                rec_s    = _ts_s(timestamps[rec_idx]) if rec_idx else None

                events.append({
                    "peak_date":         self._ts_to_date(peak_ts),
                    "trough_date":       self._ts_to_date(timestamps[trough_idx]),
                    "recovery_date":     self._ts_to_date(timestamps[rec_idx]) if rec_idx else None,
                    "drawdown_pct":      round(dd, 2),
                    "days_to_trough":    round((trough_s - peak_s) / 86400, 1),
                    "days_to_recovery":  round((rec_s - peak_s) / 86400, 1) if rec_s else None,
                    "recovered":         rec_idx is not None,
                })
                # Advance past trough
                i = trough_idx + 1
            else:
                i += 1

        return events

    # ------------------------------------------------------------------
    # Best / worst periods
    # ------------------------------------------------------------------

    def get_best_worst_periods(self, period: str = "monthly") -> dict:
        """
        Return ranked best and worst calendar periods.

        Parameters
        ----------
        period : str
            'weekly', 'monthly', 'quarterly', 'yearly'

        Returns
        -------
        dict with 'best' and 'worst' lists of {period, return_pct}
        """
        returns = self.get_returns(period)
        if not returns:
            return {"best": [], "worst": [], "average_pct": 0.0}

        sorted_asc  = sorted(returns, key=lambda r: r["return_pct"])
        sorted_desc = sorted(returns, key=lambda r: r["return_pct"], reverse=True)
        all_rets    = [r["return_pct"] for r in returns]

        def _fmt(entry):
            return {
                "timestamp":  entry["timestamp"],
                "date":       self._ts_to_date(entry["timestamp"]),
                "return_pct": entry["return_pct"],
            }

        return {
            "period":      period,
            "best":        [_fmt(r) for r in sorted_desc[:5]],
            "worst":       [_fmt(r) for r in sorted_asc[:5]],
            "average_pct": round(_mean(all_rets), 4),
            "median_pct":  round(_median(all_rets), 4),
            "positive_periods_pct": round(sum(1 for r in all_rets if r > 0) / len(all_rets) * 100, 2),
        }

    # ------------------------------------------------------------------
    # Seasonal patterns
    # ------------------------------------------------------------------

    def get_seasonal_patterns(self) -> dict:
        """
        Compute average returns by calendar month and quarter.

        Returns
        -------
        dict with monthly_avg (list 1-12) and quarterly_avg (list 1-4)
        """
        import datetime

        monthly_buckets = {m: [] for m in range(1, 13)}
        quarterly_buckets = {q: [] for q in range(1, 5)}

        prices = self._prices
        timestamps = self._timestamps

        for i in range(1, len(prices)):
            ts = timestamps[i]
            ts_s = ts / 1000 if ts > 1e10 else ts
            try:
                dt = datetime.datetime.utcfromtimestamp(ts_s)
                month = dt.month
                quarter = (month - 1) // 3 + 1
                ret = _pct_return(prices[i - 1], prices[i])
                monthly_buckets[month].append(ret)
                quarterly_buckets[quarter].append(ret)
            except Exception:
                continue

        monthly_avg = {}
        for m, rets in monthly_buckets.items():
            monthly_avg[m] = {
                "month":         m,
                "avg_return_pct": round(_mean(rets), 4) if rets else None,
                "positive_rate_pct": round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1) if rets else None,
                "sample_count":  len(rets),
            }

        quarterly_avg = {}
        for q, rets in quarterly_buckets.items():
            quarterly_avg[q] = {
                "quarter":        q,
                "avg_return_pct": round(_mean(rets), 4) if rets else None,
                "sample_count":   len(rets),
            }

        # Best and worst months by average return
        valid_months = [(m, d["avg_return_pct"]) for m, d in monthly_avg.items() if d["avg_return_pct"] is not None]
        best_month  = max(valid_months, key=lambda x: x[1])[0] if valid_months else None
        worst_month = min(valid_months, key=lambda x: x[1])[0] if valid_months else None

        month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                       7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

        return {
            "monthly":    monthly_avg,
            "quarterly":  quarterly_avg,
            "best_month":  month_names.get(best_month, ""),
            "worst_month": month_names.get(worst_month, ""),
            "note": "Returns calculated as close-to-close percentage changes",
        }

    # ------------------------------------------------------------------
    # Return distribution
    # ------------------------------------------------------------------

    def get_distribution(self) -> dict:
        """
        Compute the statistical distribution of daily returns.

        Returns
        -------
        dict with mean, std, median, skewness, excess_kurtosis,
        percentiles, normality_note
        """
        returns = self.get_returns("daily")
        rets = [r["return_pct"] for r in returns]
        if not rets:
            return {}

        pctiles = {
            "p1":  _percentile(rets, 1),
            "p5":  _percentile(rets, 5),
            "p10": _percentile(rets, 10),
            "p25": _percentile(rets, 25),
            "p50": _percentile(rets, 50),
            "p75": _percentile(rets, 75),
            "p90": _percentile(rets, 90),
            "p95": _percentile(rets, 95),
            "p99": _percentile(rets, 99),
        }

        std = _stddev(rets)
        skew = _skewness(rets)
        kurt = _kurtosis(rets)

        # Rough normality check: |skewness| < 0.5 and |kurtosis| < 1
        is_normal_like = abs(skew) < 0.5 and abs(kurt) < 1.0

        return {
            "count":                  len(rets),
            "mean_return_pct":        round(_mean(rets), 4),
            "median_return_pct":      round(_median(rets), 4),
            "std_return_pct":         round(std, 4),
            "skewness":               round(skew, 4),
            "excess_kurtosis":        round(kurt, 4),
            "percentiles":            {k: round(v, 4) for k, v in pctiles.items()},
            "min_return_pct":         round(min(rets), 4),
            "max_return_pct":         round(max(rets), 4),
            "positive_days_pct":      round(sum(1 for r in rets if r > 0) / len(rets) * 100, 2),
            "is_approximately_normal": is_normal_like,
            "distribution_note": (
                "Bitcoin returns exhibit positive skewness and fat tails (leptokurtic), "
                "meaning extreme gains/losses occur more frequently than a normal distribution predicts."
            ),
        }

    # ------------------------------------------------------------------
    # Percentile rank
    # ------------------------------------------------------------------

    def get_percentile_rank(self, current_price: float) -> dict:
        """
        Return the percentile rank of ``current_price`` within the
        historical series.

        Returns
        -------
        dict with rank_pct, interpretation, min, max, median prices
        """
        prices = sorted(self._prices)
        below = sum(1 for p in prices if p < current_price)
        rank  = below / len(prices) * 100 if prices else 0

        median_price = _median(prices)
        mean_price   = _mean(prices)

        if rank < 10:
            interpretation = "Near historical lows — potential long-term accumulation zone"
        elif rank < 30:
            interpretation = "Below median — historically favourable entry territory"
        elif rank < 60:
            interpretation = "Near median price range"
        elif rank < 80:
            interpretation = "Above median — price elevated relative to history"
        else:
            interpretation = "Near historical highs — caution warranted"

        return {
            "current_price":      round(current_price, 2),
            "percentile_rank":    round(rank, 2),
            "interpretation":     interpretation,
            "historical_min":     round(min(prices), 2),
            "historical_max":     round(max(prices), 2),
            "historical_median":  round(median_price, 2),
            "historical_mean":    round(mean_price, 2),
        }

    # ------------------------------------------------------------------
    # Support & Resistance
    # ------------------------------------------------------------------

    def detect_support_resistance(self, sensitivity: float = 0.03) -> dict:
        """
        Detect key support and resistance levels using local extrema
        and price clustering.

        Parameters
        ----------
        sensitivity : float
            Cluster radius as fraction of price (default 3%).

        Returns
        -------
        dict with 'support' and 'resistance' lists of
        {price, strength, touches, type}
        """
        prices = self._prices
        if len(prices) < 10:
            return {"support": [], "resistance": []}

        # Find local minima (support) and maxima (resistance)
        local_min = []
        local_max = []
        window = 5
        for i in range(window, len(prices) - window):
            left_slice  = prices[i - window:i]
            right_slice = prices[i + 1:i + window + 1]
            if prices[i] <= min(left_slice) and prices[i] <= min(right_slice):
                local_min.append(prices[i])
            if prices[i] >= max(left_slice) and prices[i] >= max(right_slice):
                local_max.append(prices[i])

        def _cluster(levels: list, label: str) -> list:
            if not levels:
                return []
            sorted_levels = sorted(levels)
            clusters = []
            cluster = [sorted_levels[0]]
            for price in sorted_levels[1:]:
                centre = _mean(cluster)
                if abs(price - centre) / centre <= sensitivity:
                    cluster.append(price)
                else:
                    clusters.append(cluster)
                    cluster = [price]
            clusters.append(cluster)

            result = []
            for cl in clusters:
                avg_price = _mean(cl)
                strength  = min(len(cl) * 20, 100)  # 5 touches = 100%
                result.append({
                    "price":    round(avg_price, 2),
                    "strength": strength,
                    "touches":  len(cl),
                    "type":     label,
                })
            # Sort by strength
            result.sort(key=lambda x: x["strength"], reverse=True)
            return result[:10]  # top 10

        return {
            "support":    _cluster(local_min, "support"),
            "resistance": _cluster(local_max, "resistance"),
            "sensitivity": sensitivity,
        }

    # ------------------------------------------------------------------
    # Trend detection
    # ------------------------------------------------------------------

    def detect_trends(self, min_length: int = 14) -> list[dict]:
        """
        Identify consecutive up-trends and down-trends with minimum length.

        Returns
        -------
        list of {start_index, end_index, start_date, end_date,
                 direction (up/down), return_pct, duration_days}
        """
        prices = self._prices
        timestamps = self._timestamps
        if len(prices) < min_length:
            return []

        trends = []
        direction = None
        start_idx = 0

        for i in range(1, len(prices)):
            new_dir = "up" if prices[i] >= prices[i - 1] else "down"
            if direction is None:
                direction = new_dir
                start_idx = 0
            elif new_dir != direction:
                # Finish current trend
                length = i - start_idx
                if length >= min_length:
                    ret = _pct_return(prices[start_idx], prices[i - 1])
                    t_s = timestamps[start_idx]
                    t_e = timestamps[i - 1]
                    ts_s_start = (t_s / 1000 if t_s > 1e10 else t_s)
                    ts_s_end   = (t_e / 1000 if t_e > 1e10 else t_e)
                    trends.append({
                        "start_index":  start_idx,
                        "end_index":    i - 1,
                        "start_date":   self._ts_to_date(t_s),
                        "end_date":     self._ts_to_date(t_e),
                        "direction":    direction,
                        "return_pct":   round(ret, 2),
                        "duration_days": round((ts_s_end - ts_s_start) / 86400, 1),
                        "start_price":  round(prices[start_idx], 2),
                        "end_price":    round(prices[i - 1], 2),
                    })
                start_idx = i
                direction = new_dir

        return trends

    # ------------------------------------------------------------------
    # DCA Backtesting
    # ------------------------------------------------------------------

    def backtest_dca(self, amount: float, frequency: str = "monthly",
                     start_date: Optional[int] = None) -> dict:
        """
        Backtest a Dollar Cost Averaging strategy.

        Parameters
        ----------
        amount : float
            USD amount per purchase.
        frequency : str
            'daily', 'weekly', 'monthly'
        start_date : int, optional
            Unix timestamp to start from. Defaults to beginning of data.

        Returns
        -------
        dict with total_invested, final_value, total_btc, roi_pct,
        irr_pct, best_buy, worst_buy, buy_events list
        """
        freq_seconds = {"daily": 86400, "weekly": 604800, "monthly": 2592000}
        step_s = freq_seconds.get(frequency, 2592000)

        prices = self._prices
        timestamps = self._timestamps

        if not prices:
            return {}

        # Filter by start_date
        start_ts = start_date if start_date else timestamps[0]
        start_ts_s = start_ts / 1000 if start_ts > 1e10 else start_ts

        # Build index of (timestamp_s, price)
        pairs = []
        for i, ts in enumerate(timestamps):
            ts_s = ts / 1000 if ts > 1e10 else ts
            if ts_s >= start_ts_s:
                pairs.append((ts_s, prices[i]))

        if not pairs:
            return {}

        total_invested = 0.0
        total_btc      = 0.0
        buy_events     = []
        next_buy_ts    = pairs[0][0]

        for ts_s, price in pairs:
            if ts_s >= next_buy_ts and price > 0:
                btc_bought = amount / price
                total_invested += amount
                total_btc      += btc_bought
                buy_events.append({
                    "date":        self._ts_to_date(int(ts_s * 1000)),
                    "price_usd":   round(price, 2),
                    "btc_bought":  round(btc_bought, 8),
                    "amount_usd":  amount,
                })
                next_buy_ts = ts_s + step_s

        if not buy_events:
            return {}

        final_price  = prices[-1]
        final_value  = total_btc * final_price
        roi_pct      = _pct_return(total_invested, final_value)

        # Average cost basis
        avg_cost = total_invested / total_btc if total_btc > 0 else 0

        # Lump sum comparison
        first_price  = pairs[0][1]
        lump_btc     = total_invested / first_price if first_price > 0 else 0
        lump_value   = lump_btc * final_price
        lump_roi_pct = _pct_return(total_invested, lump_value)

        best_buy  = min(buy_events, key=lambda e: e["price_usd"])
        worst_buy = max(buy_events, key=lambda e: e["price_usd"])

        return {
            "strategy":         "DCA",
            "frequency":        frequency,
            "amount_per_period": amount,
            "num_purchases":    len(buy_events),
            "total_invested":   round(total_invested, 2),
            "total_btc":        round(total_btc, 8),
            "avg_cost_basis":   round(avg_cost, 2),
            "final_price":      round(final_price, 2),
            "final_value":      round(final_value, 2),
            "roi_pct":          round(roi_pct, 2),
            "vs_lump_sum": {
                "lump_sum_btc":    round(lump_btc, 8),
                "lump_sum_value":  round(lump_value, 2),
                "lump_sum_roi_pct": round(lump_roi_pct, 2),
                "dca_outperformed": roi_pct > lump_roi_pct,
            },
            "best_buy":         best_buy,
            "worst_buy":        worst_buy,
            "buy_events":       buy_events,
        }

    # ------------------------------------------------------------------
    # Strategy comparison
    # ------------------------------------------------------------------

    def compare_strategies(self, strategies: list) -> dict:
        """
        Compare multiple investment strategies over the same period.

        Parameters
        ----------
        strategies : list of dicts, each with:
            - type: 'dca' | 'lump_sum' | 'value_averaging'
            - amount: float (USD per period or total for lump sum)
            - frequency: str (for DCA)

        Returns
        -------
        dict comparing final values, ROI, and risk-adjusted metrics
        """
        results = {}
        prices = self._prices
        if not prices:
            return {}

        first_price = prices[0]
        final_price = prices[-1]

        for strat in strategies:
            stype = strat.get("type", "dca")
            amount = float(strat.get("amount", 100))
            freq   = strat.get("frequency", "monthly")
            label  = strat.get("label", f"{stype}_{amount}")

            if stype == "lump_sum":
                btc_bought   = amount / first_price if first_price > 0 else 0
                final_value  = btc_bought * final_price
                roi          = _pct_return(amount, final_value)
                results[label] = {
                    "type":          "lump_sum",
                    "total_invested": round(amount, 2),
                    "final_value":    round(final_value, 2),
                    "roi_pct":        round(roi, 2),
                    "total_btc":      round(btc_bought, 8),
                }

            elif stype == "dca":
                dca = self.backtest_dca(amount, frequency=freq)
                if dca:
                    results[label] = {
                        "type":           "dca",
                        "frequency":      freq,
                        "total_invested": dca["total_invested"],
                        "final_value":    dca["final_value"],
                        "roi_pct":        dca["roi_pct"],
                        "total_btc":      dca["total_btc"],
                        "avg_cost_basis": dca["avg_cost_basis"],
                    }

            elif stype == "value_averaging":
                # Simplified: buy more when below target growth, less when above
                target_growth_pct = strat.get("target_growth_pct", 5.0)
                va_result = self._backtest_value_averaging(amount, target_growth_pct, freq)
                results[label] = va_result

        # Rank by ROI
        ranked = sorted(results.items(), key=lambda x: x[1].get("roi_pct", 0), reverse=True)
        best_strategy = ranked[0][0] if ranked else None

        return {
            "strategies":     results,
            "best_by_roi":    best_strategy,
            "period_start":   self._ts_to_date(self._timestamps[0]),
            "period_end":     self._ts_to_date(self._timestamps[-1]),
            "first_price":    round(first_price, 2),
            "final_price":    round(final_price, 2),
            "total_return_pct": round(_pct_return(first_price, final_price), 2),
        }

    def _backtest_value_averaging(self, base_amount: float,
                                   target_growth_pct: float,
                                   frequency: str = "monthly") -> dict:
        """Simplified value averaging: target portfolio grows by fixed % each period."""
        freq_seconds = {"daily": 86400, "weekly": 604800, "monthly": 2592000}
        step_s = freq_seconds.get(frequency, 2592000)

        prices = self._prices
        timestamps = self._timestamps
        if not prices:
            return {}

        total_invested = 0.0
        total_btc      = 0.0
        target_value   = base_amount
        period_num     = 0

        next_buy_ts = (timestamps[0] / 1000 if timestamps[0] > 1e10 else timestamps[0])

        for i, ts in enumerate(timestamps):
            ts_s = ts / 1000 if ts > 1e10 else ts
            if ts_s >= next_buy_ts:
                period_num += 1
                target_value = base_amount * (1 + target_growth_pct / 100) ** period_num
                current_value = total_btc * prices[i]
                invest = target_value - current_value
                if invest > 0 and prices[i] > 0:
                    btc_bought = invest / prices[i]
                    total_btc += btc_bought
                    total_invested += invest
                elif invest < 0 and total_btc > 0:
                    # Sell some BTC
                    btc_sell = min(abs(invest) / prices[i], total_btc)
                    total_btc -= btc_sell
                    total_invested -= btc_sell * prices[i]
                next_buy_ts += step_s

        final_value = total_btc * prices[-1]
        roi = _pct_return(total_invested, final_value) if total_invested > 0 else 0

        return {
            "type":           "value_averaging",
            "total_invested": round(total_invested, 2),
            "final_value":    round(final_value, 2),
            "roi_pct":        round(roi, 2),
            "total_btc":      round(total_btc, 8),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ts_to_date(ts) -> str:
        try:
            import datetime
            ts_s = ts / 1000 if ts > 1e10 else ts
            return datetime.datetime.utcfromtimestamp(ts_s).strftime("%Y-%m-%d")
        except Exception:
            return str(ts)
