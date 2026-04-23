"""
HTTP route handlers for the Market Data Engine.

All handlers return (response_dict, status_code) tuples following
the convention used throughout the Magma app.
"""

from .engine import MarketEngine
from .history import PriceHistory
from .signals import SignalEngine

_engine = MarketEngine()
_signal_engine = SignalEngine()


def handle_market_overview(body: dict) -> tuple[dict, int]:
    """GET/POST /market/overview — public, no auth."""
    try:
        result = _engine.get_market_overview()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_price_history(query: dict) -> tuple[dict, int]:
    """
    GET /market/history?days=30&interval=daily

    Query params:
        days     : int (default 30)
        interval : 'daily' | 'hourly' (default 'daily')
    """
    try:
        days     = int(query.get("days", 30))
        interval = query.get("interval", "daily")

        if days < 1 or days > 365:
            return {"detail": "days must be between 1 and 365"}, 400
        if interval not in ("daily", "hourly"):
            return {"detail": "interval must be 'daily' or 'hourly'"}, 400

        candles = _engine.get_price_history(days=days, interval=interval)

        # Optionally wrap with PriceHistory analytics
        include_analytics = query.get("analytics", "false").lower() == "true"
        analytics = {}
        if include_analytics and candles:
            price_dicts = [{"timestamp": c["timestamp"], "price": c["close"],
                            "volume": c.get("volume", 0)} for c in candles]
            ph = PriceHistory(price_dicts)
            analytics = {
                "volatility_30d_pct": ph.get_volatility(30),
                "max_drawdown":       ph.get_max_drawdown(),
                "return_distribution": ph.get_distribution(),
                "best_worst_monthly": ph.get_best_worst_periods("monthly"),
            }

        return {
            "days":      days,
            "interval":  interval,
            "count":     len(candles),
            "candles":   candles,
            "analytics": analytics,
        }, 200

    except Exception as e:
        return {"detail": str(e)}, 500


def handle_market_signals(body: dict) -> tuple[dict, int]:
    """
    POST /market/signals

    Body:
        prices  : list of {close, volume, timestamp} or list of floats
        mode    : 'summary' | 'backtest' | 'score' (default 'summary')
        signal_type : str (required for 'backtest' mode)
    """
    try:
        prices = body.get("prices", [])
        mode   = body.get("mode", "summary")

        if not prices:
            # Fall back to fetched history
            candles = _engine.get_price_history(days=90)
            prices  = [{"close": c["close"], "volume": c.get("volume", 0),
                        "timestamp": c["timestamp"]} for c in candles]

        if len(prices) < 20:
            return {"detail": "Need at least 20 price points"}, 400

        if mode == "summary":
            result = _signal_engine.get_signal_summary(prices)
        elif mode == "score":
            result = _signal_engine.score_setup(prices)
        elif mode == "backtest":
            signal_type = body.get("signal_type", "")
            if not signal_type:
                return {"detail": "signal_type required for backtest mode"}, 400
            result = _signal_engine.backtest_signal(signal_type, prices)
        else:
            return {"detail": "mode must be 'summary', 'score', or 'backtest'"}, 400

        return result, 200

    except Exception as e:
        return {"detail": str(e)}, 500


def handle_market_sentiment(body: dict) -> tuple[dict, int]:
    """GET/POST /market/sentiment — fear/greed index."""
    try:
        result = _engine.get_market_sentiment()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_halving_info(body: dict) -> tuple[dict, int]:
    """GET/POST /market/halving — next halving info."""
    try:
        result = _engine.get_halving_info()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_fair_value(body: dict) -> tuple[dict, int]:
    """GET/POST /market/fair-value — model-based fair value."""
    try:
        result = _engine.calculate_fair_value()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_mining_stats(body: dict) -> tuple[dict, int]:
    """GET/POST /market/mining — mining network stats."""
    try:
        result = _engine.get_mining_stats()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_supply_metrics(body: dict) -> tuple[dict, int]:
    """GET/POST /market/supply — Bitcoin supply metrics."""
    try:
        result = _engine.get_supply_metrics()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_correlations(body: dict) -> tuple[dict, int]:
    """GET/POST /market/correlations — BTC correlations with other assets."""
    try:
        result = _engine.get_correlations()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_market_cycle(body: dict) -> tuple[dict, int]:
    """GET/POST /market/cycle — current market cycle phase."""
    try:
        result = _engine.get_market_cycle_phase()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_whale_indicator(body: dict) -> tuple[dict, int]:
    """GET/POST /market/whales — whale activity indicator."""
    try:
        result = _engine.get_whale_indicator()
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_price_analysis(body: dict) -> tuple[dict, int]:
    """
    POST /market/analysis — comprehensive price history analysis.

    Body:
        days         : int (default 365)
        include_sr   : bool — include support/resistance
        include_dca  : bool — include DCA backtest
        dca_amount   : float (default 100)
    """
    try:
        days       = int(body.get("days", 365))
        include_sr = body.get("include_sr", True)
        include_dca= body.get("include_dca", False)
        dca_amount = float(body.get("dca_amount", 100))

        candles = _engine.get_price_history(days=min(days, 365))
        if not candles:
            return {"detail": "No price data available"}, 503

        price_dicts = [{"timestamp": c["timestamp"], "price": c["close"],
                        "volume": c.get("volume", 0)} for c in candles]
        ph = PriceHistory(price_dicts)

        current_price = candles[-1]["close"] if candles else 0

        result = {
            "period_days":        days,
            "current_price":      current_price,
            "volatility_30d_pct": ph.get_volatility(30),
            "max_drawdown":       ph.get_max_drawdown(),
            "return_distribution": ph.get_distribution(),
            "seasonal_patterns":  ph.get_seasonal_patterns(),
            "best_worst_monthly": ph.get_best_worst_periods("monthly"),
            "percentile_rank":    ph.get_percentile_rank(current_price),
        }

        if include_sr:
            result["support_resistance"] = ph.detect_support_resistance()

        if include_dca:
            result["dca_backtest"] = ph.backtest_dca(amount=dca_amount, frequency="monthly")

        return result, 200

    except Exception as e:
        return {"detail": str(e)}, 500
