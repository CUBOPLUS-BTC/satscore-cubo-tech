"""Analytics HTTP route handlers.

All handlers return ``(body_dict, status_code)`` tuples; the HTTP
server is responsible for JSON serialisation and response writing.

Endpoints:
  GET  /analytics/user          -> handle_user_analytics(pubkey)
  GET  /analytics/platform      -> handle_platform_stats(body)
  GET  /analytics/dca           -> handle_dca_performance(pubkey)
  GET  /analytics/leaderboard   -> handle_leaderboard(query)
"""

from .engine import AnalyticsEngine
from .aggregator import DataAggregator
from ..validation import validate_pubkey

_engine = AnalyticsEngine()
_aggregator = DataAggregator()


def handle_user_analytics(pubkey: str) -> tuple[dict, int]:
    """GET /analytics/user — per-user activity summary.

    Combines the rolling-window activity report from the engine with
    the DCA performance snapshot and deposit-pattern analysis.

    Requires authentication (pubkey injected by the auth middleware).
    """
    try:
        if not validate_pubkey(pubkey):
            return {"detail": "Invalid pubkey"}, 400

        activity = _engine.get_user_activity(pubkey, days=30)
        dca = _aggregator.compute_dca_performance(pubkey)
        patterns = _aggregator.get_deposit_patterns(pubkey)

        return {
            "activity": activity,
            "dca_summary": {
                "total_invested_usd": dca["total_invested_usd"],
                "total_sats": dca["total_sats"],
                "avg_buy_price_usd": dca["avg_buy_price_usd"],
                "roi_pct": dca["roi_pct"],
            },
            "deposit_patterns": {
                "deposit_count": patterns["deposit_count"],
                "avg_deposit_usd": patterns["avg_deposit_usd"],
                "deposits_per_month": patterns["deposits_per_month"],
                "most_active_day": patterns["most_active_day"],
            },
        }, 200
    except Exception as exc:
        return {"detail": str(exc)}, 500


def handle_platform_stats(body: dict) -> tuple[dict, int]:
    """GET /analytics/platform — platform-wide aggregate statistics.

    No authentication required (public endpoint intended for admins /
    dashboards that are behind their own access control layer).

    Optional body / query params (currently unused, reserved for
    future date-range filtering):
      - date_from (int Unix timestamp)
      - date_to   (int Unix timestamp)
    """
    try:
        stats = _engine.get_platform_stats()
        feature_usage = _engine.get_feature_usage()

        return {
            "stats": stats,
            "top_features": feature_usage["features"][:10],
        }, 200
    except Exception as exc:
        return {"detail": str(exc)}, 500


def handle_dca_performance(pubkey: str) -> tuple[dict, int]:
    """GET /analytics/dca — full DCA performance analysis for a user.

    Returns the compute_dca_performance result, the volatility impact
    analysis, and the full savings growth time series.

    Requires authentication.
    """
    try:
        if not validate_pubkey(pubkey):
            return {"detail": "Invalid pubkey"}, 400

        performance = _aggregator.compute_dca_performance(pubkey)
        volatility = _aggregator.compute_volatility_impact(pubkey)
        growth = _aggregator.aggregate_savings_growth(pubkey)

        # Track that the user viewed this feature
        _engine.track_event("dca_performance_viewed", pubkey, {
            "total_invested_usd": performance.get("total_invested_usd"),
        })

        return {
            "performance": performance,
            "volatility_impact": volatility,
            "growth_series": growth,
        }, 200
    except Exception as exc:
        return {"detail": str(exc)}, 500


def handle_leaderboard(query: dict) -> tuple[dict, int]:
    """GET /analytics/leaderboard — anonymised top-savers leaderboard.

    Query parameters:
      - limit (int, default 10, max 100): number of entries to return

    No authentication required (all pubkeys are anonymised).
    """
    try:
        limit = int(query.get("limit", 10))
        limit = min(max(1, limit), 100)

        entries = _aggregator.get_top_savers(limit=limit)

        return {
            "leaderboard": entries,
            "total_entries": len(entries),
        }, 200
    except Exception as exc:
        return {"detail": str(exc)}, 500
