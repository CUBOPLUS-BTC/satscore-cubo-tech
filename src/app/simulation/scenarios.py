"""
Scenario analysis engine for Magma Bitcoin app.

ScenarioAnalyzer provides:
  - Portfolio impact analysis for predefined and custom scenarios
  - Stress testing across multiple scenarios
  - Sensitivity analysis (vary a single parameter)
  - What-if analysis (apply multiple changes)
  - Break-even analysis

PREDEFINED_SCENARIOS: 15 major market scenarios.

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
    return sum(values) / len(values) if values else 0.0


def _pct(old: float, new: float) -> float:
    return (new - old) / old * 100.0 if old else 0.0


def _apply_change(value: float, pct_change: float) -> float:
    return value * (1 + pct_change / 100)


# ---------------------------------------------------------------------------
# Scenario definition
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """A named market scenario with asset-level impacts."""
    name:          str
    description:   str
    duration_days: int
    probability:   float      # estimated annual probability
    category:      str
    asset_changes: dict       # {asset: pct_change}
    macro_impacts: dict = field(default_factory=dict)  # additional macro variables
    historical_analog: str = ""

    def to_dict(self) -> dict:
        return {
            "name":              self.name,
            "description":       self.description,
            "duration_days":     self.duration_days,
            "probability":       self.probability,
            "category":          self.category,
            "asset_changes":     self.asset_changes,
            "macro_impacts":     self.macro_impacts,
            "historical_analog": self.historical_analog,
        }


# ---------------------------------------------------------------------------
# 15 predefined scenarios
# ---------------------------------------------------------------------------

PREDEFINED_SCENARIOS: list[Scenario] = [
    Scenario(
        "BULL_RUN",
        "Broad Bitcoin bull market driven by institutional demand and ETF inflows",
        365, 0.25, "bitcoin",
        {"BTC": 200.0, "ETH": 300.0, "USDT": 0.0, "gold": 5.0, "sp500": 15.0, "bonds": -5.0},
        {"inflation": 1.5, "interest_rates": -0.5, "usd_index": -3.0},
        "2020-2021 bull market",
    ),
    Scenario(
        "BEAR_MARKET",
        "Prolonged Bitcoin bear market, typical 2-year cycle with 70%+ drawdowns",
        730, 0.30, "bitcoin",
        {"BTC": -70.0, "ETH": -90.0, "USDT": 0.0, "gold": 8.0, "sp500": -15.0, "bonds": 10.0},
        {"inflation": -0.5, "interest_rates": 1.0, "usd_index": 5.0},
        "2018 bear market, 2022 bear market",
    ),
    Scenario(
        "FLASH_CRASH",
        "Sudden liquidation cascade drops BTC 40% in under 48 hours",
        7, 0.40, "bitcoin",
        {"BTC": -40.0, "ETH": -50.0, "USDT": 2.0, "gold": -2.0, "sp500": -5.0, "bonds": 2.0},
        {"volatility_spike": 300.0, "funding_rate": -0.5},
        "March 2020 COVID crash, May 2021 crash",
    ),
    Scenario(
        "HYPERBITCOINIZATION",
        "Bitcoin becomes global reserve asset; nation-states accumulate BTC",
        1825, 0.02, "bitcoin",
        {"BTC": 1000.0, "ETH": 200.0, "USDT": -50.0, "gold": -30.0, "sp500": -20.0, "bonds": -40.0},
        {"usd_index": -60.0, "inflation": 20.0},
        "Speculative scenario (El Salvador, Bhutan precedent)",
    ),
    Scenario(
        "REGULATORY_BAN",
        "Major jurisdiction (US or EU) bans Bitcoin holding and trading",
        180, 0.05, "regulatory",
        {"BTC": -80.0, "ETH": -85.0, "USDT": -5.0, "gold": 10.0, "sp500": -10.0, "bonds": 5.0},
        {"compliance_cost": 100.0, "exchange_volume": -60.0},
        "China 2021 mining ban, India proposed ban",
    ),
    Scenario(
        "HALVING_PUMP",
        "Post-halving supply shock triggers 18-month bull run",
        540, 0.50, "bitcoin",
        {"BTC": 150.0, "ETH": 200.0, "USDT": 0.0, "gold": 8.0, "sp500": 10.0, "bonds": -3.0},
        {"miner_revenue": -50.0, "fee_market": 200.0},
        "2012, 2016, 2020 post-halving cycles",
    ),
    Scenario(
        "EXCHANGE_COLLAPSE",
        "Top-5 exchange collapses (FTX-style), contagion across ecosystem",
        90, 0.15, "bitcoin",
        {"BTC": -30.0, "ETH": -45.0, "USDT": -2.0, "gold": 5.0, "sp500": -8.0, "bonds": 3.0},
        {"exchange_volume": -40.0, "withdrawal_freeze": True},
        "FTX collapse 2022, MT Gox 2014",
    ),
    Scenario(
        "STABLECOIN_DEPEG",
        "Major stablecoin (USDT/USDC) loses its $1 peg, panic spreads",
        30, 0.10, "bitcoin",
        {"BTC": 10.0, "ETH": -20.0, "USDT": -10.0, "USDC": -8.0, "gold": 5.0, "sp500": -3.0},
        {"defi_tvl": -30.0, "stablecoin_outflow": 15000000000},
        "UST/Terra collapse 2022",
    ),
    Scenario(
        "FED_RATE_HIKE",
        "Aggressive Federal Reserve rate increases reduce risk appetite globally",
        180, 0.35, "macro",
        {"BTC": -20.0, "ETH": -25.0, "USDT": 0.0, "gold": -5.0, "sp500": -18.0, "bonds": -8.0},
        {"interest_rates": 2.5, "usd_index": 8.0, "inflation": -1.0},
        "2022 Fed hiking cycle",
    ),
    Scenario(
        "GLOBAL_RECESSION",
        "Deep global recession triggers risk-off across all asset classes",
        365, 0.15, "macro",
        {"BTC": -50.0, "ETH": -60.0, "USDT": 0.0, "gold": 15.0, "sp500": -35.0, "bonds": 12.0},
        {"gdp_growth": -4.0, "unemployment": 5.0, "corporate_earnings": -25.0},
        "2008 GFC, 2020 COVID (initial phase)",
    ),
    Scenario(
        "DOLLAR_WEAKNESS",
        "USD reserve status erodes; BTC, gold, and real assets benefit",
        365, 0.10, "macro",
        {"BTC": 50.0, "ETH": 40.0, "USDT": -15.0, "gold": 20.0, "sp500": 5.0, "bonds": -15.0},
        {"usd_index": -20.0, "de_dollarization": 10.0},
        "1970s dollar collapse, BRICS de-dollarization trend",
    ),
    Scenario(
        "TECH_BREAKTHROUGH",
        "Lightning Network achieves mass adoption; Bitcoin transaction volumes up 500%",
        365, 0.15, "bitcoin",
        {"BTC": 80.0, "ETH": 30.0, "USDT": 0.0, "gold": 0.0, "sp500": 3.0, "bonds": 0.0},
        {"lightning_capacity": 500.0, "fee_revenue": 800.0},
        "Speculative: Lightning adoption S-curve",
    ),
    Scenario(
        "INSTITUTIONAL_ADOPTION",
        "Sovereign wealth funds and pension funds allocate 1-5% to Bitcoin",
        365, 0.20, "bitcoin",
        {"BTC": 100.0, "ETH": 80.0, "USDT": 0.0, "gold": 5.0, "sp500": 5.0, "bonds": -2.0},
        {"institutional_inflow": 500000000000, "etf_aum": 300.0},
        "BlackRock ETF approval 2024; Norway SWF precedent",
    ),
    Scenario(
        "MINING_CRISIS",
        "Geopolitical event or energy crisis disrupts 40% of global hashrate",
        90, 0.10, "bitcoin",
        {"BTC": -25.0, "ETH": -15.0, "USDT": 0.0, "gold": 8.0, "sp500": -3.0, "bonds": 2.0},
        {"hashrate": -40.0, "block_time": 40.0, "difficulty_adjustment": -35.0},
        "China mining ban 2021, Kazakhstan blackouts 2022",
    ),
    Scenario(
        "BLACK_SWAN",
        "Unknown catastrophic event simultaneously shocks all markets",
        90, 0.05, "black_swan",
        {"BTC": -60.0, "ETH": -70.0, "USDT": 5.0, "gold": -5.0, "sp500": -40.0, "bonds": 5.0},
        {"volatility_spike": 500.0, "correlation_to_1": True},
        "COVID March 2020, 9/11 market impact, Fukushima",
    ),
]

SCENARIO_DICT: dict[str, Scenario] = {s.name: s for s in PREDEFINED_SCENARIOS}


# ---------------------------------------------------------------------------
# ScenarioAnalyzer
# ---------------------------------------------------------------------------

class ScenarioAnalyzer:
    """
    Analyzes portfolio outcomes under various market scenarios.
    """

    def analyze_scenario(self, portfolio: dict, scenario_name: str = None,
                          custom_scenario: dict = None) -> dict:
        """
        Compute portfolio impact for a single scenario.

        Parameters
        ----------
        portfolio : {asset: {value_usd, allocation_pct}}
            or {asset: allocation_pct}
        scenario_name   : name of predefined scenario
        custom_scenario : custom scenario dict (overrides scenario_name)

        Returns
        -------
        dict with portfolio_impact_pct, asset_impacts, scenario details
        """
        if custom_scenario:
            scenario = Scenario(
                name=custom_scenario.get("name", "Custom"),
                description=custom_scenario.get("description", ""),
                duration_days=custom_scenario.get("duration_days", 30),
                probability=custom_scenario.get("probability", 0.0),
                category=custom_scenario.get("category", "custom"),
                asset_changes=custom_scenario.get("asset_changes", {}),
            )
        elif scenario_name and scenario_name in SCENARIO_DICT:
            scenario = SCENARIO_DICT[scenario_name]
        else:
            return {"error": f"Unknown scenario: {scenario_name}"}

        return self._compute_impact(portfolio, scenario)

    def run_stress_test(self, portfolio: dict,
                         scenarios: list[str] = None) -> dict:
        """
        Run portfolio through multiple scenarios and summarize results.

        Parameters
        ----------
        portfolio : portfolio dict
        scenarios : list of scenario names; None = all predefined

        Returns
        -------
        dict with results per scenario, worst case, best case, summary
        """
        if scenarios:
            scenario_list = [SCENARIO_DICT[s] for s in scenarios if s in SCENARIO_DICT]
        else:
            scenario_list = PREDEFINED_SCENARIOS

        results = {}
        for scenario in scenario_list:
            results[scenario.name] = self._compute_impact(portfolio, scenario)

        impacts = {k: v["portfolio_impact_pct"] for k, v in results.items()}
        worst_case = min(impacts, key=impacts.get)
        best_case  = max(impacts, key=impacts.get)

        expected_loss = _mean([v for v in impacts.values() if v < 0]) if any(v < 0 for v in impacts.values()) else 0
        expected_gain = _mean([v for v in impacts.values() if v > 0]) if any(v > 0 for v in impacts.values()) else 0

        return {
            "scenarios":        results,
            "worst_case":       {worst_case: results[worst_case]},
            "best_case":        {best_case:  results[best_case]},
            "avg_negative_impact_pct": round(expected_loss, 2),
            "avg_positive_impact_pct": round(expected_gain, 2),
            "n_scenarios_positive": sum(1 for v in impacts.values() if v >= 0),
            "n_scenarios_negative": sum(1 for v in impacts.values() if v < 0),
            "portfolio_resilience_score": self._resilience_score(impacts),
        }

    def sensitivity_analysis(self, portfolio: dict, variable: str,
                               range_pct: float = 50.0,
                               steps: int = 11) -> dict:
        """
        Vary a single asset or parameter and measure portfolio impact.

        Parameters
        ----------
        portfolio  : portfolio dict
        variable   : asset name (e.g. 'BTC') or macro variable
        range_pct  : total range to vary (e.g. 50 = ±25% each side)
        steps      : number of data points

        Returns
        -------
        dict with sensitivity curve
        """
        half   = range_pct / 2
        step_size = range_pct / (steps - 1) if steps > 1 else range_pct
        results = []

        total_value = self._portfolio_value(portfolio)
        if total_value == 0:
            return {"error": "Portfolio has no value"}

        for i in range(steps):
            change_pct = -half + i * step_size
            # Apply change to the variable (asset)
            new_value = 0.0
            for asset, data in portfolio.items():
                if isinstance(data, dict):
                    asset_value = data.get("value_usd", 0)
                    alloc = data.get("allocation_pct", 0) / 100
                else:
                    asset_value = float(data) / 100 * total_value
                    alloc = float(data) / 100

                if asset.upper() == variable.upper():
                    new_value += asset_value * (1 + change_pct / 100)
                else:
                    new_value += asset_value

            impact_pct = _pct(total_value, new_value)
            results.append({
                "variable_change_pct": round(change_pct, 2),
                "portfolio_impact_pct": round(impact_pct, 4),
                "new_portfolio_value":  round(new_value, 2),
            })

        # Compute sensitivity coefficient (impact per 1% change in variable)
        btc_alloc = 0.0
        for asset, data in portfolio.items():
            if asset.upper() == variable.upper():
                if isinstance(data, dict):
                    btc_alloc = data.get("allocation_pct", 0) / 100
                else:
                    btc_alloc = float(data) / 100
        sensitivity_coef = btc_alloc  # for 1% change in variable, portfolio moves alloc%

        return {
            "variable":            variable,
            "range_pct":           range_pct,
            "sensitivity_curve":   results,
            "sensitivity_coefficient": round(sensitivity_coef, 4),
            "portfolio_value":     round(total_value, 2),
            "note": (f"A 1% change in {variable} results in approximately "
                     f"{sensitivity_coef*100:.2f}% change in portfolio value."),
        }

    def what_if_analysis(self, portfolio: dict, changes: dict) -> dict:
        """
        Apply a set of custom changes to the portfolio and compute impact.

        Parameters
        ----------
        portfolio : {asset: {value_usd, allocation_pct}}
        changes   : {asset: pct_change}

        Returns
        -------
        dict with new portfolio values, total impact
        """
        total_value = self._portfolio_value(portfolio)
        new_values  = {}
        asset_impacts = {}

        for asset, data in portfolio.items():
            if isinstance(data, dict):
                original_value = data.get("value_usd", 0)
            else:
                original_value = float(data) / 100 * total_value

            change_pct = changes.get(asset, changes.get(asset.upper(), 0))
            new_value  = _apply_change(original_value, change_pct)
            new_values[asset]   = round(new_value, 2)
            asset_impacts[asset] = {
                "original_value":  round(original_value, 2),
                "change_pct":      change_pct,
                "new_value":       round(new_value, 2),
                "pnl":             round(new_value - original_value, 2),
            }

        new_total   = sum(new_values.values())
        total_pnl   = new_total - total_value
        total_impact = _pct(total_value, new_total)

        return {
            "original_value":    round(total_value, 2),
            "new_value":         round(new_total, 2),
            "total_pnl":         round(total_pnl, 2),
            "total_impact_pct":  round(total_impact, 4),
            "asset_impacts":     asset_impacts,
            "applied_changes":   changes,
        }

    def breakeven_analysis(self, portfolio: dict,
                            target_return: float = 0.0) -> dict:
        """
        Determine the minimum BTC price change required to achieve
        the target portfolio return.

        Parameters
        ----------
        portfolio      : portfolio dict
        target_return  : target total portfolio return % (default 0 = breakeven)

        Returns
        -------
        dict with required BTC price change, current BTC allocation impact
        """
        total_value = self._portfolio_value(portfolio)
        if total_value == 0:
            return {"error": "Portfolio has no value"}

        # Find BTC allocation
        btc_alloc = 0.0
        for asset, data in portfolio.items():
            if asset.upper() == "BTC":
                if isinstance(data, dict):
                    btc_alloc = data.get("allocation_pct", 0) / 100
                else:
                    btc_alloc = float(data) / 100

        if btc_alloc == 0:
            return {"error": "No BTC in portfolio", "target_return_pct": target_return}

        # target_return = btc_alloc * btc_change + (1-btc_alloc) * other_change
        # Assume other assets are flat (worst-case)
        required_btc_change = target_return / btc_alloc if btc_alloc > 0 else 0

        current_btc_price = 65_000  # approximate

        return {
            "target_return_pct":     target_return,
            "btc_allocation_pct":    round(btc_alloc * 100, 2),
            "required_btc_change_pct": round(required_btc_change, 2),
            "required_btc_price":    round(current_btc_price * (1 + required_btc_change / 100), 2),
            "current_btc_price_estimate": current_btc_price,
            "interpretation": (
                f"BTC must move {required_btc_change:+.2f}% to achieve "
                f"{target_return:+.2f}% portfolio return (all else equal)."
            ),
        }

    def get_scenario_list(self) -> list[dict]:
        """Return all predefined scenarios as a list."""
        return [s.to_dict() for s in PREDEFINED_SCENARIOS]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_impact(portfolio: dict, scenario: Scenario) -> dict:
        """Apply scenario asset changes to portfolio."""
        total_value = ScenarioAnalyzer._portfolio_value(portfolio)
        if total_value == 0:
            return {"portfolio_impact_pct": 0.0, "scenario": scenario.name}

        new_total     = 0.0
        asset_impacts = {}

        for asset, data in portfolio.items():
            if isinstance(data, dict):
                asset_value = data.get("value_usd", 0)
                alloc_pct   = data.get("allocation_pct", 0)
            else:
                alloc_pct   = float(data)
                asset_value = alloc_pct / 100 * total_value

            # Find scenario change for this asset
            change_pct = (
                scenario.asset_changes.get(asset.upper())
                or scenario.asset_changes.get(asset)
                or (scenario.asset_changes.get("BTC", 0) * 0.7 if asset.upper() not in ("USDT","USD","USDC","BUSD") else 0)
            )

            new_value = _apply_change(asset_value, change_pct)
            new_total += new_value

            asset_impacts[asset] = {
                "allocation_pct":  round(alloc_pct, 2),
                "original_value":  round(asset_value, 2),
                "change_pct":      change_pct,
                "new_value":       round(new_value, 2),
                "contribution_pct": round(alloc_pct / 100 * change_pct, 4),
            }

        portfolio_impact = _pct(total_value, new_total)
        value_at_risk    = max(total_value - new_total, 0)

        return {
            "scenario":              scenario.name,
            "description":           scenario.description,
            "category":              scenario.category,
            "duration_days":         scenario.duration_days,
            "annual_probability":    scenario.probability,
            "portfolio_impact_pct":  round(portfolio_impact, 4),
            "original_value":        round(total_value, 2),
            "new_value":             round(new_total, 2),
            "absolute_pnl":          round(new_total - total_value, 2),
            "value_at_risk":         round(value_at_risk, 2),
            "asset_impacts":         asset_impacts,
            "historical_analog":     scenario.historical_analog,
        }

    @staticmethod
    def _portfolio_value(portfolio: dict) -> float:
        """Extract total portfolio value."""
        total = 0.0
        for asset, data in portfolio.items():
            if isinstance(data, dict):
                total += data.get("value_usd", 0)
            else:
                # If just allocation %, assume $10,000 base
                total = 10_000.0
                break
        return total

    @staticmethod
    def _resilience_score(impacts: dict) -> float:
        """
        Score 0–100: resilience of portfolio against scenario set.
        Higher = fewer/smaller negative impacts.
        """
        if not impacts:
            return 50.0
        positive = sum(1 for v in impacts.values() if v >= 0)
        small_loss = sum(1 for v in impacts.values() if -10 <= v < 0)
        large_loss = sum(1 for v in impacts.values() if v < -10)
        n = len(impacts)
        score = (positive * 2 + small_loss * 1) / (n * 2) * 100
        return round(score, 1)
