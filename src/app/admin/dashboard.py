"""
Admin dashboard analytics for Magma Bitcoin app.
Aggregates key metrics across users, deposits, and system health.
Pure Python stdlib — no third-party dependencies.
"""

import time
import json
import math
from typing import Optional

from ..database import get_conn as get_connection


# ---------------------------------------------------------------------------
# AdminDashboard
# ---------------------------------------------------------------------------

class AdminDashboard:
    """
    Provides all dashboard data for the Magma admin panel.
    All queries are read-only and safe to call frequently.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def get_overview(self) -> dict:
        """
        Return key platform metrics for the dashboard overview card.
        Includes user totals, deposit volume, and activity counts.
        """
        try:
            conn = get_connection()

            total_users = conn.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

            users_today = conn.execute(
                "SELECT COUNT(*) FROM users WHERE created_at >= ?",
                (int(time.time()) - 86400,),
            ).fetchone()[0]

            users_week = conn.execute(
                "SELECT COUNT(*) FROM users WHERE created_at >= ?",
                (int(time.time()) - 604800,),
            ).fetchone()[0]

            total_deposits = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount_usd), 0) FROM savings_deposits"
            ).fetchone()

            volume_today_row = conn.execute(
                "SELECT COALESCE(SUM(amount_usd), 0) FROM savings_deposits WHERE created_at >= ?",
                (int(time.time()) - 86400,),
            ).fetchone()

            btc_total = conn.execute(
                "SELECT COALESCE(SUM(btc_amount), 0) FROM savings_deposits"
            ).fetchone()[0]

            active_sessions = 0
            try:
                active_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE expires_at > ?",
                    (int(time.time()),),
                ).fetchone()[0]
            except Exception:
                pass

            achievements_total = 0
            try:
                achievements_total = conn.execute(
                    "SELECT COUNT(*) FROM user_achievements"
                ).fetchone()[0]
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "users": {
                "total":   total_users,
                "today":   users_today,
                "this_week": users_week,
            },
            "deposits": {
                "count":       total_deposits[0],
                "volume_usd":  round(total_deposits[1], 2),
                "volume_btc":  round(btc_total, 8),
                "today_usd":   round(volume_today_row[0], 2),
            },
            "engagement": {
                "active_sessions":    active_sessions,
                "achievements_earned": achievements_total,
            },
            "generated_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # User growth
    # ------------------------------------------------------------------

    def get_user_growth(self, days: int = 30) -> list:
        """
        Return daily new user counts for the past ``days`` days.
        Each entry: {"date": "YYYY-MM-DD", "new_users": int, "cumulative": int}.
        """
        days = max(1, min(days, 365))
        since = int(time.time()) - (days * 86400)

        try:
            conn = get_connection()

            rows = conn.execute(
                """
                SELECT (created_at / 86400) * 86400 as day_bucket, COUNT(*) as cnt
                FROM users
                WHERE created_at >= ?
                GROUP BY day_bucket
                ORDER BY day_bucket
                """,
                (since,),
            ).fetchall()

            total_before = conn.execute(
                "SELECT COUNT(*) FROM users WHERE created_at < ?", (since,)
            ).fetchone()[0]

        except Exception:
            return []

        result = []
        cumulative = total_before
        row_map = {row[0]: row[1] for row in rows}

        for day_offset in range(days):
            day_ts = ((int(time.time()) - (days - day_offset - 1) * 86400) // 86400) * 86400
            new_users = row_map.get(day_ts, 0)
            cumulative += new_users
            date_str = _ts_to_date(day_ts)
            result.append({
                "date":       date_str,
                "new_users":  new_users,
                "cumulative": cumulative,
            })

        return result

    # ------------------------------------------------------------------
    # Deposit volume
    # ------------------------------------------------------------------

    def get_deposit_volume(self, days: int = 30) -> list:
        """
        Return daily deposit volume for the past ``days`` days.
        Each entry: {"date": str, "count": int, "usd": float, "btc": float}.
        """
        days = max(1, min(days, 365))
        since = int(time.time()) - (days * 86400)

        try:
            conn = get_connection()
            rows = conn.execute(
                """
                SELECT (created_at / 86400) * 86400 as day_bucket,
                       COUNT(*) as cnt,
                       COALESCE(SUM(amount_usd), 0) as usd,
                       COALESCE(SUM(btc_amount), 0) as btc
                FROM savings_deposits
                WHERE created_at >= ?
                GROUP BY day_bucket
                ORDER BY day_bucket
                """,
                (since,),
            ).fetchall()
        except Exception:
            return []

        row_map = {row[0]: (row[1], row[2], row[3]) for row in rows}
        result = []

        for day_offset in range(days):
            day_ts = ((int(time.time()) - (days - day_offset - 1) * 86400) // 86400) * 86400
            cnt, usd, btc = row_map.get(day_ts, (0, 0.0, 0.0))
            result.append({
                "date":  _ts_to_date(day_ts),
                "count": cnt,
                "usd":   round(float(usd), 2),
                "btc":   round(float(btc), 8),
            })

        return result

    # ------------------------------------------------------------------
    # Active users
    # ------------------------------------------------------------------

    def get_active_users(self, days: int = 7) -> dict:
        """
        Return DAU / WAU / MAU metrics.
        'Active' is defined as having at least one deposit in the period.
        """
        now = int(time.time())

        try:
            conn = get_connection()

            dau = conn.execute(
                "SELECT COUNT(DISTINCT pubkey) FROM savings_deposits WHERE created_at >= ?",
                (now - 86400,),
            ).fetchone()[0]

            wau = conn.execute(
                "SELECT COUNT(DISTINCT pubkey) FROM savings_deposits WHERE created_at >= ?",
                (now - 604800,),
            ).fetchone()[0]

            mau = conn.execute(
                "SELECT COUNT(DISTINCT pubkey) FROM savings_deposits WHERE created_at >= ?",
                (now - 2592000,),
            ).fetchone()[0]

            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        except Exception:
            return {}

        return {
            "dau":           dau,
            "wau":           wau,
            "mau":           mau,
            "total_users":   total_users,
            "dau_mau_ratio": round(dau / mau, 4) if mau > 0 else 0,
            "wau_mau_ratio": round(wau / mau, 4) if mau > 0 else 0,
            "stickiness":    f"{round(dau / mau * 100, 1)}%" if mau > 0 else "0%",
        }

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------

    def get_retention_metrics(self) -> dict:
        """
        Return day-1, day-7, day-30 retention rates.
        Retention = users who deposited again after their first deposit.
        """
        try:
            conn = get_connection()

            # Users who signed up >= 30 days ago
            cohort_ts = int(time.time()) - (30 * 86400)

            cohort_users = conn.execute(
                "SELECT pubkey, created_at FROM users WHERE created_at <= ?",
                (cohort_ts,),
            ).fetchall()

            if not cohort_users:
                return {"day1": 0, "day7": 0, "day30": 0, "cohort_size": 0}

            cohort_size = len(cohort_users)
            day1_retained = day7_retained = day30_retained = 0

            for pubkey, signup_ts in cohort_users:
                deposits_after_signup = conn.execute(
                    "SELECT created_at FROM savings_deposits WHERE pubkey = ? AND created_at > ? ORDER BY created_at",
                    (pubkey, signup_ts),
                ).fetchall()

                if not deposits_after_signup:
                    continue

                first_return = deposits_after_signup[0][0]
                days_to_return = (first_return - signup_ts) / 86400

                if days_to_return <= 1:
                    day1_retained += 1
                if days_to_return <= 7:
                    day7_retained += 1
                if days_to_return <= 30:
                    day30_retained += 1

        except Exception:
            return {}

        return {
            "cohort_size":      cohort_size,
            "day1_count":       day1_retained,
            "day7_count":       day7_retained,
            "day30_count":      day30_retained,
            "day1_rate":        round(day1_retained / cohort_size * 100, 1) if cohort_size else 0,
            "day7_rate":        round(day7_retained / cohort_size * 100, 1) if cohort_size else 0,
            "day30_rate":       round(day30_retained / cohort_size * 100, 1) if cohort_size else 0,
        }

    # ------------------------------------------------------------------
    # Feature adoption
    # ------------------------------------------------------------------

    def get_feature_adoption(self) -> dict:
        """
        Return adoption rates for each major feature.
        """
        try:
            conn = get_connection()

            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if total_users == 0:
                return {}

            savings_users = conn.execute(
                "SELECT COUNT(DISTINCT pubkey) FROM savings_deposits"
            ).fetchone()[0]

            goals_users = 0
            try:
                goals_users = conn.execute(
                    "SELECT COUNT(*) FROM savings_goals"
                ).fetchone()[0]
            except Exception:
                pass

            achievement_users = 0
            try:
                achievement_users = conn.execute(
                    "SELECT COUNT(DISTINCT pubkey) FROM user_achievements"
                ).fetchone()[0]
            except Exception:
                pass

            alert_users = 0
            try:
                alert_users = conn.execute(
                    "SELECT COUNT(*) FROM user_preferences WHERE alerts_enabled = 1"
                ).fetchone()[0]
            except Exception:
                pass

        except Exception:
            return {}

        def pct(n):
            return round(n / total_users * 100, 1) if total_users else 0

        return {
            "total_users":         total_users,
            "savings_deposits":    {"users": savings_users,     "rate": pct(savings_users)},
            "savings_goals":       {"users": goals_users,       "rate": pct(goals_users)},
            "achievements":        {"users": achievement_users, "rate": pct(achievement_users)},
            "alerts_enabled":      {"users": alert_users,       "rate": pct(alert_users)},
        }

    # ------------------------------------------------------------------
    # Session analytics
    # ------------------------------------------------------------------

    def get_session_analytics(self) -> dict:
        """
        Return session-level statistics including auth method distribution.
        """
        try:
            conn = get_connection()

            auth_methods = conn.execute(
                "SELECT auth_method, COUNT(*) FROM users GROUP BY auth_method"
            ).fetchall()

            active_sessions = 0
            try:
                active_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE expires_at > ?",
                    (int(time.time()),),
                ).fetchone()[0]
            except Exception:
                pass

        except Exception:
            return {}

        return {
            "active_sessions": active_sessions,
            "auth_method_distribution": dict(auth_methods),
        }

    # ------------------------------------------------------------------
    # Error rates
    # ------------------------------------------------------------------

    def get_error_rates(self, hours: int = 24) -> dict:
        """
        Return API error statistics for the past ``hours`` hours.
        Reads from security_audit_log if available.
        """
        since = int(time.time()) - (hours * 3600)

        try:
            conn = get_connection()
            auth_failures = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE event_type = 'AUTH_FAILURE' AND timestamp >= ?",
                (since,),
            ).fetchone()[0]
            rate_limits = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE event_type = 'RATE_LIMIT' AND timestamp >= ?",
                (since,),
            ).fetchone()[0]
            suspicious = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE event_type = 'SUSPICIOUS' AND timestamp >= ?",
                (since,),
            ).fetchone()[0]
        except Exception:
            auth_failures = rate_limits = suspicious = 0

        return {
            "period_hours":   hours,
            "auth_failures":  auth_failures,
            "rate_limits":    rate_limits,
            "suspicious":     suspicious,
            "total_errors":   auth_failures + rate_limits + suspicious,
        }

    # ------------------------------------------------------------------
    # API usage
    # ------------------------------------------------------------------

    def get_api_usage(self) -> dict:
        """
        Return API endpoint usage statistics derived from audit logs.
        """
        since = int(time.time()) - 86400

        try:
            conn = get_connection()
            rows = conn.execute(
                """
                SELECT action, COUNT(*) as cnt
                FROM security_audit_log
                WHERE timestamp >= ?
                GROUP BY action
                ORDER BY cnt DESC
                LIMIT 20
                """,
                (since,),
            ).fetchall()
        except Exception:
            rows = []

        return {
            "period": "last_24h",
            "top_actions": [{"action": row[0], "count": row[1]} for row in rows],
        }

    # ------------------------------------------------------------------
    # System health
    # ------------------------------------------------------------------

    def get_system_health(self) -> dict:
        """
        Return a quick system health check.
        Checks database connectivity, session store, and basic counts.
        """
        checks = {}

        # Database connectivity
        try:
            conn = get_connection()
            conn.execute("SELECT 1").fetchone()
            checks["database"] = {"status": "ok"}
        except Exception as exc:
            checks["database"] = {"status": "error", "detail": str(exc)}

        # Audit log table
        try:
            conn = get_connection()
            conn.execute("SELECT COUNT(*) FROM security_audit_log").fetchone()
            checks["audit_log"] = {"status": "ok"}
        except Exception:
            checks["audit_log"] = {"status": "missing"}

        healthy = all(v.get("status") == "ok" for v in checks.values())

        return {
            "healthy":  healthy,
            "checks":   checks,
            "checked_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # Top users
    # ------------------------------------------------------------------

    def get_top_users(self, metric: str = "volume", limit: int = 10) -> list:
        """
        Return top users by the specified metric.
        Supported metrics: "volume" (total USD deposited), "count" (deposit count),
        "achievements" (achievements earned).
        """
        limit = max(1, min(limit, 100))

        try:
            conn = get_connection()

            if metric == "count":
                rows = conn.execute(
                    """
                    SELECT pubkey, COUNT(*) as metric_val
                    FROM savings_deposits
                    GROUP BY pubkey
                    ORDER BY metric_val DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            elif metric == "achievements":
                rows = conn.execute(
                    """
                    SELECT pubkey, COUNT(*) as metric_val
                    FROM user_achievements
                    GROUP BY pubkey
                    ORDER BY metric_val DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:  # volume (default)
                rows = conn.execute(
                    """
                    SELECT pubkey, COALESCE(SUM(amount_usd), 0) as metric_val
                    FROM savings_deposits
                    GROUP BY pubkey
                    ORDER BY metric_val DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        except Exception:
            return []

        return [
            {"rank": i + 1, "pubkey": row[0], "value": round(float(row[1]), 2), "metric": metric}
            for i, row in enumerate(rows)
        ]

    # ------------------------------------------------------------------
    # Cohort analysis
    # ------------------------------------------------------------------

    def get_cohort_analysis(self, months: int = 6) -> dict:
        """
        Monthly cohort retention analysis.
        Returns retention rates for each cohort month.
        """
        months = max(1, min(months, 24))
        now = int(time.time())
        cohorts = []

        try:
            conn = get_connection()

            for m in range(months, 0, -1):
                cohort_start = now - (m * 30 * 86400)
                cohort_end   = now - ((m - 1) * 30 * 86400)

                users = conn.execute(
                    "SELECT pubkey FROM users WHERE created_at BETWEEN ? AND ?",
                    (cohort_start, cohort_end),
                ).fetchall()

                if not users:
                    continue

                cohort_pubkeys = [u[0] for u in users]
                cohort_size = len(cohort_pubkeys)

                # Month-1 retention
                placeholders = ",".join("?" * cohort_size)
                retained_m1 = conn.execute(
                    f"""
                    SELECT COUNT(DISTINCT pubkey) FROM savings_deposits
                    WHERE pubkey IN ({placeholders})
                    AND created_at BETWEEN ? AND ?
                    """,
                    cohort_pubkeys + [cohort_end, cohort_end + 30 * 86400],
                ).fetchone()[0]

                cohorts.append({
                    "cohort_month":  _ts_to_month(cohort_start),
                    "cohort_size":   cohort_size,
                    "m1_retained":   retained_m1,
                    "m1_rate":       round(retained_m1 / cohort_size * 100, 1) if cohort_size else 0,
                })

        except Exception:
            return {}

        return {"cohorts": cohorts, "months_analyzed": months}

    # ------------------------------------------------------------------
    # Funnel metrics
    # ------------------------------------------------------------------

    def get_funnel_metrics(self) -> dict:
        """
        Return conversion funnel metrics:
        signup → first deposit → goal set → recurring depositor.
        """
        try:
            conn = get_connection()

            total_signups = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

            made_deposit = conn.execute(
                "SELECT COUNT(DISTINCT pubkey) FROM savings_deposits"
            ).fetchone()[0]

            set_goal = 0
            try:
                set_goal = conn.execute("SELECT COUNT(*) FROM savings_goals").fetchone()[0]
            except Exception:
                pass

            recurring = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT pubkey FROM savings_deposits
                    GROUP BY pubkey HAVING COUNT(*) >= 2
                )
                """,
            ).fetchone()[0]

        except Exception:
            return {}

        def pct(num, den):
            return round(num / den * 100, 1) if den > 0 else 0

        return {
            "signup":          {"count": total_signups,  "rate": 100.0},
            "first_deposit":   {"count": made_deposit,   "rate": pct(made_deposit, total_signups)},
            "goal_set":        {"count": set_goal,        "rate": pct(set_goal, total_signups)},
            "recurring":       {"count": recurring,       "rate": pct(recurring, total_signups)},
        }

    # ------------------------------------------------------------------
    # Geographic distribution (simplified)
    # ------------------------------------------------------------------

    def get_geographic_distribution(self) -> dict:
        """
        Return a simplified geographic distribution of users.
        Uses the security audit log IPs for GeoIP lookup.
        """
        try:
            from ..security.threats import GeoIPLookup

            conn = get_connection()
            ips = conn.execute(
                """
                SELECT DISTINCT source_ip FROM security_audit_log
                WHERE source_ip != '' AND event_type = 'AUTH_SUCCESS'
                LIMIT 500
                """,
            ).fetchall()

            geo = GeoIPLookup()
            country_counts: dict = {}

            for (ip,) in ips:
                info = geo.lookup(ip)
                country = info.get("country", "XX")
                country_counts[country] = country_counts.get(country, 0) + 1

            total = sum(country_counts.values())
            distribution = [
                {"country": c, "count": n, "percentage": round(n / total * 100, 1)}
                for c, n in sorted(country_counts.items(), key=lambda x: -x[1])
            ]

        except Exception:
            distribution = []
            total = 0

        return {
            "distribution": distribution,
            "total_located": total,
            "note": "Approximate — based on heuristic GeoIP patterns",
        }

    # ------------------------------------------------------------------
    # Revenue metrics (placeholder for future monetization)
    # ------------------------------------------------------------------

    def get_revenue_metrics(self) -> dict:
        """
        Return revenue metrics (placeholder — extend when fee model is added).
        Currently returns volume-based metrics.
        """
        try:
            conn = get_connection()

            total_volume = conn.execute(
                "SELECT COALESCE(SUM(amount_usd), 0) FROM savings_deposits"
            ).fetchone()[0]

            monthly_volume = conn.execute(
                "SELECT COALESCE(SUM(amount_usd), 0) FROM savings_deposits WHERE created_at >= ?",
                (int(time.time()) - 2592000,),
            ).fetchone()[0]

        except Exception:
            return {}

        # Hypothetical 0.5% fee
        fee_rate = 0.005
        return {
            "total_volume_usd":   round(float(total_volume), 2),
            "monthly_volume_usd": round(float(monthly_volume), 2),
            "estimated_fees_total":   round(float(total_volume) * fee_rate, 2),
            "estimated_fees_monthly": round(float(monthly_volume) * fee_rate, 2),
            "fee_rate":           fee_rate,
            "note":               "Estimated — actual fee model not yet implemented",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_to_date(ts: int) -> str:
    """Convert Unix timestamp to YYYY-MM-DD string."""
    import datetime
    try:
        return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "1970-01-01"


def _ts_to_month(ts: int) -> str:
    """Convert Unix timestamp to YYYY-MM string."""
    import datetime
    try:
        return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m")
    except Exception:
        return "1970-01"
