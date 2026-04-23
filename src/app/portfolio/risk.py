"""
Risk analysis for Magma Bitcoin app.

RiskAnalyzer provides:
  - Value at Risk (historical, parametric, Monte Carlo)
  - Conditional VaR (Expected Shortfall)
  - Beta, Alpha, Treynor ratio, Information ratio
  - Max drawdown with duration
  - Calmar ratio
  - Stress testing against predefined macro scenarios
  - Monte Carlo portfolio simulation
  - Position sizing (fixed-risk and Kelly criterion)

SCENARIOS: 10 predefined market stress scenarios.

Uses only Python standard library.
"""

import math
import time
import random
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


def _percentile(values: list, p: float) -> float:
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


def _normal_inv_cdf(p: float) -> float:
    """Approximation of the inverse normal CDF (Beasley-Springer-Moro)."""
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0
    a = [0, -3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [0, -5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    p_low  = 0.02425
    p_high = 1 - p_low
    if p_low <= p <= p_high:
        q = p - 0.5
        r = q * q
        return (q * (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6]) /
                (((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1))
    elif p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def _box_muller() -> float:
    """Generate a standard normal random number using Box-Muller transform."""
    u1 = random.random()
    u2 = random.random()
    if u1 == 0:
        u1 = 1e-10
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


# ---------------------------------------------------------------------------
# Stress scenario definitions
# ---------------------------------------------------------------------------

@dataclass
class StressScenario:
    name:          str
    description:   str
    btc_change:    float      # % price change
    duration_days: int        # expected duration
    probability:   float      # annual probability estimate
    category:      str        # macro | bitcoin | regulatory | black_swan
    asset_impacts: dict = field(default_factory=dict)  # {asset: pct_change}


SCENARIOS: list[StressScenario] = [
    StressScenario(
        "BULL_RUN",
        "Broad Bitcoin bull market driven by institutional adoption",
        200.0, 365, 0.25, "bitcoin",
        {"BTC": 200.0, "ETH": 300.0, "bonds": -5.0, "gold": 5.0, "sp500": 15.0},
    ),
    StressScenario(
        "BEAR_MARKET",
        "Extended Bitcoin bear market, typical 2-year cycle",
        -70.0, 730, 0.30, "bitcoin",
        {"BTC": -70.0, "ETH": -90.0, "bonds": 10.0, "gold": 8.0, "sp500": -15.0},
    ),
    StressScenario(
        "FLASH_CRASH",
        "Sudden 40% crash within 24–48 hours (liquidation cascade)",
        -40.0, 7, 0.40, "bitcoin",
        {"BTC": -40.0, "ETH": -50.0, "bonds": 2.0, "gold": -2.0, "sp500": -5.0},
    ),
    StressScenario(
        "HYPERBITCOINIZATION",
        "Bitcoin becomes global reserve currency / medium of exchange",
        1000.0, 1825, 0.02, "bitcoin",
        {"BTC": 1000.0, "ETH": 200.0, "bonds": -40.0, "gold": -30.0, "sp500": -20.0},
    ),
    StressScenario(
        "REGULATORY_BAN",
        "Major jurisdiction bans Bitcoin holding/trading",
        -80.0, 180, 0.05, "regulatory",
        {"BTC": -80.0, "ETH": -85.0, "bonds": 5.0, "gold": 10.0, "sp500": -10.0},
    ),
    StressScenario(
        "HALVING_PUMP",
        "Post-halving supply shock drives 18-month bull run",
        150.0, 540, 0.50, "bitcoin",
        {"BTC": 150.0, "ETH": 200.0, "bonds": -3.0, "gold": 8.0, "sp500": 10.0},
    ),
    StressScenario(
        "EXCHANGE_COLLAPSE",
        "Major exchange collapses (FTX-style), contagion spreads",
        -30.0, 90, 0.15, "bitcoin",
        {"BTC": -30.0, "ETH": -45.0, "bonds": 3.0, "gold": 5.0, "sp500": -8.0},
    ),
    StressScenario(
        "STABLECOIN_DEPEG",
        "Major stablecoin loses peg, flight to BTC and fiat",
        10.0, 30, 0.10, "bitcoin",
        {"BTC": 10.0, "ETH": -20.0, "USDT": -10.0, "bonds": 2.0, "sp500": -3.0},
    ),
    StressScenario(
        "FED_RATE_HIKE",
        "Aggressive Fed rate hikes reduce risk appetite",
        -20.0, 180, 0.35, "macro",
        {"BTC": -20.0, "ETH": -25.0, "bonds": -8.0, "gold": -5.0, "sp500": -18.0},
    ),
    StressScenario(
        "GLOBAL_RECESSION",
        "Deep global recession, risk-off across all assets",
        -50.0, 365, 0.15, "macro",
        {"BTC": -50.0, "ETH": -60.0, "bonds": 12.0, "gold": 15.0, "sp500": -35.0},
    ),
    StressScenario(
        "DOLLAR_WEAKNESS",
        "US dollar loses reserve status, BTC/gold benefit",
        50.0, 365, 0.10, "macro",
        {"BTC": 50.0, "ETH": 40.0, "bonds": -15.0, "gold": 20.0, "sp500": 5.0},
    ),
    StressScenario(
        "TECH_BREAKTHROUGH",
        "Lightning Network mass adoption, 500% transaction growth",
        80.0, 365, 0.15, "bitcoin",
        {"BTC": 80.0, "ETH": 30.0, "bonds": 0.0, "gold": 0.0, "sp500": 3.0},
    ),
    StressScenario(
        "INSTITUTIONAL_ADOPTION",
        "Sovereign wealth funds and pension funds allocate to BTC",
        100.0, 365, 0.20, "bitcoin",
        {"BTC": 100.0, "ETH": 80.0, "bonds": -2.0, "gold": 5.0, "sp500": 5.0},
    ),
    StressScenario(
        "MINING_CRISIS",
        "Energy crisis / geopolitical event disrupts 40% of hashrate",
        -25.0, 90, 0.10, "bitcoin",
        {"BTC": -25.0, "ETH": -15.0, "bonds": 2.0, "gold": 8.0, "sp500": -3.0},
    ),
    StressScenario(
        "BLACK_SWAN",
        "Unknown catastrophic event shocks all markets simultaneously",
        -60.0, 90, 0.05, "black_swan",
        {"BTC": -60.0, "ETH": -70.0, "bonds": 5.0, "gold": -5.0, "sp500": -40.0},
    ),
]

SCENARIOS_DICT: dict[str, StressScenario] = {s.name: s for s in SCENARIOS}


# ---------------------------------------------------------------------------
# RiskAnalyzer
# ---------------------------------------------------------------------------

class RiskAnalyzer:
    """
    Comprehensive risk analytics for Bitcoin and multi-asset portfolios.
    """

    # ------------------------------------------------------------------
    # Value at Risk
    # ------------------------------------------------------------------

    def calculate_var(self, returns: list[float], confidence: float = 0.95,
                       method: str = "historical") -> dict:
        """
        Calculate Value at Risk (VaR).

        Parameters
        ----------
        returns    : list of daily returns (as fractions, e.g. 0.03 = +3%)
        confidence : confidence level, e.g. 0.95, 0.99
        method     : 'historical' | 'parametric' | 'monte_carlo'

        Returns
        -------
        dict with var_pct, var_usd (per $10,000), method, confidence
        """
        if not returns:
            return {"var_pct": 0.0, "method": method}

        if method == "historical":
            loss_quantile = 1 - confidence
            var_pct = abs(_percentile(returns, loss_quantile * 100))

        elif method == "parametric":
            mu     = _mean(returns)
            sigma  = _stddev(returns)
            z      = abs(_normal_inv_cdf(1 - confidence))
            var_pct = abs(mu - z * sigma)

        elif method == "monte_carlo":
            mu    = _mean(returns)
            sigma = _stddev(returns)
            simulated = [_box_muller() * sigma + mu for _ in range(10_000)]
            loss_quantile = 1 - confidence
            var_pct = abs(_percentile(simulated, loss_quantile * 100))

        else:
            return {"error": f"Unknown method: {method}"}

        return {
            "var_pct":        round(var_pct * 100, 4),
            "var_usd_per_10k": round(var_pct * 10_000, 2),
            "confidence":     confidence,
            "method":         method,
            "horizon":        "1 day",
            "interpretation": (
                f"With {confidence*100:.0f}% confidence, the maximum 1-day loss is "
                f"approximately {var_pct*100:.2f}% (${var_pct*10_000:,.0f} per $10,000)."
            ),
        }

    # ------------------------------------------------------------------
    # Conditional VaR (Expected Shortfall)
    # ------------------------------------------------------------------

    def calculate_cvar(self, returns: list[float], confidence: float = 0.95) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).
        Returns the average loss beyond the VaR threshold.
        """
        if not returns:
            return 0.0
        sorted_rets = sorted(returns)
        cutoff_idx  = int((1 - confidence) * len(sorted_rets))
        tail_losses = sorted_rets[:max(cutoff_idx, 1)]
        cvar = abs(_mean(tail_losses)) * 100
        return round(cvar, 4)

    # ------------------------------------------------------------------
    # Beta and Alpha
    # ------------------------------------------------------------------

    def calculate_beta(self, asset_returns: list[float],
                        market_returns: list[float]) -> float:
        """
        Market beta: sensitivity of asset to market movements.
        β > 1 = more volatile than market; β < 1 = less volatile.
        """
        n = min(len(asset_returns), len(market_returns))
        if n < 2:
            return 1.0

        ar = asset_returns[:n]
        mr = market_returns[:n]
        mar = _mean(ar)
        mmr = _mean(mr)

        cov = sum((ar[i] - mar) * (mr[i] - mmr) for i in range(n)) / (n - 1)
        var = sum((mr[i] - mmr) ** 2 for i in range(n)) / (n - 1)

        if var == 0:
            return 1.0
        return round(cov / var, 4)

    def calculate_alpha(self, asset_returns: list[float],
                         market_returns: list[float],
                         risk_free_rate: float = 0.05) -> float:
        """
        Jensen's Alpha: excess return vs CAPM expectation.
        Positive alpha = outperformance after adjusting for market risk.
        """
        if not asset_returns or not market_returns:
            return 0.0

        beta       = self.calculate_beta(asset_returns, market_returns)
        asset_ann  = _mean(asset_returns) * 252
        market_ann = _mean(market_returns) * 252
        rfr_daily  = risk_free_rate / 252

        capm_expected = risk_free_rate + beta * (market_ann - risk_free_rate)
        alpha = asset_ann - capm_expected
        return round(alpha, 4)

    def calculate_treynor_ratio(self, returns: list[float],
                                  market_returns: list[float],
                                  risk_free_rate: float = 0.05) -> float:
        """Treynor Ratio: (excess return) / beta."""
        beta = self.calculate_beta(returns, market_returns)
        if beta == 0:
            return 0.0
        excess_return = _mean(returns) * 252 - risk_free_rate
        return round(excess_return / beta, 4)

    def calculate_information_ratio(self, returns: list[float],
                                      benchmark_returns: list[float]) -> float:
        """
        Information Ratio: excess return vs benchmark / tracking error.
        Measures active management skill.
        """
        n = min(len(returns), len(benchmark_returns))
        if n < 2:
            return 0.0

        active_returns = [returns[i] - benchmark_returns[i] for i in range(n)]
        ann_active     = _mean(active_returns) * 252
        tracking_error = _stddev(active_returns) * math.sqrt(252)

        if tracking_error == 0:
            return 0.0
        return round(ann_active / tracking_error, 4)

    # ------------------------------------------------------------------
    # Max Drawdown
    # ------------------------------------------------------------------

    def calculate_max_drawdown(self, values: list[float]) -> dict:
        """
        Max drawdown with peak, trough, duration, and recovery time.
        """
        if len(values) < 2:
            return {"drawdown_pct": 0.0}

        peak_val   = values[0]
        peak_idx   = 0
        max_dd     = 0.0
        best_peak  = 0
        best_trough = 0

        for i in range(1, len(values)):
            if values[i] > peak_val:
                peak_val = values[i]
                peak_idx = i
            else:
                dd = (values[i] - peak_val) / peak_val
                if dd < max_dd:
                    max_dd = dd
                    best_peak   = peak_idx
                    best_trough = i

        # Recovery
        recovery_idx = None
        peak_price   = values[best_peak]
        for j in range(best_trough + 1, len(values)):
            if values[j] >= peak_price:
                recovery_idx = j
                break

        duration_periods = best_trough - best_peak
        recovery_periods = (recovery_idx - best_peak) if recovery_idx else None

        return {
            "drawdown_pct":       round(max_dd * 100, 4),
            "peak_index":         best_peak,
            "trough_index":       best_trough,
            "peak_value":         round(values[best_peak], 4),
            "trough_value":       round(values[best_trough], 4),
            "duration_periods":   duration_periods,
            "recovery_periods":   recovery_periods,
            "recovered":          recovery_idx is not None,
        }

    # ------------------------------------------------------------------
    # Calmar Ratio
    # ------------------------------------------------------------------

    def calculate_calmar_ratio(self, returns: list[float],
                                 max_dd: float) -> float:
        """
        Calmar Ratio: annualised return / max drawdown (absolute).
        """
        ann_return = _mean(returns) * 252
        if max_dd == 0:
            return 0.0
        return round(ann_return / abs(max_dd / 100), 4)

    # ------------------------------------------------------------------
    # Stress testing
    # ------------------------------------------------------------------

    def stress_test(self, portfolio: dict, scenarios: list[str] = None) -> list[dict]:
        """
        Apply stress scenarios to portfolio and calculate impact.

        Parameters
        ----------
        portfolio : {asset: allocation_pct (0–100)}
        scenarios : list of scenario names; None = all predefined

        Returns
        -------
        list of {scenario, portfolio_impact_pct, asset_impacts, description}
        """
        if scenarios is None:
            scenario_list = SCENARIOS
        else:
            scenario_list = [SCENARIOS_DICT[s] for s in scenarios if s in SCENARIOS_DICT]

        results = []
        for scenario in scenario_list:
            total_impact = 0.0
            asset_impacts = {}

            for asset, weight in portfolio.items():
                impact_pct = scenario.asset_impacts.get(asset.upper(),
                              scenario.btc_change if asset.upper() == "BTC"
                              else scenario.btc_change * 0.8)
                contribution = weight / 100 * impact_pct
                total_impact += contribution
                asset_impacts[asset] = {
                    "weight_pct":    weight,
                    "price_change":  impact_pct,
                    "contribution":  round(contribution, 4),
                }

            results.append({
                "scenario":              scenario.name,
                "description":           scenario.description,
                "category":              scenario.category,
                "portfolio_impact_pct":  round(total_impact, 4),
                "duration_days":         scenario.duration_days,
                "annual_probability":    scenario.probability,
                "asset_impacts":         asset_impacts,
                "value_at_risk_10k":     round(abs(min(total_impact, 0)) * 100, 2),
            })

        results.sort(key=lambda r: r["portfolio_impact_pct"])
        return results

    # ------------------------------------------------------------------
    # Monte Carlo simulation
    # ------------------------------------------------------------------

    def monte_carlo_simulation(self, portfolio: dict, n_simulations: int = 1000,
                                n_days: int = 365) -> dict:
        """
        Monte Carlo simulation of portfolio value over time.

        Parameters
        ----------
        portfolio     : {asset: {allocation_pct, expected_annual_return, annual_volatility}}
        n_simulations : number of paths
        n_days        : simulation horizon

        Returns
        -------
        dict with percentile paths, final value distribution,
        probability of loss, probability of 2x
        """
        # Aggregate portfolio parameters (weighted average)
        total_alloc = sum(v.get("allocation_pct", 0) for v in portfolio.values())
        if total_alloc == 0:
            return {}

        portfolio_return = 0.0
        portfolio_vol    = 0.0
        for asset, params in portfolio.items():
            w    = params.get("allocation_pct", 0) / total_alloc
            ret  = params.get("expected_annual_return", 0.30)  # default 30% for BTC
            vol  = params.get("annual_volatility", 0.70)       # default 70%
            portfolio_return += w * ret
            portfolio_vol    += w * vol   # simplified (no covariance)

        # Daily parameters
        daily_mu    = portfolio_return / 252
        daily_sigma = portfolio_vol / math.sqrt(252)

        initial_value = 10_000.0
        final_values  = []
        paths         = {5: [], 25: [], 50: [], 75: [], 95: []}
        _paths_raw = [[] for _ in range(min(n_simulations, 1000))]

        random.seed(42)
        for sim in range(n_simulations):
            value = initial_value
            path  = [value]
            for _ in range(n_days):
                r = _box_muller() * daily_sigma + daily_mu
                value = value * math.exp(r)
                path.append(round(value, 2))
            final_values.append(value)
            if sim < 1000:
                _paths_raw[sim] = path

        # Percentile paths (sample every 30 days for readability)
        n_sample = len(_paths_raw)
        step     = max(n_days // 30, 1)
        indices  = list(range(0, n_days + 1, step))

        for pct in [5, 25, 50, 75, 95]:
            path_by_day = []
            for idx in indices:
                day_vals = [_paths_raw[s][idx] for s in range(n_sample)
                            if idx < len(_paths_raw[s])]
                path_by_day.append(round(_percentile(day_vals, pct), 2))
            paths[pct] = path_by_day

        prob_loss = sum(1 for v in final_values if v < initial_value) / n_simulations
        prob_2x   = sum(1 for v in final_values if v >= initial_value * 2) / n_simulations
        prob_10x  = sum(1 for v in final_values if v >= initial_value * 10) / n_simulations

        return {
            "initial_value":      initial_value,
            "n_simulations":      n_simulations,
            "horizon_days":       n_days,
            "portfolio_params": {
                "expected_annual_return": round(portfolio_return, 4),
                "annual_volatility":      round(portfolio_vol, 4),
            },
            "final_value_distribution": {
                "mean":   round(_mean(final_values), 2),
                "median": round(_percentile(final_values, 50), 2),
                "p5":     round(_percentile(final_values, 5), 2),
                "p25":    round(_percentile(final_values, 25), 2),
                "p75":    round(_percentile(final_values, 75), 2),
                "p95":    round(_percentile(final_values, 95), 2),
            },
            "probabilities": {
                "loss_pct":  round(prob_loss * 100, 2),
                "gain_2x_pct": round(prob_2x * 100, 2),
                "gain_10x_pct": round(prob_10x * 100, 2),
            },
            "percentile_paths": paths,
            "sample_days":       indices,
        }

    # ------------------------------------------------------------------
    # Comprehensive risk metrics
    # ------------------------------------------------------------------

    def get_risk_metrics(self, returns: list[float],
                          risk_free_rate: float = 0.05) -> dict:
        """
        Comprehensive risk metrics summary.
        """
        if not returns:
            return {}

        ann_return  = _mean(returns) * 252
        ann_vol     = _stddev(returns) * math.sqrt(252)
        sharpe      = (ann_return - risk_free_rate) / ann_vol if ann_vol > 0 else 0
        sortino_denom = _stddev([r for r in returns if r < 0]) * math.sqrt(252)
        sortino     = (ann_return - risk_free_rate) / sortino_denom if sortino_denom > 0 else 0

        cumulative  = [1.0]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r))
        mdd_info    = self.calculate_max_drawdown(cumulative)
        calmar      = self.calculate_calmar_ratio(returns, mdd_info["drawdown_pct"])

        var_hist    = self.calculate_var(returns, 0.95, "historical")
        var_param   = self.calculate_var(returns, 0.95, "parametric")
        cvar        = self.calculate_cvar(returns, 0.95)

        skewness_sum = sum((r - _mean(returns)) ** 3 for r in returns)
        n = len(returns)
        s = _stddev(returns)
        skewness = (skewness_sum / n) / (s ** 3) if s > 0 else 0
        kurtosis_sum = sum((r - _mean(returns)) ** 4 for r in returns)
        kurtosis = ((kurtosis_sum / n) / (s ** 4) - 3) if s > 0 else 0

        pos_days = sum(1 for r in returns if r > 0)
        neg_days = len(returns) - pos_days

        return {
            "period_data_points":      len(returns),
            "annualised_return_pct":   round(ann_return * 100, 4),
            "annualised_volatility_pct": round(ann_vol * 100, 4),
            "sharpe_ratio":            round(sharpe, 4),
            "sortino_ratio":           round(sortino, 4),
            "calmar_ratio":            round(calmar, 4),
            "max_drawdown_pct":        mdd_info["drawdown_pct"],
            "var_95_historical_pct":   var_hist.get("var_pct", 0),
            "var_95_parametric_pct":   var_param.get("var_pct", 0),
            "cvar_95_pct":             cvar,
            "skewness":                round(skewness, 4),
            "excess_kurtosis":         round(kurtosis, 4),
            "positive_days":           pos_days,
            "negative_days":           neg_days,
            "win_rate_pct":            round(pos_days / len(returns) * 100, 2),
            "risk_free_rate":          risk_free_rate,
        }

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def calculate_position_size(self, account_value: float,
                                  risk_pct: float,
                                  entry_price: float,
                                  stop_loss_price: float) -> dict:
        """
        Calculate position size using fixed-risk model.

        Parameters
        ----------
        account_value  : total account value in USD
        risk_pct       : max % of account to risk per trade (e.g. 2.0 = 2%)
        entry_price    : intended entry price
        stop_loss_price: stop loss price

        Returns
        -------
        dict with position_size_btc, position_value_usd, risk_usd,
        risk_pct, risk_reward_guidance
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return {"error": "Prices must be positive"}

        risk_per_trade = account_value * (risk_pct / 100)
        risk_per_btc   = abs(entry_price - stop_loss_price)

        if risk_per_btc == 0:
            return {"error": "Entry and stop-loss cannot be the same price"}

        position_size_btc = risk_per_trade / risk_per_btc
        position_value    = position_size_btc * entry_price
        portfolio_pct     = position_value / account_value * 100

        side = "long" if entry_price > stop_loss_price else "short"

        return {
            "side":               side,
            "account_value_usd":  account_value,
            "entry_price":        entry_price,
            "stop_loss_price":    stop_loss_price,
            "risk_per_trade_usd": round(risk_per_trade, 2),
            "risk_pct":           risk_pct,
            "risk_per_btc":       round(risk_per_btc, 2),
            "position_size_btc":  round(position_size_btc, 6),
            "position_value_usd": round(position_value, 2),
            "portfolio_pct":      round(portfolio_pct, 2),
            "note": "Assumes stop-loss is always executed at the specified price.",
        }

    def calculate_kelly_criterion(self, win_rate: float,
                                    win_loss_ratio: float) -> float:
        """
        Full Kelly fraction: f* = W - (1-W)/R
        where W = win rate, R = win/loss ratio.

        Returns optimal fraction of capital to risk per trade.
        Practical usage: half-Kelly (f*/2) is often recommended.
        """
        if win_loss_ratio <= 0:
            return 0.0
        kelly = win_rate - (1 - win_rate) / win_loss_ratio
        full_kelly     = round(max(kelly, 0), 4)
        half_kelly     = round(full_kelly / 2, 4)
        quarter_kelly  = round(full_kelly / 4, 4)

        return {
            "full_kelly_fraction":    full_kelly,
            "half_kelly_fraction":    half_kelly,
            "quarter_kelly_fraction": quarter_kelly,
            "win_rate":               win_rate,
            "win_loss_ratio":         win_loss_ratio,
            "recommendation":         half_kelly,
            "note": (
                "Full Kelly maximises logarithmic growth but can be very aggressive. "
                "Half or quarter Kelly is recommended for most practical use."
            ),
        }
