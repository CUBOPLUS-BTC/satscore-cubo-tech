"""
Trading signal generation and alert management for Magma Bitcoin app.

SignalEngine computes multi-indicator signals from price/volume series.
AlertEngine manages conditional price alerts with persistence in memory.

Signal types:
    MA_CROSSOVER        Golden/death cross (50/200 MA)
    RSI_EXTREME         RSI overbought (>70) / oversold (<30)
    VOLUME_SPIKE        Unusual volume vs rolling average
    BREAKOUT            Price breaks above resistance or below support
    DIVERGENCE          RSI divergence from price
    TREND_CHANGE        Reversal in dominant trend direction
    ACCUMULATION        Sustained high-volume low-volatility period
    DISTRIBUTION        High-volume with little price progress (topping)

Uses only Python standard library.
"""

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Signal type constants
# ---------------------------------------------------------------------------

MA_CROSSOVER   = "MA_CROSSOVER"
RSI_EXTREME    = "RSI_EXTREME"
VOLUME_SPIKE   = "VOLUME_SPIKE"
BREAKOUT       = "BREAKOUT"
DIVERGENCE     = "DIVERGENCE"
TREND_CHANGE   = "TREND_CHANGE"
ACCUMULATION   = "ACCUMULATION"
DISTRIBUTION   = "DISTRIBUTION"

ALL_SIGNAL_TYPES = [
    MA_CROSSOVER, RSI_EXTREME, VOLUME_SPIKE, BREAKOUT,
    DIVERGENCE, TREND_CHANGE, ACCUMULATION, DISTRIBUTION,
]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _ema(values: list, period: int) -> list:
    """Exponential Moving Average series."""
    if not values or period <= 0:
        return []
    k = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _sma(values: list, period: int) -> list:
    """Simple Moving Average series (length = len(values) - period + 1)."""
    if len(values) < period:
        return []
    return [_mean(values[i:i + period]) for i in range(len(values) - period + 1)]


def _rsi(prices: list, period: int = 14) -> float:
    """Wilder's RSI."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains  = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_g  = _mean(gains[:period])
    avg_l  = _mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_g = (avg_g * (period - 1) + gains[i])  / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)


def _macd(prices: list, fast: int = 12, slow: int = 26, signal_period: int = 9):
    """Returns (macd_line, signal_line, histogram) as lists."""
    if len(prices) < slow:
        return [], [], []
    fast_ema   = _ema(prices, fast)
    slow_ema   = _ema(prices, slow)
    macd_line  = [fast_ema[i] - slow_ema[i] for i in range(len(slow_ema))]
    signal_line = _ema(macd_line, signal_period)
    min_len    = min(len(macd_line), len(signal_line))
    histogram  = [macd_line[-min_len + i] - signal_line[-min_len + i] for i in range(min_len)]
    return macd_line, signal_line, histogram


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    signal_type: str
    direction:   str          # 'bullish', 'bearish', 'neutral'
    strength:    float        # 0.0 – 1.0
    description: str
    timestamp:   float = field(default_factory=time.time)
    metadata:    dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type,
            "direction":   self.direction,
            "strength":    round(self.strength, 4),
            "description": self.description,
            "timestamp":   self.timestamp,
            "metadata":    self.metadata,
        }


# ---------------------------------------------------------------------------
# SignalEngine
# ---------------------------------------------------------------------------

class SignalEngine:
    """
    Multi-indicator signal generator for Bitcoin price series.

    Input price series is a list of dicts with at minimum:
        {"close": float, "volume": float (optional), "timestamp": int}
    or simply a list of floats (close prices).
    """

    def generate_signals(self, prices: list) -> list[Signal]:
        """
        Run all signal checks and return a list of Signal objects.

        Parameters
        ----------
        prices : list
            Either list of floats (closes) or list of dicts with
            'close' and optionally 'volume'.
        """
        close_prices, volumes = self._extract(prices)
        if len(close_prices) < 30:
            return []

        signals = []

        result = self._check_ma_crossover(close_prices)
        if result:
            signals.append(result)

        result = self._check_rsi_divergence(close_prices)
        if result:
            signals.append(result)

        result = self._check_volume_breakout(close_prices, volumes)
        if result:
            signals.append(result)

        result = self._check_support_resistance_break(close_prices)
        if result:
            signals.append(result)

        result = self._check_trend_reversal(close_prices)
        if result:
            signals.append(result)

        result = self._check_momentum(close_prices)
        if result:
            signals.append(result)

        result = self._check_accumulation_distribution(close_prices, volumes)
        if result:
            signals.append(result)

        result = self._check_rsi_extreme(close_prices)
        if result:
            signals.append(result)

        return signals

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_ma_crossover(self, prices: list) -> Optional[Signal]:
        """Golden cross (50MA crosses above 200MA) / Death cross."""
        if len(prices) < 201:
            return None

        ma50_series  = _sma(prices, 50)
        ma200_series = _sma(prices, 200)
        if len(ma200_series) < 2:
            return None

        # Align: sma50 starts at index 49, sma200 at index 199
        # We need the latest two aligned values
        # sma50 has (n-49) elements, sma200 has (n-199) elements
        n = len(prices)
        sma50_latest   = _sma(prices[-52:], 50)   # last 2
        sma200_latest  = _sma(prices[-202:], 200) if n >= 202 else None

        if not sma50_latest or sma200_latest is None or len(sma200_latest) < 2:
            return None

        ma50_prev  = sma50_latest[-2]  if len(sma50_latest)  >= 2 else sma50_latest[-1]
        ma50_curr  = sma50_latest[-1]
        ma200_prev = sma200_latest[-2] if len(sma200_latest) >= 2 else sma200_latest[-1]
        ma200_curr = sma200_latest[-1]

        # Golden cross: 50MA crosses above 200MA
        if ma50_prev <= ma200_prev and ma50_curr > ma200_curr:
            gap_pct = (ma50_curr - ma200_curr) / ma200_curr
            return Signal(
                signal_type=MA_CROSSOVER,
                direction="bullish",
                strength=_clamp(0.5 + gap_pct * 10, 0.5, 1.0),
                description="Golden Cross: 50-day MA crossed above 200-day MA",
                metadata={"ma50": round(ma50_curr, 2), "ma200": round(ma200_curr, 2),
                           "cross_type": "golden"},
            )

        # Death cross: 50MA crosses below 200MA
        if ma50_prev >= ma200_prev and ma50_curr < ma200_curr:
            gap_pct = (ma200_curr - ma50_curr) / ma200_curr
            return Signal(
                signal_type=MA_CROSSOVER,
                direction="bearish",
                strength=_clamp(0.5 + gap_pct * 10, 0.5, 1.0),
                description="Death Cross: 50-day MA crossed below 200-day MA",
                metadata={"ma50": round(ma50_curr, 2), "ma200": round(ma200_curr, 2),
                           "cross_type": "death"},
            )

        return None

    def _check_rsi_extreme(self, prices: list) -> Optional[Signal]:
        """Detect RSI overbought / oversold conditions."""
        if len(prices) < 15:
            return None

        current_rsi = _rsi(prices, 14)

        if current_rsi >= 75:
            strength = _clamp((current_rsi - 70) / 30, 0, 1)
            return Signal(
                signal_type=RSI_EXTREME,
                direction="bearish",
                strength=strength,
                description=f"RSI overbought at {current_rsi:.1f} — potential reversal",
                metadata={"rsi": round(current_rsi, 2), "threshold": 75},
            )

        if current_rsi <= 25:
            strength = _clamp((30 - current_rsi) / 30, 0, 1)
            return Signal(
                signal_type=RSI_EXTREME,
                direction="bullish",
                strength=strength,
                description=f"RSI oversold at {current_rsi:.1f} — potential bounce",
                metadata={"rsi": round(current_rsi, 2), "threshold": 25},
            )

        return None

    def _check_rsi_divergence(self, prices: list) -> Optional[Signal]:
        """
        Detect RSI divergence:
        - Bullish: lower price lows but higher RSI lows
        - Bearish: higher price highs but lower RSI highs
        """
        if len(prices) < 30:
            return None

        window = 30
        recent_prices = prices[-window:]

        # Compute RSI at each point
        rsi_series = []
        for i in range(14, len(recent_prices) + 1):
            rsi_series.append(_rsi(recent_prices[:i], 14))

        if len(rsi_series) < 10:
            return None

        # Find price and RSI swing highs/lows in the recent window
        # Simplified: compare first half vs second half
        half = len(recent_prices) // 2
        price_first = _mean(recent_prices[:half])
        price_second = _mean(recent_prices[half:])
        rsi_first = _mean(rsi_series[:len(rsi_series)//2])
        rsi_second = _mean(rsi_series[len(rsi_series)//2:])

        # Bearish divergence: price going up, RSI going down
        if price_second > price_first * 1.02 and rsi_second < rsi_first - 5:
            return Signal(
                signal_type=DIVERGENCE,
                direction="bearish",
                strength=0.65,
                description="Bearish RSI divergence: rising price with falling RSI momentum",
                metadata={
                    "price_change_pct": round((price_second - price_first) / price_first * 100, 2),
                    "rsi_change":       round(rsi_second - rsi_first, 2),
                },
            )

        # Bullish divergence: price going down, RSI going up
        if price_second < price_first * 0.98 and rsi_second > rsi_first + 5:
            return Signal(
                signal_type=DIVERGENCE,
                direction="bullish",
                strength=0.65,
                description="Bullish RSI divergence: falling price with rising RSI momentum",
                metadata={
                    "price_change_pct": round((price_second - price_first) / price_first * 100, 2),
                    "rsi_change":       round(rsi_second - rsi_first, 2),
                },
            )

        return None

    def _check_volume_breakout(self, prices: list, volumes: list) -> Optional[Signal]:
        """Detect unusual volume spikes relative to rolling average."""
        if len(volumes) < 20 or not any(v > 0 for v in volumes):
            return None

        vol_mean = _mean([v for v in volumes[-20:] if v > 0])
        if vol_mean == 0:
            return None

        latest_vol = volumes[-1]
        ratio = latest_vol / vol_mean

        if ratio < 2.0:
            return None  # Not a spike

        price_change_pct = 0.0
        if len(prices) >= 2 and prices[-2] > 0:
            price_change_pct = (prices[-1] - prices[-2]) / prices[-2] * 100

        direction = "bullish" if price_change_pct >= 0 else "bearish"
        strength  = _clamp(0.4 + (ratio - 2) * 0.1, 0.4, 1.0)

        return Signal(
            signal_type=VOLUME_SPIKE,
            direction=direction,
            strength=strength,
            description=f"Volume spike {ratio:.1f}x average with {price_change_pct:+.2f}% price move",
            metadata={
                "volume_ratio": round(ratio, 2),
                "price_change_pct": round(price_change_pct, 4),
                "avg_volume": round(vol_mean, 0),
                "latest_volume": round(latest_vol, 0),
            },
        )

    def _check_support_resistance_break(self, prices: list) -> Optional[Signal]:
        """Detect breakout above resistance or breakdown below support."""
        if len(prices) < 30:
            return None

        lookback = min(30, len(prices) - 1)
        recent   = prices[-(lookback + 1):-1]   # exclude current
        current  = prices[-1]

        if not recent:
            return None

        resistance = max(recent)
        support    = min(recent)

        # Breakout above resistance
        if current > resistance * 1.01:
            breakout_pct = (current - resistance) / resistance * 100
            return Signal(
                signal_type=BREAKOUT,
                direction="bullish",
                strength=_clamp(0.5 + breakout_pct * 0.05, 0.5, 1.0),
                description=f"Breakout above {lookback}-period resistance at ${resistance:,.0f}",
                metadata={
                    "resistance_level": round(resistance, 2),
                    "current_price":    round(current, 2),
                    "breakout_pct":     round(breakout_pct, 2),
                },
            )

        # Breakdown below support
        if current < support * 0.99:
            breakdown_pct = (support - current) / support * 100
            return Signal(
                signal_type=BREAKOUT,
                direction="bearish",
                strength=_clamp(0.5 + breakdown_pct * 0.05, 0.5, 1.0),
                description=f"Breakdown below {lookback}-period support at ${support:,.0f}",
                metadata={
                    "support_level":  round(support, 2),
                    "current_price":  round(current, 2),
                    "breakdown_pct":  round(breakdown_pct, 2),
                },
            )

        return None

    def _check_trend_reversal(self, prices: list) -> Optional[Signal]:
        """Detect a reversal in the dominant short-term trend."""
        if len(prices) < 20:
            return None

        # Short MA vs medium MA
        ma5  = _mean(prices[-5:])
        ma10 = _mean(prices[-10:])
        ma20 = _mean(prices[-20:])

        # Previous state (shifted by 3 periods)
        prev_ma5  = _mean(prices[-8:-3])
        prev_ma10 = _mean(prices[-13:-3])

        # Reversal: was bearish (ma5 < ma10), now bullish (ma5 > ma10)
        was_bearish = prev_ma5 < prev_ma10
        now_bullish = ma5 > ma10

        if was_bearish and now_bullish:
            return Signal(
                signal_type=TREND_CHANGE,
                direction="bullish",
                strength=0.6,
                description="Short-term trend reversal: upward momentum gaining vs prior downtrend",
                metadata={"ma5": round(ma5, 2), "ma10": round(ma10, 2), "ma20": round(ma20, 2)},
            )

        was_bullish   = prev_ma5 > prev_ma10
        now_bearish   = ma5 < ma10

        if was_bullish and now_bearish:
            return Signal(
                signal_type=TREND_CHANGE,
                direction="bearish",
                strength=0.6,
                description="Short-term trend reversal: downward momentum gaining vs prior uptrend",
                metadata={"ma5": round(ma5, 2), "ma10": round(ma10, 2), "ma20": round(ma20, 2)},
            )

        return None

    def _check_momentum(self, prices: list) -> Optional[Signal]:
        """Check MACD histogram crossover for momentum signal."""
        if len(prices) < 35:
            return None

        macd_line, signal_line, histogram = _macd(prices)
        if len(histogram) < 3:
            return None

        h_prev = histogram[-2]
        h_curr = histogram[-1]

        # MACD histogram cross from negative to positive
        if h_prev < 0 and h_curr > 0:
            return Signal(
                signal_type=MA_CROSSOVER,
                direction="bullish",
                strength=0.55,
                description="MACD histogram crossed above zero line — momentum turning bullish",
                metadata={"histogram_current": round(h_curr, 4),
                           "histogram_previous": round(h_prev, 4)},
            )

        if h_prev > 0 and h_curr < 0:
            return Signal(
                signal_type=MA_CROSSOVER,
                direction="bearish",
                strength=0.55,
                description="MACD histogram crossed below zero line — momentum turning bearish",
                metadata={"histogram_current": round(h_curr, 4),
                           "histogram_previous": round(h_prev, 4)},
            )

        return None

    def _check_accumulation_distribution(self, prices: list, volumes: list) -> Optional[Signal]:
        """
        Detect accumulation (high vol, tight range, no big move up) or
        distribution (high vol, tight range, no big move despite attempt).
        """
        if len(prices) < 20 or not any(v > 0 for v in volumes):
            return None

        recent_prices  = prices[-20:]
        recent_volumes = [v for v in volumes[-20:] if v > 0]

        price_range_pct = (max(recent_prices) - min(recent_prices)) / _mean(recent_prices) * 100
        vol_mean_overall = _mean([v for v in volumes if v > 0]) if any(v > 0 for v in volumes) else 1
        vol_mean_recent  = _mean(recent_volumes) if recent_volumes else 1
        vol_ratio        = vol_mean_recent / vol_mean_overall if vol_mean_overall > 0 else 1

        price_trend_pct = (prices[-1] - prices[-20]) / prices[-20] * 100 if prices[-20] > 0 else 0

        # Accumulation: above-average volume, tight price range, slight upward bias
        if vol_ratio > 1.2 and price_range_pct < 10 and -3 < price_trend_pct < 10:
            return Signal(
                signal_type=ACCUMULATION,
                direction="bullish",
                strength=0.55,
                description="Accumulation pattern: elevated volume with compressed price range",
                metadata={
                    "vol_ratio":       round(vol_ratio, 2),
                    "price_range_pct": round(price_range_pct, 2),
                    "trend_pct":       round(price_trend_pct, 2),
                },
            )

        # Distribution: above-average volume, price stalls or slightly negative
        if vol_ratio > 1.2 and price_range_pct < 10 and -10 < price_trend_pct < 3:
            return Signal(
                signal_type=DISTRIBUTION,
                direction="bearish",
                strength=0.50,
                description="Distribution pattern: elevated volume but price making no progress",
                metadata={
                    "vol_ratio":       round(vol_ratio, 2),
                    "price_range_pct": round(price_range_pct, 2),
                    "trend_pct":       round(price_trend_pct, 2),
                },
            )

        return None

    # ------------------------------------------------------------------
    # Backtesting
    # ------------------------------------------------------------------

    def backtest_signal(self, signal_type: str, prices: list) -> dict:
        """
        Backtest a specific signal type on historical prices.
        Simulates: enter on signal, exit after 14 days, measure return.

        Returns
        -------
        dict with total_signals, avg_return_pct, win_rate_pct,
        best_trade, worst_trade, all_trades list
        """
        close_prices, volumes = self._extract(prices)
        if len(close_prices) < 60:
            return {"error": "Insufficient data (need 60+ periods)"}

        trades = []
        i = 30
        while i < len(close_prices) - 15:
            window = close_prices[:i + 1]
            vol_window = volumes[:i + 1]

            signal = None
            if signal_type == MA_CROSSOVER:
                signal = self._check_ma_crossover(window)
            elif signal_type == RSI_EXTREME:
                signal = self._check_rsi_extreme(window)
            elif signal_type == VOLUME_SPIKE:
                signal = self._check_volume_breakout(window, vol_window)
            elif signal_type == BREAKOUT:
                signal = self._check_support_resistance_break(window)
            elif signal_type == DIVERGENCE:
                signal = self._check_rsi_divergence(window)
            elif signal_type == TREND_CHANGE:
                signal = self._check_trend_reversal(window)
            elif signal_type == ACCUMULATION:
                signal = self._check_accumulation_distribution(window, vol_window)

            if signal:
                entry_price = close_prices[i]
                exit_idx    = min(i + 14, len(close_prices) - 1)
                exit_price  = close_prices[exit_idx]
                if entry_price > 0:
                    raw_ret = (exit_price - entry_price) / entry_price * 100
                    # Flip for bearish signals
                    trade_ret = -raw_ret if signal.direction == "bearish" else raw_ret
                    trades.append({
                        "entry_index": i,
                        "exit_index":  exit_idx,
                        "entry_price": round(entry_price, 2),
                        "exit_price":  round(exit_price, 2),
                        "return_pct":  round(trade_ret, 4),
                        "direction":   signal.direction,
                        "won":         trade_ret > 0,
                    })
                i += 15  # skip forward to avoid overlapping trades
            else:
                i += 1

        if not trades:
            return {
                "signal_type": signal_type,
                "total_signals": 0,
                "message": "No signals triggered on provided data",
            }

        returns    = [t["return_pct"] for t in trades]
        wins       = [t for t in trades if t["won"]]
        win_rate   = len(wins) / len(trades) * 100
        avg_return = _mean(returns)
        best_trade = max(trades, key=lambda t: t["return_pct"])
        worst_trade= min(trades, key=lambda t: t["return_pct"])

        profit_factor = 0.0
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss   = abs(sum(r for r in returns if r < 0))
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss

        return {
            "signal_type":    signal_type,
            "total_signals":  len(trades),
            "win_rate_pct":   round(win_rate, 2),
            "avg_return_pct": round(avg_return, 4),
            "profit_factor":  round(profit_factor, 2),
            "best_trade":     best_trade,
            "worst_trade":    worst_trade,
            "all_trades":     trades,
            "holding_period": "14 periods",
        }

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_signal_summary(self, prices: list) -> dict:
        """
        Compute all signals and return a consensus summary.

        Returns
        -------
        dict with overall_bias, confidence_pct, active_signals list,
        bullish_count, bearish_count, neutral_count
        """
        signals = self.generate_signals(prices)
        if not signals:
            return {
                "overall_bias":     "neutral",
                "confidence_pct":   0,
                "active_signals":   [],
                "bullish_count":    0,
                "bearish_count":    0,
                "neutral_count":    0,
            }

        bullish_signals = [s for s in signals if s.direction == "bullish"]
        bearish_signals = [s for s in signals if s.direction == "bearish"]
        neutral_signals = [s for s in signals if s.direction == "neutral"]

        bullish_weight = sum(s.strength for s in bullish_signals)
        bearish_weight = sum(s.strength for s in bearish_signals)
        total_weight   = bullish_weight + bearish_weight + 0.01

        if bullish_weight > bearish_weight * 1.3:
            bias = "bullish"
            confidence = _clamp(bullish_weight / total_weight * 100, 50, 95)
        elif bearish_weight > bullish_weight * 1.3:
            bias = "bearish"
            confidence = _clamp(bearish_weight / total_weight * 100, 50, 95)
        else:
            bias = "neutral"
            confidence = 40.0

        close_prices, _ = self._extract(prices)
        current_rsi     = _rsi(close_prices, 14) if len(close_prices) >= 15 else 50

        return {
            "overall_bias":     bias,
            "confidence_pct":   round(confidence, 1),
            "active_signals":   [s.to_dict() for s in signals],
            "bullish_count":    len(bullish_signals),
            "bearish_count":    len(bearish_signals),
            "neutral_count":    len(neutral_signals),
            "total_signals":    len(signals),
            "current_rsi":      round(current_rsi, 2),
            "computed_at":      int(time.time()),
        }

    def score_setup(self, prices: list) -> dict:
        """
        Rate the current trading setup on a 0–100 scale.
        Combines signal count, strength, and market context.
        """
        summary = self.get_signal_summary(prices)
        signals = self.generate_signals(prices)

        if not signals:
            return {"score": 50, "grade": "C", "summary": "No clear setup detected"}

        bias = summary["overall_bias"]
        conf = summary["confidence_pct"]

        # Strong setup: strong bias, multiple confirming signals
        signal_count = summary["bullish_count"] if bias == "bullish" else summary["bearish_count"]
        score = _clamp(conf * 0.7 + signal_count * 5, 0, 100)

        grade = "F"
        if score >= 80:
            grade = "A"
        elif score >= 65:
            grade = "B"
        elif score >= 50:
            grade = "C"
        elif score >= 35:
            grade = "D"

        return {
            "score":          round(score, 1),
            "grade":          grade,
            "bias":           bias,
            "confidence_pct": conf,
            "signal_count":   len(signals),
            "key_signals":    [s.to_dict() for s in signals[:3]],
            "summary": (
                f"{grade} setup: {bias} bias with {len(signals)} active signal(s), "
                f"{conf:.0f}% confidence."
            ),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract(prices: list) -> tuple[list, list]:
        """Extract close prices and volumes from mixed input."""
        if not prices:
            return [], []
        if isinstance(prices[0], dict):
            closes  = [float(p.get("close", p.get("price", 0))) for p in prices]
            volumes = [float(p.get("volume", 0)) for p in prices]
        else:
            closes  = [float(p) for p in prices]
            volumes = [0.0] * len(closes)
        return closes, volumes


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    alert_id:    str
    alert_type:  str   # 'price_above', 'price_below', 'pct_change', 'rsi_above', 'rsi_below', 'signal'
    params:      dict
    created_at:  float = field(default_factory=time.time)
    triggered:   bool  = False
    triggered_at: Optional[float] = None
    active:      bool  = True
    note:        str   = ""

    def to_dict(self) -> dict:
        return {
            "alert_id":     self.alert_id,
            "alert_type":   self.alert_type,
            "params":       self.params,
            "created_at":   self.created_at,
            "triggered":    self.triggered,
            "triggered_at": self.triggered_at,
            "active":       self.active,
            "note":         self.note,
        }


# ---------------------------------------------------------------------------
# AlertEngine
# ---------------------------------------------------------------------------

class AlertEngine:
    """
    Manage conditional price and signal alerts.
    Alerts are stored in memory; for persistence use the DB layer.

    Supported alert types:
        price_above    : triggers when current_price >= params['threshold']
        price_below    : triggers when current_price <= params['threshold']
        pct_change     : triggers on |% change in window| >= params['pct']
        rsi_above      : triggers when RSI >= params['level']
        rsi_below      : triggers when RSI <= params['level']
        signal         : triggers when a specific signal type fires
    """

    def __init__(self):
        self._alerts: dict[str, Alert] = {}
        self._signal_engine = SignalEngine()

    def add_alert(self, alert_type: str, params: dict, note: str = "") -> str:
        """
        Create a new alert.

        Returns
        -------
        str : alert_id
        """
        alert_id = str(uuid.uuid4())[:8].upper()
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            params=params,
            note=note,
        )
        self._alerts[alert_id] = alert
        return alert_id

    def check_alerts(self, current_data: dict) -> list[dict]:
        """
        Check all active alerts against current market data.

        Parameters
        ----------
        current_data : dict
            Must include 'price' (float) and optionally 'prices_series'
            (list of floats for RSI and signal checks).

        Returns
        -------
        list of triggered alert dicts
        """
        triggered = []
        price = float(current_data.get("price", 0))
        prices_series = current_data.get("prices_series", [])

        for alert in list(self._alerts.values()):
            if not alert.active or alert.triggered:
                continue

            fired = False
            reason = ""

            if alert.alert_type == "price_above":
                threshold = float(alert.params.get("threshold", 0))
                if price >= threshold:
                    fired = True
                    reason = f"Price ${price:,.2f} reached above ${threshold:,.2f}"

            elif alert.alert_type == "price_below":
                threshold = float(alert.params.get("threshold", 0))
                if price <= threshold:
                    fired = True
                    reason = f"Price ${price:,.2f} dropped below ${threshold:,.2f}"

            elif alert.alert_type == "pct_change":
                required_pct = float(alert.params.get("pct", 5))
                ref_price    = float(alert.params.get("ref_price", price))
                if ref_price > 0:
                    change = abs(price - ref_price) / ref_price * 100
                    if change >= required_pct:
                        fired = True
                        direction = "up" if price > ref_price else "down"
                        reason = f"Price moved {change:.2f}% {direction} from reference ${ref_price:,.2f}"

            elif alert.alert_type == "rsi_above":
                level = float(alert.params.get("level", 70))
                if prices_series:
                    current_rsi = _rsi(prices_series, 14)
                    if current_rsi >= level:
                        fired = True
                        reason = f"RSI {current_rsi:.1f} exceeded {level}"

            elif alert.alert_type == "rsi_below":
                level = float(alert.params.get("level", 30))
                if prices_series:
                    current_rsi = _rsi(prices_series, 14)
                    if current_rsi <= level:
                        fired = True
                        reason = f"RSI {current_rsi:.1f} fell below {level}"

            elif alert.alert_type == "signal":
                target_signal = alert.params.get("signal_type", "")
                if prices_series and target_signal:
                    signals = self._signal_engine.generate_signals(prices_series)
                    matching = [s for s in signals if s.signal_type == target_signal]
                    if matching:
                        fired = True
                        reason = f"Signal {target_signal} fired: {matching[0].description}"

            if fired:
                alert.triggered    = True
                alert.triggered_at = time.time()
                if not alert.params.get("repeating", False):
                    alert.active = False
                triggered.append({
                    **alert.to_dict(),
                    "trigger_reason":  reason,
                    "current_price":   price,
                })

        return triggered

    def get_active_alerts(self) -> list[dict]:
        """Return all non-triggered, active alerts."""
        return [a.to_dict() for a in self._alerts.values() if a.active and not a.triggered]

    def get_all_alerts(self) -> list[dict]:
        """Return all alerts including triggered."""
        return [a.to_dict() for a in self._alerts.values()]

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID."""
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            return True
        return False

    def reset_alert(self, alert_id: str) -> bool:
        """Re-arm a triggered alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        alert.triggered    = False
        alert.triggered_at = None
        alert.active       = True
        return True

    def get_alert_count(self) -> dict:
        alerts = list(self._alerts.values())
        return {
            "total":     len(alerts),
            "active":    sum(1 for a in alerts if a.active and not a.triggered),
            "triggered": sum(1 for a in alerts if a.triggered),
        }
