"""
Portfolio optimization for Magma Bitcoin app.

PortfolioOptimizer implements several allocation strategies:
  - Mean-variance (efficient frontier)
  - Minimum variance portfolio
  - Maximum Sharpe ratio
  - Risk parity
  - Simplified Black-Litterman
  - Rebalancing recommendations
  - Tax-loss harvesting

CorrelationMatrix computes pairwise correlations and diversification metrics.

Uses only Python standard library — no numpy/scipy.
"""

import math
import time
from typing import Optional


# ---------------------------------------------------------------------------
# Utility maths (pure Python, no third-party deps)
# ---------------------------------------------------------------------------

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _dot(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


def _mat_vec(matrix: list[list], vec: list) -> list:
    return [_dot(row, vec) for row in matrix]


def _vec_scalar(v: list, s: float) -> list:
    return [x * s for x in v]


def _vec_add(a: list, b: list) -> list:
    return [x + y for x, y in zip(a, b)]


def _vec_sub(a: list, b: list) -> list:
    return [x - y for x, y in zip(a, b)]


def _portfolio_return(weights: list, returns: list) -> float:
    return _dot(weights, returns)


def _portfolio_variance(weights: list, cov_matrix: list[list]) -> float:
    tmp = _mat_vec(cov_matrix, weights)
    return _dot(weights, tmp)


def _portfolio_std(weights: list, cov_matrix: list[list]) -> float:
    v = _portfolio_variance(weights, cov_matrix)
    return math.sqrt(max(v, 0))


def _covariance_matrix(returns_dict: dict[str, list]) -> list[list]:
    """Compute NxN covariance matrix from dict of return series."""
    assets = list(returns_dict.keys())
    n = len(assets)
    data = [returns_dict[a] for a in assets]
    min_len = min(len(d) for d in data)
    data = [d[:min_len] for d in data]

    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            mi = _mean(data[i])
            mj = _mean(data[j])
            c = sum((data[i][k] - mi) * (data[j][k] - mj)
                    for k in range(min_len)) / max(min_len - 1, 1)
            cov[i][j] = c
            cov[j][i] = c
    return cov


def _normalize_weights(weights: list) -> list:
    """Ensure weights sum to 1, clamp negatives to 0."""
    w = [max(0.0, x) for x in weights]
    total = sum(w)
    if total == 0:
        n = len(w)
        return [1.0 / n] * n
    return [x / total for x in w]


def _gradient_descent_min_var(cov_matrix, n_assets, lr=0.01, n_iter=500):
    """Simple gradient descent to find minimum variance weights."""
    w = [1.0 / n_assets] * n_assets
    for _ in range(n_iter):
        # Gradient of variance = 2 * Sigma * w
        grad = _vec_scalar(_mat_vec(cov_matrix, w), 2.0)
        # Projected gradient step
        w = _vec_sub(w, _vec_scalar(grad, lr))
        w = _normalize_weights(w)
    return w


def _golden_section_search(f, a, b, tol=1e-5):
    """Find minimum of f in [a,b] using golden section search."""
    phi = (math.sqrt(5) + 1) / 2
    c = b - (b - a) / phi
    d = a + (b - a) / phi
    for _ in range(100):
        if abs(b - a) < tol:
            break
        if f(c) < f(d):
            b = d
        else:
            a = c
        c = b - (b - a) / phi
        d = a + (b - a) / phi
    return (a + b) / 2


# ---------------------------------------------------------------------------
# PortfolioOptimizer
# ---------------------------------------------------------------------------

class PortfolioOptimizer:
    """
    Portfolio allocation and optimization engine.
    All methods accept lists of floats; no pandas/numpy required.
    """

    def optimize_allocation(self, assets: list[str], returns: list[float],
                             risk_tolerance: str = "moderate") -> dict:
        """
        Return a recommended allocation based on risk tolerance.

        Parameters
        ----------
        assets        : list of asset names
        returns       : expected annual return for each asset (as fraction, e.g. 0.10)
        risk_tolerance: 'conservative' | 'moderate' | 'aggressive'

        Returns
        -------
        dict with weights, expected_return, expected_risk, sharpe
        """
        n = len(assets)
        if n == 0:
            return {}

        # Risk tolerance → target return
        risk_config = {
            "conservative": {"target_vol": 0.10, "btc_cap": 0.20},
            "moderate":      {"target_vol": 0.25, "btc_cap": 0.50},
            "aggressive":    {"target_vol": 0.50, "btc_cap": 0.80},
        }
        cfg = risk_config.get(risk_tolerance, risk_config["moderate"])

        # Simple heuristic: weight by return-to-risk ratio
        # Use mean return directly when no covariance available
        weights_raw = [max(r, 0) for r in returns]
        total = sum(weights_raw)
        if total == 0:
            weights_raw = [1.0 / n] * n
            total = 1.0
        weights = [w / total for w in weights_raw]

        # Cap BTC if present
        btc_cap = cfg["btc_cap"]
        btc_idx = next((i for i, a in enumerate(assets)
                        if a.upper() in ("BTC", "BITCOIN")), None)
        if btc_idx is not None and weights[btc_idx] > btc_cap:
            excess = weights[btc_idx] - btc_cap
            weights[btc_idx] = btc_cap
            # Redistribute excess proportionally
            non_btc = [i for i in range(n) if i != btc_idx]
            non_btc_total = sum(weights[i] for i in non_btc) or 1
            for i in non_btc:
                weights[i] += excess * (weights[i] / non_btc_total)

        weights = _normalize_weights(weights)
        exp_return = _portfolio_return(weights, returns)
        exp_risk   = cfg["target_vol"]  # approximate

        sharpe = (exp_return - 0.05) / exp_risk if exp_risk > 0 else 0

        return {
            "risk_tolerance":  risk_tolerance,
            "weights":         {assets[i]: round(weights[i], 4) for i in range(n)},
            "expected_return": round(exp_return, 4),
            "expected_risk":   round(exp_risk, 4),
            "sharpe_ratio":    round(sharpe, 4),
        }

    def efficient_frontier(self, assets: list[str], returns_series: dict[str, list],
                            n_portfolios: int = 50) -> list[dict]:
        """
        Generate efficient frontier portfolios.

        Parameters
        ----------
        assets         : list of asset names
        returns_series : dict mapping asset → list of historical returns
        n_portfolios   : number of frontier points

        Returns
        -------
        list of {weights, expected_return, std, sharpe}
        """
        n = len(assets)
        if n < 2:
            return []

        expected_returns = [_mean(returns_series.get(a, [0.0])) * 252
                            for a in assets]
        cov_matrix = _covariance_matrix(returns_series)

        min_ret = min(expected_returns)
        max_ret = max(expected_returns)
        if min_ret == max_ret:
            return []

        frontier = []
        for i in range(n_portfolios):
            target = min_ret + (max_ret - min_ret) * i / (n_portfolios - 1)

            # Find weights that target this return with minimum variance
            # Simple parametric: mix between min-var and max-return portfolios
            w_min_var  = _gradient_descent_min_var(cov_matrix, n)
            # Max-return: all weight on highest-return asset
            max_ret_idx = expected_returns.index(max(expected_returns))
            w_max_ret  = [0.0] * n
            w_max_ret[max_ret_idx] = 1.0

            alpha = (target - min_ret) / (max_ret - min_ret) if max_ret != min_ret else 0
            alpha = max(0, min(1, alpha))
            w = _vec_add(_vec_scalar(w_min_var, 1 - alpha),
                          _vec_scalar(w_max_ret, alpha))
            w = _normalize_weights(w)

            port_ret = _portfolio_return(w, expected_returns)
            port_std = _portfolio_std(w, cov_matrix) * math.sqrt(252)
            sharpe   = (port_ret - 0.05) / port_std if port_std > 0 else 0

            frontier.append({
                "weights":          {assets[j]: round(w[j], 4) for j in range(n)},
                "expected_return":  round(port_ret, 4),
                "std":              round(port_std, 4),
                "sharpe_ratio":     round(sharpe, 4),
            })

        return frontier

    def minimum_variance_portfolio(self, assets: list[str],
                                    returns_series: dict[str, list]) -> dict:
        """
        Find the portfolio with minimum variance (lowest risk).
        """
        n = len(assets)
        if n < 2:
            return {}

        cov_matrix = _covariance_matrix(returns_series)
        w = _gradient_descent_min_var(cov_matrix, n)
        w = _normalize_weights(w)

        expected_returns = [_mean(returns_series.get(a, [0.0])) * 252 for a in assets]
        port_ret = _portfolio_return(w, expected_returns)
        port_std = _portfolio_std(w, cov_matrix) * math.sqrt(252)
        sharpe   = (port_ret - 0.05) / port_std if port_std > 0 else 0

        return {
            "portfolio_type":   "minimum_variance",
            "weights":          {assets[i]: round(w[i], 4) for i in range(n)},
            "expected_return":  round(port_ret, 4),
            "expected_std":     round(port_std, 4),
            "sharpe_ratio":     round(sharpe, 4),
        }

    def maximum_sharpe_portfolio(self, assets: list[str],
                                   returns_series: dict[str, list],
                                   risk_free_rate: float = 0.05) -> dict:
        """
        Find the portfolio with the maximum Sharpe ratio.
        Uses grid search over efficient frontier.
        """
        frontier = self.efficient_frontier(assets, returns_series, n_portfolios=100)
        if not frontier:
            return {}

        best = max(frontier, key=lambda p: p["sharpe_ratio"])
        best["portfolio_type"] = "maximum_sharpe"
        best["risk_free_rate"] = risk_free_rate
        return best

    def risk_parity_allocation(self, assets: list[str],
                                volatilities: list[float]) -> dict:
        """
        Allocate inversely proportional to volatility (risk parity).
        Each asset contributes equally to total portfolio risk.

        Parameters
        ----------
        volatilities : list of annualised volatility (as fraction, e.g. 0.80 for 80%)
        """
        n = len(assets)
        if n == 0:
            return {}

        # Weight ∝ 1/vol
        inv_vols = [1 / v if v > 0 else 0 for v in volatilities]
        total    = sum(inv_vols) or 1.0
        weights  = [iv / total for iv in inv_vols]

        weighted_vol = sum(weights[i] * volatilities[i] for i in range(n))

        return {
            "portfolio_type": "risk_parity",
            "weights":        {assets[i]: round(weights[i], 4) for i in range(n)},
            "target_equal_risk_contribution": True,
            "weighted_avg_volatility": round(weighted_vol, 4),
        }

    def black_litterman(self, prior_returns: list[float],
                         views: list[dict],
                         confidences: list[float]) -> dict:
        """
        Simplified Black-Litterman posterior return estimates.

        Parameters
        ----------
        prior_returns : list of prior expected returns (CAPM equilibrium)
        views         : list of {asset_idx, view_return} absolute views
        confidences   : list of confidence levels (0–1) for each view

        Returns
        -------
        dict with posterior_returns and interpretation
        """
        if not views or not prior_returns:
            return {"posterior_returns": prior_returns, "views_applied": 0}

        posterior = list(prior_returns)

        for view, confidence in zip(views, confidences):
            idx        = view.get("asset_idx", 0)
            view_ret   = view.get("view_return", 0)
            confidence = max(0.0, min(1.0, confidence))

            if idx < len(posterior):
                # Blend prior with view according to confidence
                posterior[idx] = (
                    posterior[idx] * (1 - confidence)
                    + view_ret * confidence
                )

        return {
            "posterior_returns":    [round(r, 4) for r in posterior],
            "prior_returns":        [round(r, 4) for r in prior_returns],
            "views_applied":        len(views),
            "methodology":          "Simplified BL: confidence-weighted blend of prior and view",
        }

    def rebalance_recommendations(self, current: dict[str, float],
                                   target: dict[str, float]) -> list[dict]:
        """
        Generate rebalancing actions to move from current to target allocation.

        Parameters
        ----------
        current : {asset: current_weight}
        target  : {asset: target_weight}

        Returns
        -------
        list of {asset, action, delta_weight, priority}
        """
        all_assets = set(list(current.keys()) + list(target.keys()))
        recommendations = []

        for asset in all_assets:
            current_w = current.get(asset, 0.0)
            target_w  = target.get(asset, 0.0)
            delta     = target_w - current_w

            if abs(delta) < 0.005:
                continue  # Less than 0.5% drift, skip

            action   = "buy" if delta > 0 else "sell"
            priority = "high" if abs(delta) > 0.10 else ("medium" if abs(delta) > 0.05 else "low")

            recommendations.append({
                "asset":         asset,
                "action":        action,
                "current_weight": round(current_w, 4),
                "target_weight":  round(target_w, 4),
                "delta_weight":   round(delta, 4),
                "priority":      priority,
            })

        recommendations.sort(key=lambda r: abs(r["delta_weight"]), reverse=True)
        return recommendations

    def tax_loss_harvesting(self, holdings: list[dict],
                             current_prices: dict[str, float]) -> list[dict]:
        """
        Identify positions with unrealized losses for tax-loss harvesting.

        Parameters
        ----------
        holdings      : list of {asset, amount, cost_basis_usd}
        current_prices: {asset: current_price}

        Returns
        -------
        list of harvesting opportunities sorted by loss magnitude
        """
        opportunities = []

        for holding in holdings:
            asset       = holding.get("asset", "BTC")
            amount      = float(holding.get("amount", 0))
            cost_basis  = float(holding.get("cost_basis_usd", 0))
            price       = current_prices.get(asset, 0)

            if price <= 0 or amount <= 0:
                continue

            current_value = amount * price
            unrealised    = current_value - cost_basis

            if unrealised < -50:  # Only worth harvesting if loss > $50
                loss_pct = (unrealised / cost_basis * 100) if cost_basis else 0
                opportunities.append({
                    "asset":            asset,
                    "amount":           round(amount, 8),
                    "cost_basis_usd":   round(cost_basis, 2),
                    "current_value_usd": round(current_value, 2),
                    "unrealised_loss":  round(unrealised, 2),
                    "loss_pct":         round(loss_pct, 2),
                    "tax_benefit_est":  round(abs(unrealised) * 0.25, 2),  # 25% marginal rate
                    "recommendation":   f"Consider selling {amount:.4f} {asset} to realise ${abs(unrealised):,.0f} loss",
                    "wash_sale_note":   "Wait 30 days before rebuying to avoid wash-sale rules (where applicable)",
                })

        opportunities.sort(key=lambda x: x["unrealised_loss"])
        return opportunities

    def calculate_rebalancing_cost(self, current: dict[str, float],
                                    target: dict[str, float],
                                    prices: dict[str, float],
                                    portfolio_value: float = 10000.0,
                                    tx_fee_pct: float = 0.001) -> dict:
        """
        Estimate transaction costs of rebalancing.

        Parameters
        ----------
        current       : {asset: weight}
        target        : {asset: weight}
        prices        : {asset: price_usd}
        portfolio_value: total portfolio value in USD
        tx_fee_pct    : transaction fee as fraction (e.g., 0.001 = 0.1%)
        """
        actions = self.rebalance_recommendations(current, target)
        total_trade_value = 0.0
        details = []

        for action in actions:
            asset       = action["asset"]
            delta_w     = abs(action["delta_weight"])
            trade_value = delta_w * portfolio_value
            fee         = trade_value * tx_fee_pct
            total_trade_value += trade_value

            details.append({
                "asset":        asset,
                "action":       action["action"],
                "trade_value_usd": round(trade_value, 2),
                "fee_usd":       round(fee, 2),
            })

        total_fees = total_trade_value * tx_fee_pct
        fee_drag_pct = total_fees / portfolio_value * 100

        return {
            "portfolio_value_usd": portfolio_value,
            "total_trade_value":   round(total_trade_value, 2),
            "total_fees_usd":      round(total_fees, 2),
            "fee_drag_pct":        round(fee_drag_pct, 4),
            "tx_fee_pct":          tx_fee_pct,
            "worthwhile":          fee_drag_pct < 0.5,  # Worth rebalancing if fees < 0.5%
            "details":             details,
        }


# ---------------------------------------------------------------------------
# CorrelationMatrix
# ---------------------------------------------------------------------------

class CorrelationMatrix:
    """
    Computes pairwise Pearson correlation coefficients from return series.
    """

    def __init__(self):
        self._assets: list[str]  = []
        self._matrix: list[list] = []

    def compute(self, returns_dict: dict[str, list]) -> dict:
        """
        Compute the full correlation matrix.

        Parameters
        ----------
        returns_dict : {asset: [return0, return1, ...]}

        Returns
        -------
        dict with assets and matrix (list of lists)
        """
        assets = list(returns_dict.keys())
        n      = len(assets)
        data   = [returns_dict[a] for a in assets]
        min_len = min(len(d) for d in data) if data else 0
        data   = [d[:min_len] for d in data]

        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    corr = self._pearson(data[i], data[j])
                    matrix[i][j] = corr
                    matrix[j][i] = corr

        self._assets = assets
        self._matrix = matrix

        return {
            "assets": assets,
            "matrix": [[round(matrix[i][j], 4) for j in range(n)] for i in range(n)],
        }

    @staticmethod
    def _pearson(x: list, y: list) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        mx, my = _mean(x), _mean(y)
        num    = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        sx     = math.sqrt(sum((v - mx) ** 2 for v in x))
        sy     = math.sqrt(sum((v - my) ** 2 for v in y))
        if sx == 0 or sy == 0:
            return 0.0
        return num / (sx * sy)

    def get_heatmap_data(self) -> list[dict]:
        """Return flattened heatmap data for frontend rendering."""
        n = len(self._assets)
        result = []
        for i in range(n):
            for j in range(n):
                result.append({
                    "asset_x":     self._assets[i],
                    "asset_y":     self._assets[j],
                    "correlation": round(self._matrix[i][j], 4),
                })
        return result

    def get_highly_correlated(self, threshold: float = 0.7) -> list[dict]:
        """Return pairs with |correlation| >= threshold."""
        n = len(self._assets)
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                corr = self._matrix[i][j]
                if abs(corr) >= threshold:
                    pairs.append({
                        "asset_1":     self._assets[i],
                        "asset_2":     self._assets[j],
                        "correlation": round(corr, 4),
                        "type":        "positive" if corr >= 0 else "negative",
                    })
        pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)
        return pairs

    def get_diversification_benefit(self) -> float:
        """
        Compute diversification benefit as the reduction in portfolio
        variance achieved by combining assets vs. holding them separately.
        Returns a 0–1 score (higher = more diversification benefit).
        """
        n = len(self._assets)
        if n < 2 or not self._matrix:
            return 0.0

        # Equal-weight portfolio correlation
        off_diagonal = [
            self._matrix[i][j]
            for i in range(n)
            for j in range(n)
            if i != j
        ]
        avg_corr = _mean(off_diagonal) if off_diagonal else 1.0

        # Benefit: 1 - avg_correlation; higher when assets are less correlated
        benefit = max(0.0, 1.0 - avg_corr)
        return round(benefit, 4)
