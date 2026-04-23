"""
Financial data models for the Magma Bitcoin app.

Pure standard-library Python. Uses dataclasses (Python 3.7+).
"""

import math
import uuid
import datetime
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# PricePoint
# ---------------------------------------------------------------------------

@dataclass
class PricePoint:
    """
    A single candlestick / OHLCV data point.

    Attributes
    ----------
    timestamp : int   — Unix timestamp (seconds)
    open      : float
    high      : float
    low       : float
    close     : float
    volume    : float
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def typical_price(self) -> float:
        """(high + low + close) / 3"""
        return (self.high + self.low + self.close) / 3.0

    def range(self) -> float:
        """high - low"""
        return self.high - self.low

    def body(self) -> float:
        """abs(close - open)"""
        return abs(self.close - self.open)

    def is_bullish(self) -> bool:
        return self.close >= self.open

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PricePoint":
        return cls(
            timestamp=int(data["timestamp"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data.get("volume", 0.0)),
        )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------

class OHLCV:
    """
    Container for an ordered series of PricePoint objects, with methods for
    resampling, return calculation, risk metrics, and statistical summaries.
    """

    RESAMPLE_SECONDS = {
        "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "12h": 43200,
        "1d": 86400, "3d": 259200, "1w": 604800,
    }

    def __init__(self, candles: List[PricePoint] = None):
        self.candles: List[PricePoint] = candles or []

    # -- Construction helpers -----------------------------------------------

    @classmethod
    def from_raw(cls, data: list) -> "OHLCV":
        """
        Create OHLCV from a list of raw dicts or lists.

        Accepts either:
          - dicts with keys: timestamp, open, high, low, close, volume
          - lists: [timestamp, open, high, low, close, volume]
        """
        candles = []
        for row in data:
            if isinstance(row, dict):
                candles.append(PricePoint.from_dict(row))
            elif isinstance(row, (list, tuple)) and len(row) >= 5:
                candles.append(PricePoint(
                    timestamp=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]) if len(row) > 5 else 0.0,
                ))
            else:
                raise ValueError(f"Unrecognised row format: {row!r}")
        candles.sort(key=lambda c: c.timestamp)
        return cls(candles)

    def resample(self, interval: str) -> "OHLCV":
        """
        Resample candles to a coarser timeframe.

        Parameters
        ----------
        interval : str  — e.g. '5m', '1h', '1d'

        Returns
        -------
        OHLCV with resampled candles
        """
        if interval not in self.RESAMPLE_SECONDS:
            raise ValueError(
                f"Unknown interval '{interval}'. "
                f"Valid: {list(self.RESAMPLE_SECONDS.keys())}"
            )
        period_secs = self.RESAMPLE_SECONDS[interval]
        buckets: Dict[int, List[PricePoint]] = {}

        for candle in self.candles:
            bucket_ts = (candle.timestamp // period_secs) * period_secs
            buckets.setdefault(bucket_ts, []).append(candle)

        new_candles = []
        for bucket_ts in sorted(buckets.keys()):
            group = buckets[bucket_ts]
            new_candles.append(PricePoint(
                timestamp=bucket_ts,
                open=group[0].open,
                high=max(c.high for c in group),
                low=min(c.low for c in group),
                close=group[-1].close,
                volume=sum(c.volume for c in group),
            ))

        return OHLCV(new_candles)

    # -- Price series helpers -----------------------------------------------

    def closes(self) -> list:
        return [c.close for c in self.candles]

    def highs(self) -> list:
        return [c.high for c in self.candles]

    def lows(self) -> list:
        return [c.low for c in self.candles]

    def volumes(self) -> list:
        return [c.volume for c in self.candles]

    def timestamps(self) -> list:
        return [c.timestamp for c in self.candles]

    # -- Return calculations ------------------------------------------------

    def get_returns(self, price_type: str = "close") -> list:
        """
        Simple percentage returns: (P_t - P_{t-1}) / P_{t-1}

        Parameters
        ----------
        price_type : str  — 'close', 'open', 'high', 'low', 'typical'

        Returns
        -------
        list of float (length = len(candles) - 1)
        """
        if not self.candles:
            return []
        if price_type == "close":
            prices = [c.close for c in self.candles]
        elif price_type == "open":
            prices = [c.open for c in self.candles]
        elif price_type == "high":
            prices = [c.high for c in self.candles]
        elif price_type == "low":
            prices = [c.low for c in self.candles]
        elif price_type == "typical":
            prices = [c.typical_price() for c in self.candles]
        else:
            raise ValueError(f"Unknown price_type: {price_type}")

        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                returns.append((prices[i] - prices[i - 1]) / prices[i - 1])
            else:
                returns.append(0.0)
        return returns

    def get_log_returns(self) -> list:
        """
        Log returns: ln(P_t / P_{t-1})
        """
        closes = self.closes()
        result = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0 and closes[i] > 0:
                result.append(math.log(closes[i] / closes[i - 1]))
            else:
                result.append(0.0)
        return result

    def get_volatility(self, window: int = 30, annualise: bool = True) -> float:
        """
        Annualised historical volatility (standard deviation of log returns).

        Parameters
        ----------
        window    : int   — rolling window; if 0 uses all data
        annualise : bool  — multiply by sqrt(252) if True (daily data)

        Returns
        -------
        float
        """
        log_returns = self.get_log_returns()
        if not log_returns:
            return 0.0
        if window > 0:
            log_returns = log_returns[-window:]
        if len(log_returns) < 2:
            return 0.0
        stdev = statistics.stdev(log_returns)
        if annualise:
            stdev *= math.sqrt(252)
        return stdev

    # -- Drawdown -----------------------------------------------------------

    def get_drawdown(self) -> dict:
        """
        Maximum drawdown analysis.

        Returns
        -------
        dict with:
            'max_drawdown'       : float  — as a decimal (e.g. -0.30 = -30%)
            'max_drawdown_pct'   : float  — as percentage
            'peak_index'         : int
            'trough_index'       : int
            'peak_timestamp'     : int or None
            'trough_timestamp'   : int or None
            'peak_price'         : float
            'trough_price'       : float
            'recovery_index'     : int or None
            'drawdown_series'    : list of floats
        """
        closes = self.closes()
        if not closes:
            return {}

        peak = closes[0]
        peak_idx = 0
        max_dd = 0.0
        max_dd_peak_idx = 0
        max_dd_trough_idx = 0
        drawdown_series = []

        for i, price in enumerate(closes):
            if price > peak:
                peak = price
                peak_idx = i
            dd = (price - peak) / peak if peak > 0 else 0.0
            drawdown_series.append(dd)
            if dd < max_dd:
                max_dd = dd
                max_dd_peak_idx = peak_idx
                max_dd_trough_idx = i

        # Find recovery (first time price returns to peak after trough)
        trough_price = closes[max_dd_trough_idx]
        peak_price = closes[max_dd_peak_idx]
        recovery_idx = None
        for i in range(max_dd_trough_idx + 1, len(closes)):
            if closes[i] >= peak_price:
                recovery_idx = i
                break

        return {
            "max_drawdown": round(max_dd, 6),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "peak_index": max_dd_peak_idx,
            "trough_index": max_dd_trough_idx,
            "peak_timestamp": self.candles[max_dd_peak_idx].timestamp if self.candles else None,
            "trough_timestamp": self.candles[max_dd_trough_idx].timestamp if self.candles else None,
            "peak_price": round(peak_price, 8),
            "trough_price": round(trough_price, 8),
            "recovery_index": recovery_idx,
            "drawdown_series": [round(d, 6) for d in drawdown_series],
        }

    # -- Risk ratios --------------------------------------------------------

    def get_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Annualised Sharpe Ratio (assumes daily data).

        Sharpe = (mean_daily_return - daily_rf) / stdev_daily_return * sqrt(252)
        """
        returns = self.get_returns()
        if len(returns) < 2:
            return 0.0
        daily_rf = risk_free_rate / 252
        excess = [r - daily_rf for r in returns]
        mean_excess = sum(excess) / len(excess)
        if len(excess) < 2:
            return 0.0
        std = statistics.stdev(excess)
        if std == 0:
            return 0.0
        return mean_excess / std * math.sqrt(252)

    def get_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Annualised Sortino Ratio (downside deviation only).
        """
        returns = self.get_returns()
        if len(returns) < 2:
            return 0.0
        daily_rf = risk_free_rate / 252
        excess = [r - daily_rf for r in returns]
        mean_excess = sum(excess) / len(excess)
        downside = [r for r in excess if r < 0]
        if not downside:
            return float("inf")
        downside_dev = math.sqrt(sum(r ** 2 for r in downside) / len(downside))
        if downside_dev == 0:
            return 0.0
        return mean_excess / downside_dev * math.sqrt(252)

    def get_calmar_ratio(self) -> float:
        """
        Calmar Ratio = annualised return / abs(max drawdown).
        """
        returns = self.get_returns()
        if not returns:
            return 0.0
        ann_return = (1 + sum(returns) / len(returns)) ** 252 - 1
        dd = self.get_drawdown()
        max_dd = abs(dd.get("max_drawdown", 0))
        if max_dd == 0:
            return float("inf")
        return ann_return / max_dd

    # -- Statistics ---------------------------------------------------------

    def summary(self) -> dict:
        """
        Comprehensive statistical summary of close prices and returns.

        Returns
        -------
        dict with descriptive stats, percentiles, returns stats, risk metrics
        """
        closes = self.closes()
        returns = self.get_returns()
        log_rets = self.get_log_returns()

        if not closes:
            return {"error": "No data"}

        n = len(closes)
        mean_c = sum(closes) / n
        sorted_closes = sorted(closes)

        def percentile(data, pct):
            k = (len(data) - 1) * pct / 100
            lo, hi = int(k), math.ceil(k)
            if lo == hi:
                return data[lo]
            return data[lo] + (data[hi] - data[lo]) * (k - lo)

        std_c = statistics.stdev(closes) if n > 1 else 0.0

        # Skewness
        if n > 2 and std_c > 0:
            skew = sum((x - mean_c) ** 3 for x in closes) / n / std_c ** 3
        else:
            skew = 0.0

        # Excess kurtosis
        if n > 3 and std_c > 0:
            kurt = sum((x - mean_c) ** 4 for x in closes) / n / std_c ** 4 - 3
        else:
            kurt = 0.0

        result = {
            "n": n,
            "first_timestamp": self.candles[0].timestamp if self.candles else None,
            "last_timestamp": self.candles[-1].timestamp if self.candles else None,
            "price": {
                "open": self.candles[0].open if self.candles else None,
                "close": self.candles[-1].close if self.candles else None,
                "min": min(closes),
                "max": max(closes),
                "mean": round(mean_c, 4),
                "median": round(percentile(sorted_closes, 50), 4),
                "std": round(std_c, 4),
                "skewness": round(skew, 4),
                "excess_kurtosis": round(kurt, 4),
                "p5": round(percentile(sorted_closes, 5), 4),
                "p25": round(percentile(sorted_closes, 25), 4),
                "p75": round(percentile(sorted_closes, 75), 4),
                "p95": round(percentile(sorted_closes, 95), 4),
            },
            "returns": {},
            "risk": {},
        }

        if returns:
            m = sum(returns) / len(returns)
            std_r = statistics.stdev(returns) if len(returns) > 1 else 0.0
            result["returns"] = {
                "mean_daily": round(m, 6),
                "std_daily": round(std_r, 6),
                "best_day": round(max(returns), 4),
                "worst_day": round(min(returns), 4),
                "positive_days": sum(1 for r in returns if r > 0),
                "negative_days": sum(1 for r in returns if r < 0),
                "total_return": round((closes[-1] / closes[0] - 1) * 100, 2),
            }

        result["risk"] = {
            "volatility_annualised": round(self.get_volatility(), 4),
            "sharpe_ratio": round(self.get_sharpe_ratio(), 4),
            "sortino_ratio": round(self.get_sortino_ratio(), 4),
            "calmar_ratio": round(self.get_calmar_ratio(), 4),
            "max_drawdown_pct": self.get_drawdown().get("max_drawdown_pct", 0),
        }

        return result

    # -- Slicing & merging --------------------------------------------------

    def slice(self, start_ts: int, end_ts: int) -> "OHLCV":
        """Return a new OHLCV covering [start_ts, end_ts]."""
        filtered = [c for c in self.candles if start_ts <= c.timestamp <= end_ts]
        return OHLCV(filtered)

    def merge(self, other: "OHLCV") -> "OHLCV":
        """Merge two OHLCV series, deduplicating by timestamp."""
        ts_map = {c.timestamp: c for c in self.candles}
        for c in other.candles:
            ts_map[c.timestamp] = c
        merged = sorted(ts_map.values(), key=lambda c: c.timestamp)
        return OHLCV(merged)

    def to_dict(self) -> dict:
        return {
            "candles": [c.to_dict() for c in self.candles],
            "count": len(self.candles),
            "first_ts": self.candles[0].timestamp if self.candles else None,
            "last_ts": self.candles[-1].timestamp if self.candles else None,
        }

    def __len__(self):
        return len(self.candles)

    def __getitem__(self, idx):
        return self.candles[idx]

    def __iter__(self):
        return iter(self.candles)

    def __repr__(self):
        return f"<OHLCV n={len(self.candles)} candles>"


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """
    A single executed trade.

    Attributes
    ----------
    id        : str   — unique identifier
    timestamp : int   — Unix timestamp
    side      : str   — 'buy' or 'sell'
    amount    : float — units traded
    price     : float — execution price
    fee       : float — trading fee in quote currency
    total     : float — gross amount in quote currency (amount * price)
    """
    timestamp: int
    side: str
    amount: float
    price: float
    fee: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def total(self) -> float:
        return self.amount * self.price

    @property
    def net_total(self) -> float:
        return self.total + self.fee if self.side == "buy" else self.total - self.fee

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "side": self.side,
            "amount": self.amount,
            "price": self.price,
            "fee": self.fee,
            "total": round(self.total, 8),
            "net_total": round(self.net_total, 8),
        }


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

class Position:
    """
    Represents an open or closed trading position.
    """

    def __init__(
        self,
        side: str,
        amount: float,
        entry_price: float,
        timestamp: int,
        position_id: str = None,
    ):
        """
        Open a new position.

        Parameters
        ----------
        side        : 'long' or 'short'
        amount      : float  — position size in base currency
        entry_price : float
        timestamp   : int    — Unix open time
        position_id : str    — optional custom id
        """
        self.id = position_id or str(uuid.uuid4())
        self.side = side
        self.amount = amount
        self.entry_price = entry_price
        self.open_timestamp = timestamp
        self.close_timestamp: Optional[int] = None
        self.exit_price: Optional[float] = None
        self.is_open = True
        self.trades: List[Trade] = []

    def open(self, side: str, amount: float, entry_price: float, timestamp: int):
        """Re-open or re-initialise the position."""
        self.side = side
        self.amount = amount
        self.entry_price = entry_price
        self.open_timestamp = timestamp
        self.close_timestamp = None
        self.exit_price = None
        self.is_open = True

    def close(self, exit_price: float, timestamp: int) -> dict:
        """
        Close the position and return P&L details.

        Returns
        -------
        dict with realized_pnl, realized_pnl_pct, duration_seconds, etc.
        """
        if not self.is_open:
            raise ValueError("Position is already closed")
        self.exit_price = exit_price
        self.close_timestamp = timestamp
        self.is_open = False

        if self.side == "long":
            pnl = (exit_price - self.entry_price) * self.amount
        else:
            pnl = (self.entry_price - exit_price) * self.amount

        pnl_pct = pnl / (self.entry_price * self.amount) * 100 if self.entry_price != 0 else 0.0
        duration = timestamp - self.open_timestamp

        return {
            "id": self.id,
            "side": self.side,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "exit_price": exit_price,
            "realized_pnl": round(pnl, 8),
            "realized_pnl_pct": round(pnl_pct, 4),
            "duration_seconds": duration,
        }

    def get_unrealized_pnl(self, current_price: float) -> dict:
        """
        Unrealized P&L at a given current price.

        Returns
        -------
        dict with unrealized_pnl, unrealized_pnl_pct, current_value
        """
        if not self.is_open:
            return {"error": "Position is closed"}

        if self.side == "long":
            pnl = (current_price - self.entry_price) * self.amount
        else:
            pnl = (self.entry_price - current_price) * self.amount

        cost_basis = self.entry_price * self.amount
        pnl_pct = pnl / cost_basis * 100 if cost_basis != 0 else 0.0
        current_value = current_price * self.amount

        return {
            "id": self.id,
            "side": self.side,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "current_price": current_price,
            "current_value": round(current_value, 8),
            "cost_basis": round(cost_basis, 8),
            "unrealized_pnl": round(pnl, 8),
            "unrealized_pnl_pct": round(pnl_pct, 4),
        }

    def get_duration(self) -> int:
        """
        Duration in seconds (up to now if open, to close if closed).
        """
        now = int(datetime.datetime.utcnow().timestamp())
        end = self.close_timestamp if self.close_timestamp else now
        return end - self.open_timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "side": self.side,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "open_timestamp": self.open_timestamp,
            "close_timestamp": self.close_timestamp,
            "exit_price": self.exit_price,
            "is_open": self.is_open,
            "duration_seconds": self.get_duration(),
        }


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class Portfolio:
    """
    Manages a collection of open and closed positions across multiple assets.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.positions: Dict[str, Position] = {}   # id -> Position
        self.closed_positions: List[dict] = []     # realized P&L records
        self.cash: float = 0.0

    def add_position(self, position: Position):
        """Register a new open position."""
        self.positions[position.id] = position

    def close_position(self, position_id: str, exit_price: float) -> dict:
        """
        Close an open position and record the result.

        Returns
        -------
        dict — P&L record from Position.close()
        """
        if position_id not in self.positions:
            raise KeyError(f"Position {position_id!r} not found")
        pos = self.positions[position_id]
        ts = int(datetime.datetime.utcnow().timestamp())
        result = pos.close(exit_price, ts)
        self.closed_positions.append(result)
        del self.positions[position_id]
        return result

    def get_value(self, prices: dict) -> float:
        """
        Total portfolio value at given prices.

        Parameters
        ----------
        prices : dict mapping symbol/asset to current price
                 e.g. {'BTC': 50000, 'ETH': 3000}
                 Positions whose keys are not in prices are valued at entry_price.

        Returns
        -------
        float — sum of all open position values + cash
        """
        total = self.cash
        for pos in self.positions.values():
            price = prices.get(pos.side, pos.entry_price)
            total += pos.amount * price
        return total

    def get_allocation(self) -> dict:
        """
        Current open position sizes (not weighted by price).

        Returns
        -------
        dict mapping position id -> amount
        """
        return {pid: pos.amount for pid, pos in self.positions.items()}

    def get_performance(self) -> dict:
        """
        Summary of all closed positions' realized P&L.

        Returns
        -------
        dict with total_realized_pnl, win_rate, avg_win, avg_loss, profit_factor
        """
        if not self.closed_positions:
            return {
                "closed_count": 0,
                "total_realized_pnl": 0.0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
            }

        wins = [p["realized_pnl"] for p in self.closed_positions if p["realized_pnl"] > 0]
        losses = [p["realized_pnl"] for p in self.closed_positions if p["realized_pnl"] <= 0]
        total_pnl = sum(p["realized_pnl"] for p in self.closed_positions)
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        return {
            "closed_count": len(self.closed_positions),
            "total_realized_pnl": round(total_pnl, 8),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": round(len(wins) / len(self.closed_positions) * 100, 2),
            "avg_win": round(sum(wins) / len(wins), 8) if wins else 0.0,
            "avg_loss": round(sum(losses) / len(losses), 8) if losses else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf"),
        }

    def rebalance(self, target_weights: dict, prices: dict) -> list:
        """
        Generate rebalance orders to reach target_weights.

        Parameters
        ----------
        target_weights : dict  — {'BTC': 0.60, 'ETH': 0.40}  (must sum to ~1)
        prices         : dict  — current prices per asset

        Returns
        -------
        list of dicts: {asset, action ('buy'/'sell'), amount, estimated_value}
        """
        total_value = self.get_value(prices)
        if total_value == 0:
            return []

        # Current weights by summing open positions per side
        current_values: Dict[str, float] = {}
        for pos in self.positions.values():
            asset = pos.side  # using side as asset label convention
            price = prices.get(asset, pos.entry_price)
            current_values[asset] = current_values.get(asset, 0.0) + pos.amount * price

        orders = []
        for asset, target_w in target_weights.items():
            target_value = total_value * target_w
            current_value = current_values.get(asset, 0.0)
            diff_value = target_value - current_value
            price = prices.get(asset)
            if price and price > 0:
                diff_amount = diff_value / price
                if abs(diff_amount) > 1e-8:
                    orders.append({
                        "asset": asset,
                        "action": "buy" if diff_amount > 0 else "sell",
                        "amount": round(abs(diff_amount), 8),
                        "estimated_value": round(abs(diff_value), 2),
                        "target_weight": target_w,
                        "current_weight": round(current_value / total_value, 4),
                    })

        return orders

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cash": self.cash,
            "open_positions": [p.to_dict() for p in self.positions.values()],
            "closed_count": len(self.closed_positions),
            "performance": self.get_performance(),
        }
