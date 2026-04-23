"""Predefined background tasks for the Magma API.

Each public ``task_*`` function is a zero-argument callable suitable
for registration with :class:`~app.scheduler.scheduler.TaskScheduler`.
Factory functions (those that accept dependencies) return zero-argument
closures so callers can inject live service instances.

Suggested registration
----------------------
::

    from app.scheduler.scheduler import TaskScheduler
    from app.scheduler import tasks

    sched = TaskScheduler()
    sched.register("cleanup_sessions",    tasks.task_cleanup_sessions,          interval=300)
    sched.register("cleanup_lnurl",       tasks.task_cleanup_lnurl,             interval=300)
    sched.register("update_prices",       tasks.task_update_prices,             interval=60)
    sched.register("price_alerts",        tasks.task_check_price_alerts(...),   interval=60)
    sched.register("fee_alerts",          tasks.task_check_fee_alerts(...),     interval=60)
    sched.register("daily_stats",         tasks.task_compute_daily_stats(...),  interval=3600)
    sched.register("cleanup_ratelimits",  tasks.task_cleanup_rate_limits(...),  interval=300)
    sched.register("health_check",        tasks.task_health_check,              interval=300)
    sched.register("db_maintenance",      tasks.task_database_maintenance,      interval=86400)
    sched.register("webhook_retry",       tasks.task_webhook_retry(...),        interval=600)
    sched.start()
"""

from __future__ import annotations

import time
import traceback
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..ratelimit.storage import MemoryStorage
    from ..webhooks.dispatcher import WebhookDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(level: str, task: str, message: str) -> None:
    """Minimal structured log line written to stdout."""
    ts = int(time.time())
    print(f"[{ts}] [{level.upper()}] [task:{task}] {message}")


# ---------------------------------------------------------------------------
# 1. Session cleanup (every 5 min)
# ---------------------------------------------------------------------------

def task_cleanup_sessions() -> None:
    """Expire in-memory sessions older than their TTL."""
    try:
        from ..auth.sessions import _sessions, SESSION_TTL  # type: ignore[attr-defined]
        now = time.time()
        expired = [t for t, (pk, exp) in list(_sessions.items()) if exp < now]
        for token in expired:
            _sessions.pop(token, None)
        if expired:
            _log("info", "cleanup_sessions", f"Removed {len(expired)} expired session(s).")
    except ImportError:
        pass
    except Exception as exc:
        _log("error", "cleanup_sessions", str(exc))


# ---------------------------------------------------------------------------
# 2. LNURL challenge cleanup (every 5 min)
# ---------------------------------------------------------------------------

def task_cleanup_lnurl() -> None:
    """Expire stale LNURL-auth challenges."""
    try:
        from ..auth.lnurl import _challenges  # type: ignore[attr-defined]
        now = time.time()
        expired = [
            k for k, v in list(_challenges.items())
            if isinstance(v, dict) and v.get("expires_at", 0) < now
        ]
        for k in expired:
            _challenges.pop(k, None)
        if expired:
            _log("info", "cleanup_lnurl", f"Removed {len(expired)} expired LNURL challenge(s).")
    except ImportError:
        pass
    except Exception as exc:
        _log("error", "cleanup_lnurl", str(exc))


# ---------------------------------------------------------------------------
# 3. Price cache refresh (every 60 s)
# ---------------------------------------------------------------------------

def task_update_prices() -> None:
    """Trigger a price cache refresh for all tracked assets."""
    try:
        from ..services.price import get_price_service  # type: ignore[attr-defined]
        svc = get_price_service()
        if hasattr(svc, "refresh"):
            svc.refresh()
        _log("info", "update_prices", "Price cache refreshed.")
    except ImportError:
        pass
    except Exception as exc:
        _log("error", "update_prices", str(exc))


# ---------------------------------------------------------------------------
# 4. Price-alert checker (every 60 s) — factory
# ---------------------------------------------------------------------------

def task_check_price_alerts(
    price_aggregator: Any,
    webhook_dispatcher: "WebhookDispatcher",
) -> Callable[[], None]:
    """Return a zero-argument task that checks user-configured price alerts.

    Parameters
    ----------
    price_aggregator:
        Object with a ``get_current_price(asset) -> float`` method.
    webhook_dispatcher:
        Active :class:`~app.webhooks.dispatcher.WebhookDispatcher`.
    """

    def _task() -> None:
        try:
            from ..database import get_conn, _is_postgres

            btc_price = price_aggregator.get_current_price("BTC")
            conn = get_conn()
            rows = conn.execute(
                "SELECT pubkey, price_alerts, alerts_enabled "
                "FROM user_preferences"
            ).fetchall()

            triggered_pubkeys = []
            for row in rows:
                if hasattr(row, "keys"):
                    d = dict(row)
                else:
                    d = dict(zip(["pubkey", "price_alerts", "alerts_enabled"], row))
                if not d.get("alerts_enabled"):
                    continue
                import json
                alerts = json.loads(d.get("price_alerts") or "[]")
                pubkey = d["pubkey"]
                for alert in alerts:
                    target = alert.get("price", 0)
                    direction = alert.get("direction", "above")
                    if direction == "above" and btc_price >= target:
                        triggered_pubkeys.append((pubkey, target, direction, btc_price))
                    elif direction == "below" and btc_price <= target:
                        triggered_pubkeys.append((pubkey, target, direction, btc_price))

            for pubkey, target, direction, current in triggered_pubkeys:
                webhook_dispatcher.dispatch(
                    "price_alert",
                    {
                        "asset": "BTC",
                        "current_price": current,
                        "target_price": target,
                        "direction": direction,
                    },
                    pubkeys=[pubkey],
                )

            if triggered_pubkeys:
                _log(
                    "info",
                    "price_alerts",
                    f"Triggered {len(triggered_pubkeys)} price alert(s) at BTC={btc_price}.",
                )
        except Exception as exc:
            _log("error", "price_alerts", f"{type(exc).__name__}: {exc}")

    return _task


# ---------------------------------------------------------------------------
# 5. Fee-alert checker (every 60 s) — factory
# ---------------------------------------------------------------------------

def task_check_fee_alerts(
    mempool_client: Any,
    webhook_dispatcher: "WebhookDispatcher",
) -> Callable[[], None]:
    """Return a task that fires fee alerts when user thresholds are crossed."""

    def _task() -> None:
        try:
            fees = mempool_client.get_fees()
            fastest_fee = fees.get("fastestFee", 0)
            economy_fee = fees.get("economyFee", 0)

            from ..database import get_conn

            conn = get_conn()
            rows = conn.execute(
                "SELECT pubkey, fee_alert_low, fee_alert_high, alerts_enabled "
                "FROM user_preferences"
            ).fetchall()

            for row in rows:
                if hasattr(row, "keys"):
                    d = dict(row)
                else:
                    d = dict(zip(
                        ["pubkey", "fee_alert_low", "fee_alert_high", "alerts_enabled"],
                        row,
                    ))
                if not d.get("alerts_enabled"):
                    continue
                pubkey = d["pubkey"]
                low_threshold = d.get("fee_alert_low", 5)
                high_threshold = d.get("fee_alert_high", 50)

                if economy_fee <= low_threshold:
                    webhook_dispatcher.dispatch(
                        "fee_alert",
                        {
                            "type": "low",
                            "economy_fee": economy_fee,
                            "threshold": low_threshold,
                            "unit": "sat/vbyte",
                        },
                        pubkeys=[pubkey],
                    )
                if fastest_fee >= high_threshold:
                    webhook_dispatcher.dispatch(
                        "fee_alert",
                        {
                            "type": "high",
                            "fastest_fee": fastest_fee,
                            "threshold": high_threshold,
                            "unit": "sat/vbyte",
                        },
                        pubkeys=[pubkey],
                    )
        except Exception as exc:
            _log("error", "fee_alerts", f"{type(exc).__name__}: {exc}")

    return _task


# ---------------------------------------------------------------------------
# 6. Daily statistics computation (every 1 h) — factory
# ---------------------------------------------------------------------------

def task_compute_daily_stats(analytics_engine: Any) -> Callable[[], None]:
    """Return a task that triggers daily analytics aggregation."""

    def _task() -> None:
        try:
            if hasattr(analytics_engine, "compute_daily_stats"):
                analytics_engine.compute_daily_stats()
                _log("info", "daily_stats", "Daily statistics computed.")
            else:
                _log("warn", "daily_stats", "analytics_engine has no compute_daily_stats method.")
        except Exception as exc:
            _log("error", "daily_stats", f"{type(exc).__name__}: {exc}")

    return _task


# ---------------------------------------------------------------------------
# 7. Rate limit cleanup (every 5 min) — factory
# ---------------------------------------------------------------------------

def task_cleanup_rate_limits(storage: "MemoryStorage") -> Callable[[], None]:
    """Return a task that removes expired rate-limit entries."""

    def _task() -> None:
        try:
            removed = storage.cleanup()
            if removed:
                _log("info", "cleanup_ratelimits", f"Removed {removed} stale rate-limit entry/entries.")
        except Exception as exc:
            _log("error", "cleanup_ratelimits", f"{type(exc).__name__}: {exc}")

    return _task


# ---------------------------------------------------------------------------
# 8. Health check (every 5 min)
# ---------------------------------------------------------------------------

def task_health_check() -> None:
    """Probe external services (Mempool, price APIs) and log health status."""
    import urllib.request
    import urllib.error

    services = {
        "mempool_space": "https://mempool.space/api/v1/fees/recommended",
        "coingecko":     "https://api.coingecko.com/api/v3/ping",
    }
    results = {}
    for name, url in services.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Magma/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                results[name] = resp.status == 200
        except Exception:
            results[name] = False

    ok_count = sum(1 for v in results.values() if v)
    total = len(results)
    _log(
        "info" if ok_count == total else "warn",
        "health_check",
        f"Services healthy: {ok_count}/{total} — {results}",
    )


# ---------------------------------------------------------------------------
# 9. Database maintenance (every 24 h)
# ---------------------------------------------------------------------------

def task_database_maintenance() -> None:
    """Run VACUUM and ANALYZE to keep the database healthy."""
    try:
        from ..database import get_conn, _is_postgres

        conn = get_conn()
        if _is_postgres():
            # Autocommit required for VACUUM in PostgreSQL.
            old_autocommit = conn.autocommit
            conn.autocommit = True
            try:
                conn.execute("VACUUM ANALYZE")
            finally:
                conn.autocommit = old_autocommit
        else:
            # SQLite VACUUM cannot run inside a transaction.
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.commit()
        _log("info", "db_maintenance", "VACUUM / ANALYZE completed.")
    except Exception as exc:
        _log("error", "db_maintenance", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# 10. Webhook retry (every 10 min) — factory
# ---------------------------------------------------------------------------

def task_webhook_retry(dispatcher: "WebhookDispatcher") -> Callable[[], None]:
    """Return a task that re-queues failed webhook deliveries."""

    def _task() -> None:
        try:
            from ..database import get_conn

            conn = get_conn()
            # Find subscriptions with recent failures but still active.
            rows = conn.execute(
                "SELECT id, pubkey FROM webhook_subscriptions "
                "WHERE active = 1 AND failure_count > 0"
            ).fetchall()

            requeued = 0
            for row in rows:
                if hasattr(row, "keys"):
                    sub_id, pubkey = row["id"], row["pubkey"]
                else:
                    sub_id, pubkey = row[0], row[1]
                if dispatcher.retry_failed(pubkey, sub_id):
                    requeued += 1

            if requeued:
                _log("info", "webhook_retry", f"Re-queued {requeued} failed webhook(s).")
        except Exception as exc:
            _log("error", "webhook_retry", f"{type(exc).__name__}: {exc}")

    return _task


# ---------------------------------------------------------------------------
# Convenience: build and return a fully-wired scheduler
# ---------------------------------------------------------------------------

def build_default_scheduler(
    price_aggregator: Optional[Any] = None,
    mempool_client: Optional[Any] = None,
    analytics_engine: Optional[Any] = None,
    rate_limit_storage: Optional[Any] = None,
    webhook_dispatcher: Optional["WebhookDispatcher"] = None,
) -> "TaskScheduler":
    """Create a :class:`TaskScheduler` pre-wired with all standard tasks.

    Pass ``None`` for any dependency you don't have yet; those tasks
    will be registered but will log a warning and exit cleanly.
    """
    from .scheduler import TaskScheduler

    sched = TaskScheduler()
    sched.register("cleanup_sessions",   task_cleanup_sessions,    interval=300)
    sched.register("cleanup_lnurl",      task_cleanup_lnurl,       interval=300)
    sched.register("update_prices",      task_update_prices,       interval=60)
    sched.register("health_check",       task_health_check,        interval=300)
    sched.register("db_maintenance",     task_database_maintenance, interval=86400)

    if price_aggregator is not None and webhook_dispatcher is not None:
        sched.register(
            "price_alerts",
            task_check_price_alerts(price_aggregator, webhook_dispatcher),
            interval=60,
        )

    if mempool_client is not None and webhook_dispatcher is not None:
        sched.register(
            "fee_alerts",
            task_check_fee_alerts(mempool_client, webhook_dispatcher),
            interval=60,
        )

    if analytics_engine is not None:
        sched.register(
            "daily_stats",
            task_compute_daily_stats(analytics_engine),
            interval=3600,
        )

    if rate_limit_storage is not None:
        sched.register(
            "cleanup_ratelimits",
            task_cleanup_rate_limits(rate_limit_storage),
            interval=300,
        )

    if webhook_dispatcher is not None:
        sched.register(
            "webhook_retry",
            task_webhook_retry(webhook_dispatcher),
            interval=600,
        )

    return sched
