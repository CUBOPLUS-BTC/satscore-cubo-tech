"""
Strategy backtesting engine for Magma Bitcoin app.

Provides BacktestEngine for running strategies against historical prices,
a Strategy base class, built-in strategies (DCA, momentum, mean-reversion,
trend-following, etc.), BacktestResult, and walk-forward optimization.

Uses only Python standard library.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Utility maths
# ---------------------------------------------------------------------------

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _sma(values: list, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return _mean(values[-period:])


def _ema(values: list, period: int) -> float:
    if not values:
        return 0.0
    k = 2 / (period + 1)
    result = values[0]
    for v in values[1:]:
        result = v * k + result * (1 - k)
    return result


def _rsi(prices: list, period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
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


def _max_drawdown(values: list) -> float:
    if len(values) < 2:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (v - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd * 100  # as percentage


def _annualise(total_return_pct: float, n_days: float) -> float:
    if n_days <= 0 or total_return_pct <= -100:
        return 0.0
    years = n_days / 365
    return ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100


# ---------------------------------------------------------------------------
# Order dataclass
# ---------------------------------------------------------------------------

@dataclass
class Order:
    """Represents a trade order placed by a strategy."""
    order_type:  str      # 'buy' | 'sell' | 'hold'
    amount:      float    # fraction of portfolio (0.0–1.0) or USD amount
    price:       float
    timestamp:   int
    reason:      str = ""

    def to_dict(self) -> dict:
        return {
            "order_type": self.order_type,
            "amount":     round(self.amount, 8),
            "price":      round(self.price, 2),
            "timestamp":  self.timestamp,
            "reason":     self.reason,
        }


# ---------------------------------------------------------------------------
# Strategy base class
# ---------------------------------------------------------------------------

class Strategy:
    """
    Base class for all trading strategies.
    Subclasses must implement on_data().
    """

    def on_data(self, price: float, timestamp: int,
                portfolio: dict, history: list) -> list[Order]:
        """
        Called for each data point. Returns list of Orders.

        Parameters
        ----------
        price     : current price
        timestamp : Unix timestamp
        portfolio : {cash: float, btc: float, equity: float}
        history   : list of past close prices
        """
        raise NotImplementedError

    def get_parameters(self) -> dict:
        return {}

    def name(self) -> str:
        return self.__class__.__name__


# ---------------------------------------------------------------------------
# Built-in strategies
# ---------------------------------------------------------------------------

class DCAStrategy(Strategy):
    """Dollar Cost Averaging: buy fixed USD amount at regular intervals."""

    def __init__(self, amount: float = 100.0, frequency: int = 30):
        """
        Parameters
        ----------
        amount    : USD to invest per period
        frequency : number of periods between purchases
        """
        self.amount    = amount
        self.frequency = frequency
        self._counter  = 0

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        self._counter += 1
        if self._counter % self.frequency == 0 and portfolio["cash"] >= self.amount:
            btc_amount = self.amount / price
            return [Order("buy", btc_amount, price, timestamp,
                          f"DCA buy ${self.amount}")]
        return []

    def get_parameters(self) -> dict:
        return {"amount": self.amount, "frequency": self.frequency}


class ValueAveragingStrategy(Strategy):
    """
    Value Averaging: adjust purchase size to keep portfolio on a growth target.
    """

    def __init__(self, target_growth: float = 0.05, frequency: int = 30,
                 base_amount: float = 100.0):
        self.target_growth = target_growth
        self.frequency     = frequency
        self.base_amount   = base_amount
        self._counter      = 0
        self._period       = 0

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        self._counter += 1
        if self._counter % self.frequency != 0:
            return []

        self._period += 1
        target_value = self.base_amount * (1 + self.target_growth) ** self._period
        current_value = portfolio["equity"]
        diff = target_value - current_value

        if diff > 0 and portfolio["cash"] >= diff and price > 0:
            return [Order("buy", diff / price, price, timestamp,
                          f"VA buy ${diff:.2f} to reach target")]
        elif diff < 0 and portfolio["btc"] * abs(diff) / current_value > 0:
            sell_btc = abs(diff) / price
            sell_btc = min(sell_btc, portfolio["btc"])
            return [Order("sell", sell_btc, price, timestamp,
                          f"VA sell ${abs(diff):.2f} above target")]
        return []

    def get_parameters(self) -> dict:
        return {"target_growth": self.target_growth, "frequency": self.frequency,
                "base_amount": self.base_amount}


class MomentumStrategy(Strategy):
    """Buy when price exceeds lookback high; sell when it falls below lookback low."""

    def __init__(self, lookback: int = 20, threshold: float = 0.02,
                 position_size: float = 0.5):
        self.lookback       = lookback
        self.threshold      = threshold
        self.position_size  = position_size

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        if len(history) < self.lookback:
            return []
        window = history[-self.lookback:]
        high   = max(window)
        low    = min(window)

        orders = []
        if price > high * (1 + self.threshold) and portfolio["cash"] > 0:
            invest = portfolio["cash"] * self.position_size
            orders.append(Order("buy", invest / price, price, timestamp,
                                f"Momentum breakout above {self.lookback}d high"))
        elif price < low * (1 - self.threshold) and portfolio["btc"] > 0:
            orders.append(Order("sell", portfolio["btc"] * self.position_size,
                                price, timestamp,
                                f"Momentum breakdown below {self.lookback}d low"))
        return orders

    def get_parameters(self) -> dict:
        return {"lookback": self.lookback, "threshold": self.threshold}


class MeanReversionStrategy(Strategy):
    """Buy when price is far below SMA; sell when it reverts above SMA."""

    def __init__(self, window: int = 20, std_threshold: float = 2.0,
                 position_size: float = 0.5):
        self.window        = window
        self.std_threshold = std_threshold
        self.position_size = position_size

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        if len(history) < self.window:
            return []
        window_prices = history[-self.window:]
        ma  = _mean(window_prices)
        std = _stddev(window_prices)
        if std == 0:
            return []

        z_score = (price - ma) / std
        orders  = []

        if z_score <= -self.std_threshold and portfolio["cash"] > 0:
            invest = portfolio["cash"] * self.position_size
            orders.append(Order("buy", invest / price, price, timestamp,
                                f"Mean reversion buy (z={z_score:.2f})"))
        elif z_score >= self.std_threshold and portfolio["btc"] > 0:
            orders.append(Order("sell", portfolio["btc"] * self.position_size,
                                price, timestamp,
                                f"Mean reversion sell (z={z_score:.2f})"))
        return orders

    def get_parameters(self) -> dict:
        return {"window": self.window, "std_threshold": self.std_threshold}


class BuyAndHoldStrategy(Strategy):
    """Buy once at the start, hold until the end."""

    def __init__(self, initial_buy_pct: float = 0.95):
        self.initial_buy_pct = initial_buy_pct
        self._bought = False

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        if not self._bought and portfolio["cash"] > 0:
            invest = portfolio["cash"] * self.initial_buy_pct
            self._bought = True
            return [Order("buy", invest / price, price, timestamp,
                          "Initial buy-and-hold position")]
        return []

    def get_parameters(self) -> dict:
        return {"initial_buy_pct": self.initial_buy_pct}


class RebalancingStrategy(Strategy):
    """
    Periodically rebalance to target BTC/cash allocation.
    """

    def __init__(self, target_allocation: float = 0.60,
                 rebalance_threshold: float = 0.05,
                 frequency: int = 30):
        self.target       = target_allocation
        self.threshold    = rebalance_threshold
        self.frequency    = frequency
        self._counter     = 0

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        self._counter += 1
        if self._counter % self.frequency != 0:
            return []

        total_equity = portfolio["equity"]
        if total_equity <= 0:
            return []

        current_btc_alloc = (portfolio["btc"] * price) / total_equity
        drift = current_btc_alloc - self.target

        orders = []
        if abs(drift) > self.threshold:
            if drift < 0:
                # Under-allocated: buy BTC
                invest = abs(drift) * total_equity
                if portfolio["cash"] >= invest:
                    orders.append(Order("buy", invest / price, price, timestamp,
                                        f"Rebalance buy (drift={drift:.3f})"))
            else:
                # Over-allocated: sell BTC
                sell_value = drift * total_equity
                sell_btc   = sell_value / price
                if portfolio["btc"] >= sell_btc:
                    orders.append(Order("sell", sell_btc, price, timestamp,
                                        f"Rebalance sell (drift={drift:.3f})"))
        return orders

    def get_parameters(self) -> dict:
        return {"target_allocation": self.target, "rebalance_threshold": self.threshold}


class TrendFollowingStrategy(Strategy):
    """
    Fast MA / Slow MA crossover trend-following strategy.
    """

    def __init__(self, fast_ma: int = 20, slow_ma: int = 50,
                 position_size: float = 0.90):
        self.fast_ma      = fast_ma
        self.slow_ma      = slow_ma
        self.position_size = position_size
        self._in_trade    = False

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        if len(history) < self.slow_ma + 1:
            return []

        fast = _sma(history, self.fast_ma)
        slow = _sma(history, self.slow_ma)
        prev_fast = _sma(history[:-1], self.fast_ma)
        prev_slow = _sma(history[:-1], self.slow_ma)

        if None in (fast, slow, prev_fast, prev_slow):
            return []

        orders = []
        # Golden cross: fast crosses above slow
        if prev_fast <= prev_slow and fast > slow and not self._in_trade:
            invest = portfolio["cash"] * self.position_size
            if invest > 0:
                orders.append(Order("buy", invest / price, price, timestamp,
                                    f"TF Golden Cross MA{self.fast_ma}/MA{self.slow_ma}"))
                self._in_trade = True

        # Death cross: fast crosses below slow
        elif prev_fast >= prev_slow and fast < slow and self._in_trade:
            if portfolio["btc"] > 0:
                orders.append(Order("sell", portfolio["btc"], price, timestamp,
                                    f"TF Death Cross MA{self.fast_ma}/MA{self.slow_ma}"))
                self._in_trade = False

        return orders

    def get_parameters(self) -> dict:
        return {"fast_ma": self.fast_ma, "slow_ma": self.slow_ma}


class AccumulationStrategy(Strategy):
    """
    Buy dips: increase position when price drops below threshold;
    reduce position on strength.
    """

    def __init__(self, buy_dip_threshold: float = 0.10,
                 amount: float = 200.0,
                 lookback: int = 30):
        self.buy_dip_threshold = buy_dip_threshold
        self.amount            = amount
        self.lookback          = lookback

    def on_data(self, price, timestamp, portfolio, history) -> list[Order]:
        if len(history) < self.lookback:
            return []

        recent_high = max(history[-self.lookback:])
        dip_pct     = (price - recent_high) / recent_high  # negative = dip

        orders = []
        if dip_pct <= -self.buy_dip_threshold and portfolio["cash"] >= self.amount:
            orders.append(Order("buy", self.amount / price, price, timestamp,
                                f"Accumulation buy dip {dip_pct*100:.1f}%"))
        return orders

    def get_parameters(self) -> dict:
        return {"buy_dip_threshold": self.buy_dip_threshold, "amount": self.amount}


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    strategy_name:     str
    initial_capital:   float
    final_equity:      float
    total_return:      float        # percent
    annualised_return: float        # percent
    sharpe_ratio:      float
    max_drawdown:      float        # percent
    win_rate:          float        # percent
    profit_factor:     float
    total_trades:      int
    winning_trades:    int
    losing_trades:     int
    monthly_returns:   list[float] = field(default_factory=list)
    equity_curve:      list[float] = field(default_factory=list)
    trade_log:         list[dict]  = field(default_factory=list)
    period_days:       int = 0

    def to_dict(self) -> dict:
        return {
            "strategy":          self.strategy_name,
            "initial_capital":   round(self.initial_capital, 2),
            "final_equity":      round(self.final_equity, 2),
            "total_return_pct":  round(self.total_return, 4),
            "annualised_return_pct": round(self.annualised_return, 4),
            "sharpe_ratio":      round(self.sharpe_ratio, 4),
            "max_drawdown_pct":  round(self.max_drawdown, 4),
            "win_rate_pct":      round(self.win_rate, 2),
            "profit_factor":     round(self.profit_factor, 4),
            "total_trades":      self.total_trades,
            "winning_trades":    self.winning_trades,
            "losing_trades":     self.losing_trades,
            "period_days":       self.period_days,
            "monthly_returns":   [round(r, 4) for r in self.monthly_returns],
            "equity_curve":      [round(v, 2) for v in self.equity_curve[::max(1, len(self.equity_curve)//100)]],
            "trade_log":         self.trade_log[:50],  # first 50 trades
        }


# ---------------------------------------------------------------------------
# BacktestEngine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """
    Event-driven backtesting engine supporting any Strategy subclass.
    """

    def run(self, strategy: Strategy, prices: list[dict],
            initial_capital: float = 10_000.0) -> BacktestResult:
        """
        Run a strategy against historical price data.

        Parameters
        ----------
        strategy        : Strategy instance
        prices          : list of {timestamp, close, volume}
        initial_capital : starting cash in USD

        Returns
        -------
        BacktestResult
        """
        if len(prices) < 10:
            return self._empty_result(strategy.name(), initial_capital)

        # Reset strategy state if it has counter
        if hasattr(strategy, '_counter'):
            strategy._counter = 0
        if hasattr(strategy, '_bought'):
            strategy._bought = False
        if hasattr(strategy, '_in_trade'):
            strategy._in_trade = False
        if hasattr(strategy, '_period'):
            strategy._period = 0

        cash     = initial_capital
        btc      = 0.0
        equity_curve = []
        trade_log    = []
        history      = []
        tx_cost_pct  = 0.001  # 0.1% per trade

        for candle in prices:
            price     = float(candle.get("close", candle.get("price", 0)))
            timestamp = int(candle.get("timestamp", 0))

            if price <= 0:
                continue

            equity    = cash + btc * price
            portfolio = {"cash": cash, "btc": btc, "equity": equity}
            history.append(price)

            orders = strategy.on_data(price, timestamp, portfolio, list(history))

            for order in orders:
                if order.order_type == "buy":
                    cost = order.amount * price * (1 + tx_cost_pct)
                    if cost <= cash:
                        cash -= cost
                        btc  += order.amount
                        trade_log.append({
                            "type":      "buy",
                            "price":     round(price, 2),
                            "amount":    round(order.amount, 8),
                            "cost":      round(cost, 2),
                            "timestamp": timestamp,
                            "reason":    order.reason,
                        })

                elif order.order_type == "sell":
                    sell_amount = min(order.amount, btc)
                    if sell_amount > 0:
                        proceeds = sell_amount * price * (1 - tx_cost_pct)
                        btc  -= sell_amount
                        cash += proceeds
                        trade_log.append({
                            "type":      "sell",
                            "price":     round(price, 2),
                            "amount":    round(sell_amount, 8),
                            "proceeds":  round(proceeds, 2),
                            "timestamp": timestamp,
                            "reason":    order.reason,
                        })

            equity_curve.append(cash + btc * price)

        final_price  = prices[-1].get("close", prices[-1].get("price", 0))
        final_equity = cash + btc * float(final_price)

        total_return = (final_equity - initial_capital) / initial_capital * 100
        period_days  = len(prices)
        ann_return   = _annualise(total_return, period_days)

        # Sharpe ratio from equity curve returns
        equity_returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                equity_returns.append(
                    (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                )

        sharpe = 0.0
        if equity_returns:
            ret_mean = _mean(equity_returns) * 252
            ret_std  = _stddev(equity_returns) * math.sqrt(252)
            if ret_std > 0:
                sharpe = (ret_mean - 0.05) / ret_std

        max_dd = _max_drawdown(equity_curve)

        # Trade analysis
        wins   = [t for t in trade_log if t["type"] == "sell" and
                  t.get("proceeds", 0) > t.get("cost", 0)]
        losses = [t for t in trade_log if t["type"] == "sell" and
                  t.get("proceeds", 0) <= t.get("cost", 0)]

        sell_trades = [t for t in trade_log if t["type"] == "sell"]
        win_count   = len(wins)
        loss_count  = len(sell_trades) - win_count
        win_rate    = (win_count / len(sell_trades) * 100) if sell_trades else 0

        gross_profit = sum(t.get("proceeds", 0) for t in wins)
        gross_loss   = sum(t.get("proceeds", 0) for t in losses)
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        profit_factor = min(profit_factor, 999.9)

        # Monthly returns
        monthly_returns = self._compute_monthly_returns(equity_curve, len(prices))

        return BacktestResult(
            strategy_name     = strategy.name(),
            initial_capital   = initial_capital,
            final_equity      = round(final_equity, 2),
            total_return      = round(total_return, 4),
            annualised_return = round(ann_return, 4),
            sharpe_ratio      = round(sharpe, 4),
            max_drawdown      = round(max_dd, 4),
            win_rate          = round(win_rate, 2),
            profit_factor     = round(profit_factor, 4),
            total_trades      = len(trade_log),
            winning_trades    = win_count,
            losing_trades     = loss_count,
            monthly_returns   = monthly_returns,
            equity_curve      = equity_curve,
            trade_log         = trade_log,
            period_days       = period_days,
        )

    def compare_strategies(self, strategies: list[Strategy],
                            prices: list[dict],
                            capital: float = 10_000.0) -> dict:
        """
        Run multiple strategies on the same price data and compare results.

        Returns
        -------
        dict with results per strategy and rankings
        """
        results = {}
        for strategy in strategies:
            result = self.run(strategy, prices, capital)
            results[strategy.name()] = result.to_dict()

        # Rankings
        by_return = sorted(results.items(),
                           key=lambda x: x[1]["total_return_pct"], reverse=True)
        by_sharpe = sorted(results.items(),
                           key=lambda x: x[1]["sharpe_ratio"], reverse=True)
        by_drawdown = sorted(results.items(),
                             key=lambda x: abs(x[1]["max_drawdown_pct"]))

        return {
            "strategies":          results,
            "best_by_return":      by_return[0][0] if by_return else None,
            "best_by_sharpe":      by_sharpe[0][0] if by_sharpe else None,
            "lowest_drawdown":     by_drawdown[0][0] if by_drawdown else None,
            "price_period_days":   len(prices),
            "initial_capital":     capital,
            "benchmark_bah":       results.get("BuyAndHoldStrategy"),
        }

    def walk_forward_optimization(self, strategy: Strategy, prices: list[dict],
                                   train_pct: float = 0.70,
                                   n_splits: int = 5) -> dict:
        """
        Walk-forward optimization: train on in-sample, test on out-of-sample.

        Parameters
        ----------
        strategy  : Strategy to test
        prices    : full price dataset
        train_pct : fraction of each window used for training
        n_splits  : number of walk-forward windows

        Returns
        -------
        dict with in-sample and out-of-sample results per split
        """
        n = len(prices)
        window_size = n // n_splits
        splits = []

        for i in range(n_splits):
            start_idx = i * window_size
            end_idx   = start_idx + window_size
            split_prices = prices[start_idx:end_idx]

            train_end   = int(len(split_prices) * train_pct)
            train_data  = split_prices[:train_end]
            test_data   = split_prices[train_end:]

            if not train_data or not test_data:
                continue

            train_result = self.run(strategy, train_data)
            test_result  = self.run(strategy, test_data)

            splits.append({
                "split":              i + 1,
                "train_start":        train_data[0].get("timestamp"),
                "train_end":          train_data[-1].get("timestamp"),
                "test_start":         test_data[0].get("timestamp"),
                "test_end":           test_data[-1].get("timestamp"),
                "in_sample_return":   train_result.total_return,
                "out_of_sample_return": test_result.total_return,
                "in_sample_sharpe":   train_result.sharpe_ratio,
                "out_of_sample_sharpe": test_result.sharpe_ratio,
            })

        avg_oos_return = _mean([s["out_of_sample_return"] for s in splits])
        avg_is_return  = _mean([s["in_sample_return"] for s in splits])

        return {
            "strategy":           strategy.name(),
            "n_splits":           n_splits,
            "train_pct":          train_pct,
            "splits":             splits,
            "avg_in_sample_return_pct":     round(avg_is_return, 4),
            "avg_out_of_sample_return_pct": round(avg_oos_return, 4),
            "overfitting_ratio":  round(avg_oos_return / avg_is_return, 4) if avg_is_return != 0 else 0,
        }

    @staticmethod
    def _compute_monthly_returns(equity_curve: list, n_periods: int) -> list[float]:
        """Approximate monthly returns from equity curve."""
        if not equity_curve:
            return []
        days_per_month = 30
        n_months = max(n_periods // days_per_month, 1)
        chunk = max(len(equity_curve) // n_months, 1)
        monthly = []
        for i in range(0, len(equity_curve), chunk):
            start = equity_curve[i]
            end   = equity_curve[min(i + chunk - 1, len(equity_curve) - 1)]
            if start > 0:
                monthly.append(round((end - start) / start * 100, 4))
        return monthly

    @staticmethod
    def _empty_result(name: str, capital: float) -> BacktestResult:
        return BacktestResult(
            strategy_name=name,
            initial_capital=capital,
            final_equity=capital,
            total_return=0.0,
            annualised_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
        )
