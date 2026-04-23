"""
Admin API route handlers for Magma Bitcoin app.
All endpoints require admin-level authorization.
Admin pubkeys are loaded from the ADMIN_PUBKEYS environment variable
(comma-separated hex pubkeys).
"""

import os
import json
import time
from typing import Optional

from .dashboard import AdminDashboard
from .users import UserManager
from .system import SystemAdmin
from ..i18n import t


# ---------------------------------------------------------------------------
# Admin authorization
# ---------------------------------------------------------------------------

def _get_admin_pubkeys() -> set:
    """Return the set of authorised admin pubkeys from the environment."""
    raw = os.environ.get("ADMIN_PUBKEYS", "")
    if not raw:
        return set()
    return {pk.strip().lower() for pk in raw.split(",") if pk.strip()}


def _require_admin(pubkey: Optional[str]) -> Optional[tuple]:
    """
    Return an error tuple if pubkey is not in the admin list.
    Returns None if the caller is authorised.
    """
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401

    admin_keys = _get_admin_pubkeys()
    if not admin_keys:
        # No admin keys configured — deny all admin access
        return {"detail": t("admin.access.not_configured")}, 403

    if pubkey.lower() not in admin_keys:
        return {"detail": t("admin.access.denied")}, 403

    return None  # Authorised


def _get_caller_pubkey(body: dict = None, query: dict = None) -> Optional[str]:
    """Extract the caller's pubkey from body or query params."""
    if body and "pubkey" in body:
        return body.get("pubkey", "").strip()
    if query and "pubkey" in query:
        return query.get("pubkey", "").strip()
    return None


# ---------------------------------------------------------------------------
# Singleton service instances
# ---------------------------------------------------------------------------

_dashboard = AdminDashboard()
_users     = UserManager()
_system    = SystemAdmin()


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_admin_overview(body: dict) -> tuple:
    """
    GET/POST /admin/overview
    Returns the full admin dashboard overview.
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    return {
        "overview":       _dashboard.get_overview(),
        "active_users":   _dashboard.get_active_users(),
        "feature_adoption": _dashboard.get_feature_adoption(),
        "system_health":  _dashboard.get_system_health(),
        "error_rates":    _dashboard.get_error_rates(hours=24),
        "funnel":         _dashboard.get_funnel_metrics(),
        "generated_at":   int(time.time()),
    }, 200


def handle_admin_users(query: dict) -> tuple:
    """
    GET /admin/users
    Returns a paginated, filterable list of users.

    Query params: pubkey (auth), limit, offset, sort_by, order,
                  auth_method, banned, created_after, created_before
    """
    pubkey = _get_caller_pubkey(query=query)
    err = _require_admin(pubkey)
    if err:
        return err

    limit    = _safe_int(query.get("limit", 50), 1, 200, 50)
    offset   = _safe_int(query.get("offset", 0), 0, 1_000_000, 0)
    sort_by  = query.get("sort_by", "created_at")
    order    = query.get("order", "desc")

    filter_by = {}
    if "auth_method" in query:
        filter_by["auth_method"] = query["auth_method"]
    if "created_after" in query:
        filter_by["created_after"] = query["created_after"]
    if "created_before" in query:
        filter_by["created_before"] = query["created_before"]
    if query.get("banned") in ("true", "1", "yes"):
        filter_by["banned"] = True

    result = _users.list_users(
        limit=limit, offset=offset,
        sort_by=sort_by, order=order,
        filter_by=filter_by,
    )

    if "error" in result:
        return result, 500

    return result, 200


def handle_admin_user_detail(query: dict) -> tuple:
    """
    GET /admin/user
    Returns the full profile for a single user.

    Query params: pubkey (auth), target_pubkey
    """
    pubkey = _get_caller_pubkey(query=query)
    err = _require_admin(pubkey)
    if err:
        return err

    target = query.get("target_pubkey", "").strip()
    if not target:
        return {"detail": t("admin.target.required")}, 400

    detail = _users.get_user_detail(target)
    if "error" in detail:
        if detail["error"] == "user_not_found":
            return {"detail": t("admin.user.not_found")}, 404
        return detail, 500

    # Also attach activity and risk score
    detail["risk_score"]  = _users.get_user_risk_score(target)
    detail["deposits"]    = _users.get_user_deposits(target, limit=20)
    detail["sessions"]    = _users.get_user_sessions(target)

    return detail, 200


def handle_admin_user_activity(query: dict) -> tuple:
    """
    GET /admin/user/activity
    Returns the activity timeline for a user.
    """
    pubkey = _get_caller_pubkey(query=query)
    err = _require_admin(pubkey)
    if err:
        return err

    target = query.get("target_pubkey", "").strip()
    days   = _safe_int(query.get("days", 30), 1, 365, 30)

    if not target:
        return {"detail": t("admin.target.required")}, 400

    result = _users.get_user_activity(target, days=days)
    return result, 200


def handle_admin_system(body: dict) -> tuple:
    """
    POST /admin/system
    Returns system information and stats.
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    return {
        "system_info":     _system.get_system_info(),
        "database_stats":  _system.get_database_stats(),
        "cache_stats":     _system.get_cache_stats(),
        "connection_stats": _system.get_connection_stats(),
        "background_tasks": _system.get_background_tasks(),
        "rate_limit_stats": _system.get_rate_limit_stats(),
        "uptime":          _system.get_uptime(),
    }, 200


def handle_admin_diagnostics(body: dict) -> tuple:
    """
    POST /admin/diagnostics
    Runs the full diagnostic suite.
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    return _system.run_diagnostics(), 200


def handle_admin_performance(body: dict) -> tuple:
    """
    POST /admin/performance
    Returns request latency percentiles.
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    return _system.get_performance_metrics(), 200


def handle_admin_user_ban(body: dict) -> tuple:
    """
    POST /admin/user/ban
    Ban or unban a user.

    Body: pubkey (auth), target_pubkey, action ("ban"|"unban"),
          reason (optional), duration_seconds (optional, default 0=permanent)
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    target   = (body.get("target_pubkey") or "").strip()
    action   = (body.get("action") or "ban").lower()
    reason   = (body.get("reason") or "Admin action").strip()
    duration = _safe_int(body.get("duration_seconds", 0), 0, 86400 * 365, 0)

    if not target:
        return {"detail": t("admin.target.required")}, 400

    if action == "unban":
        result = _users.unban_user(target, unbanned_by=pubkey)
    else:
        result = _users.ban_user(target, reason=reason, duration=duration, banned_by=pubkey)

    if "error" in result:
        return result, 500

    return result, 200


def handle_admin_user_sessions(body: dict) -> tuple:
    """
    POST /admin/user/sessions
    Revoke a specific session or all sessions for a user.

    Body: pubkey (auth), target_pubkey, action ("revoke_all"|"revoke"),
          token (required for action="revoke")
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    target = (body.get("target_pubkey") or "").strip()
    action = (body.get("action") or "revoke_all").lower()
    token  = (body.get("token") or "").strip()

    if not target:
        return {"detail": t("admin.target.required")}, 400

    if action == "revoke_all":
        count = _users.revoke_all_sessions(target)
        return {"target_pubkey": target, "sessions_revoked": count}, 200

    if action == "revoke":
        if not token:
            return {"detail": t("admin.token.required")}, 400
        ok = _users.revoke_session(target, token)
        return {"target_pubkey": target, "revoked": ok}, 200

    return {"detail": t("admin.action.unknown", action=action)}, 400


def handle_admin_config(body: dict) -> tuple:
    """
    POST /admin/config
    Read or update runtime configuration.

    Body: pubkey (auth), action ("get"|"set"), key (for set), value (for set)
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    action = (body.get("action") or "get").lower()

    if action == "get":
        return _system.get_config(), 200

    if action == "set":
        key   = (body.get("key") or "").strip()
        value = body.get("value")

        if not key:
            return {"detail": t("admin.key.required")}, 400

        result = _system.update_config(key, value)
        if "error" in result:
            return result, 400

        return result, 200

    return {"detail": t("admin.action.unknown", action=action)}, 400


def handle_admin_maintenance(body: dict) -> tuple:
    """
    POST /admin/maintenance
    Run database and in-memory maintenance operations.
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    result = _system.run_maintenance()
    return result, 200


def handle_admin_export_user(body: dict) -> tuple:
    """
    POST /admin/user/export
    Export all data for a user (GDPR).

    Body: pubkey (auth), target_pubkey
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    target = (body.get("target_pubkey") or "").strip()
    if not target:
        return {"detail": t("admin.target.required")}, 400

    result = _users.export_user_data(target)
    if "error" in result:
        if result["error"] == "user_not_found":
            return {"detail": t("admin.user.not_found")}, 404
        return result, 500

    return result, 200


def handle_admin_delete_user(body: dict) -> tuple:
    """
    POST /admin/user/delete
    GDPR right-to-erasure: delete all data for a user.

    Body: pubkey (auth), target_pubkey, confirm ("DELETE")
    """
    pubkey = _get_caller_pubkey(body=body)
    err = _require_admin(pubkey)
    if err:
        return err

    target  = (body.get("target_pubkey") or "").strip()
    confirm = (body.get("confirm") or "").strip()

    if not target:
        return {"detail": t("admin.target.required")}, 400

    if confirm != "DELETE":
        return {"detail": t("admin.delete.confirm")}, 400

    result = _users.delete_user_data(target, deleted_by=pubkey)
    if "error" in result:
        return result, 500

    return result, 200


def handle_admin_growth(query: dict) -> tuple:
    """
    GET /admin/growth
    Returns user growth and deposit volume charts.
    """
    pubkey = _get_caller_pubkey(query=query)
    err = _require_admin(pubkey)
    if err:
        return err

    days = _safe_int(query.get("days", 30), 1, 365, 30)

    return {
        "user_growth":    _dashboard.get_user_growth(days=days),
        "deposit_volume": _dashboard.get_deposit_volume(days=days),
        "retention":      _dashboard.get_retention_metrics(),
        "cohorts":        _dashboard.get_cohort_analysis(months=6),
    }, 200


def handle_admin_top_users(query: dict) -> tuple:
    """
    GET /admin/top-users
    Returns top users by a given metric.
    """
    pubkey = _get_caller_pubkey(query=query)
    err = _require_admin(pubkey)
    if err:
        return err

    metric = query.get("metric", "volume")
    limit  = _safe_int(query.get("limit", 10), 1, 100, 10)

    result = _dashboard.get_top_users(metric=metric, limit=limit)
    return {"top_users": result, "metric": metric}, 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(value, min_val: int, max_val: int, default: int) -> int:
    """Safely parse an integer from a query/body value, clamped to range."""
    try:
        return max(min_val, min(max_val, int(value)))
    except (TypeError, ValueError):
        return default
