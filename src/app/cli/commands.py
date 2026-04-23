"""
Individual command implementations for the Magma admin CLI.

Each cmd_*() function performs a single, focused task and returns a dict (or
list of dicts) that the admin.py layer renders into a formatted table or
summary.  No function in this module prints directly — output is the
caller's concern so that commands remain testable.
"""

import time
import json
import sqlite3
from typing import Optional, Any


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_conn():
    """Return the live database connection."""
    from app.database import get_conn
    return get_conn()


def _is_postgres() -> bool:
    from app.database import _is_postgres as _pg
    return _pg()


def _ph() -> str:
    return "%s" if _is_postgres() else "?"


def _table_exists(conn, name: str) -> bool:
    """Return True if the table exists in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Database commands
# ---------------------------------------------------------------------------


def cmd_db_status() -> dict:
    """Return database statistics including table row counts."""
    conn = _get_conn()
    tables = [
        "users",
        "user_preferences",
        "savings_goals",
        "savings_deposits",
        "user_achievements",
        "scoring_history",
        "analytics_events",
        "scheduled_tasks",
        "webhook_subscriptions",
        "rate_limits",
        "_migrations",
    ]
    stats = []
    for tbl in tables:
        if _table_exists(conn, tbl):
            row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            stats.append({"table": tbl, "rows": row[0], "exists": True})
        else:
            stats.append({"table": tbl, "rows": 0, "exists": False})

    return {
        "tables": stats,
        "total_tables_known": len(tables),
        "tables_present": sum(1 for s in stats if s["exists"]),
    }


def cmd_db_migrate() -> dict:
    """Apply all pending database migrations."""
    from app.migrations.runner import MigrationRunner
    conn = _get_conn()
    runner = MigrationRunner(conn, is_postgres=_is_postgres())
    pending = runner.get_pending()
    if not pending:
        return {"applied": [], "message": "Already up to date — no pending migrations."}
    results = runner.apply_all()
    return {
        "applied": results,
        "message": f"Applied {len(results)} migration(s).",
    }


def cmd_db_rollback(target: str) -> dict:
    """Roll back migrations to (and including) the target migration ID.

    Args:
        target: Migration ID to roll back to, e.g. "0003".
    """
    from app.migrations.runner import MigrationRunner
    conn = _get_conn()
    runner = MigrationRunner(conn, is_postgres=_is_postgres())
    results = runner.rollback_to(target)
    return {
        "rolled_back": results,
        "message": f"Rolled back {len(results)} migration(s) to {target!r}.",
    }


# ---------------------------------------------------------------------------
# User commands
# ---------------------------------------------------------------------------


def cmd_user_list(limit: int = 20, offset: int = 0) -> dict:
    """List users with pagination.

    Args:
        limit:  Maximum rows to return (default 20).
        offset: Skip this many rows (default 0).
    """
    conn = _get_conn()
    ph = _ph()
    rows = conn.execute(
        f"SELECT pubkey, auth_method, created_at FROM users "
        f"ORDER BY created_at DESC LIMIT {ph} OFFSET {ph}",
        (limit, offset),
    ).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    users = [
        {
            "pubkey": r[0] if isinstance(r, tuple) else r["pubkey"],
            "auth_method": r[1] if isinstance(r, tuple) else r["auth_method"],
            "created_at": r[2] if isinstance(r, tuple) else r["created_at"],
        }
        for r in rows
    ]
    return {
        "users": users,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


def cmd_user_info(pubkey: str) -> dict:
    """Return detailed information about a single user.

    Includes preferences, savings goal, deposit count, and achievements.

    Args:
        pubkey: 64-char hex pubkey of the user.
    """
    conn = _get_conn()
    ph = _ph()

    user_row = conn.execute(
        f"SELECT pubkey, auth_method, created_at FROM users WHERE pubkey = {ph}",
        (pubkey,),
    ).fetchone()

    if user_row is None:
        return {"found": False, "pubkey": pubkey}

    # Preferences
    pref_row = conn.execute(
        f"SELECT fee_alert_low, fee_alert_high, alerts_enabled FROM user_preferences WHERE pubkey = {ph}",
        (pubkey,),
    ).fetchone()

    # Savings goal
    goal_row = conn.execute(
        f"SELECT monthly_target_usd, target_years FROM savings_goals WHERE pubkey = {ph}",
        (pubkey,),
    ).fetchone()

    # Deposit count
    dep_count = conn.execute(
        f"SELECT COUNT(*) FROM savings_deposits WHERE pubkey = {ph}",
        (pubkey,),
    ).fetchone()[0]

    # Achievement count
    ach_count = conn.execute(
        f"SELECT COUNT(*) FROM user_achievements WHERE pubkey = {ph}",
        (pubkey,),
    ).fetchone()[0]

    def _get(row, idx, key):
        if row is None:
            return None
        return row[idx] if isinstance(row, tuple) else row[key]

    return {
        "found": True,
        "pubkey": _get(user_row, 0, "pubkey"),
        "auth_method": _get(user_row, 1, "auth_method"),
        "created_at": _get(user_row, 2, "created_at"),
        "preferences": {
            "fee_alert_low": _get(pref_row, 0, "fee_alert_low"),
            "fee_alert_high": _get(pref_row, 1, "fee_alert_high"),
            "alerts_enabled": _get(pref_row, 2, "alerts_enabled"),
        } if pref_row else None,
        "savings_goal": {
            "monthly_target_usd": _get(goal_row, 0, "monthly_target_usd"),
            "target_years": _get(goal_row, 1, "target_years"),
        } if goal_row else None,
        "deposit_count": dep_count,
        "achievement_count": ach_count,
    }


def cmd_user_delete(pubkey: str) -> dict:
    """Delete a user and all associated data (cascades via FK or manual delete).

    Args:
        pubkey: 64-char hex pubkey of the user to delete.
    """
    conn = _get_conn()
    ph = _ph()

    tables = [
        "user_preferences",
        "savings_goals",
        "savings_deposits",
        "user_achievements",
        "scoring_history",
        "webhook_subscriptions",
    ]
    deleted_rows: dict[str, int] = {}
    for tbl in tables:
        if _table_exists(conn, tbl):
            cur = conn.execute(
                f"DELETE FROM {tbl} WHERE pubkey = {ph}", (pubkey,)
            )
            deleted_rows[tbl] = cur.rowcount

    user_cur = conn.execute(f"DELETE FROM users WHERE pubkey = {ph}", (pubkey,))
    conn.commit()

    return {
        "deleted": user_cur.rowcount > 0,
        "pubkey": pubkey,
        "cascaded": deleted_rows,
    }


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------


def cmd_session_list() -> dict:
    """List all active in-memory session tokens (pubkey, expiry)."""
    from app.auth.sessions import _sessions, _lock
    now = time.time()
    active = []
    with _lock:
        for token, (pubkey, exp) in list(_sessions.items()):
            active.append({
                "token_prefix": token[:8] + "...",
                "pubkey": pubkey,
                "expires_at": int(exp),
                "ttl_seconds": max(0, int(exp - now)),
            })
    return {
        "sessions": active,
        "count": len(active),
        "timestamp": int(now),
    }


def cmd_session_cleanup() -> dict:
    """Force cleanup of all expired in-memory sessions."""
    from app.auth.sessions import _sessions, _lock
    from app.auth.lnurl import cleanup_expired as lnurl_cleanup

    before_count = 0
    with _lock:
        before_count = len(_sessions)

    from app.auth.sessions import cleanup_expired
    cleanup_expired()
    lnurl_cleanup()

    after_count = 0
    with _lock:
        after_count = len(_sessions)

    removed = before_count - after_count
    return {
        "removed": removed,
        "remaining": after_count,
        "message": f"Cleaned up {removed} expired session(s).",
    }


# ---------------------------------------------------------------------------
# Achievement stats
# ---------------------------------------------------------------------------


def cmd_achievement_stats() -> dict:
    """Return distribution of achievements across all users."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT achievement_id, COUNT(*) as cnt "
        "FROM user_achievements GROUP BY achievement_id ORDER BY cnt DESC"
    ).fetchall()

    distribution = [
        {
            "achievement_id": r[0] if isinstance(r, tuple) else r["achievement_id"],
            "user_count": r[1] if isinstance(r, tuple) else r["cnt"],
        }
        for r in rows
    ]

    total_awards = sum(d["user_count"] for d in distribution)
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    return {
        "distribution": distribution,
        "total_awards": total_awards,
        "total_users": total_users,
        "distinct_achievements": len(distribution),
    }


# ---------------------------------------------------------------------------
# Savings stats
# ---------------------------------------------------------------------------


def cmd_savings_stats() -> dict:
    """Return aggregate savings statistics across all users."""
    conn = _get_conn()

    dep_row = conn.execute(
        "SELECT COUNT(*), SUM(amount_usd), AVG(amount_usd), MAX(btc_price), MIN(btc_price) "
        "FROM savings_deposits"
    ).fetchone()

    goal_count = conn.execute("SELECT COUNT(*) FROM savings_goals").fetchone()[0]

    return {
        "total_deposits": dep_row[0] or 0,
        "total_usd_saved": round(dep_row[1] or 0.0, 2),
        "avg_deposit_usd": round(dep_row[2] or 0.0, 2),
        "max_btc_price_at_deposit": round(dep_row[3] or 0.0, 2),
        "min_btc_price_at_deposit": round(dep_row[4] or 0.0, 2),
        "users_with_goals": goal_count,
    }


# ---------------------------------------------------------------------------
# Price check
# ---------------------------------------------------------------------------


def cmd_price_check() -> dict:
    """Fetch current BTC price from all available sources."""
    results = []
    errors = []

    sources = [
        ("CoinGecko", _fetch_coingecko_price),
        ("Kraken", _fetch_kraken_price),
    ]

    for name, fn in sources:
        try:
            price = fn()
            results.append({"source": name, "price_usd": round(price, 2), "ok": True})
        except Exception as exc:
            errors.append({"source": name, "error": str(exc), "ok": False})
            results.append({"source": name, "price_usd": None, "ok": False})

    prices = [r["price_usd"] for r in results if r["ok"]]
    median = sorted(prices)[len(prices) // 2] if prices else None

    return {
        "sources": results,
        "median_price_usd": median,
        "errors": errors,
        "timestamp": int(time.time()),
    }


def _fetch_coingecko_price() -> float:
    from app.services.coingecko_client import CoinGeckoClient
    return CoinGeckoClient().get_price()


def _fetch_kraken_price() -> float:
    from app.services.kraken_client import KrakenClient
    return KrakenClient().get_price()


# ---------------------------------------------------------------------------
# Alert history
# ---------------------------------------------------------------------------


def cmd_alert_history(limit: int = 50) -> dict:
    """Return recent analytics / alert events.

    Args:
        limit: Maximum number of events to return (default 50).
    """
    conn = _get_conn()
    if not _table_exists(conn, "analytics_events"):
        return {"events": [], "message": "analytics_events table does not exist yet"}

    ph = _ph()
    rows = conn.execute(
        f"SELECT id, pubkey, event_type, event_data, created_at "
        f"FROM analytics_events ORDER BY created_at DESC LIMIT {ph}",
        (limit,),
    ).fetchall()

    events = []
    for r in rows:
        events.append({
            "id": r[0] if isinstance(r, tuple) else r["id"],
            "pubkey": r[1] if isinstance(r, tuple) else r["pubkey"],
            "event_type": r[2] if isinstance(r, tuple) else r["event_type"],
            "event_data": r[3] if isinstance(r, tuple) else r["event_data"],
            "created_at": r[4] if isinstance(r, tuple) else r["created_at"],
        })

    return {"events": events, "count": len(events)}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def cmd_health_check() -> dict:
    """Comprehensive system health status."""
    checks: dict[str, Any] = {}

    # Database connectivity
    try:
        conn = _get_conn()
        conn.execute("SELECT 1").fetchone()
        checks["database"] = {"ok": True, "message": "Connected"}
    except Exception as exc:
        checks["database"] = {"ok": False, "message": str(exc)}

    # Migration state
    try:
        from app.migrations.runner import MigrationRunner
        conn = _get_conn()
        runner = MigrationRunner(conn)
        status = runner.get_status()
        checks["migrations"] = {
            "ok": status["is_up_to_date"],
            "applied": status["applied_count"],
            "pending": status["pending_count"],
            "message": "Up to date" if status["is_up_to_date"] else f"{status['pending_count']} pending",
        }
    except Exception as exc:
        checks["migrations"] = {"ok": False, "message": str(exc)}

    # Session store
    try:
        from app.auth.sessions import _sessions
        checks["sessions"] = {"ok": True, "active": len(_sessions)}
    except Exception as exc:
        checks["sessions"] = {"ok": False, "message": str(exc)}

    # BTC price
    try:
        from app.services.coingecko_client import CoinGeckoClient
        price = CoinGeckoClient().get_price()
        checks["btc_price"] = {"ok": True, "price_usd": round(price, 2)}
    except Exception as exc:
        checks["btc_price"] = {"ok": False, "message": str(exc)}

    all_ok = all(v.get("ok", False) for v in checks.values())
    return {
        "healthy": all_ok,
        "checks": checks,
        "timestamp": int(time.time()),
    }


# ---------------------------------------------------------------------------
# Export users
# ---------------------------------------------------------------------------


def cmd_export_users(fmt: str = "json", output: Optional[str] = None) -> dict:
    """Export all user data.

    Args:
        fmt:    Output format — "json" or "csv".
        output: Optional file path. If None, returns data in the result dict.

    Returns:
        dict with keys: format, row_count, output_path (if written to file),
        data (if no output path given).
    """
    conn = _get_conn()
    rows = conn.execute(
        "SELECT pubkey, auth_method, created_at FROM users ORDER BY created_at ASC"
    ).fetchall()

    users = [
        {
            "pubkey": r[0] if isinstance(r, tuple) else r["pubkey"],
            "auth_method": r[1] if isinstance(r, tuple) else r["auth_method"],
            "created_at": r[2] if isinstance(r, tuple) else r["created_at"],
        }
        for r in rows
    ]

    if fmt == "csv":
        lines = ["pubkey,auth_method,created_at"]
        for u in users:
            lines.append(f"{u['pubkey']},{u['auth_method']},{u['created_at']}")
        content = "\n".join(lines)
    else:
        content = json.dumps(users, indent=2)

    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(content)
        return {
            "format": fmt,
            "row_count": len(users),
            "output_path": output,
        }

    return {
        "format": fmt,
        "row_count": len(users),
        "data": content,
    }
