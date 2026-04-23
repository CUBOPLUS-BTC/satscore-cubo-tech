"""HTTP route handlers for the Bitcoin statistics module.

All handlers follow the project convention: return ``(body_dict, status_code)``.

Endpoints
---------
POST /stats/analyze
     Body:
       - data     : list[float]  — required (price or metric time series)
       - include  : list[str]    — optional subset of analyses to run
                    Options: "descriptive", "normality", "runs", "volatility",
                             "drawdown", "adf", "kde", "pareto", "smoothing"
       - alpha    : float        — smoothing alpha for EMA (default 0.1)
       - window   : int          — MA window (default 20)

POST /stats/correlation
     Body:
       - x        : list[float]  — required
       - y        : list[float]  — required
       - methods  : list[str]    — optional: "pearson", "spearman"
                                   (default: both)
       - include_regression : bool — include linear regression (default true)

POST /stats/regression
     Body:
       - x        : list[float]  — required (independent variable)
       - y        : list[float]  — required (dependent variable)
       - type     : str          — "linear" | "log_linear" | "power_law"
                                   (default "linear")
       - bootstrap_ci : bool     — include bootstrap CI for slope (default false)
       - n_bootstrap  : int      — bootstrap resamples (default 500)
"""

from __future__ import annotations

from .calculator import StatisticsCalculator

_calc = StatisticsCalculator()

# Default maximum data length to prevent abuse (tune as needed)
_MAX_DATA_POINTS = 10_000


def handle_stats_analyze(body: dict) -> tuple[dict, int]:
    """POST /stats/analyze

    Runs one or more statistical analyses on a provided data series.
    Designed for Bitcoin price data, fee rate series, or any numeric metric.

    The ``include`` list controls which analyses are computed.  Omit it
    to run the full default set.

    Returns a dict with one key per analysis type, each containing the
    result dict from the corresponding calculator method.
    """
    try:
        raw_data = body.get("data")
        if raw_data is None:
            return {"detail": "Missing required field: data"}, 400
        if not isinstance(raw_data, list):
            return {"detail": "Field 'data' must be a list of numbers."}, 400
        if len(raw_data) == 0:
            return {"detail": "Field 'data' must not be empty."}, 400
        if len(raw_data) > _MAX_DATA_POINTS:
            return {
                "detail": f"data exceeds maximum of {_MAX_DATA_POINTS} points."
            }, 400

        try:
            data = [float(x) for x in raw_data]
        except (TypeError, ValueError) as exc:
            return {"detail": f"data contains non-numeric values: {exc}"}, 400

        # Optional parameters
        include = body.get("include") or [
            "descriptive", "normality", "runs", "volatility", "drawdown",
            "smoothing", "confidence_interval",
        ]
        if not isinstance(include, list):
            return {"detail": "Field 'include' must be a list of strings."}, 400

        alpha = float(body.get("alpha") or 0.1)
        window = int(body.get("window") or min(20, max(2, len(data) // 5)))

        results: dict = {
            "n": len(data),
            "analyses": {},
        }

        # Run each requested analysis
        for analysis in include:
            analysis = analysis.strip().lower()
            try:
                if analysis == "descriptive":
                    results["analyses"]["descriptive"] = _calc.descriptive_stats(data)

                elif analysis == "normality":
                    if len(data) >= 8:
                        results["analyses"]["normality"] = _calc.jarque_bera_test(data)
                    else:
                        results["analyses"]["normality"] = {
                            "error": "Requires at least 8 data points"
                        }

                elif analysis == "runs":
                    if len(data) >= 10:
                        results["analyses"]["runs"] = _calc.runs_test(data)
                    else:
                        results["analyses"]["runs"] = {
                            "error": "Requires at least 10 data points"
                        }

                elif analysis == "volatility":
                    # Compute log-returns for volatility analysis
                    if len(data) >= 11 and all(x > 0 for x in data):
                        import math
                        log_returns = [
                            math.log(data[i] / data[i - 1])
                            for i in range(1, len(data))
                        ]
                        results["analyses"]["volatility"] = _calc.volatility_metrics(
                            log_returns
                        )
                    else:
                        results["analyses"]["volatility"] = {
                            "error": "Requires at least 11 positive data points for log-return computation"
                        }

                elif analysis == "drawdown":
                    if len(data) >= 2 and all(x > 0 for x in data):
                        results["analyses"]["drawdown"] = _calc.drawdown_analysis(data)
                    else:
                        results["analyses"]["drawdown"] = {
                            "error": "Requires at least 2 positive data points"
                        }

                elif analysis == "smoothing":
                    ema = _calc.exponential_smoothing(data, alpha=alpha)
                    sma = _calc.moving_average(data, window=min(window, len(data)))
                    results["analyses"]["smoothing"] = {
                        "ema_alpha": alpha,
                        "sma_window": min(window, len(data)),
                        "ema": ema[-20:],    # Last 20 for brevity
                        "sma": sma[-20:],
                    }

                elif analysis == "confidence_interval":
                    if len(data) >= 2:
                        results["analyses"]["confidence_interval"] = (
                            _calc.confidence_interval(data, confidence=0.95)
                        )
                    else:
                        results["analyses"]["confidence_interval"] = {
                            "error": "Requires at least 2 data points"
                        }

                elif analysis == "adf":
                    if len(data) >= 20:
                        results["analyses"]["adf"] = _calc.adf_test(data)
                    else:
                        results["analyses"]["adf"] = {
                            "error": "Requires at least 20 data points"
                        }

                elif analysis == "kde":
                    if len(data) >= 3:
                        results["analyses"]["kde"] = _calc.kernel_density_estimation(
                            data, n_points=50
                        )
                    else:
                        results["analyses"]["kde"] = {
                            "error": "Requires at least 3 data points"
                        }

                elif analysis == "pareto":
                    if len(data) >= 2 and all(x >= 0 for x in data):
                        results["analyses"]["pareto"] = _calc.pareto_analysis(data)
                    else:
                        results["analyses"]["pareto"] = {
                            "error": "Requires at least 2 non-negative data points"
                        }

                else:
                    results["analyses"][analysis] = {
                        "error": f"Unknown analysis type '{analysis}'"
                    }

            except (ValueError, TypeError, ZeroDivisionError) as exc:
                results["analyses"][analysis] = {"error": str(exc)}

        return results, 200

    except Exception as exc:
        return {"detail": f"Analysis error: {exc}"}, 500


def handle_stats_correlation(body: dict) -> tuple[dict, int]:
    """POST /stats/correlation

    Compute correlation statistics between two parallel data series.
    Optionally includes linear regression.

    Typical use: correlate Bitcoin price with hash rate, fee rate with
    mempool size, or DCA performance with time.
    """
    try:
        x_raw = body.get("x")
        y_raw = body.get("y")

        if x_raw is None:
            return {"detail": "Missing required field: x"}, 400
        if y_raw is None:
            return {"detail": "Missing required field: y"}, 400
        if not isinstance(x_raw, list) or not isinstance(y_raw, list):
            return {"detail": "Fields 'x' and 'y' must be lists."}, 400
        if len(x_raw) != len(y_raw):
            return {
                "detail": f"x (len={len(x_raw)}) and y (len={len(y_raw)}) must have equal length."
            }, 400
        if len(x_raw) < 2:
            return {"detail": "At least 2 data points are required for correlation."}, 400
        if len(x_raw) > _MAX_DATA_POINTS:
            return {"detail": f"Data exceeds {_MAX_DATA_POINTS} points."}, 400

        try:
            x = [float(v) for v in x_raw]
            y = [float(v) for v in y_raw]
        except (TypeError, ValueError) as exc:
            return {"detail": f"Non-numeric values: {exc}"}, 400

        methods = body.get("methods") or ["pearson", "spearman"]
        if not isinstance(methods, list):
            return {"detail": "Field 'methods' must be a list."}, 400

        include_regression = body.get("include_regression", True)
        if not isinstance(include_regression, bool):
            include_regression = str(include_regression).lower() != "false"

        results: dict = {
            "n": len(x),
            "correlations": {},
        }

        for method in methods:
            method = method.strip().lower()
            try:
                if method == "pearson":
                    r = _calc.correlation(x, y)
                    cov = _calc.covariance(x, y)
                    results["correlations"]["pearson"] = {
                        "r": r,
                        "r_squared": round(r ** 2, 8),
                        "covariance": cov,
                        "interpretation": _interpret_correlation(r),
                    }
                elif method == "spearman":
                    rho = _calc.spearman_correlation(x, y)
                    results["correlations"]["spearman"] = {
                        "rho": rho,
                        "rho_squared": round(rho ** 2, 8),
                        "interpretation": _interpret_correlation(rho),
                    }
                else:
                    results["correlations"][method] = {
                        "error": f"Unknown method '{method}'. Use 'pearson' or 'spearman'."
                    }
            except (ValueError, ZeroDivisionError) as exc:
                results["correlations"][method] = {"error": str(exc)}

        if include_regression:
            try:
                reg = _calc.linear_regression(x, y)
                results["regression"] = {
                    "slope": reg["slope"],
                    "intercept": reg["intercept"],
                    "r_squared": reg["r_squared"],
                    "adj_r_squared": reg["adjusted_r_squared"],
                    "rmse": reg["rmse"],
                    "mae": reg["mae"],
                    "t_stat_slope": reg["t_stat_slope"],
                }
            except (ValueError, ZeroDivisionError) as exc:
                results["regression"] = {"error": str(exc)}

        return results, 200

    except Exception as exc:
        return {"detail": f"Correlation error: {exc}"}, 500


def handle_stats_regression(body: dict) -> tuple[dict, int]:
    """POST /stats/regression

    Fit a regression model to two paired data series and return
    diagnostic statistics.  Supports linear, log-linear, and power law
    regression — all relevant for Bitcoin price modelling.
    """
    try:
        x_raw = body.get("x")
        y_raw = body.get("y")

        if x_raw is None:
            return {"detail": "Missing required field: x"}, 400
        if y_raw is None:
            return {"detail": "Missing required field: y"}, 400
        if not isinstance(x_raw, list) or not isinstance(y_raw, list):
            return {"detail": "Fields 'x' and 'y' must be lists."}, 400
        if len(x_raw) != len(y_raw):
            return {
                "detail": f"x (len={len(x_raw)}) and y (len={len(y_raw)}) must match."
            }, 400
        if len(x_raw) < 3:
            return {"detail": "At least 3 data points are required for regression."}, 400
        if len(x_raw) > _MAX_DATA_POINTS:
            return {"detail": f"Data exceeds {_MAX_DATA_POINTS} points."}, 400

        try:
            x = [float(v) for v in x_raw]
            y = [float(v) for v in y_raw]
        except (TypeError, ValueError) as exc:
            return {"detail": f"Non-numeric values: {exc}"}, 400

        regression_type = (body.get("type") or "linear").strip().lower()
        if regression_type not in ("linear", "log_linear", "power_law"):
            return {
                "detail": "Invalid type. Use 'linear', 'log_linear', or 'power_law'."
            }, 400

        bootstrap_ci = body.get("bootstrap_ci", False)
        if not isinstance(bootstrap_ci, bool):
            bootstrap_ci = str(bootstrap_ci).lower() == "true"

        n_bootstrap = int(body.get("n_bootstrap") or 500)
        if n_bootstrap < 100:
            n_bootstrap = 100
        if n_bootstrap > 5000:
            n_bootstrap = 5000

        # Run regression
        try:
            if regression_type == "linear":
                reg_result = _calc.linear_regression(x, y)
            elif regression_type == "log_linear":
                reg_result = _calc.log_linear_regression(x, y)
            else:  # power_law
                reg_result = _calc.power_law_fit(x, y)
        except (ValueError, ZeroDivisionError) as exc:
            return {"detail": f"Regression failed: {exc}"}, 400

        # Remove large arrays to keep response manageable
        predicted = reg_result.pop("predicted", None)
        residuals = reg_result.pop("residuals", None)
        if "log_regression" in reg_result:
            log_reg = reg_result.pop("log_regression", {})
            log_reg.pop("predicted", None)
            log_reg.pop("residuals", None)
            reg_result["log_regression_diagnostics"] = log_reg

        # Optional bootstrap CI on slope
        bootstrap_result = None
        if bootstrap_ci and regression_type == "linear" and len(x) >= 10:
            try:
                def slope_statistic(idx_data: list[float]) -> float:
                    """Compute slope on a bootstrap resample of paired data."""
                    # Data is encoded as flat list [x0,y0, x1,y1, ...]
                    n_half = len(idx_data) // 2
                    bx = idx_data[:n_half]
                    by = idx_data[n_half:]
                    calc = StatisticsCalculator()
                    return calc.linear_regression(bx, by)["slope"]

                # Interleave x and y for bootstrap
                interleaved = x + y
                bootstrap_result = _calc.bootstrap_confidence(
                    interleaved,
                    statistic_fn=slope_statistic,
                    n_bootstrap=n_bootstrap,
                    confidence=0.95,
                )
            except (ValueError, ZeroDivisionError) as exc:
                bootstrap_result = {"error": str(exc)}

        response = {
            "type": regression_type,
            "n": len(x),
            "result": reg_result,
        }
        if bootstrap_ci:
            response["bootstrap_ci_slope_95pct"] = bootstrap_result

        # Add brief predicted/residual summary (last 10 points)
        if predicted is not None:
            response["predicted_last10"] = [round(p, 4) for p in predicted[-10:]]
        if residuals is not None:
            response["residual_stats"] = {
                "mean": round(sum(residuals) / len(residuals), 8),
                "std": round(
                    (sum(r**2 for r in residuals) / len(residuals)) ** 0.5, 8
                ),
                "last10": [round(r, 6) for r in residuals[-10:]],
            }

        return response, 200

    except Exception as exc:
        return {"detail": f"Regression error: {exc}"}, 500


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _interpret_correlation(r: float) -> str:
    """Human-readable interpretation of a correlation coefficient."""
    abs_r = abs(r)
    direction = "positive" if r >= 0 else "negative"
    if abs_r >= 0.9:
        strength = "very strong"
    elif abs_r >= 0.7:
        strength = "strong"
    elif abs_r >= 0.5:
        strength = "moderate"
    elif abs_r >= 0.3:
        strength = "weak"
    else:
        strength = "very weak or no"
    return f"{strength} {direction} correlation"
