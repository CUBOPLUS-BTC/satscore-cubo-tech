"""
Monte Carlo simulation engine for Magma Bitcoin app.

Provides price path simulation, portfolio growth, retirement planning,
savings goal analysis, probability of ruin, and DCA outcome projection.

All randomness uses Python's built-in random module with Box-Muller
transform for normally distributed samples. No third-party deps.
"""

import math
import random
import time
from typing import Optional


# ---------------------------------------------------------------------------
# Statistical utilities
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
    return s[-1] if hi >= n else s[lo] * (1 - frac) + s[hi] * frac


def _box_muller(mu: float = 0.0, sigma: float = 1.0) -> float:
    """Generate normal random number via Box-Muller transform."""
    u1 = random.random()
    u2 = random.random()
    if u1 < 1e-15:
        u1 = 1e-15
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return mu + sigma * z


def _t_sample(df: int) -> float:
    """Student-t sample using ratio of normals (df > 2)."""
    z = _box_muller()
    chi2 = sum(_box_muller() ** 2 for _ in range(df))
    return z / math.sqrt(chi2 / df)


# ---------------------------------------------------------------------------
# MonteCarloEngine
# ---------------------------------------------------------------------------

class MonteCarloEngine:
    """
    Monte Carlo simulation engine for financial projections.

    Supports:
        - Bitcoin price path simulation (GBM)
        - Portfolio growth with periodic contributions
        - Retirement goal analysis
        - Savings goal probability
        - Probability of ruin analysis
        - DCA outcome distribution
    """

    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)

    # ------------------------------------------------------------------
    # Price path simulation
    # ------------------------------------------------------------------

    def simulate_price_path(self, current_price: float,
                              volatility: float,
                              drift: float,
                              days: int,
                              n_paths: int = 500) -> dict:
        """
        Simulate Bitcoin price paths using Geometric Brownian Motion.

        Parameters
        ----------
        current_price : current BTC price in USD
        volatility    : annualised volatility (e.g. 0.70 = 70%)
        drift         : expected annualised return (e.g. 0.50 = 50%)
        days          : simulation horizon in days
        n_paths       : number of Monte Carlo paths

        Returns
        -------
        dict with percentile_paths, final_distribution,
        probability metrics, and summary
        """
        dt        = 1 / 365.0
        daily_mu  = (drift - 0.5 * volatility ** 2) * dt
        daily_sig = volatility * math.sqrt(dt)

        final_prices = []
        # Store sampled paths for percentile bands
        stored_paths  = []
        n_store       = min(n_paths, 200)

        for sim in range(n_paths):
            price = current_price
            path  = [price]
            for _ in range(days):
                z     = _box_muller()
                price = price * math.exp(daily_mu + daily_sig * z)
                path.append(round(price, 2))
            final_prices.append(price)
            if sim < n_store:
                stored_paths.append(path)

        # Sample points for chart (every 7 days)
        step   = max(days // 50, 1)
        sample_days = list(range(0, days + 1, step))

        pct_paths = {}
        for pct in [5, 25, 50, 75, 95]:
            pct_series = []
            for idx in sample_days:
                day_vals = [stored_paths[s][idx] for s in range(n_store)
                            if idx < len(stored_paths[s])]
                pct_series.append(round(_percentile(day_vals, pct), 2))
            pct_paths[pct] = pct_series

        summary = self._summarize_results(final_prices)

        prob_above_current = sum(1 for p in final_prices if p > current_price) / n_paths * 100
        prob_2x            = sum(1 for p in final_prices if p >= current_price * 2) / n_paths * 100
        prob_10x           = sum(1 for p in final_prices if p >= current_price * 10) / n_paths * 100
        prob_halved        = sum(1 for p in final_prices if p <= current_price * 0.5) / n_paths * 100

        return {
            "current_price":       current_price,
            "horizon_days":        days,
            "n_paths":             n_paths,
            "annualised_drift":    round(drift, 4),
            "annualised_vol":      round(volatility, 4),
            "final_distribution":  summary,
            "percentile_paths":    pct_paths,
            "sample_days":         sample_days,
            "probabilities": {
                "above_current_pct": round(prob_above_current, 2),
                "2x_pct":            round(prob_2x, 2),
                "10x_pct":           round(prob_10x, 2),
                "halved_pct":        round(prob_halved, 2),
            },
            "simulated_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # Portfolio growth simulation
    # ------------------------------------------------------------------

    def simulate_portfolio_growth(self, initial: float,
                                   contributions: float,
                                   returns_dist: dict,
                                   years: int,
                                   n_sims: int = 1000) -> dict:
        """
        Simulate portfolio growth with periodic contributions.

        Parameters
        ----------
        initial       : starting portfolio value in USD
        contributions : monthly contribution in USD
        returns_dist  : {mean: float, std: float, distribution: str}
                        distribution: 'normal' | 'lognormal' | 't'
        years         : projection horizon
        n_sims        : number of simulations

        Returns
        -------
        dict with percentile outcomes at each year,
        final value distribution, and probability metrics
        """
        months      = years * 12
        mean        = returns_dist.get("mean", 0.50)       # annual return
        std         = returns_dist.get("std", 0.70)        # annual vol
        distribution = returns_dist.get("distribution", "lognormal")
        monthly_mean = mean / 12
        monthly_std  = std / math.sqrt(12)

        final_values    = []
        yearly_snapshots = [[] for _ in range(years + 1)]

        for _ in range(n_sims):
            value = initial
            yearly_snapshots[0].append(value)
            year_counter = 0
            month_counter = 0

            for m in range(1, months + 1):
                r = self._generate_return(monthly_mean, monthly_std, distribution)
                value = value * (1 + r) + contributions
                value = max(value, 0)  # can't go negative

                if m % 12 == 0:
                    year_counter += 1
                    if year_counter <= years:
                        yearly_snapshots[year_counter].append(value)

            final_values.append(value)

        # Compute percentiles at each year
        yearly_percentiles = {}
        for yr in range(years + 1):
            snap = yearly_snapshots[yr]
            if snap:
                yearly_percentiles[yr] = {
                    "p5":    round(_percentile(snap, 5), 2),
                    "p25":   round(_percentile(snap, 25), 2),
                    "p50":   round(_percentile(snap, 50), 2),
                    "p75":   round(_percentile(snap, 75), 2),
                    "p95":   round(_percentile(snap, 95), 2),
                    "mean":  round(_mean(snap), 2),
                }

        total_contributions = initial + contributions * months
        summary = self._summarize_results(final_values)
        prob_positive = sum(1 for v in final_values if v > total_contributions) / n_sims * 100

        return {
            "initial_value":       initial,
            "monthly_contribution": contributions,
            "horizon_years":        years,
            "n_simulations":        n_sims,
            "returns_distribution": returns_dist,
            "total_contributed":    round(total_contributions, 2),
            "final_distribution":   summary,
            "yearly_percentiles":   yearly_percentiles,
            "probability_of_gain_pct": round(prob_positive, 2),
        }

    # ------------------------------------------------------------------
    # Retirement simulation
    # ------------------------------------------------------------------

    def simulate_retirement(self, params: dict, n_sims: int = 1000) -> dict:
        """
        Retirement planning Monte Carlo simulation.

        Parameters
        ----------
        params : {
            current_age          : int
            retirement_age       : int
            life_expectancy      : int
            current_savings      : float (USD)
            monthly_contribution : float
            monthly_expenses     : float (retirement withdrawals)
            btc_allocation_pct   : float (0–100)
            expected_btc_return  : float (annual, e.g. 0.40)
            btc_volatility       : float (e.g. 0.70)
            expected_trad_return : float (non-BTC annual return)
            trad_volatility      : float
            inflation_rate       : float (e.g. 0.03)
        }

        Returns
        -------
        dict with probability of success, ruin, final wealth distribution
        """
        current_age          = int(params.get("current_age", 30))
        retirement_age       = int(params.get("retirement_age", 65))
        life_expectancy      = int(params.get("life_expectancy", 85))
        current_savings      = float(params.get("current_savings", 10000))
        monthly_contribution = float(params.get("monthly_contribution", 500))
        monthly_expenses     = float(params.get("monthly_expenses", 3000))
        btc_alloc            = float(params.get("btc_allocation_pct", 20)) / 100
        btc_ret              = float(params.get("expected_btc_return", 0.40))
        btc_vol              = float(params.get("btc_volatility", 0.70))
        trad_ret             = float(params.get("expected_trad_return", 0.07))
        trad_vol             = float(params.get("trad_volatility", 0.15))
        inflation            = float(params.get("inflation_rate", 0.03))

        accum_years   = max(retirement_age - current_age, 1)
        withdraw_years = max(life_expectancy - retirement_age, 1)
        accum_months   = accum_years * 12
        withdraw_months = withdraw_years * 12

        # Blended portfolio parameters
        blended_ret = btc_alloc * btc_ret + (1 - btc_alloc) * trad_ret
        blended_vol = math.sqrt(btc_alloc ** 2 * btc_vol ** 2 +
                                (1 - btc_alloc) ** 2 * trad_vol ** 2)
        monthly_mean = blended_ret / 12
        monthly_std  = blended_vol / math.sqrt(12)

        success_count   = 0
        ruin_count      = 0
        final_values    = []
        ruin_ages       = []

        for _ in range(n_sims):
            value = current_savings

            # Accumulation phase
            for _ in range(accum_months):
                r = self._generate_return(monthly_mean, monthly_std, "lognormal")
                value = max(value * (1 + r) + monthly_contribution, 0)

            retirement_balance = value

            # Withdrawal phase — inflation-adjusted withdrawals
            ruined = False
            ruin_month = None
            for m in range(withdraw_months):
                inflation_adj = (1 + inflation) ** (m / 12)
                withdrawal = monthly_expenses * inflation_adj
                r = self._generate_return(monthly_mean * 0.6, monthly_std * 0.8, "lognormal")
                value = value * (1 + r) - withdrawal

                if value <= 0:
                    ruined = True
                    ruin_month = m
                    ruin_age = retirement_age + m / 12
                    ruin_ages.append(ruin_age)
                    break

            if ruined:
                ruin_count += 1
                final_values.append(0)
            else:
                success_count += 1
                final_values.append(max(value, 0))

        success_rate = success_count / n_sims * 100
        ruin_rate    = ruin_count   / n_sims * 100
        avg_ruin_age = _mean(ruin_ages) if ruin_ages else None

        summary = self._summarize_results([v for v in final_values if v > 0])

        return {
            "input_params":         params,
            "n_simulations":        n_sims,
            "success_rate_pct":     round(success_rate, 2),
            "ruin_rate_pct":        round(ruin_rate, 2),
            "avg_ruin_age":         round(avg_ruin_age, 1) if avg_ruin_age else None,
            "retirement_balance_estimate": {
                "p5":  round(_percentile([retirement_balance], 5), 2),
                "p50": round(retirement_balance, 2),
            },
            "final_wealth_distribution": summary,
            "blended_portfolio": {
                "expected_annual_return": round(blended_ret, 4),
                "annual_volatility":      round(blended_vol, 4),
            },
            "recommendation": (
                "Your plan appears sustainable." if success_rate >= 80
                else "Consider increasing contributions or reducing expenses."
            ),
        }

    # ------------------------------------------------------------------
    # Savings goal simulation
    # ------------------------------------------------------------------

    def simulate_savings_goal(self, target: float,
                               monthly: float,
                               years: int,
                               return_dist: dict,
                               n_sims: int = 1000) -> dict:
        """
        Simulate the probability of reaching a savings target.

        Parameters
        ----------
        target      : target savings amount in USD
        monthly     : monthly contribution
        years       : time horizon
        return_dist : {mean, std, distribution}

        Returns
        -------
        dict with probability of reaching goal, median time to goal,
        and percentile outcomes
        """
        mean         = return_dist.get("mean", 0.30)
        std          = return_dist.get("std", 0.60)
        distribution = return_dist.get("distribution", "lognormal")
        monthly_mean = mean / 12
        monthly_std  = std / math.sqrt(12)
        months       = years * 12

        reached_count   = 0
        time_to_goal    = []
        final_values    = []

        for _ in range(n_sims):
            value   = 0.0
            reached = False
            for m in range(1, months + 1):
                r = self._generate_return(monthly_mean, monthly_std, distribution)
                value = max(value * (1 + r) + monthly, 0)
                if value >= target and not reached:
                    reached = True
                    time_to_goal.append(m / 12)  # years to goal
                    reached_count += 1
            final_values.append(value)

        prob_reached    = reached_count / n_sims * 100
        median_time     = _percentile(time_to_goal, 50) if time_to_goal else None
        total_deposited = monthly * months

        return {
            "target_usd":            target,
            "monthly_contribution":  monthly,
            "horizon_years":         years,
            "n_simulations":         n_sims,
            "returns_distribution":  return_dist,
            "total_deposited":       round(total_deposited, 2),
            "probability_reached_pct": round(prob_reached, 2),
            "median_years_to_goal":  round(median_time, 1) if median_time else None,
            "fastest_years":         round(min(time_to_goal), 1) if time_to_goal else None,
            "final_value_distribution": self._summarize_results(final_values),
        }

    # ------------------------------------------------------------------
    # Probability of ruin
    # ------------------------------------------------------------------

    def probability_of_ruin(self, portfolio_value: float,
                              monthly_withdrawals: float,
                              returns_dist: dict,
                              years: int,
                              n_sims: int = 1000) -> dict:
        """
        Calculate probability that portfolio is depleted within `years`.

        Parameters
        ----------
        portfolio_value   : starting portfolio
        monthly_withdrawals: fixed monthly withdrawal
        returns_dist       : {mean, std, distribution}
        years              : horizon to test

        Returns
        -------
        dict with ruin_probability_pct, safe_withdrawal_rate,
        median_depletion_year if ruin common
        """
        mean         = returns_dist.get("mean", 0.07)
        std          = returns_dist.get("std", 0.15)
        distribution = returns_dist.get("distribution", "normal")
        monthly_mean = mean / 12
        monthly_std  = std / math.sqrt(12)
        months       = years * 12

        ruin_count      = 0
        depletion_years = []
        final_values    = []

        for _ in range(n_sims):
            value  = portfolio_value
            ruined = False
            for m in range(1, months + 1):
                r = self._generate_return(monthly_mean, monthly_std, distribution)
                value = value * (1 + r) - monthly_withdrawals
                if value <= 0:
                    ruined = True
                    depletion_years.append(m / 12)
                    ruin_count += 1
                    break
            if not ruined:
                final_values.append(max(value, 0))
            else:
                final_values.append(0)

        ruin_pct = ruin_count / n_sims * 100

        # Safe withdrawal rate: monthly withdrawal as % of portfolio
        swr_monthly_pct = (monthly_withdrawals / portfolio_value * 100) if portfolio_value else 0
        swr_annual_pct  = swr_monthly_pct * 12

        # 4% rule check
        safe_4pct_monthly = portfolio_value * 0.04 / 12

        return {
            "portfolio_value":        portfolio_value,
            "monthly_withdrawal":     monthly_withdrawals,
            "annual_withdrawal":      monthly_withdrawals * 12,
            "horizon_years":          years,
            "n_simulations":          n_sims,
            "returns_distribution":   returns_dist,
            "ruin_probability_pct":   round(ruin_pct, 2),
            "withdrawal_rate_annual_pct": round(swr_annual_pct, 2),
            "is_sustainable": ruin_pct < 5.0,
            "classic_4pct_monthly":   round(safe_4pct_monthly, 2),
            "median_depletion_year":  round(_percentile(depletion_years, 50), 1) if depletion_years else None,
            "final_value_distribution": self._summarize_results(final_values),
        }

    # ------------------------------------------------------------------
    # DCA outcomes
    # ------------------------------------------------------------------

    def simulate_dca_outcomes(self, amount: float,
                               frequency: str,
                               price_model: dict,
                               years: int,
                               n_sims: int = 1000) -> dict:
        """
        Simulate DCA strategy outcomes under uncertain price paths.

        Parameters
        ----------
        amount     : USD per purchase
        frequency  : 'daily' | 'weekly' | 'monthly'
        price_model: {initial_price, drift, volatility}
        years      : simulation horizon
        n_sims     : number of Monte Carlo paths

        Returns
        -------
        dict with total_btc, portfolio_value, ROI distributions
        """
        freq_per_year = {"daily": 365, "weekly": 52, "monthly": 12}
        periods_per_year = freq_per_year.get(frequency, 12)
        total_periods = years * periods_per_year

        initial_price = float(price_model.get("initial_price", 65_000))
        drift         = float(price_model.get("drift", 0.40))
        vol           = float(price_model.get("volatility", 0.70))

        dt        = 1 / periods_per_year
        daily_mu  = (drift - 0.5 * vol ** 2) * dt
        daily_sig = vol * math.sqrt(dt)

        total_invested   = amount * total_periods
        final_values     = []
        total_btc_list   = []
        roi_list         = []

        for _ in range(n_sims):
            price     = initial_price
            total_btc = 0.0
            for _ in range(total_periods):
                if price > 0:
                    total_btc += amount / price
                z     = _box_muller()
                price = price * math.exp(daily_mu + daily_sig * z)
                price = max(price, 1.0)

            final_value = total_btc * price
            roi         = (final_value - total_invested) / total_invested * 100

            final_values.append(final_value)
            total_btc_list.append(total_btc)
            roi_list.append(roi)

        return {
            "strategy":          "DCA",
            "frequency":         frequency,
            "amount_per_period": amount,
            "horizon_years":     years,
            "total_invested":    round(total_invested, 2),
            "n_simulations":     n_sims,
            "price_model":       price_model,
            "final_value_distribution": self._summarize_results(final_values),
            "total_btc_distribution": {
                "mean":   round(_mean(total_btc_list), 6),
                "p5":     round(_percentile(total_btc_list, 5), 6),
                "p50":    round(_percentile(total_btc_list, 50), 6),
                "p95":    round(_percentile(total_btc_list, 95), 6),
            },
            "roi_distribution": {
                "mean_pct":   round(_mean(roi_list), 2),
                "p5_pct":     round(_percentile(roi_list, 5), 2),
                "p50_pct":    round(_percentile(roi_list, 50), 2),
                "p95_pct":    round(_percentile(roi_list, 95), 2),
            },
            "probability_profitable_pct": round(
                sum(1 for r in roi_list if r > 0) / n_sims * 100, 2
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_returns(self, mean: float, std: float, n: int,
                           distribution: str = "normal") -> list[float]:
        """Generate n return samples from specified distribution."""
        if distribution == "normal":
            return [_box_muller(mean, std) for _ in range(n)]
        elif distribution == "lognormal":
            # Parameters for lognormal: mu and sigma of log-returns
            sigma2 = math.log(1 + (std / (mean + 1e-10)) ** 2) if mean + std != 0 else std ** 2
            mu_ln  = math.log(1 + mean) - 0.5 * sigma2
            sig_ln = math.sqrt(sigma2)
            return [math.exp(_box_muller(mu_ln, sig_ln)) - 1 for _ in range(n)]
        elif distribution == "t":
            df = 5
            samples = []
            for _ in range(n):
                t = _t_sample(df)
                samples.append(mean + std * t)
            return samples
        else:
            return [_box_muller(mean, std) for _ in range(n)]

    def _generate_return(self, mean: float, std: float,
                          distribution: str = "normal") -> float:
        """Generate a single return sample."""
        if distribution == "normal":
            return _box_muller(mean, std)
        elif distribution == "lognormal":
            if std == 0:
                return mean
            sigma2 = math.log(1 + (std / (abs(mean) + 1e-10)) ** 2)
            mu_ln  = math.log(1 + mean) - 0.5 * sigma2
            sig_ln = math.sqrt(abs(sigma2))
            return math.exp(_box_muller(mu_ln, sig_ln)) - 1
        elif distribution == "t":
            return mean + std * _t_sample(5)
        return _box_muller(mean, std)

    @staticmethod
    def _calculate_percentiles(paths: list, percentiles: list) -> dict:
        """Compute given percentiles for a list of final values."""
        result = {}
        for p in percentiles:
            result[f"p{p}"] = round(_percentile(paths, p), 2)
        return result

    @staticmethod
    def _summarize_results(final_values: list) -> dict:
        """Standard summary statistics for a list of final simulation values."""
        if not final_values:
            return {}
        return {
            "mean":   round(_mean(final_values), 2),
            "median": round(_percentile(final_values, 50), 2),
            "std":    round(_stddev(final_values), 2),
            "min":    round(min(final_values), 2),
            "max":    round(max(final_values), 2),
            "p5":     round(_percentile(final_values, 5), 2),
            "p10":    round(_percentile(final_values, 10), 2),
            "p25":    round(_percentile(final_values, 25), 2),
            "p75":    round(_percentile(final_values, 75), 2),
            "p90":    round(_percentile(final_values, 90), 2),
            "p95":    round(_percentile(final_values, 95), 2),
            "count":  len(final_values),
        }
