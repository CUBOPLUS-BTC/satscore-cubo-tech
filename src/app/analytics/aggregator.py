"""Data Aggregator — deposit and savings aggregations, DCA metrics, leaderboard.

Provides:
  - aggregate_deposits: daily/weekly/monthly deposit buckets per user
  - aggregate_savings_growth: cumulative BTC and USD growth over time
  - compute_dca_performance: average buy price, unrealised ROI, etc.
  - compute_volatility_impact: how price swings affected DCA outcomes
  - get_top_savers: anonymised leaderboard by total sats saved
  - get_deposit_patterns: day-of-week and frequency analysis
"""

import hashlib
import json
import math
import time
from ..database import get_conn, _is_postgres

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SATOSHIS_PER_BTC = 100_000_000


def _ph() -> str:
    return "%s" if _is_postgres() else "?"


def _row_get(row, key_or_index, default=None):
    """Unified accessor for sqlite3.Row and plain tuples."""
    try:
        if hasattr(row, "keys"):
            return row[key_or_index] if isinstance(key_or_index, str) else list(row)[key_or_index]
        return row[key_or_index]
    except (IndexError, KeyError):
        return default


def _anonymise(pubkey: str) -> str:
    """Return a short, stable, non-reversible alias for leaderboard display."""
    digest = hashlib.sha256(pubkey.encode()).hexdigest()[:8]
    return f"saver_{digest}"


def _period_bucket(ts: int, period: str) -> str:
    """Convert a Unix timestamp to a bucket label for the requested period."""
    import datetime
    dt = datetime.datetime.utcfromtimestamp(ts)
    if period == "daily":
        return dt.strftime("%Y-%m-%d")
    if period == "weekly":
        # ISO week string
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    # monthly (default)
    return dt.strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DataAggregator:
    """Aggregates raw deposit and event data into useful analytical summaries."""

    # ------------------------------------------------------------------
    # Deposit aggregation
    # ------------------------------------------------------------------

    def aggregate_deposits(self, pubkey: str, period: str = "monthly") -> list:
        """Aggregate deposits into time buckets for charting.

        Parameters
        ----------
        pubkey:
            Target user's public key.
        period:
            One of ``"daily"``, ``"weekly"``, or ``"monthly"``
            (default ``"monthly"``).

        Returns
        -------
        list of dict, each with keys:
            bucket (label), deposit_count, total_usd,
            total_btc, avg_btc_price, avg_usd_per_deposit
        Sorted chronologically.
        """
        if period not in ("daily", "weekly", "monthly"):
            period = "monthly"

        conn = get_conn()
        p = _ph()
        rows = conn.execute(
            f"SELECT amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p}"
            f" ORDER BY created_at ASC",
            (pubkey,),
        ).fetchall()

        buckets: dict[str, dict] = {}
        for row in rows:
            usd = float(_row_get(row, "amount_usd" if hasattr(row, "keys") else 0) or 0)
            price = float(_row_get(row, "btc_price" if hasattr(row, "keys") else 1) or 0)
            btc = float(_row_get(row, "btc_amount" if hasattr(row, "keys") else 2) or 0)
            ts = int(_row_get(row, "created_at" if hasattr(row, "keys") else 3) or 0)

            label = _period_bucket(ts, period)
            if label not in buckets:
                buckets[label] = {
                    "bucket": label,
                    "deposit_count": 0,
                    "total_usd": 0.0,
                    "total_btc": 0.0,
                    "_price_sum": 0.0,
                }
            b = buckets[label]
            b["deposit_count"] += 1
            b["total_usd"] += usd
            b["total_btc"] += btc
            b["_price_sum"] += price

        result = []
        for label in sorted(buckets.keys()):
            b = buckets[label]
            count = b["deposit_count"]
            avg_price = round(b["_price_sum"] / count, 2) if count else 0.0
            result.append({
                "bucket": label,
                "deposit_count": count,
                "total_usd": round(b["total_usd"], 2),
                "total_btc": round(b["total_btc"], 8),
                "avg_btc_price": avg_price,
                "avg_usd_per_deposit": round(b["total_usd"] / count, 2) if count else 0.0,
            })
        return result

    # ------------------------------------------------------------------
    # Savings growth
    # ------------------------------------------------------------------

    def aggregate_savings_growth(self, pubkey: str) -> list:
        """Return cumulative savings growth as a time series.

        Each point represents the state of the user's savings immediately
        after a deposit: cumulative USD invested, cumulative BTC held,
        and the current value of that BTC at the deposit price.

        Returns
        -------
        list of dict with keys:
            date (YYYY-MM-DD), deposit_usd, cumulative_usd,
            deposit_btc, cumulative_btc, cumulative_value_usd (at deposit price),
            btc_price_at_deposit
        """
        conn = get_conn()
        p = _ph()
        rows = conn.execute(
            f"SELECT amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p}"
            f" ORDER BY created_at ASC",
            (pubkey,),
        ).fetchall()

        import datetime

        cum_usd = 0.0
        cum_btc = 0.0
        series = []

        for row in rows:
            usd = float(_row_get(row, "amount_usd" if hasattr(row, "keys") else 0) or 0)
            price = float(_row_get(row, "btc_price" if hasattr(row, "keys") else 1) or 1)
            btc = float(_row_get(row, "btc_amount" if hasattr(row, "keys") else 2) or 0)
            ts = int(_row_get(row, "created_at" if hasattr(row, "keys") else 3) or 0)

            cum_usd += usd
            cum_btc += btc
            dt_str = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")

            series.append({
                "date": dt_str,
                "timestamp": ts,
                "deposit_usd": round(usd, 2),
                "cumulative_usd": round(cum_usd, 2),
                "deposit_btc": round(btc, 8),
                "cumulative_btc": round(cum_btc, 8),
                "cumulative_sats": int(cum_btc * SATOSHIS_PER_BTC),
                "cumulative_value_usd": round(cum_btc * price, 2),
                "btc_price_at_deposit": round(price, 2),
            })

        return series

    # ------------------------------------------------------------------
    # DCA performance
    # ------------------------------------------------------------------

    def compute_dca_performance(self, pubkey: str) -> dict:
        """Compute Dollar-Cost Averaging performance metrics.

        Uses the weighted average purchase price (WAPP) across all
        deposits.  An estimated current BTC price is obtained from the
        most recent deposit price as a conservative proxy.

        Returns
        -------
        dict with keys:
            total_invested_usd, total_btc, total_sats,
            avg_buy_price_usd, deposits, first_deposit_at,
            last_deposit_at, holding_days,
            current_price_usd (last known),
            current_value_usd, unrealised_pnl_usd,
            unrealised_pnl_pct, roi_pct,
            best_buy_usd, worst_buy_usd, price_range_pct
        """
        conn = get_conn()
        p = _ph()
        rows = conn.execute(
            f"SELECT amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p}"
            f" ORDER BY created_at ASC",
            (pubkey,),
        ).fetchall()

        if not rows:
            return {
                "total_invested_usd": 0.0,
                "total_btc": 0.0,
                "total_sats": 0,
                "avg_buy_price_usd": 0.0,
                "deposits": 0,
                "first_deposit_at": None,
                "last_deposit_at": None,
                "holding_days": 0,
                "current_price_usd": 0.0,
                "current_value_usd": 0.0,
                "unrealised_pnl_usd": 0.0,
                "unrealised_pnl_pct": 0.0,
                "roi_pct": 0.0,
                "best_buy_usd": 0.0,
                "worst_buy_usd": 0.0,
                "price_range_pct": 0.0,
            }

        total_usd = 0.0
        total_btc = 0.0
        prices = []
        first_ts: int | None = None
        last_ts: int | None = None

        for row in rows:
            usd = float(_row_get(row, "amount_usd" if hasattr(row, "keys") else 0) or 0)
            price = float(_row_get(row, "btc_price" if hasattr(row, "keys") else 1) or 0)
            btc = float(_row_get(row, "btc_amount" if hasattr(row, "keys") else 2) or 0)
            ts = int(_row_get(row, "created_at" if hasattr(row, "keys") else 3) or 0)

            total_usd += usd
            total_btc += btc
            if price > 0:
                prices.append(price)
            if first_ts is None:
                first_ts = ts
            last_ts = ts

        deposits = len(rows)
        avg_buy_price = total_usd / total_btc if total_btc > 0 else 0.0
        current_price = prices[-1] if prices else 0.0
        current_value = total_btc * current_price
        pnl_usd = current_value - total_usd
        pnl_pct = (pnl_usd / total_usd * 100) if total_usd > 0 else 0.0
        holding_days = ((last_ts - first_ts) // 86400) if (first_ts and last_ts) else 0

        best_buy = min(prices) if prices else 0.0
        worst_buy = max(prices) if prices else 0.0
        price_range_pct = ((worst_buy - best_buy) / best_buy * 100) if best_buy > 0 else 0.0

        return {
            "total_invested_usd": round(total_usd, 2),
            "total_btc": round(total_btc, 8),
            "total_sats": int(total_btc * SATOSHIS_PER_BTC),
            "avg_buy_price_usd": round(avg_buy_price, 2),
            "deposits": deposits,
            "first_deposit_at": first_ts,
            "last_deposit_at": last_ts,
            "holding_days": holding_days,
            "current_price_usd": round(current_price, 2),
            "current_value_usd": round(current_value, 2),
            "unrealised_pnl_usd": round(pnl_usd, 2),
            "unrealised_pnl_pct": round(pnl_pct, 2),
            "roi_pct": round(pnl_pct, 2),
            "best_buy_usd": round(best_buy, 2),
            "worst_buy_usd": round(worst_buy, 2),
            "price_range_pct": round(price_range_pct, 2),
        }

    # ------------------------------------------------------------------
    # Volatility impact
    # ------------------------------------------------------------------

    def compute_volatility_impact(self, pubkey: str) -> dict:
        """Quantify how BTC price volatility affected a user's DCA outcomes.

        Compares what the user would have paid in a hypothetical
        lump-sum scenario (buying everything at the first price) against
        their actual DCA result to compute the "volatility benefit"
        (positive when DCA beat lump-sum).

        Also computes the standard deviation of purchase prices and the
        coefficient of variation as a normalised volatility measure.

        Returns
        -------
        dict with keys:
            deposit_count, price_std_dev, coefficient_of_variation,
            lump_sum_avg_price, dca_avg_price,
            volatility_benefit_pct, best_month, worst_month,
            monthly_price_variance (list of {month, avg_price, deposit_count})
        """
        conn = get_conn()
        p = _ph()
        rows = conn.execute(
            f"SELECT amount_usd, btc_price, btc_amount, created_at"
            f" FROM savings_deposits WHERE pubkey = {p}"
            f" ORDER BY created_at ASC",
            (pubkey,),
        ).fetchall()

        if not rows:
            return {
                "deposit_count": 0,
                "price_std_dev": 0.0,
                "coefficient_of_variation": 0.0,
                "lump_sum_avg_price": 0.0,
                "dca_avg_price": 0.0,
                "volatility_benefit_pct": 0.0,
                "best_month": None,
                "worst_month": None,
                "monthly_price_variance": [],
            }

        import datetime

        prices = []
        monthly_data: dict[str, list] = {}
        total_usd = 0.0
        total_btc = 0.0

        for row in rows:
            usd = float(_row_get(row, "amount_usd" if hasattr(row, "keys") else 0) or 0)
            price = float(_row_get(row, "btc_price" if hasattr(row, "keys") else 1) or 0)
            btc = float(_row_get(row, "btc_amount" if hasattr(row, "keys") else 2) or 0)
            ts = int(_row_get(row, "created_at" if hasattr(row, "keys") else 3) or 0)

            if price <= 0:
                continue
            prices.append(price)
            total_usd += usd
            total_btc += btc

            month = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m")
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(price)

        if not prices:
            return {
                "deposit_count": len(rows),
                "price_std_dev": 0.0,
                "coefficient_of_variation": 0.0,
                "lump_sum_avg_price": 0.0,
                "dca_avg_price": 0.0,
                "volatility_benefit_pct": 0.0,
                "best_month": None,
                "worst_month": None,
                "monthly_price_variance": [],
            }

        n = len(prices)
        mean_price = sum(prices) / n
        variance = sum((p_ - mean_price) ** 2 for p_ in prices) / n
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_price if mean_price > 0 else 0.0

        # Lump-sum equivalent: invest everything at the first price
        lump_sum_price = prices[0]
        dca_avg = total_usd / total_btc if total_btc > 0 else 0.0
        volatility_benefit = (
            (lump_sum_price - dca_avg) / lump_sum_price * 100
            if lump_sum_price > 0
            else 0.0
        )

        monthly_variance = []
        best_month = None
        worst_month = None
        best_price = None
        worst_price = None

        for month in sorted(monthly_data.keys()):
            month_prices = monthly_data[month]
            avg = sum(month_prices) / len(month_prices)
            monthly_variance.append({
                "month": month,
                "avg_price": round(avg, 2),
                "deposit_count": len(month_prices),
            })
            if best_price is None or avg < best_price:
                best_price = avg
                best_month = month
            if worst_price is None or avg > worst_price:
                worst_price = avg
                worst_month = month

        return {
            "deposit_count": n,
            "price_std_dev": round(std_dev, 2),
            "coefficient_of_variation": round(cv, 4),
            "lump_sum_avg_price": round(lump_sum_price, 2),
            "dca_avg_price": round(dca_avg, 2),
            "volatility_benefit_pct": round(volatility_benefit, 2),
            "best_month": best_month,
            "worst_month": worst_month,
            "monthly_price_variance": monthly_variance,
        }

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_top_savers(self, limit: int = 10) -> list:
        """Return an anonymised leaderboard of top savers by sats accumulated.

        Parameters
        ----------
        limit:
            Maximum number of entries to return (default 10, max 100).

        Returns
        -------
        list of dict with keys:
            rank, alias, total_sats, total_btc, deposit_count,
            holding_days
        Sorted by total_sats descending.
        """
        limit = min(max(1, limit), 100)
        conn = get_conn()

        rows = conn.execute(
            "SELECT pubkey,"
            "       COUNT(*) AS deposit_count,"
            "       SUM(btc_amount) AS total_btc,"
            "       SUM(amount_usd) AS total_usd,"
            "       MIN(created_at) AS first_dep,"
            "       MAX(created_at) AS last_dep"
            " FROM savings_deposits"
            " GROUP BY pubkey"
            " ORDER BY total_btc DESC"
            f" LIMIT {limit}"
        ).fetchall()

        now = int(time.time())
        leaderboard = []
        for rank, row in enumerate(rows, start=1):
            pk = _row_get(row, "pubkey" if hasattr(row, "keys") else 0) or ""
            count = int(_row_get(row, "deposit_count" if hasattr(row, "keys") else 1) or 0)
            total_btc = float(_row_get(row, "total_btc" if hasattr(row, "keys") else 2) or 0)
            first_dep = int(_row_get(row, "first_dep" if hasattr(row, "keys") else 4) or now)
            last_dep = int(_row_get(row, "last_dep" if hasattr(row, "keys") else 5) or now)
            holding_days = max(0, (last_dep - first_dep) // 86400)

            leaderboard.append({
                "rank": rank,
                "alias": _anonymise(pk),
                "total_sats": int(total_btc * SATOSHIS_PER_BTC),
                "total_btc": round(total_btc, 8),
                "deposit_count": count,
                "holding_days": holding_days,
            })

        return leaderboard

    # ------------------------------------------------------------------
    # Deposit patterns
    # ------------------------------------------------------------------

    def get_deposit_patterns(self, pubkey: str) -> dict:
        """Analyse deposit timing patterns for a user.

        Examines day-of-week distribution, hour-of-day distribution,
        inter-deposit interval statistics, and overall deposit
        frequency (deposits per month).

        Returns
        -------
        dict with keys:
            deposit_count, avg_deposit_usd, median_deposit_usd,
            by_day_of_week (list[7] of {day, count, pct}),
            by_hour_of_day (list[24] of {hour, count, pct}),
            avg_interval_days, min_interval_days, max_interval_days,
            deposits_per_month, most_active_day, most_active_hour
        """
        conn = get_conn()
        p = _ph()
        rows = conn.execute(
            f"SELECT amount_usd, created_at FROM savings_deposits"
            f" WHERE pubkey = {p} ORDER BY created_at ASC",
            (pubkey,),
        ).fetchall()

        if not rows:
            return {
                "deposit_count": 0,
                "avg_deposit_usd": 0.0,
                "median_deposit_usd": 0.0,
                "by_day_of_week": [],
                "by_hour_of_day": [],
                "avg_interval_days": 0.0,
                "min_interval_days": 0.0,
                "max_interval_days": 0.0,
                "deposits_per_month": 0.0,
                "most_active_day": None,
                "most_active_hour": None,
            }

        import datetime

        amounts = []
        dow_counts = [0] * 7  # 0=Monday ... 6=Sunday
        hod_counts = [0] * 24
        timestamps = []

        for row in rows:
            usd = float(_row_get(row, "amount_usd" if hasattr(row, "keys") else 0) or 0)
            ts = int(_row_get(row, "created_at" if hasattr(row, "keys") else 1) or 0)
            dt = datetime.datetime.utcfromtimestamp(ts)

            amounts.append(usd)
            timestamps.append(ts)
            dow_counts[dt.weekday()] += 1
            hod_counts[dt.hour] += 1

        count = len(amounts)
        avg_usd = sum(amounts) / count
        sorted_amounts = sorted(amounts)
        mid = count // 2
        median_usd = (
            sorted_amounts[mid]
            if count % 2 != 0
            else (sorted_amounts[mid - 1] + sorted_amounts[mid]) / 2
        )

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_dow = [
            {
                "day": day_names[i],
                "day_index": i,
                "count": dow_counts[i],
                "pct": round(dow_counts[i] / count * 100, 1),
            }
            for i in range(7)
        ]
        by_hod = [
            {
                "hour": i,
                "label": f"{i:02d}:00",
                "count": hod_counts[i],
                "pct": round(hod_counts[i] / count * 100, 1),
            }
            for i in range(24)
        ]

        # Inter-deposit intervals
        intervals_days = []
        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i - 1]) / 86400
            if diff >= 0:
                intervals_days.append(diff)

        avg_interval = sum(intervals_days) / len(intervals_days) if intervals_days else 0.0
        min_interval = min(intervals_days) if intervals_days else 0.0
        max_interval = max(intervals_days) if intervals_days else 0.0

        # Deposits per month
        if len(timestamps) >= 2:
            span_days = max(1, (timestamps[-1] - timestamps[0]) / 86400)
            deps_per_month = count / (span_days / 30.44)
        else:
            deps_per_month = float(count)

        most_active_day = day_names[dow_counts.index(max(dow_counts))]
        most_active_hour = hod_counts.index(max(hod_counts))

        return {
            "deposit_count": count,
            "avg_deposit_usd": round(avg_usd, 2),
            "median_deposit_usd": round(median_usd, 2),
            "by_day_of_week": by_dow,
            "by_hour_of_day": by_hod,
            "avg_interval_days": round(avg_interval, 2),
            "min_interval_days": round(min_interval, 2),
            "max_interval_days": round(max_interval, 2),
            "deposits_per_month": round(deps_per_month, 2),
            "most_active_day": most_active_day,
            "most_active_hour": most_active_hour,
        }
