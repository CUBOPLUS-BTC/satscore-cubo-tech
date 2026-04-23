"""
HTTP route handlers for the Simulation Engine.

All handlers return (response_dict, status_code) tuples.
"""

from .montecarlo import MonteCarloEngine
from .backtest import (
    BacktestEngine,
    DCAStrategy,
    ValueAveragingStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    BuyAndHoldStrategy,
    RebalancingStrategy,
    TrendFollowingStrategy,
    AccumulationStrategy,
)
from .scenarios import ScenarioAnalyzer, PREDEFINED_SCENARIOS

_mc       = MonteCarloEngine(seed=42)
_backtest = BacktestEngine()
_scenario = ScenarioAnalyzer()


def handle_simulate_portfolio(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/portfolio

    Simulate portfolio growth with monthly contributions.

    Body:
        initial           : float (starting value, default 1000)
        monthly_contribution : float (default 100)
        returns_dist      : {mean, std, distribution} (default BTC-like)
        years             : int (default 10)
        n_simulations     : int (default 1000, max 5000)
    """
    try:
        initial      = float(body.get("initial", 1000))
        monthly      = float(body.get("monthly_contribution", 100))
        years        = int(body.get("years", 10))
        n_sims       = min(int(body.get("n_simulations", 1000)), 5000)
        returns_dist = body.get("returns_dist", {
            "mean": 0.40, "std": 0.70, "distribution": "lognormal"
        })

        if initial < 0:
            return {"detail": "initial must be non-negative"}, 400
        if monthly < 0:
            return {"detail": "monthly_contribution must be non-negative"}, 400
        if years < 1 or years > 50:
            return {"detail": "years must be between 1 and 50"}, 400

        result = _mc.simulate_portfolio_growth(
            initial=initial,
            contributions=monthly,
            returns_dist=returns_dist,
            years=years,
            n_sims=n_sims,
        )
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_simulate_dca(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/dca

    Simulate DCA outcomes under uncertain price paths.

    Body:
        amount          : float (USD per purchase, default 100)
        frequency       : 'daily' | 'weekly' | 'monthly' (default 'monthly')
        initial_price   : float (default 65000)
        drift           : float (annual, e.g. 0.40)
        volatility      : float (annual, e.g. 0.70)
        years           : int (default 5)
        n_simulations   : int (default 1000)
    """
    try:
        amount      = float(body.get("amount", 100))
        frequency   = body.get("frequency", "monthly")
        years       = int(body.get("years", 5))
        n_sims      = min(int(body.get("n_simulations", 1000)), 5000)
        price_model = {
            "initial_price": float(body.get("initial_price", 65_000)),
            "drift":         float(body.get("drift", 0.40)),
            "volatility":    float(body.get("volatility", 0.70)),
        }

        if amount <= 0:
            return {"detail": "amount must be positive"}, 400
        if frequency not in ("daily", "weekly", "monthly"):
            return {"detail": "frequency must be 'daily', 'weekly', or 'monthly'"}, 400
        if years < 1 or years > 30:
            return {"detail": "years must be between 1 and 30"}, 400

        result = _mc.simulate_dca_outcomes(
            amount=amount,
            frequency=frequency,
            price_model=price_model,
            years=years,
            n_sims=n_sims,
        )
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_backtest(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/backtest

    Run one or more strategies against provided price data.

    Body:
        strategy    : str name OR list of str names (default 'dca')
        prices      : list of {close, timestamp, volume} (required)
        capital     : float (default 10000)
        strategy_params : dict of strategy-specific params (optional)
        compare     : bool — if true, compare all built-in strategies
    """
    try:
        prices  = body.get("prices", [])
        capital = float(body.get("capital", 10_000))

        if not prices:
            return {"detail": "prices list is required"}, 400
        if len(prices) < 20:
            return {"detail": "Need at least 20 price data points"}, 400

        compare = body.get("compare", False)

        if compare:
            # Run all built-in strategies
            strategies = [
                BuyAndHoldStrategy(),
                DCAStrategy(amount=capital / len(prices) * 30),
                MomentumStrategy(lookback=20),
                MeanReversionStrategy(window=20),
                TrendFollowingStrategy(fast_ma=20, slow_ma=50),
                RebalancingStrategy(target_allocation=0.60),
                AccumulationStrategy(buy_dip_threshold=0.10, amount=capital / 50),
            ]
            result = _backtest.compare_strategies(strategies, prices, capital)
            return result, 200

        # Single strategy
        strategy_name = body.get("strategy", "dca")
        params        = body.get("strategy_params", {})

        strategy = _build_strategy(strategy_name, params, capital, prices)
        if strategy is None:
            return {"detail": f"Unknown strategy: {strategy_name}"}, 400

        result = _backtest.run(strategy, prices, capital)
        return result.to_dict(), 200

    except Exception as e:
        return {"detail": str(e)}, 500


def _build_strategy(name: str, params: dict, capital: float, prices: list):
    """Instantiate a strategy by name."""
    name_lower = name.lower()
    if name_lower in ("dca", "dollar_cost_averaging"):
        amount    = float(params.get("amount", capital / 30))
        frequency = int(params.get("frequency", 30))
        return DCAStrategy(amount=amount, frequency=frequency)

    elif name_lower in ("buy_and_hold", "bah", "buyandhold"):
        pct = float(params.get("initial_buy_pct", 0.95))
        return BuyAndHoldStrategy(initial_buy_pct=pct)

    elif name_lower == "momentum":
        lookback  = int(params.get("lookback", 20))
        threshold = float(params.get("threshold", 0.02))
        return MomentumStrategy(lookback=lookback, threshold=threshold)

    elif name_lower in ("mean_reversion", "meanreversion"):
        window = int(params.get("window", 20))
        std_t  = float(params.get("std_threshold", 2.0))
        return MeanReversionStrategy(window=window, std_threshold=std_t)

    elif name_lower in ("trend_following", "trendfollowing"):
        fast = int(params.get("fast_ma", 20))
        slow = int(params.get("slow_ma", 50))
        return TrendFollowingStrategy(fast_ma=fast, slow_ma=slow)

    elif name_lower in ("rebalancing", "rebalance"):
        target = float(params.get("target_allocation", 0.60))
        thresh = float(params.get("threshold", 0.05))
        freq   = int(params.get("frequency", 30))
        return RebalancingStrategy(target_allocation=target,
                                    rebalance_threshold=thresh,
                                    frequency=freq)

    elif name_lower in ("value_averaging", "valueaveraging"):
        base   = float(params.get("base_amount", capital / 60))
        growth = float(params.get("target_growth", 0.05))
        return ValueAveragingStrategy(base_amount=base, target_growth=growth)

    elif name_lower in ("accumulation", "buy_the_dip"):
        dip = float(params.get("buy_dip_threshold", 0.10))
        amt = float(params.get("amount", capital / 20))
        return AccumulationStrategy(buy_dip_threshold=dip, amount=amt)

    return None


def handle_scenario_analysis(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/scenario

    Analyze portfolio under a specific scenario or run a full stress test.

    Body:
        portfolio      : {asset: allocation_pct} or {asset: {value_usd, allocation_pct}}
        scenario       : str (predefined scenario name) OR null for stress test
        custom_scenario: dict (optional, overrides scenario name)
        mode           : 'single' | 'stress_test' | 'list' (default 'single')
    """
    try:
        mode      = body.get("mode", "single")
        portfolio = body.get("portfolio", {"BTC": 100})

        if mode == "list":
            return {"scenarios": [s.to_dict() for s in PREDEFINED_SCENARIOS]}, 200

        if mode == "stress_test":
            scenarios = body.get("scenarios")  # None = all
            result = _scenario.run_stress_test(portfolio, scenarios)
            return result, 200

        if mode == "single":
            scenario_name   = body.get("scenario")
            custom_scenario = body.get("custom_scenario")
            if not scenario_name and not custom_scenario:
                return {"detail": "scenario name or custom_scenario required for single mode"}, 400
            result = _scenario.analyze_scenario(portfolio, scenario_name, custom_scenario)
            return result, 200

        return {"detail": "mode must be 'single', 'stress_test', or 'list'"}, 400

    except Exception as e:
        return {"detail": str(e)}, 500


def handle_monte_carlo(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/monte-carlo

    Simulate Bitcoin price paths using Geometric Brownian Motion.

    Body:
        current_price : float (default 65000)
        volatility    : float annualised (default 0.70)
        drift         : float annualised (default 0.40)
        days          : int (default 365)
        n_paths       : int (default 500, max 2000)
    """
    try:
        current_price = float(body.get("current_price", 65_000))
        volatility    = float(body.get("volatility", 0.70))
        drift         = float(body.get("drift", 0.40))
        days          = int(body.get("days", 365))
        n_paths       = min(int(body.get("n_paths", 500)), 2000)

        if current_price <= 0:
            return {"detail": "current_price must be positive"}, 400
        if volatility <= 0 or volatility > 5:
            return {"detail": "volatility must be between 0 and 5"}, 400
        if days < 1 or days > 3650:
            return {"detail": "days must be between 1 and 3650"}, 400

        result = _mc.simulate_price_path(
            current_price=current_price,
            volatility=volatility,
            drift=drift,
            days=days,
            n_paths=n_paths,
        )
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_retirement_sim(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/retirement

    Monte Carlo retirement planning simulation.

    Body:
        current_age          : int
        retirement_age       : int
        life_expectancy      : int (default 85)
        current_savings      : float
        monthly_contribution : float
        monthly_expenses     : float (in retirement)
        btc_allocation_pct   : float (default 20)
        expected_btc_return  : float (default 0.40)
        btc_volatility       : float (default 0.70)
        expected_trad_return : float (default 0.07)
        trad_volatility      : float (default 0.15)
        inflation_rate       : float (default 0.03)
        n_simulations        : int (default 1000)
    """
    try:
        n_sims = min(int(body.get("n_simulations", 1000)), 5000)
        params = {
            "current_age":          int(body.get("current_age", 30)),
            "retirement_age":       int(body.get("retirement_age", 65)),
            "life_expectancy":      int(body.get("life_expectancy", 85)),
            "current_savings":      float(body.get("current_savings", 10_000)),
            "monthly_contribution": float(body.get("monthly_contribution", 500)),
            "monthly_expenses":     float(body.get("monthly_expenses", 3_000)),
            "btc_allocation_pct":   float(body.get("btc_allocation_pct", 20)),
            "expected_btc_return":  float(body.get("expected_btc_return", 0.40)),
            "btc_volatility":       float(body.get("btc_volatility", 0.70)),
            "expected_trad_return": float(body.get("expected_trad_return", 0.07)),
            "trad_volatility":      float(body.get("trad_volatility", 0.15)),
            "inflation_rate":       float(body.get("inflation_rate", 0.03)),
        }

        if params["current_age"] >= params["retirement_age"]:
            return {"detail": "current_age must be less than retirement_age"}, 400
        if params["retirement_age"] >= params["life_expectancy"]:
            return {"detail": "retirement_age must be less than life_expectancy"}, 400

        result = _mc.simulate_retirement(params=params, n_sims=n_sims)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_probability_of_ruin(body: dict) -> tuple[dict, int]:
    """
    POST /simulation/ruin

    Calculate probability of portfolio depletion.

    Body:
        portfolio_value    : float
        monthly_withdrawals: float
        returns_dist       : {mean, std, distribution}
        years              : int (default 30)
        n_simulations      : int (default 1000)
    """
    try:
        portfolio_value    = float(body.get("portfolio_value", 100_000))
        monthly_withdrawals = float(body.get("monthly_withdrawals", 2_000))
        years              = int(body.get("years", 30))
        n_sims             = min(int(body.get("n_simulations", 1000)), 5000)
        returns_dist       = body.get("returns_dist", {
            "mean": 0.07, "std": 0.15, "distribution": "normal"
        })

        if portfolio_value <= 0:
            return {"detail": "portfolio_value must be positive"}, 400
        if monthly_withdrawals <= 0:
            return {"detail": "monthly_withdrawals must be positive"}, 400

        result = _mc.probability_of_ruin(
            portfolio_value=portfolio_value,
            monthly_withdrawals=monthly_withdrawals,
            returns_dist=returns_dist,
            years=years,
            n_sims=n_sims,
        )
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500
