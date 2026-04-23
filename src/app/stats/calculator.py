"""Pure-stdlib statistical analysis engine for Bitcoin data.

``StatisticsCalculator`` provides descriptive statistics, correlation,
regression, time-series smoothing, hypothesis tests, and distribution
fitting.  Every computation uses only Python's standard library (math,
statistics, itertools) — no numpy, scipy, or pandas.

Bitcoin-specific context
------------------------
All methods are generic but are designed for the types of data common in
Bitcoin analytics:
  - Price time-series (USD/BTC)
  - On-chain metrics (hash rate, difficulty, UTXO count, etc.)
  - Savings accumulation data (sats over time)
  - Fee rate distributions
  - Network activity metrics
"""

from __future__ import annotations

import math
import statistics
from typing import Callable


class StatisticsCalculator:
    """Comprehensive statistical analysis for Bitcoin-related numerical data.

    All methods are pure functions: they accept lists of floats and return
    dicts or lists.  No state is stored between calls.  Raise ``ValueError``
    for invalid inputs (empty lists, mismatched lengths, etc.).
    """

    # =========================================================================
    # D E S C R I P T I V E   S T A T I S T I C S
    # =========================================================================

    def descriptive_stats(self, data: list[float]) -> dict:
        """Compute a comprehensive descriptive statistics summary.

        Metrics computed
        ----------------
        mean, median, mode, std (population), variance (population),
        std_sample (sample), variance_sample, skewness, kurtosis (excess),
        minimum, maximum, range, sum, count, iqr (interquartile range),
        q1, q3, percentile_5, percentile_95, coefficient_of_variation,
        geometric_mean, harmonic_mean.

        Parameters
        ----------
        data : Non-empty list of numbers.

        Returns
        -------
        dict with all computed statistics.

        Raises
        ------
        ValueError : If data is empty or contains non-numeric values.
        """
        data = self._validate_data(data, min_length=1, name="data")
        n = len(data)
        sorted_data = sorted(data)

        mean = statistics.mean(data)
        median = statistics.median(data)

        try:
            mode = statistics.mode(data)
        except statistics.StatisticsError:
            mode = None  # No unique mode

        # Population std / variance
        if n > 1:
            variance_pop = statistics.pvariance(data)
            std_pop = statistics.pstdev(data)
            variance_sample = statistics.variance(data)
            std_sample = statistics.stdev(data)
        else:
            variance_pop = 0.0
            std_pop = 0.0
            variance_sample = 0.0
            std_sample = 0.0

        minimum = sorted_data[0]
        maximum = sorted_data[-1]
        data_range = maximum - minimum
        data_sum = sum(data)

        # Percentiles (linear interpolation)
        q1 = self._percentile(sorted_data, 25)
        q3 = self._percentile(sorted_data, 75)
        iqr = q3 - q1
        p5 = self._percentile(sorted_data, 5)
        p95 = self._percentile(sorted_data, 95)

        # Coefficient of variation
        cv = (std_sample / mean * 100) if mean != 0 else None

        # Geometric mean (only valid for positive data)
        try:
            geo_mean = statistics.geometric_mean(data) if all(x > 0 for x in data) else None
        except (AttributeError, statistics.StatisticsError):
            # geometric_mean added in Python 3.8; compute manually
            if all(x > 0 for x in data):
                log_sum = sum(math.log(x) for x in data)
                geo_mean = math.exp(log_sum / n)
            else:
                geo_mean = None

        # Harmonic mean (only valid for positive data)
        try:
            h_mean = statistics.harmonic_mean(data) if all(x > 0 for x in data) else None
        except (AttributeError, statistics.StatisticsError):
            if all(x > 0 for x in data):
                h_mean = n / sum(1.0 / x for x in data)
            else:
                h_mean = None

        # Skewness (Fisher's moment coefficient)
        skewness = self._skewness(data, mean, std_pop) if std_pop > 0 else 0.0

        # Excess kurtosis
        kurtosis = self._kurtosis(data, mean, std_pop) if std_pop > 0 else 0.0

        return {
            "count": n,
            "mean": round(mean, 8),
            "median": round(median, 8),
            "mode": round(mode, 8) if mode is not None else None,
            "std": round(std_pop, 8),
            "std_sample": round(std_sample, 8),
            "variance": round(variance_pop, 8),
            "variance_sample": round(variance_sample, 8),
            "skewness": round(skewness, 8),
            "kurtosis": round(kurtosis, 8),
            "min": round(minimum, 8),
            "max": round(maximum, 8),
            "range": round(data_range, 8),
            "sum": round(data_sum, 8),
            "q1": round(q1, 8),
            "q3": round(q3, 8),
            "iqr": round(iqr, 8),
            "percentile_5": round(p5, 8),
            "percentile_95": round(p95, 8),
            "coefficient_of_variation_pct": round(cv, 4) if cv is not None else None,
            "geometric_mean": round(geo_mean, 8) if geo_mean is not None else None,
            "harmonic_mean": round(h_mean, 8) if h_mean is not None else None,
        }

    # =========================================================================
    # C O R R E L A T I O N   A N D   C O V A R I A N C E
    # =========================================================================

    def correlation(self, x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient between x and y.

        Returns a value in [-1, 1].  1 = perfect positive linear correlation,
        -1 = perfect negative, 0 = no linear correlation.

        Parameters
        ----------
        x, y : Equal-length non-empty lists of numbers.

        Returns
        -------
        Pearson r as a float, rounded to 8 decimal places.
        """
        x, y = self._validate_paired(x, y)
        n = len(x)
        if n < 2:
            raise ValueError("Correlation requires at least 2 data points.")

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if denom_x == 0 or denom_y == 0:
            return 0.0  # Constant series has no correlation

        r = numerator / (denom_x * denom_y)
        return round(max(-1.0, min(1.0, r)), 8)  # Clamp for floating-point safety

    def covariance(self, x: list[float], y: list[float]) -> float:
        """Compute sample covariance between x and y.

        Parameters
        ----------
        x, y : Equal-length lists with at least 2 elements.

        Returns
        -------
        Sample covariance as a float.
        """
        x, y = self._validate_paired(x, y)
        n = len(x)
        if n < 2:
            raise ValueError("Covariance requires at least 2 data points.")

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (n - 1)
        return round(cov, 8)

    def spearman_correlation(self, x: list[float], y: list[float]) -> float:
        """Compute Spearman rank correlation coefficient.

        More robust than Pearson for non-linear monotonic relationships
        and for data with outliers (common in Bitcoin price series).

        Parameters
        ----------
        x, y : Equal-length non-empty lists.

        Returns
        -------
        Spearman rho in [-1, 1].
        """
        x, y = self._validate_paired(x, y)
        n = len(x)
        if n < 2:
            raise ValueError("Spearman correlation requires at least 2 points.")

        rank_x = self._rank(x)
        rank_y = self._rank(y)
        return self.correlation(rank_x, rank_y)

    # =========================================================================
    # R E G R E S S I O N
    # =========================================================================

    def linear_regression(self, x: list[float], y: list[float]) -> dict:
        """Compute ordinary least-squares (OLS) linear regression.

        Fits y = slope * x + intercept and computes standard diagnostics.

        Parameters
        ----------
        x : Independent variable (e.g., time index, block height).
        y : Dependent variable (e.g., price, hash rate).

        Returns
        -------
        dict with: slope, intercept, r_squared, adjusted_r_squared,
        std_error_slope, std_error_intercept, t_stat_slope, residuals,
        predicted, mae, mse, rmse.
        """
        x, y = self._validate_paired(x, y)
        n = len(x)
        if n < 2:
            raise ValueError("Linear regression requires at least 2 data points.")

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        ss_xx = sum((xi - mean_x) ** 2 for xi in x)
        ss_yy = sum((yi - mean_y) ** 2 for yi in y)

        if ss_xx == 0:
            raise ValueError("x is constant — regression is undefined.")

        slope = ss_xy / ss_xx
        intercept = mean_y - slope * mean_x

        predicted = [slope * xi + intercept for xi in x]
        residuals = [yi - yhat for yi, yhat in zip(y, predicted)]

        ss_res = sum(r ** 2 for r in residuals)
        ss_tot = ss_yy if ss_yy != 0 else 1e-12

        r_squared = 1.0 - ss_res / ss_tot
        adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / max(n - 2, 1)

        # Standard errors
        mse = ss_res / max(n - 2, 1)
        rmse = math.sqrt(mse)
        se_slope = math.sqrt(mse / ss_xx) if ss_xx > 0 else 0.0
        se_intercept = math.sqrt(mse * sum(xi ** 2 for xi in x) / (n * ss_xx)) if ss_xx > 0 else 0.0

        t_stat_slope = slope / se_slope if se_slope > 0 else float("inf")

        mae = sum(abs(r) for r in residuals) / n

        return {
            "slope": round(slope, 10),
            "intercept": round(intercept, 10),
            "r_squared": round(r_squared, 8),
            "adjusted_r_squared": round(adj_r_squared, 8),
            "std_error_slope": round(se_slope, 10),
            "std_error_intercept": round(se_intercept, 10),
            "t_stat_slope": round(t_stat_slope, 6),
            "mae": round(mae, 8),
            "mse": round(mse, 8),
            "rmse": round(rmse, 8),
            "n": n,
            "predicted": [round(p, 6) for p in predicted],
            "residuals": [round(r, 8) for r in residuals],
        }

    def log_linear_regression(self, x: list[float], y: list[float]) -> dict:
        """Fit a log-linear regression: log(y) = slope * x + intercept.

        Useful for Bitcoin price which often displays exponential growth.
        Requires all y values to be strictly positive.

        Returns
        -------
        OLS regression result applied to log(y), plus the exponentiated
        intercept (scale factor A in y = A * e^(slope*x)).
        """
        if any(yi <= 0 for yi in y):
            raise ValueError("All y values must be positive for log-linear regression.")
        log_y = [math.log(yi) for yi in y]
        result = self.linear_regression(x, log_y)
        result["scale_factor_A"] = round(math.exp(result["intercept"]), 6)
        result["model_type"] = "log-linear (y = A * e^(slope*x))"
        return result

    def power_law_fit(self, x: list[float], y: list[float]) -> dict:
        """Fit a power law: y = a * x^b via log-log regression.

        Relevant for Bitcoin metrics that follow power laws:
        - Price vs. time (S-curve / power law growth)
        - Hash rate vs. difficulty
        - Network effects (Metcalfe's law approximations)

        Requires all x and y values to be strictly positive.

        Returns
        -------
        dict with exponent b, coefficient a, r_squared, and model diagnostics.
        """
        if any(xi <= 0 for xi in x) or any(yi <= 0 for yi in y):
            raise ValueError("All values must be positive for power law fitting.")

        log_x = [math.log(xi) for xi in x]
        log_y = [math.log(yi) for yi in y]
        result = self.linear_regression(log_x, log_y)

        b = result["slope"]          # power law exponent
        log_a = result["intercept"]  # log(a)
        a = math.exp(log_a)          # coefficient

        return {
            "coefficient_a": round(a, 8),
            "exponent_b": round(b, 8),
            "r_squared": result["r_squared"],
            "adjusted_r_squared": result["adjusted_r_squared"],
            "log_regression": result,
            "model": f"y = {round(a, 4)} * x^{round(b, 4)}",
            "interpretation": (
                "exponential growth" if b > 1.5
                else "linear growth" if 0.8 < b < 1.2
                else "power law growth"
            ),
        }

    # =========================================================================
    # M O V I N G   A V E R A G E S   &   S M O O T H I N G
    # =========================================================================

    def moving_average(self, data: list[float], window: int) -> list[float]:
        """Compute a simple moving average (SMA) with the given window.

        The first (window - 1) values are ``None`` (insufficient history).

        Parameters
        ----------
        data   : Time series of values.
        window : Look-back window size (>= 1).

        Returns
        -------
        List of moving averages, same length as data.
        """
        data = self._validate_data(data, min_length=1, name="data")
        if window < 1:
            raise ValueError("window must be >= 1")
        if window > len(data):
            raise ValueError(f"window ({window}) exceeds data length ({len(data)})")

        result: list[float | None] = [None] * (window - 1)
        for i in range(window - 1, len(data)):
            window_data = data[i - window + 1 : i + 1]
            result.append(round(sum(window_data) / window, 8))
        return result  # type: ignore[return-value]

    def weighted_moving_average(self, data: list[float], window: int) -> list[float]:
        """Compute a linearly weighted moving average (WMA).

        More recent observations receive higher weight.  Weights are
        1, 2, 3, ..., window (normalised).

        Parameters
        ----------
        data   : Time series.
        window : Look-back window.

        Returns
        -------
        List of WMA values.
        """
        data = self._validate_data(data, min_length=1, name="data")
        if window < 1:
            raise ValueError("window must be >= 1")
        if window > len(data):
            raise ValueError(f"window ({window}) exceeds data length ({len(data)})")

        weights = list(range(1, window + 1))
        weight_sum = sum(weights)

        result: list[float | None] = [None] * (window - 1)
        for i in range(window - 1, len(data)):
            window_data = data[i - window + 1 : i + 1]
            wma = sum(w * v for w, v in zip(weights, window_data)) / weight_sum
            result.append(round(wma, 8))
        return result  # type: ignore[return-value]

    def exponential_smoothing(self, data: list[float], alpha: float) -> list[float]:
        """Compute single exponential smoothing (Holt's level-only model).

        S_t = alpha * x_t + (1 - alpha) * S_{t-1}

        Parameters
        ----------
        data  : Time series.
        alpha : Smoothing factor in (0, 1].  Higher alpha = more responsive.

        Returns
        -------
        Smoothed series of same length as data.
        """
        data = self._validate_data(data, min_length=1, name="data")
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")

        smoothed = [data[0]]
        for i in range(1, len(data)):
            s = alpha * data[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(round(s, 8))
        return smoothed

    def double_exponential_smoothing(
        self,
        data: list[float],
        alpha: float,
        beta: float,
    ) -> dict:
        """Holt's double exponential smoothing (level + trend).

        Suitable for time series with a trend but no seasonality.  Useful
        for projecting Bitcoin DCA accumulation or hash rate growth.

        Parameters
        ----------
        data  : Time series (at least 2 points).
        alpha : Level smoothing factor in (0, 1].
        beta  : Trend smoothing factor in (0, 1].

        Returns
        -------
        dict with ``smoothed`` (list), ``forecast_next`` (float), and
        the final ``level`` and ``trend`` components.
        """
        data = self._validate_data(data, min_length=2, name="data")
        if not (0 < alpha <= 1 and 0 < beta <= 1):
            raise ValueError("alpha and beta must be in (0, 1]")

        level = data[0]
        trend = data[1] - data[0]
        smoothed = [round(level + trend, 8)]

        for i in range(1, len(data)):
            prev_level = level
            level = alpha * data[i] + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend
            smoothed.append(round(level + trend, 8))

        return {
            "smoothed": smoothed,
            "forecast_next": round(level + trend, 8),
            "final_level": round(level, 8),
            "final_trend": round(trend, 8),
        }

    def holt_winters(
        self,
        data: list[float],
        alpha: float,
        beta: float,
        gamma: float,
        season_length: int,
    ) -> dict:
        """Holt-Winters triple exponential smoothing (additive seasonality).

        Handles time series with both trend and seasonal components.
        Useful for detecting weekly/monthly patterns in Bitcoin fee rates
        or trading activity.

        Parameters
        ----------
        data          : Time series (at least 2 complete seasons).
        alpha         : Level smoothing (0 < alpha <= 1).
        beta          : Trend smoothing (0 < beta <= 1).
        gamma         : Seasonal smoothing (0 < gamma <= 1).
        season_length : Number of periods in one season (e.g., 7 for weekly).

        Returns
        -------
        dict with ``smoothed`` list, one-period ``forecast``, ``level``,
        ``trend``, and ``seasonal`` components.
        """
        data = self._validate_data(data, min_length=2 * season_length, name="data")
        if not (0 < alpha <= 1 and 0 < beta <= 1 and 0 < gamma <= 1):
            raise ValueError("alpha, beta, and gamma must be in (0, 1]")
        if season_length < 2:
            raise ValueError("season_length must be >= 2")

        n = len(data)

        # Initialise level, trend, and seasonal indices
        n_seasons = n // season_length
        level = statistics.mean(data[:season_length])
        trend = (statistics.mean(data[season_length:2 * season_length]) - level) / season_length

        seasonal = []
        for s in range(season_length):
            s_avg = statistics.mean(
                data[s + i * season_length]
                for i in range(n_seasons)
                if s + i * season_length < n
            )
            seasonal.append(s_avg - level)

        smoothed = []
        for i in range(n):
            s_idx = i % season_length
            prev_level = level
            level = alpha * (data[i] - seasonal[s_idx]) + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend
            seasonal[s_idx] = gamma * (data[i] - level) + (1 - gamma) * seasonal[s_idx]
            smoothed.append(round(level + trend + seasonal[s_idx], 8))

        forecast = round(level + trend + seasonal[n % season_length], 8)

        return {
            "smoothed": smoothed,
            "forecast": forecast,
            "final_level": round(level, 8),
            "final_trend": round(trend, 8),
            "seasonal_indices": [round(s, 8) for s in seasonal],
        }

    # =========================================================================
    # C O N F I D E N C E   I N T E R V A L S
    # =========================================================================

    def confidence_interval(
        self,
        data: list[float],
        confidence: float = 0.95,
    ) -> dict:
        """Compute a confidence interval for the population mean.

        Uses the t-distribution approximation (n-1 degrees of freedom) for
        the CI of the mean.  For large n the t-distribution approaches
        the normal distribution.

        Parameters
        ----------
        data       : Sample data.
        confidence : Confidence level (e.g., 0.95 for 95% CI).

        Returns
        -------
        dict with mean, lower, upper, margin_of_error, std_error,
        confidence, n, t_critical.
        """
        data = self._validate_data(data, min_length=2, name="data")
        if not 0 < confidence < 1:
            raise ValueError("confidence must be in (0, 1)")

        n = len(data)
        mean = statistics.mean(data)
        std_sample = statistics.stdev(data)
        std_error = std_sample / math.sqrt(n)

        # t-critical value approximation (good for n >= 5)
        alpha = 1 - confidence
        t_crit = self._t_critical(n - 1, alpha / 2)

        margin = t_crit * std_error
        lower = mean - margin
        upper = mean + margin

        return {
            "mean": round(mean, 8),
            "lower": round(lower, 8),
            "upper": round(upper, 8),
            "margin_of_error": round(margin, 8),
            "std_error": round(std_error, 8),
            "confidence": confidence,
            "n": n,
            "t_critical": round(t_crit, 6),
        }

    def bootstrap_confidence(
        self,
        data: list[float],
        statistic_fn: Callable[[list[float]], float],
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
    ) -> dict:
        """Compute a bootstrap confidence interval for any statistic.

        Bootstrap resampling works for any statistic (mean, median, Sharpe
        ratio, max drawdown, etc.) without distributional assumptions.
        Uses a deterministic pseudo-random seed based on the data for
        reproducibility.

        Parameters
        ----------
        data         : Original sample data.
        statistic_fn : Function that takes a list and returns a float.
        n_bootstrap  : Number of bootstrap resamples.
        confidence   : Confidence level.

        Returns
        -------
        dict with observed (the statistic on original data), lower, upper,
        std_error, bias, n_bootstrap, confidence.
        """
        data = self._validate_data(data, min_length=2, name="data")
        if not 0 < confidence < 1:
            raise ValueError("confidence must be in (0, 1)")
        if n_bootstrap < 100:
            raise ValueError("n_bootstrap should be at least 100 for reliable CIs")

        n = len(data)
        observed = statistic_fn(data)

        # Deterministic LCG (Linear Congruential Generator) — no random module
        seed = int(sum(data[:10]) * 1e6) % (2**32)

        def lcg_next(state: int) -> tuple[int, int]:
            """LCG: x_{n+1} = (a*x_n + c) mod m"""
            a, c, m = 1664525, 1013904223, 2**32
            state = (a * state + c) % m
            return state, state

        boot_stats = []
        rng_state = seed
        for _ in range(n_bootstrap):
            sample = []
            for _ in range(n):
                rng_state, val = lcg_next(rng_state)
                idx = val % n
                sample.append(data[idx])
            try:
                boot_stats.append(statistic_fn(sample))
            except (ValueError, ZeroDivisionError):
                pass  # Skip degenerate bootstrap samples

        if not boot_stats:
            raise ValueError("All bootstrap samples produced errors.")

        boot_stats.sort()
        alpha = 1 - confidence
        lower_idx = max(0, int(alpha / 2 * len(boot_stats)))
        upper_idx = min(len(boot_stats) - 1, int((1 - alpha / 2) * len(boot_stats)))

        lower = boot_stats[lower_idx]
        upper = boot_stats[upper_idx]
        boot_mean = statistics.mean(boot_stats)
        bias = boot_mean - observed
        boot_std = statistics.stdev(boot_stats) if len(boot_stats) > 1 else 0.0

        return {
            "observed": round(observed, 8),
            "lower": round(lower, 8),
            "upper": round(upper, 8),
            "std_error": round(boot_std, 8),
            "bias": round(bias, 8),
            "n_bootstrap": len(boot_stats),
            "confidence": confidence,
        }

    # =========================================================================
    # H Y P O T H E S I S   T E S T S
    # =========================================================================

    def hypothesis_test(
        self,
        sample1: list[float],
        sample2: list[float],
    ) -> dict:
        """Two-sample Welch's t-test (unequal variances).

        Tests whether two independent samples have the same mean.
        Useful for comparing Bitcoin price behaviour in different market
        phases (e.g., pre- vs. post-halving returns).

        Parameters
        ----------
        sample1, sample2 : Two independent samples (at least 2 each).

        Returns
        -------
        dict with t_statistic, degrees_of_freedom, p_value (approximate),
        reject_null (at alpha=0.05), mean1, mean2, mean_difference,
        std1, std2.
        """
        sample1 = self._validate_data(sample1, min_length=2, name="sample1")
        sample2 = self._validate_data(sample2, min_length=2, name="sample2")

        n1, n2 = len(sample1), len(sample2)
        mean1 = statistics.mean(sample1)
        mean2 = statistics.mean(sample2)
        var1 = statistics.variance(sample1)
        var2 = statistics.variance(sample2)

        # Welch's t-statistic
        se = math.sqrt(var1 / n1 + var2 / n2)
        if se == 0:
            t_stat = float("inf") if mean1 != mean2 else 0.0
        else:
            t_stat = (mean1 - mean2) / se

        # Welch–Satterthwaite degrees of freedom
        numerator_df = (var1 / n1 + var2 / n2) ** 2
        denom_df = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
        df = numerator_df / denom_df if denom_df != 0 else n1 + n2 - 2

        # Approximate p-value using t-distribution CDF approximation
        p_value = self._t_pvalue(t_stat, df)
        reject_null = p_value < 0.05

        return {
            "test": "Welch's two-sample t-test",
            "t_statistic": round(t_stat, 6),
            "degrees_of_freedom": round(df, 2),
            "p_value": round(p_value, 6),
            "reject_null_alpha_0_05": reject_null,
            "mean1": round(mean1, 8),
            "mean2": round(mean2, 8),
            "mean_difference": round(mean1 - mean2, 8),
            "std1": round(math.sqrt(var1), 8),
            "std2": round(math.sqrt(var2), 8),
            "n1": n1,
            "n2": n2,
            "interpretation": (
                "Means are significantly different (p < 0.05)"
                if reject_null
                else "No significant difference between means (p >= 0.05)"
            ),
        }

    def chi_squared_test(
        self,
        observed: list[float],
        expected: list[float],
    ) -> dict:
        """Pearson chi-squared goodness-of-fit test.

        Tests whether observed frequencies match expected frequencies.
        Useful for testing whether Bitcoin return distributions follow
        a hypothesised distribution.

        Parameters
        ----------
        observed : Observed category frequencies.
        expected : Expected category frequencies (must sum to same total).

        Returns
        -------
        dict with chi_squared, degrees_of_freedom, p_value (approximate),
        reject_null.
        """
        if len(observed) != len(expected):
            raise ValueError("observed and expected must have the same length")
        if any(e <= 0 for e in expected):
            raise ValueError("All expected values must be positive")

        k = len(observed)
        if k < 2:
            raise ValueError("Chi-squared test requires at least 2 categories")

        chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
        df = k - 1

        # Approximate p-value using chi-squared CDF (regularised gamma)
        p_value = self._chi2_pvalue(chi2, df)
        reject_null = p_value < 0.05

        return {
            "test": "Pearson chi-squared goodness-of-fit",
            "chi_squared": round(chi2, 6),
            "degrees_of_freedom": df,
            "p_value": round(p_value, 6),
            "reject_null_alpha_0_05": reject_null,
            "n_categories": k,
            "interpretation": (
                "Observed distribution differs significantly from expected (p < 0.05)"
                if reject_null
                else "No significant difference from expected distribution (p >= 0.05)"
            ),
        }

    def runs_test(self, data: list[float]) -> dict:
        """Wald-Wolfowitz runs test for randomness.

        Tests whether a sequence is random by examining the number of
        "runs" (consecutive streaks of above/below-median values).
        Useful for testing whether Bitcoin price returns are random or
        exhibit autocorrelation.

        Parameters
        ----------
        data : Time series.

        Returns
        -------
        dict with n_runs, expected_runs, z_statistic, p_value (approximate),
        reject_null (randomness rejected at alpha=0.05).
        """
        data = self._validate_data(data, min_length=10, name="data")
        median = statistics.median(data)

        # Encode as above (1) or below (0) median; skip exact-median values
        coded = []
        for x in data:
            if x > median:
                coded.append(1)
            elif x < median:
                coded.append(0)
            # Skip ties at median

        if len(coded) < 10:
            raise ValueError("Not enough non-median values for runs test")

        n1 = sum(coded)        # count of 1s
        n2 = len(coded) - n1  # count of 0s
        n = n1 + n2

        if n1 == 0 or n2 == 0:
            raise ValueError("All values are on the same side of the median")

        # Count runs
        runs = 1
        for i in range(1, len(coded)):
            if coded[i] != coded[i - 1]:
                runs += 1

        # Expected runs and variance
        expected_runs = (2 * n1 * n2) / n + 1
        var_runs = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n ** 2 * (n - 1))

        if var_runs <= 0:
            z_stat = 0.0
        else:
            # Continuity correction
            z_stat = (runs - expected_runs - 0.5) / math.sqrt(var_runs)

        p_value = 2 * (1 - self._normal_cdf(abs(z_stat)))
        reject_null = p_value < 0.05

        return {
            "test": "Wald-Wolfowitz runs test",
            "n_runs": runs,
            "expected_runs": round(expected_runs, 4),
            "z_statistic": round(z_stat, 6),
            "p_value": round(p_value, 6),
            "n1_above_median": n1,
            "n2_below_median": n2,
            "reject_null_alpha_0_05": reject_null,
            "interpretation": (
                "Series is NOT random — autocorrelation detected (p < 0.05)"
                if reject_null
                else "Series appears random (p >= 0.05)"
            ),
        }

    def jarque_bera_test(self, data: list[float]) -> dict:
        """Jarque-Bera test for normality.

        Tests whether sample data have the skewness and kurtosis matching
        a normal distribution.  Bitcoin returns are famously non-normal
        (fat tails / excess kurtosis); this test quantifies that.

        Parameters
        ----------
        data : Sample data (at least 8 values recommended).

        Returns
        -------
        dict with jb_statistic, p_value (approximate), skewness, excess_kurtosis,
        reject_normality.
        """
        data = self._validate_data(data, min_length=8, name="data")
        n = len(data)
        mean = statistics.mean(data)
        std = statistics.pstdev(data)

        if std == 0:
            raise ValueError("Constant series — normality test undefined")

        skewness = self._skewness(data, mean, std)
        kurtosis = self._kurtosis(data, mean, std)  # excess kurtosis

        jb = n / 6 * (skewness ** 2 + kurtosis ** 2 / 4)
        # JB ~ chi-squared(2) under H0
        p_value = self._chi2_pvalue(jb, df=2)
        reject = p_value < 0.05

        return {
            "test": "Jarque-Bera normality test",
            "jb_statistic": round(jb, 6),
            "p_value": round(p_value, 6),
            "skewness": round(skewness, 6),
            "excess_kurtosis": round(kurtosis, 6),
            "reject_normality_alpha_0_05": reject,
            "n": n,
            "interpretation": (
                "Data is NOT normally distributed (p < 0.05) — fat tails or skew present"
                if reject
                else "Cannot reject normality (p >= 0.05)"
            ),
        }

    def adf_test(self, data: list[float]) -> dict:
        """Augmented Dickey-Fuller (ADF) test for stationarity.

        Tests whether a time series has a unit root (i.e., is non-stationary).
        Bitcoin price is non-stationary; log-returns are typically stationary.

        This is a simplified ADF implementation using OLS regression of
        first differences.  For a fully rigorous ADF with automatic lag
        selection, use a statistics library.

        Parameters
        ----------
        data : Time series (at least 20 values recommended).

        Returns
        -------
        dict with adf_statistic, p_value (approximate), n_lags_used,
        is_stationary (at 5% significance).
        """
        data = self._validate_data(data, min_length=20, name="data")
        n = len(data)

        # First differences
        diff = [data[i] - data[i - 1] for i in range(1, n)]

        # ADF with 1 lag: regress diff[t] on data[t-1] and diff[t-1]
        y = diff[1:]         # dependent: diff[t]
        x_lag = data[1:-1]   # data[t-1]
        x_diff_lag = diff[:-1]  # diff[t-1]

        if len(y) < 3:
            raise ValueError("Insufficient data for ADF test")

        # Simple OLS of y on x_lag (ignoring diff lag for simplicity)
        reg = self.linear_regression(x_lag, y)

        adf_stat = reg["t_stat_slope"]
        df = len(y) - 2

        # Approximate p-value
        p_value = self._t_pvalue(adf_stat, df)

        # ADF critical values (approx, from MacKinnon 1994, no constant)
        cv_1pct = -3.43
        cv_5pct = -2.86
        cv_10pct = -2.57

        stationary_5pct = adf_stat < cv_5pct

        return {
            "test": "Augmented Dickey-Fuller (simplified, 1 lag)",
            "adf_statistic": round(adf_stat, 6),
            "p_value_approx": round(p_value, 6),
            "n_observations": n,
            "critical_value_1pct": cv_1pct,
            "critical_value_5pct": cv_5pct,
            "critical_value_10pct": cv_10pct,
            "is_stationary_5pct": stationary_5pct,
            "interpretation": (
                "Series appears STATIONARY — unit root rejected (ADF < 5% CV)"
                if stationary_5pct
                else "Series appears NON-STATIONARY — unit root not rejected"
            ),
            "bitcoin_note": (
                "Bitcoin price is typically non-stationary; log-returns are stationary."
            ),
        }

    def granger_causality(
        self,
        x: list[float],
        y: list[float],
        max_lag: int = 4,
    ) -> dict:
        """Simplified Granger causality test: does x Granger-cause y?

        Tests whether lagged values of x improve prediction of y beyond
        lagged y alone.  Computes an F-statistic for each lag 1..max_lag.

        Useful for testing whether Bitcoin hash rate leads price, or whether
        on-chain metrics lead market moves.

        Parameters
        ----------
        x       : Potential causal variable (e.g., hash rate).
        y       : Outcome variable (e.g., price).
        max_lag : Maximum lag to test (default 4).

        Returns
        -------
        dict with results per lag (F-statistic, p-value, significant),
        and best_lag (lowest p-value).
        """
        x, y = self._validate_paired(x, y)
        n = len(x)
        if n < 2 * max_lag + 10:
            raise ValueError(
                f"Need at least {2 * max_lag + 10} observations for Granger test "
                f"with max_lag={max_lag}"
            )

        results = []
        for lag in range(1, max_lag + 1):
            # Restricted model: y_t = a + sum(b_i * y_{t-i}) for i in 1..lag
            y_dep = y[lag:]
            y_lags = [[y[i - k] for k in range(1, lag + 1)] for i in range(lag, n)]

            # OLS restricted: regress y on its own lags
            if len(y_dep) < lag + 2:
                continue

            # Use first lag only for simplicity (approximate)
            y_lag1 = [y[i - 1] for i in range(lag, n)]
            reg_restricted = self.linear_regression(y_lag1, y_dep)
            rss_restricted = reg_restricted["mse"] * (len(y_dep) - 2)

            # Unrestricted: include x lags
            x_lag1 = [x[i - 1] for i in range(lag, n)]
            # Regress residuals of restricted on x lags
            residuals_r = reg_restricted["residuals"]
            reg_unrestricted = self.linear_regression(x_lag1, residuals_r)
            rss_unrestricted = reg_unrestricted["mse"] * (len(residuals_r) - 2)

            if rss_unrestricted <= 0 or rss_restricted <= 0:
                continue

            # F-statistic
            n_obs = len(y_dep)
            f_stat = ((rss_restricted - rss_unrestricted) / lag) / (
                rss_unrestricted / max(n_obs - 2 * lag - 1, 1)
            )
            p_value = self._f_pvalue(f_stat, lag, max(n_obs - 2 * lag - 1, 1))

            results.append(
                {
                    "lag": lag,
                    "f_statistic": round(f_stat, 6),
                    "p_value": round(p_value, 6),
                    "significant_0_05": p_value < 0.05,
                }
            )

        best = min(results, key=lambda r: r["p_value"]) if results else None

        return {
            "test": "Granger causality (simplified)",
            "max_lag_tested": max_lag,
            "n_observations": n,
            "results_by_lag": results,
            "best_lag": best,
            "conclusion": (
                f"x Granger-causes y at lag {best['lag']} (p={best['p_value']:.4f})"
                if best and best["significant_0_05"]
                else "No significant Granger causality detected"
            ),
        }

    # =========================================================================
    # D I S T R I B U T I O N   A N A L Y S I S
    # =========================================================================

    def kernel_density_estimation(
        self,
        data: list[float],
        bandwidth: float | None = None,
        n_points: int = 100,
    ) -> dict:
        """Gaussian kernel density estimation (KDE).

        Produces a smooth density estimate over the data range.
        Useful for visualising Bitcoin return distributions and
        identifying multi-modal behaviour.

        Parameters
        ----------
        data      : Sample data.
        bandwidth : Smoothing bandwidth (auto-selected via Silverman's rule if None).
        n_points  : Number of evaluation points.

        Returns
        -------
        dict with x_values (evaluation grid), density (estimated density),
        bandwidth_used, and integration_check (~1.0 for a good estimate).
        """
        data = self._validate_data(data, min_length=3, name="data")
        n = len(data)
        std = statistics.stdev(data)

        # Silverman's rule of thumb
        if bandwidth is None or bandwidth <= 0:
            bandwidth = 1.06 * std * n ** (-0.2)

        x_min = min(data) - 3 * bandwidth
        x_max = max(data) + 3 * bandwidth
        step = (x_max - x_min) / (n_points - 1)
        x_vals = [x_min + i * step for i in range(n_points)]

        # Gaussian kernel: K(u) = (1/sqrt(2pi)) * exp(-u^2/2)
        inv_sqrt_2pi = 1.0 / math.sqrt(2 * math.pi)
        density = []
        for x in x_vals:
            kernel_sum = sum(
                inv_sqrt_2pi * math.exp(-0.5 * ((x - xi) / bandwidth) ** 2)
                for xi in data
            )
            density.append(round(kernel_sum / (n * bandwidth), 10))

        # Rough integration check (trapezoid rule)
        integral = sum(
            (density[i] + density[i - 1]) * step / 2
            for i in range(1, len(density))
        )

        return {
            "x_values": [round(x, 6) for x in x_vals],
            "density": density,
            "bandwidth_used": round(bandwidth, 8),
            "n_points": n_points,
            "integration_check": round(integral, 4),
            "x_range": [round(x_min, 6), round(x_max, 6)],
        }

    def pareto_analysis(self, data: list[float]) -> dict:
        """Pareto (80/20) analysis of a distribution.

        Identifies what fraction of items account for various percentages
        of the total.  Classic application in Bitcoin: what fraction of
        UTXOs account for 80% of total value? What fraction of miners
        control 80% of hash rate?

        Parameters
        ----------
        data : Non-negative values (e.g., UTXO sizes in sats).

        Returns
        -------
        dict with cumulative_pct_items, cumulative_pct_value,
        pareto_threshold_pct (% of items accounting for 80% of value),
        gini_coefficient, top_1pct_share, top_10pct_share, top_20pct_share.
        """
        data = self._validate_data(data, min_length=2, name="data")
        if any(x < 0 for x in data):
            raise ValueError("Pareto analysis requires non-negative values")

        n = len(data)
        total = sum(data)
        if total == 0:
            raise ValueError("Total is zero — Pareto analysis undefined")

        sorted_desc = sorted(data, reverse=True)

        cumulative_value = 0.0
        pareto_pct_items = None
        cumulative_data = []
        for i, val in enumerate(sorted_desc):
            cumulative_value += val
            pct_items = (i + 1) / n * 100
            pct_value = cumulative_value / total * 100
            cumulative_data.append((round(pct_items, 2), round(pct_value, 2)))
            if pareto_pct_items is None and pct_value >= 80:
                pareto_pct_items = pct_items

        # Gini coefficient
        sorted_asc = sorted(data)
        gini = self._gini(sorted_asc, total)

        # Top-share statistics
        def top_share(pct: float) -> float:
            k = max(1, int(n * pct / 100))
            return round(sum(sorted_desc[:k]) / total * 100, 4)

        return {
            "n": n,
            "total": round(total, 4),
            "gini_coefficient": round(gini, 6),
            "pareto_threshold_pct_items": round(pareto_pct_items, 2) if pareto_pct_items else 100.0,
            "top_1pct_value_share_pct": top_share(1),
            "top_10pct_value_share_pct": top_share(10),
            "top_20pct_value_share_pct": top_share(20),
            "cumulative_distribution": cumulative_data[:50],  # First 50 points
            "interpretation": (
                f"Top {round(pareto_pct_items, 1)}% of items hold 80% of value"
                if pareto_pct_items
                else "Distribution is flat"
            ),
        }

    # =========================================================================
    # B I T C O I N - S P E C I F I C   M E T R I C S
    # =========================================================================

    def drawdown_analysis(self, prices: list[float]) -> dict:
        """Analyse drawdown characteristics of a Bitcoin price series.

        Computes max drawdown, average drawdown, and drawdown periods.

        Parameters
        ----------
        prices : Chronological price series.

        Returns
        -------
        dict with max_drawdown_pct, avg_drawdown_pct, n_drawdown_periods,
        current_drawdown_pct, recovery_factor.
        """
        prices = self._validate_data(prices, min_length=2, name="prices")
        peak = prices[0]
        max_dd = 0.0
        drawdowns = []
        in_drawdown = False
        dd_start_peak = prices[0]

        for p in prices[1:]:
            if p > peak:
                if in_drawdown:
                    drawdowns.append((dd_start_peak - min_p) / dd_start_peak * 100)
                    in_drawdown = False
                peak = p
            else:
                if not in_drawdown:
                    in_drawdown = True
                    dd_start_peak = peak
                    min_p = p
                else:
                    min_p = min(min_p, p)

        if in_drawdown:
            drawdowns.append((dd_start_peak - min_p) / dd_start_peak * 100)

        max_dd = max(drawdowns) if drawdowns else 0.0
        avg_dd = statistics.mean(drawdowns) if drawdowns else 0.0

        # Current drawdown
        all_time_high = max(prices)
        current_price = prices[-1]
        current_dd = (all_time_high - current_price) / all_time_high * 100

        # Recovery factor: final value / max drawdown amount
        recovery = (prices[-1] - prices[0]) / (max_dd / 100 * max(prices)) if max_dd > 0 else None

        return {
            "max_drawdown_pct": round(max_dd, 4),
            "avg_drawdown_pct": round(avg_dd, 4),
            "n_drawdown_periods": len(drawdowns),
            "current_drawdown_from_ath_pct": round(current_dd, 4),
            "all_time_high": round(all_time_high, 4),
            "current_price": round(current_price, 4),
            "recovery_factor": round(recovery, 4) if recovery is not None else None,
        }

    def volatility_metrics(self, returns: list[float]) -> dict:
        """Compute volatility metrics from a returns series.

        Parameters
        ----------
        returns : Percentage or decimal returns (e.g., daily log-returns).

        Returns
        -------
        dict with annualised_volatility, daily_volatility, sharpe_ratio
        (assuming 0 risk-free rate), sortino_ratio, var_95, cvar_95.
        """
        returns = self._validate_data(returns, min_length=10, name="returns")
        n = len(returns)

        mean_ret = statistics.mean(returns)
        std_ret = statistics.stdev(returns) if n > 1 else 0.0

        # Annualise assuming 365 trading days (Bitcoin trades 24/7)
        ann_vol = std_ret * math.sqrt(365)
        ann_return = mean_ret * 365

        sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0

        # Sortino: downside deviation only
        downside = [r for r in returns if r < 0]
        if len(downside) > 1:
            dd_std = statistics.stdev(downside)
            sortino = ann_return / (dd_std * math.sqrt(365)) if dd_std > 0 else 0.0
        else:
            sortino = 0.0

        # VaR 95%
        sorted_r = sorted(returns)
        var_idx = int(0.05 * n)
        var_95 = sorted_r[max(0, var_idx)]

        # CVaR 95% (Expected Shortfall)
        tail = sorted_r[:max(1, var_idx)]
        cvar_95 = statistics.mean(tail)

        return {
            "n_observations": n,
            "daily_mean_return": round(mean_ret, 8),
            "daily_volatility": round(std_ret, 8),
            "annualised_volatility": round(ann_vol, 6),
            "annualised_return": round(ann_return, 6),
            "sharpe_ratio": round(sharpe, 6),
            "sortino_ratio": round(sortino, 6),
            "var_95_daily": round(var_95, 6),
            "cvar_95_daily": round(cvar_95, 6),
        }

    def dca_performance(
        self,
        prices: list[float],
        amount_per_period: float = 100.0,
    ) -> dict:
        """Calculate DCA (Dollar-Cost Averaging) performance metrics.

        Simulates buying a fixed dollar amount of Bitcoin each period
        at the given prices, and returns performance statistics.

        Parameters
        ----------
        prices           : Chronological price series (USD/BTC).
        amount_per_period: Fixed dollar amount to invest each period.

        Returns
        -------
        dict with total_invested, total_sats, avg_cost_basis,
        current_value, total_return_pct, best_period, worst_period.
        """
        prices = self._validate_data(prices, min_length=2, name="prices")
        if amount_per_period <= 0:
            raise ValueError("amount_per_period must be positive")

        total_invested = 0.0
        total_sats = 0.0
        sats_per_period = []
        cost_bases = []

        for price in prices:
            if price <= 0:
                continue
            sats = (amount_per_period / price) * 1e8  # Convert to sats
            total_invested += amount_per_period
            total_sats += sats
            sats_per_period.append(round(sats))
            cost_bases.append(price)

        if not cost_bases:
            raise ValueError("No valid price data")

        avg_cost_basis = total_invested / (total_sats / 1e8)  # USD/BTC
        current_price = prices[-1]
        current_value = (total_sats / 1e8) * current_price
        total_return_pct = (current_value - total_invested) / total_invested * 100

        return {
            "periods": len(cost_bases),
            "amount_per_period_usd": amount_per_period,
            "total_invested_usd": round(total_invested, 2),
            "total_sats": int(total_sats),
            "total_btc": round(total_sats / 1e8, 8),
            "avg_cost_basis_usd": round(avg_cost_basis, 2),
            "current_price_usd": round(current_price, 2),
            "current_value_usd": round(current_value, 2),
            "total_return_pct": round(total_return_pct, 4),
            "unrealized_gain_usd": round(current_value - total_invested, 2),
            "best_period_price": round(min(cost_bases), 2),
            "worst_period_price": round(max(cost_bases), 2),
            "sats_per_period": sats_per_period,
        }

    # =========================================================================
    # I N T E R N A L   H E L P E R S
    # =========================================================================

    @staticmethod
    def _validate_data(
        data: list[float],
        min_length: int = 1,
        name: str = "data",
    ) -> list[float]:
        """Validate a data list and coerce elements to float."""
        if not isinstance(data, (list, tuple)):
            raise TypeError(f"'{name}' must be a list, got {type(data).__name__}")
        if len(data) < min_length:
            raise ValueError(f"'{name}' must have at least {min_length} element(s)")
        try:
            return [float(x) for x in data]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{name}' contains non-numeric values: {exc}") from exc

    @staticmethod
    def _validate_paired(
        x: list[float],
        y: list[float],
    ) -> tuple[list[float], list[float]]:
        """Validate two paired lists and coerce to float."""
        if len(x) != len(y):
            raise ValueError(
                f"x (len={len(x)}) and y (len={len(y)}) must have the same length"
            )
        x = [float(v) for v in x]
        y = [float(v) for v in y]
        return x, y

    @staticmethod
    def _percentile(sorted_data: list[float], p: float) -> float:
        """Linear interpolation percentile on pre-sorted data."""
        n = len(sorted_data)
        if n == 1:
            return sorted_data[0]
        idx = (p / 100) * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        fraction = idx - lower
        return sorted_data[lower] * (1 - fraction) + sorted_data[upper] * fraction

    @staticmethod
    def _skewness(data: list[float], mean: float, std: float) -> float:
        """Fisher's moment coefficient of skewness."""
        n = len(data)
        return sum(((x - mean) / std) ** 3 for x in data) / n

    @staticmethod
    def _kurtosis(data: list[float], mean: float, std: float) -> float:
        """Excess kurtosis (Fisher's definition, normal = 0)."""
        n = len(data)
        return sum(((x - mean) / std) ** 4 for x in data) / n - 3

    @staticmethod
    def _rank(data: list[float]) -> list[float]:
        """Return average ranks for data (handles ties)."""
        n = len(data)
        sorted_indexed = sorted(enumerate(data), key=lambda ix: ix[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and sorted_indexed[j + 1][1] == sorted_indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2 + 1  # 1-based average rank
            for k in range(i, j + 1):
                ranks[sorted_indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    @staticmethod
    def _gini(sorted_asc: list[float], total: float) -> float:
        """Compute Gini coefficient from sorted (ascending) non-negative data."""
        n = len(sorted_asc)
        cumsum = 0.0
        gini_sum = 0.0
        for i, x in enumerate(sorted_asc):
            cumsum += x
            gini_sum += (2 * (i + 1) - n - 1) * x
        return gini_sum / (n * total) if total > 0 else 0.0

    @staticmethod
    def _normal_cdf(z: float) -> float:
        """Approximate standard normal CDF using Abramowitz & Stegun."""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    @classmethod
    def _t_critical(cls, df: float, alpha: float) -> float:
        """Approximate t-distribution critical value (two-tailed) via iteration."""
        # Use normal approximation for large df
        if df >= 200:
            z_crit = math.sqrt(2) * math.erfinv(1 - 2 * alpha) if hasattr(math, "erfinv") else 1.96
            return z_crit

        # Newton-Raphson approximation
        # Start from normal approximation and refine
        from math import sqrt, lgamma, exp

        def t_pdf(t: float, df: float) -> float:
            coef = exp(lgamma((df + 1) / 2) - lgamma(df / 2)) / (sqrt(df * math.pi))
            return coef * (1 + t ** 2 / df) ** (-(df + 1) / 2)

        def t_cdf_complement(t: float, df: float) -> float:
            """Complement of CDF above t, via numerical integration."""
            # Simple quadrature: 200 steps from t to t+20
            if t > 20:
                return 0.0
            steps = 200
            hi = t + 20.0
            h = (hi - t) / steps
            integral = 0.5 * (t_pdf(t, df) + t_pdf(hi, df))
            for k in range(1, steps):
                integral += t_pdf(t + k * h, df)
            return integral * h

        # Binary search for critical value
        lo, hi = 0.0, 10.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if t_cdf_complement(mid, df) > alpha:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2, 6)

    @classmethod
    def _t_pvalue(cls, t: float, df: float) -> float:
        """Approximate two-tailed p-value for t-distribution."""
        t_abs = abs(t)
        if t_abs > 20:
            return 0.0

        # Regularised incomplete beta function approximation
        x = df / (df + t_abs ** 2)
        # Series expansion of regularised incomplete beta
        p = cls._reg_inc_beta(x, df / 2, 0.5)
        return min(1.0, p)

    @staticmethod
    def _reg_inc_beta(x: float, a: float, b: float) -> float:
        """Regularised incomplete beta function I_x(a,b) via continued fraction."""
        from math import lgamma, log, exp

        if x < 0 or x > 1:
            return 0.0
        if x == 0:
            return 0.0
        if x == 1:
            return 1.0

        lbeta = lgamma(a) + lgamma(b) - lgamma(a + b)
        front = exp(log(x) * a + log(1 - x) * b - lbeta) / a

        # Lentz continued fraction (first 200 iterations)
        f = 1.0
        c = 1.0
        d = 1.0 - (a + b) * x / (a + 1)
        d = 1.0 / d if abs(d) > 1e-30 else 1e30
        f = d
        delta = 0.0

        tiny = 1e-30
        for m in range(1, 200):
            # Even step
            num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
            d = 1.0 + num * d
            if abs(d) < tiny:
                d = tiny
            c = 1.0 + num / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = c * d
            f *= delta

            # Odd step
            num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
            d = 1.0 + num * d
            if abs(d) < tiny:
                d = tiny
            c = 1.0 + num / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = c * d
            f *= delta

            if abs(delta - 1.0) < 1e-10:
                break

        if x < (a + 1) / (a + b + 2):
            return front * f
        return 1.0 - front * f  # Use symmetry

    @classmethod
    def _chi2_pvalue(cls, chi2: float, df: int) -> float:
        """Approximate p-value for chi-squared distribution."""
        if chi2 <= 0:
            return 1.0
        x = df / (df + chi2)  # Transform to beta
        return cls._reg_inc_beta(x, df / 2, 0.5)

    @staticmethod
    def _f_pvalue(f: float, df1: int, df2: int) -> float:
        """Approximate p-value for F-distribution (upper tail)."""
        if f <= 0:
            return 1.0
        # Transform to beta distribution
        x = df2 / (df2 + df1 * f)
        from math import lgamma, log, exp
        try:
            lbeta = lgamma(df1 / 2) + lgamma(df2 / 2) - lgamma((df1 + df2) / 2)
            front = exp(log(x) * (df2 / 2) + log(1 - x) * (df1 / 2) - lbeta) / (df2 / 2)
            return min(1.0, max(0.0, front))
        except (ValueError, OverflowError):
            return 0.5
