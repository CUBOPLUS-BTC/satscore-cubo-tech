"""
Order book analysis for Magma Bitcoin app.

Provides OrderBook (data structure + analytics) and OrderBookAnalyzer
(cross-snapshot analysis including spoofing detection, market impact,
liquidity heatmap, and short-term direction prediction).

Uses only Python standard library.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


# ---------------------------------------------------------------------------
# Order dataclass
# ---------------------------------------------------------------------------

@dataclass
class Order:
    price:  float
    amount: float    # BTC

    @property
    def value_usd(self) -> float:
        return self.price * self.amount


# ---------------------------------------------------------------------------
# OrderBook
# ---------------------------------------------------------------------------

class OrderBook:
    """
    Represents a limit order book for BTC/USD with analytical methods.

    Internally stores bids and asks as sorted lists of Order objects:
    - Bids: sorted descending by price (highest bid first)
    - Asks: sorted ascending by price  (lowest ask first)
    """

    def __init__(self):
        self._bids: list[Order] = []   # sorted: high → low
        self._asks: list[Order] = []   # sorted: low  → high
        self._timestamp: float = time.time()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_bid(self, price: float, amount: float):
        """Add or update a bid level."""
        self._upsert(self._bids, price, amount, descending=True)

    def add_ask(self, price: float, amount: float):
        """Add or update an ask level."""
        self._upsert(self._asks, price, amount, descending=False)

    def remove_bid(self, price: float):
        """Remove a bid at the given price level."""
        self._bids = [o for o in self._bids if o.price != price]

    def remove_ask(self, price: float):
        """Remove an ask at the given price level."""
        self._asks = [o for o in self._asks if o.price != price]

    def clear(self):
        self._bids.clear()
        self._asks.clear()

    @staticmethod
    def _upsert(orders: list, price: float, amount: float, descending: bool):
        for order in orders:
            if order.price == price:
                if amount <= 0:
                    orders.remove(order)
                else:
                    order.amount = amount
                return
        if amount > 0:
            orders.append(Order(price, amount))
            orders.sort(key=lambda o: o.price, reverse=descending)

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------

    @property
    def best_bid(self) -> Optional[Order]:
        return self._bids[0] if self._bids else None

    @property
    def best_ask(self) -> Optional[Order]:
        return self._asks[0] if self._asks else None

    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return None

    # ------------------------------------------------------------------
    # Spread
    # ------------------------------------------------------------------

    def get_spread(self) -> dict:
        """
        Compute bid-ask spread in absolute and percentage terms.
        """
        bb = self.best_bid
        ba = self.best_ask
        if not bb or not ba:
            return {"bid": None, "ask": None, "spread_usd": None, "spread_bps": None}

        spread_usd = ba.price - bb.price
        spread_bps = (spread_usd / ba.price) * 10000  # basis points

        return {
            "bid":         bb.price,
            "ask":         ba.price,
            "mid":         round((bb.price + ba.price) / 2, 2),
            "spread_usd":  round(spread_usd, 2),
            "spread_bps":  round(spread_bps, 4),
            "spread_pct":  round(spread_usd / ba.price * 100, 6),
        }

    # ------------------------------------------------------------------
    # Depth
    # ------------------------------------------------------------------

    def get_depth(self, levels: int = 20) -> dict:
        """
        Return top N bid/ask levels with cumulative volume.
        """
        def _format_side(orders, n):
            result = []
            cumulative_btc = 0.0
            cumulative_usd = 0.0
            for o in orders[:n]:
                cumulative_btc += o.amount
                cumulative_usd += o.value_usd
                result.append({
                    "price":          round(o.price, 2),
                    "amount_btc":     round(o.amount, 8),
                    "value_usd":      round(o.value_usd, 2),
                    "cumulative_btc": round(cumulative_btc, 8),
                    "cumulative_usd": round(cumulative_usd, 2),
                })
            return result

        return {
            "bids":   _format_side(self._bids, levels),
            "asks":   _format_side(self._asks, levels),
            "levels": levels,
        }

    # ------------------------------------------------------------------
    # Imbalance
    # ------------------------------------------------------------------

    def get_imbalance(self, levels: int = 10) -> float:
        """
        Compute bid/ask imbalance ratio over top N levels.
        Positive values indicate more buying pressure (bids > asks).
        Range: -1.0 (all asks) to +1.0 (all bids).
        """
        bid_vol = sum(o.amount for o in self._bids[:levels])
        ask_vol = sum(o.amount for o in self._asks[:levels])
        total   = bid_vol + ask_vol
        if total == 0:
            return 0.0
        return round((bid_vol - ask_vol) / total, 6)

    # ------------------------------------------------------------------
    # Wall detection
    # ------------------------------------------------------------------

    def get_wall_detection(self, threshold: float = 5.0) -> list[dict]:
        """
        Detect large orders (walls) that may act as significant S/R.

        Parameters
        ----------
        threshold : float
            Minimum BTC amount to qualify as a wall.

        Returns
        -------
        list of {side, price, amount_btc, value_usd, relative_size}
        """
        all_amounts = [o.amount for o in self._bids + self._asks]
        mean_amount = _mean(all_amounts) if all_amounts else 1.0

        walls = []
        for o in self._bids:
            if o.amount >= threshold:
                walls.append({
                    "side":           "bid",
                    "price":          round(o.price, 2),
                    "amount_btc":     round(o.amount, 8),
                    "value_usd":      round(o.value_usd, 2),
                    "relative_size":  round(o.amount / mean_amount, 2),
                })
        for o in self._asks:
            if o.amount >= threshold:
                walls.append({
                    "side":           "ask",
                    "price":          round(o.price, 2),
                    "amount_btc":     round(o.amount, 8),
                    "value_usd":      round(o.value_usd, 2),
                    "relative_size":  round(o.amount / mean_amount, 2),
                })

        walls.sort(key=lambda w: w["amount_btc"], reverse=True)
        return walls

    # ------------------------------------------------------------------
    # Liquidity score
    # ------------------------------------------------------------------

    def get_liquidity_score(self) -> float:
        """
        Compute a 0–100 liquidity score based on:
        - Number of levels present
        - Total depth within 2% of mid
        - Spread tightness
        """
        mid = self.mid_price
        if not mid:
            return 0.0

        spread_info = self.get_spread()
        spread_bps = spread_info.get("spread_bps") or 1000

        # Depth within 2% of mid
        depth_2pct_bids = sum(o.amount for o in self._bids if o.price >= mid * 0.98)
        depth_2pct_asks = sum(o.amount for o in self._asks if o.price <= mid * 1.02)
        total_depth_2pct = depth_2pct_bids + depth_2pct_asks

        # Components (0–100 each)
        spread_score = _clamp(100 - spread_bps * 0.5, 0, 100)
        depth_score  = _clamp(total_depth_2pct * 2, 0, 100)   # 50 BTC = 100%
        levels_score = _clamp(len(self._bids) + len(self._asks), 0, 100)

        score = (spread_score * 0.4 + depth_score * 0.4 + levels_score * 0.2)
        return round(score, 2)

    # ------------------------------------------------------------------
    # Market order simulation (slippage)
    # ------------------------------------------------------------------

    def simulate_market_order(self, side: str, amount: float) -> dict:
        """
        Estimate execution price and slippage for a market order.

        Parameters
        ----------
        side : str
            'buy' or 'sell'
        amount : float
            BTC amount to trade.

        Returns
        -------
        dict with avg_fill_price, slippage_pct, total_cost_usd,
        filled_btc, levels_consumed, unfilled_btc
        """
        if side == "buy":
            orders = self._asks   # walk up asks
        else:
            orders = self._bids   # walk down bids

        if not orders:
            return {"error": "No orders on requested side"}

        reference_price = orders[0].price
        remaining = amount
        total_cost = 0.0
        filled = 0.0
        levels_consumed = 0

        for order in orders:
            if remaining <= 0:
                break
            fill = min(remaining, order.amount)
            total_cost += fill * order.price
            filled += fill
            remaining -= fill
            levels_consumed += 1

        if filled == 0:
            return {"error": "No liquidity available"}

        avg_price = total_cost / filled
        slippage_pct = abs(avg_price - reference_price) / reference_price * 100

        return {
            "side":              side,
            "requested_btc":     amount,
            "filled_btc":        round(filled, 8),
            "unfilled_btc":      round(remaining, 8),
            "avg_fill_price":    round(avg_price, 2),
            "reference_price":   round(reference_price, 2),
            "slippage_pct":      round(slippage_pct, 4),
            "total_cost_usd":    round(total_cost, 2),
            "levels_consumed":   levels_consumed,
            "fully_filled":      remaining <= 0,
        }

    # ------------------------------------------------------------------
    # VWAP
    # ------------------------------------------------------------------

    def get_vwap_price(self, side: str, amount: float) -> float:
        """
        Volume-Weighted Average Price for executing `amount` BTC on `side`.
        Returns 0.0 if insufficient liquidity.
        """
        result = self.simulate_market_order(side, amount)
        return result.get("avg_fill_price", 0.0)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate(self, tick_size: float) -> "OrderBook":
        """
        Return a new OrderBook with prices rounded to tick_size buckets.

        Parameters
        ----------
        tick_size : float
            Price bucket size (e.g., 100.0 for $100 buckets).
        """
        new_book = OrderBook()

        # Aggregate bids
        bid_buckets: dict[float, float] = {}
        for o in self._bids:
            bucket = math.floor(o.price / tick_size) * tick_size
            bid_buckets[bucket] = bid_buckets.get(bucket, 0) + o.amount
        for price, amount in bid_buckets.items():
            new_book.add_bid(price, amount)

        # Aggregate asks
        ask_buckets: dict[float, float] = {}
        for o in self._asks:
            bucket = math.ceil(o.price / tick_size) * tick_size
            ask_buckets[bucket] = ask_buckets.get(bucket, 0) + o.amount
        for price, amount in ask_buckets.items():
            new_book.add_ask(price, amount)

        new_book._timestamp = self._timestamp
        return new_book

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def to_dict(self, levels: int = 20) -> dict:
        return {
            "timestamp":  self._timestamp,
            "mid_price":  self.mid_price,
            "spread":     self.get_spread(),
            "imbalance":  self.get_imbalance(),
            "depth":      self.get_depth(levels),
            "liquidity_score": self.get_liquidity_score(),
        }


# ---------------------------------------------------------------------------
# Helpers used by OrderBook
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# OrderBookAnalyzer
# ---------------------------------------------------------------------------

class OrderBookAnalyzer:
    """
    Cross-snapshot analysis of order book data for pattern detection
    and market microstructure insights.

    All methods accept a ``snapshots`` list – each element is a dict
    as returned by ``OrderBook.to_dict()`` – to enable time-series analysis.
    """

    # ------------------------------------------------------------------
    # Spoofing detection
    # ------------------------------------------------------------------

    def detect_spoofing(self, snapshots: list[dict]) -> list[dict]:
        """
        Identify potential spoofing: large orders that appear and
        disappear without trading (price moves through without fill).

        Heuristic: a wall (large order) present at T0 but absent at T1
        after price has moved through its level.

        Parameters
        ----------
        snapshots : list of OrderBook.to_dict() results
            Sorted chronologically.

        Returns
        -------
        list of {timestamp, side, price, amount_btc, suspicion_reason}
        """
        if len(snapshots) < 2:
            return []

        alerts = []
        for i in range(1, len(snapshots)):
            prev = snapshots[i - 1]
            curr = snapshots[i]

            prev_mid = prev.get("mid_price") or 0
            curr_mid = curr.get("mid_price") or 0

            # Reconstruct bid/ask from depth snapshots
            prev_bids = {
                level["price"]: level["amount_btc"]
                for level in (prev.get("depth") or {}).get("bids", [])
            }
            prev_asks = {
                level["price"]: level["amount_btc"]
                for level in (prev.get("depth") or {}).get("asks", [])
            }
            curr_bids = {
                level["price"]: level["amount_btc"]
                for level in (curr.get("depth") or {}).get("bids", [])
            }
            curr_asks = {
                level["price"]: level["amount_btc"]
                for level in (curr.get("depth") or {}).get("asks", [])
            }

            price_moved_up   = curr_mid > prev_mid * 1.001
            price_moved_down = curr_mid < prev_mid * 0.999

            # Large bid cancelled after price moved down (possible bear spoof)
            for price, amount in prev_bids.items():
                if amount > 5.0 and price not in curr_bids and price_moved_down:
                    alerts.append({
                        "timestamp":       curr.get("timestamp"),
                        "side":            "bid",
                        "price":           price,
                        "amount_btc":      amount,
                        "suspicion_reason": "Large bid disappeared after downward price move (potential bear spoof)",
                        "confidence":      "medium",
                    })

            # Large ask cancelled after price moved up (possible bull spoof)
            for price, amount in prev_asks.items():
                if amount > 5.0 and price not in curr_asks and price_moved_up:
                    alerts.append({
                        "timestamp":       curr.get("timestamp"),
                        "side":            "ask",
                        "price":           price,
                        "amount_btc":      amount,
                        "suspicion_reason": "Large ask disappeared after upward price move (potential bull spoof)",
                        "confidence":      "medium",
                    })

        return alerts

    # ------------------------------------------------------------------
    # Market impact
    # ------------------------------------------------------------------

    def calculate_market_impact(self, snapshots: list[dict], amount: float) -> dict:
        """
        Calculate the expected market impact of a trade of `amount` BTC
        across a set of snapshots.

        Returns
        -------
        dict with avg_buy_slippage_pct, avg_sell_slippage_pct,
        price_impact_trend, recommendation
        """
        if not snapshots:
            return {}

        buy_slippages  = []
        sell_slippages = []

        for snap in snapshots:
            # Rebuild lightweight book from depth snapshot
            book = OrderBook()
            for level in (snap.get("depth") or {}).get("bids", []):
                book.add_bid(level["price"], level["amount_btc"])
            for level in (snap.get("depth") or {}).get("asks", []):
                book.add_ask(level["price"], level["amount_btc"])

            buy_result  = book.simulate_market_order("buy", amount)
            sell_result = book.simulate_market_order("sell", amount)

            if "slippage_pct" in buy_result:
                buy_slippages.append(buy_result["slippage_pct"])
            if "slippage_pct" in sell_result:
                sell_slippages.append(sell_result["slippage_pct"])

        avg_buy  = _mean(buy_slippages)
        avg_sell = _mean(sell_slippages)

        # Trend: is slippage increasing or decreasing?
        trend = "stable"
        if len(buy_slippages) >= 3:
            first_half  = _mean(buy_slippages[:len(buy_slippages)//2])
            second_half = _mean(buy_slippages[len(buy_slippages)//2:])
            if second_half > first_half * 1.1:
                trend = "deteriorating"
            elif second_half < first_half * 0.9:
                trend = "improving"

        recommendation = (
            "Liquidity appears adequate for this order size."
            if avg_buy < 0.1
            else "Consider splitting the order to reduce slippage impact."
        )

        return {
            "order_size_btc":       amount,
            "avg_buy_slippage_pct": round(avg_buy, 4),
            "avg_sell_slippage_pct": round(avg_sell, 4),
            "buy_slippage_samples":  buy_slippages,
            "sell_slippage_samples": sell_slippages,
            "liquidity_trend":      trend,
            "recommendation":       recommendation,
        }

    # ------------------------------------------------------------------
    # Liquidity heatmap
    # ------------------------------------------------------------------

    def get_liquidity_heatmap(self, snapshots: list[dict],
                               tick_size: float = 500.0,
                               n_buckets: int = 40) -> dict:
        """
        Aggregate liquidity across snapshots into a price-level heatmap.
        Shows where the most liquidity has historically rested.

        Returns
        -------
        dict with buckets list [{price_low, price_high, bid_btc, ask_btc, total_btc}]
        sorted by price ascending.
        """
        if not snapshots:
            return {"buckets": [], "tick_size": tick_size}

        # Collect all prices to determine range
        all_prices = []
        for snap in snapshots:
            depth = snap.get("depth") or {}
            for level in depth.get("bids", []) + depth.get("asks", []):
                all_prices.append(level["price"])

        if not all_prices:
            return {"buckets": [], "tick_size": tick_size}

        min_price = min(all_prices)
        max_price = max(all_prices)

        # Dynamically compute tick size to give ~n_buckets
        if tick_size <= 0:
            tick_size = max((max_price - min_price) / n_buckets, 1.0)

        # Build buckets
        start_bucket = math.floor(min_price / tick_size) * tick_size
        buckets: dict[float, dict] = {}

        for snap in snapshots:
            depth = snap.get("depth") or {}
            for level in depth.get("bids", []):
                bkt = math.floor(level["price"] / tick_size) * tick_size
                if bkt not in buckets:
                    buckets[bkt] = {"bid_btc": 0.0, "ask_btc": 0.0}
                buckets[bkt]["bid_btc"] += level["amount_btc"]

            for level in depth.get("asks", []):
                bkt = math.floor(level["price"] / tick_size) * tick_size
                if bkt not in buckets:
                    buckets[bkt] = {"bid_btc": 0.0, "ask_btc": 0.0}
                buckets[bkt]["ask_btc"] += level["amount_btc"]

        result = []
        for price, data in sorted(buckets.items()):
            total = data["bid_btc"] + data["ask_btc"]
            result.append({
                "price_low":  round(price, 2),
                "price_high": round(price + tick_size, 2),
                "bid_btc":    round(data["bid_btc"], 4),
                "ask_btc":    round(data["ask_btc"], 4),
                "total_btc":  round(total, 4),
            })

        # Normalise for heatmap intensity (0–1)
        max_total = max((b["total_btc"] for b in result), default=1) or 1
        for b in result:
            b["intensity"] = round(b["total_btc"] / max_total, 4)

        return {"buckets": result, "tick_size": tick_size, "snapshots_used": len(snapshots)}

    # ------------------------------------------------------------------
    # Short-term direction prediction
    # ------------------------------------------------------------------

    def predict_short_term_direction(self, snapshots: list[dict]) -> dict:
        """
        Combine multiple microstructure signals to predict short-term
        price direction.

        Signals used:
        1. Order book imbalance trend
        2. Spread expansion/contraction
        3. Wall appearance/disappearance
        4. Price momentum from snapshots

        Returns
        -------
        dict with direction ('bullish'/'bearish'/'neutral'),
        confidence_pct, signals, explanation
        """
        if len(snapshots) < 3:
            return {"direction": "neutral", "confidence_pct": 0, "signals": []}

        signals = []
        bullish_score = 0
        bearish_score = 0

        # 1. Imbalance trend
        imbalances = [s.get("imbalance", 0) for s in snapshots]
        avg_imbalance = _mean(imbalances)
        recent_imbalance = _mean(imbalances[-3:])

        if recent_imbalance > 0.15:
            bullish_score += 2
            signals.append({"signal": "imbalance", "direction": "bullish",
                            "value": round(recent_imbalance, 3),
                            "note": "Strong bid-side imbalance"})
        elif recent_imbalance < -0.15:
            bearish_score += 2
            signals.append({"signal": "imbalance", "direction": "bearish",
                            "value": round(recent_imbalance, 3),
                            "note": "Strong ask-side imbalance"})
        else:
            signals.append({"signal": "imbalance", "direction": "neutral",
                            "value": round(recent_imbalance, 3),
                            "note": "Balanced order book"})

        # 2. Spread trend
        spreads = [s.get("spread", {}).get("spread_bps", 0) or 0 for s in snapshots]
        if len(spreads) >= 4:
            early_spread = _mean(spreads[:len(spreads)//2])
            late_spread  = _mean(spreads[len(spreads)//2:])
            if late_spread > early_spread * 1.2:
                bearish_score += 1
                signals.append({"signal": "spread", "direction": "bearish",
                                "note": "Widening spread indicates uncertainty"})
            elif late_spread < early_spread * 0.8:
                bullish_score += 1
                signals.append({"signal": "spread", "direction": "bullish",
                                "note": "Tightening spread indicates confidence"})

        # 3. Price momentum from snapshots
        mid_prices = [s.get("mid_price") or 0 for s in snapshots if s.get("mid_price")]
        if len(mid_prices) >= 4:
            first_price = mid_prices[0]
            last_price  = mid_prices[-1]
            if first_price > 0:
                mom_pct = (last_price - first_price) / first_price * 100
                if mom_pct > 0.2:
                    bullish_score += 1
                    signals.append({"signal": "momentum", "direction": "bullish",
                                    "value": round(mom_pct, 4),
                                    "note": "Positive short-term price momentum"})
                elif mom_pct < -0.2:
                    bearish_score += 1
                    signals.append({"signal": "momentum", "direction": "bearish",
                                    "value": round(mom_pct, 4),
                                    "note": "Negative short-term price momentum"})

        # 4. Liquidity score trend
        liq_scores = [s.get("liquidity_score", 50) for s in snapshots]
        if len(liq_scores) >= 4:
            early_liq = _mean(liq_scores[:len(liq_scores)//2])
            late_liq  = _mean(liq_scores[len(liq_scores)//2:])
            if late_liq > early_liq * 1.1:
                bullish_score += 1
                signals.append({"signal": "liquidity", "direction": "bullish",
                                "note": "Improving liquidity depth"})
            elif late_liq < early_liq * 0.9:
                bearish_score += 1
                signals.append({"signal": "liquidity", "direction": "bearish",
                                "note": "Deteriorating liquidity depth"})

        # Compile result
        total = bullish_score + bearish_score
        if total == 0:
            direction    = "neutral"
            confidence   = 0
            explanation  = "No strong directional signals detected."
        elif bullish_score > bearish_score:
            direction   = "bullish"
            confidence  = round(bullish_score / (total + 2) * 100, 1)
            explanation = "Multiple microstructure signals favour buyers."
        elif bearish_score > bullish_score:
            direction   = "bearish"
            confidence  = round(bearish_score / (total + 2) * 100, 1)
            explanation = "Multiple microstructure signals favour sellers."
        else:
            direction   = "neutral"
            confidence  = 30
            explanation = "Signals are balanced; no clear short-term edge."

        return {
            "direction":       direction,
            "confidence_pct":  confidence,
            "bullish_score":   bullish_score,
            "bearish_score":   bearish_score,
            "signals":         signals,
            "explanation":     explanation,
            "snapshots_used":  len(snapshots),
        }
