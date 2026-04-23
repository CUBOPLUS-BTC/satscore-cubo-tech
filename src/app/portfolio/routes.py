"""
HTTP route handlers for Portfolio Management.

All handlers return (response_dict, status_code) tuples.
Authenticated routes receive pubkey as a parameter.
"""

from .tracker import PortfolioTracker
from .optimizer import PortfolioOptimizer, CorrelationMatrix
from .risk import RiskAnalyzer
from ..i18n import t

_tracker   = PortfolioTracker()
_optimizer = PortfolioOptimizer()
_risk      = RiskAnalyzer()


def handle_portfolio_holdings(pubkey: str) -> tuple[dict, int]:
    """GET /portfolio/holdings — all holdings with current values."""
    try:
        holdings = _tracker.get_holdings(pubkey)
        value    = _tracker.get_portfolio_value(pubkey)
        return {
            "holdings":   holdings,
            "summary":    value,
        }, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_summary(pubkey: str) -> tuple[dict, int]:
    """GET /portfolio/summary — comprehensive portfolio summary."""
    try:
        result = _tracker.get_portfolio_summary(pubkey)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_transaction(body: dict, pubkey: str) -> tuple[dict, int]:
    """
    POST /portfolio/transaction — record a buy/sell/transfer.

    Body:
        tx_type   : 'buy' | 'sell' | 'transfer_in' | 'transfer_out'
        asset     : str (default 'BTC')
        amount    : float
        price_usd : float
        fee_usd   : float (optional)
        notes     : str (optional)
    """
    try:
        tx_type   = body.get("tx_type", "buy")
        asset     = body.get("asset", "BTC")
        amount    = float(body.get("amount", 0))
        price_usd = float(body.get("price_usd", 0))
        fee_usd   = float(body.get("fee_usd", 0))
        notes     = body.get("notes", "")

        if amount <= 0:
            return {"detail": t("portfolio.amount.positive")}, 400
        if price_usd <= 0:
            return {"detail": t("portfolio.price.positive")}, 400
        if tx_type not in ("buy", "sell", "transfer_in", "transfer_out", "fee"):
            return {"detail": t("portfolio.tx_type.invalid")}, 400

        result = _tracker.record_transaction(
            pubkey, tx_type, asset, amount, price_usd, fee_usd, notes
        )

        # If it's a buy, also add as holding
        if tx_type == "buy":
            cost_basis = amount * price_usd + fee_usd
            _tracker.add_holding(pubkey, asset, amount, cost_basis)

        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_performance(query: dict, pubkey: str) -> tuple[dict, int]:
    """
    GET /portfolio/performance?period=all

    Query params:
        period : 'day' | 'week' | 'month' | 'year' | 'all'
    """
    try:
        period = query.get("period", "all")
        if period not in ("day", "week", "month", "year", "all"):
            return {"detail": t("portfolio.period.invalid")}, 400

        result = _tracker.get_performance(pubkey, period)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_optimize(body: dict, pubkey: str) -> tuple[dict, int]:
    """
    POST /portfolio/optimize

    Body:
        assets          : list of asset names
        expected_returns : list of expected annual returns (fractions)
        risk_tolerance  : 'conservative' | 'moderate' | 'aggressive'
        method          : 'basic' | 'min_variance' | 'max_sharpe' | 'risk_parity'
        returns_series  : dict {asset: [daily_returns]} (optional, for advanced methods)
    """
    try:
        assets          = body.get("assets", ["BTC"])
        expected_returns = body.get("expected_returns", [0.80])
        risk_tolerance  = body.get("risk_tolerance", "moderate")
        method          = body.get("method", "basic")
        returns_series  = body.get("returns_series", {})

        if not assets:
            return {"detail": t("portfolio.assets.required")}, 400
        if len(assets) != len(expected_returns):
            return {"detail": t("portfolio.assets.mismatch")}, 400

        if method == "basic":
            result = _optimizer.optimize_allocation(assets, expected_returns, risk_tolerance)

        elif method == "min_variance":
            if not returns_series:
                # Build synthetic series from expected returns
                import random
                returns_series = {
                    a: [r / 252 + random.gauss(0, 0.03) for _ in range(252)]
                    for a, r in zip(assets, expected_returns)
                }
            result = _optimizer.minimum_variance_portfolio(assets, returns_series)

        elif method == "max_sharpe":
            if not returns_series:
                import random
                returns_series = {
                    a: [r / 252 + random.gauss(0, 0.03) for _ in range(252)]
                    for a, r in zip(assets, expected_returns)
                }
            result = _optimizer.maximum_sharpe_portfolio(assets, returns_series)

        elif method == "risk_parity":
            # Volatilities from returns series or default
            if returns_series:
                from .optimizer import _stddev
                vols = [_stddev(returns_series.get(a, [0.0])) * (252 ** 0.5)
                        for a in assets]
            else:
                # Default: BTC~70%, others~30%
                vols = [0.70 if a.upper() == "BTC" else 0.30 for a in assets]
            result = _optimizer.risk_parity_allocation(assets, vols)

        else:
            return {"detail": t("portfolio.method.invalid")}, 400

        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_risk(pubkey: str) -> tuple[dict, int]:
    """GET /portfolio/risk — risk metrics and stress test."""
    try:
        # Get holdings to build portfolio
        allocation = _tracker.get_allocation(pubkey)
        assets     = allocation.get("assets", {})

        # Build portfolio dict for stress test
        portfolio_alloc = {
            asset: data["allocation_pct"]
            for asset, data in assets.items()
        }

        if not portfolio_alloc:
            return {"detail": t("portfolio.no_holdings")}, 404

        # Stress test against all scenarios
        stress_results = _risk.stress_test(portfolio_alloc)

        # Diversification score
        div_score = _tracker.get_diversification_score(pubkey)

        return {
            "portfolio_allocation": portfolio_alloc,
            "diversification_score": div_score,
            "stress_tests":          stress_results,
            "risk_note": t("portfolio.risk_note"),
        }, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_cost_basis(query: dict, pubkey: str) -> tuple[dict, int]:
    """
    GET /portfolio/cost-basis?asset=BTC&method=fifo
    """
    try:
        asset  = query.get("asset", "BTC")
        method = query.get("method", "fifo")
        if method not in ("fifo", "lifo", "average"):
            return {"detail": t("portfolio.cost_method.invalid")}, 400
        result = _tracker.get_cost_basis(pubkey, asset, method)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_gains(query: dict, pubkey: str) -> tuple[dict, int]:
    """
    GET /portfolio/gains?year=2024
    """
    try:
        year_str = query.get("year")
        year     = int(year_str) if year_str else None
        realised   = _tracker.get_realized_gains(pubkey, year)
        unrealised = _tracker.get_unrealized_gains(pubkey)
        return {
            "realized":   realised,
            "unrealized": unrealised,
        }, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_portfolio_rebalance(body: dict, pubkey: str) -> tuple[dict, int]:
    """
    POST /portfolio/rebalance

    Body:
        target_allocation : {asset: target_weight_pct}
        estimate_costs    : bool (default false)
    """
    try:
        target = body.get("target_allocation", {})
        if not target:
            return {"detail": t("portfolio.target.required")}, 400

        current_alloc = _tracker.get_allocation(pubkey)
        current = {
            asset: data["allocation_pct"] / 100
            for asset, data in current_alloc.get("assets", {}).items()
        }
        target_normalized = {
            asset: w / 100 for asset, w in target.items()
        }

        recommendations = _optimizer.rebalance_recommendations(current, target_normalized)

        result = {
            "current_allocation": current,
            "target_allocation":  target_normalized,
            "recommendations":    recommendations,
        }

        if body.get("estimate_costs"):
            portfolio_value = _tracker.get_portfolio_value(pubkey)["total_value_usd"]
            cost_estimate   = _optimizer.calculate_rebalancing_cost(
                current, target_normalized, {}, portfolio_value
            )
            result["cost_estimate"] = cost_estimate

        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500
