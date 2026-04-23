"""
Individual health probes for the Magma Bitcoin application.

Each probe function:
  - Takes no arguments
  - Returns a :class:`CheckResult`
  - Is safe to call concurrently
  - Handles its own exceptions
  - Records its own wall-clock duration

All probes use only Python stdlib.
"""

import logging
import os
import platform
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Optional

from .checker import CheckResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------

def _timed(name: str, fn):
    """Run ``fn()`` and annotate the result with wall-clock duration."""
    start = time.perf_counter()
    try:
        result = fn()
        elapsed = (time.perf_counter() - start) * 1000
        result.duration_ms = round(elapsed, 3)
        return result
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, f"Unhandled exception: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_database
# ---------------------------------------------------------------------------

def probe_database() -> CheckResult:
    """Check database connectivity and basic query performance."""
    start = time.perf_counter()
    name = "database"
    try:
        from ..database import get_db
        conn = get_db()
        t0 = time.perf_counter()
        conn.execute("SELECT 1").fetchone()
        query_ms = (time.perf_counter() - t0) * 1000

        # Verify key tables exist
        tables_result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        tables = [row[0] for row in tables_result]
        expected = ["users", "deposits", "savings_goals"]
        missing = [t for t in expected if t not in tables]

        elapsed = (time.perf_counter() - start) * 1000

        if missing:
            return CheckResult.degraded(
                name,
                f"Missing tables: {missing}",
                duration_ms=elapsed,
                query_ms=round(query_ms, 3),
                tables_found=tables,
            )
        if query_ms > 100:
            return CheckResult.degraded(
                name,
                f"Slow query: {query_ms:.1f}ms",
                duration_ms=elapsed,
                query_ms=round(query_ms, 3),
            )
        return CheckResult.healthy(
            name,
            f"OK ({len(tables)} tables, query {query_ms:.1f}ms)",
            duration_ms=elapsed,
            query_ms=round(query_ms, 3),
            table_count=len(tables),
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        logger.warning("probe_database failed: %s", exc)
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_coingecko
# ---------------------------------------------------------------------------

def probe_coingecko() -> CheckResult:
    """Check CoinGecko API availability via /ping endpoint."""
    name = "coingecko"
    start = time.perf_counter()
    url = "https://api.coingecko.com/api/v3/ping"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Magma/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            elapsed = (time.perf_counter() - start) * 1000
            if "gecko_says" in body:
                return CheckResult.healthy(name, "CoinGecko API reachable", duration_ms=elapsed)
            return CheckResult.degraded(name, f"Unexpected response: {body[:80]}", duration_ms=elapsed)
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, f"HTTP {exc.code}", duration_ms=elapsed, http_code=exc.code)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_kraken
# ---------------------------------------------------------------------------

def probe_kraken() -> CheckResult:
    """Check Kraken REST API availability via the system status endpoint."""
    name = "kraken"
    start = time.perf_counter()
    url = "https://api.kraken.com/0/public/SystemStatus"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Magma/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json
            body = json.loads(resp.read().decode())
            elapsed = (time.perf_counter() - start) * 1000
            status = body.get("result", {}).get("status", "unknown")
            if status == "online":
                return CheckResult.healthy(name, "Kraken online", duration_ms=elapsed, kraken_status=status)
            return CheckResult.degraded(name, f"Kraken status: {status}", duration_ms=elapsed, kraken_status=status)
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, f"HTTP {exc.code}", duration_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_mempool
# ---------------------------------------------------------------------------

def probe_mempool() -> CheckResult:
    """Check Mempool.space API availability."""
    name = "mempool"
    start = time.perf_counter()
    url = "https://mempool.space/api/v1/fees/recommended"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Magma/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json
            body = json.loads(resp.read().decode())
            elapsed = (time.perf_counter() - start) * 1000
            fastest = body.get("fastestFee")
            if fastest is not None:
                return CheckResult.healthy(
                    name, f"Mempool reachable, fastest fee: {fastest} sat/vB",
                    duration_ms=elapsed, fastest_fee=fastest,
                )
            return CheckResult.degraded(name, "Missing fee data in response", duration_ms=elapsed)
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, f"HTTP {exc.code}", duration_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_wise
# ---------------------------------------------------------------------------

def probe_wise() -> CheckResult:
    """Check Wise (TransferWise) API reachability."""
    name = "wise"
    start = time.perf_counter()
    # Wise does not have a public /ping — check their status page host
    url = "https://api.wise.com/v1/rates?source=USD&target=EUR"
    try:
        # This endpoint requires auth; we just verify DNS + TCP connection
        socket.setdefaulttimeout(5)
        socket.getaddrinfo("api.wise.com", 443)
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.healthy(name, "Wise API hostname resolves", duration_ms=elapsed)
    except socket.gaierror as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, f"DNS failure: {exc}", duration_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_disk_space
# ---------------------------------------------------------------------------

def probe_disk_space(warn_pct: float = 80.0, crit_pct: float = 90.0) -> CheckResult:
    """Check available disk space on the root filesystem."""
    name = "disk_space"
    start = time.perf_counter()
    try:
        stat = os.statvfs("/") if hasattr(os, "statvfs") else None
        elapsed = (time.perf_counter() - start) * 1000
        if stat is None:
            # Windows fallback using shutil
            import shutil
            total, used, free = shutil.disk_usage("/")
            pct_used = used / total * 100
            return _disk_result(name, total, used, free, pct_used, warn_pct, crit_pct, elapsed)

        total = stat.f_frsize * stat.f_blocks
        free = stat.f_frsize * stat.f_bfree
        used = total - free
        pct_used = used / total * 100 if total else 0
        return _disk_result(name, total, used, free, pct_used, warn_pct, crit_pct, elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


def _disk_result(name, total, used, free, pct_used, warn_pct, crit_pct, elapsed):
    gb = 1024 ** 3
    meta = {
        "total_gb": round(total / gb, 2),
        "used_gb": round(used / gb, 2),
        "free_gb": round(free / gb, 2),
        "used_pct": round(pct_used, 2),
    }
    if pct_used >= crit_pct:
        return CheckResult.unhealthy(name, f"Disk {pct_used:.1f}% full", duration_ms=elapsed, **meta)
    if pct_used >= warn_pct:
        return CheckResult.degraded(name, f"Disk {pct_used:.1f}% full", duration_ms=elapsed, **meta)
    return CheckResult.healthy(name, f"Disk {pct_used:.1f}% used, {meta['free_gb']}GB free", duration_ms=elapsed, **meta)


# ---------------------------------------------------------------------------
# probe_memory
# ---------------------------------------------------------------------------

def probe_memory(warn_pct: float = 80.0, crit_pct: float = 90.0) -> CheckResult:
    """Check available system memory using /proc/meminfo (Linux only; degrades on others)."""
    name = "memory"
    start = time.perf_counter()
    try:
        mem_info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    mem_info[key] = int(parts[1])  # kB

        total = mem_info.get("MemTotal", 0)
        free = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
        used = total - free
        pct_used = used / total * 100 if total else 0
        elapsed = (time.perf_counter() - start) * 1000

        meta = {
            "total_mb": round(total / 1024, 1),
            "used_mb": round(used / 1024, 1),
            "free_mb": round(free / 1024, 1),
            "used_pct": round(pct_used, 2),
        }
        if pct_used >= crit_pct:
            return CheckResult.unhealthy(name, f"Memory {pct_used:.1f}% used", duration_ms=elapsed, **meta)
        if pct_used >= warn_pct:
            return CheckResult.degraded(name, f"Memory {pct_used:.1f}% used", duration_ms=elapsed, **meta)
        return CheckResult.healthy(name, f"Memory {pct_used:.1f}% used", duration_ms=elapsed, **meta)

    except FileNotFoundError:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(
            name, "/proc/meminfo not available (non-Linux?)", duration_ms=elapsed,
            platform=platform.system(),
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_cpu
# ---------------------------------------------------------------------------

def probe_cpu(warn_pct: float = 80.0, crit_pct: float = 95.0) -> CheckResult:
    """Approximate CPU usage from /proc/stat (Linux only)."""
    name = "cpu"
    start = time.perf_counter()
    try:
        def _read_cpu():
            with open("/proc/stat") as f:
                line = f.readline()
            vals = list(map(int, line.split()[1:]))
            idle = vals[3]
            total = sum(vals)
            return idle, total

        idle1, total1 = _read_cpu()
        time.sleep(0.1)
        idle2, total2 = _read_cpu()

        diff_idle = idle2 - idle1
        diff_total = total2 - total1
        cpu_pct = (1 - diff_idle / diff_total) * 100 if diff_total else 0
        elapsed = (time.perf_counter() - start) * 1000

        meta = {"cpu_pct": round(cpu_pct, 2)}
        if cpu_pct >= crit_pct:
            return CheckResult.unhealthy(name, f"CPU {cpu_pct:.1f}%", duration_ms=elapsed, **meta)
        if cpu_pct >= warn_pct:
            return CheckResult.degraded(name, f"CPU {cpu_pct:.1f}%", duration_ms=elapsed, **meta)
        return CheckResult.healthy(name, f"CPU {cpu_pct:.1f}%", duration_ms=elapsed, **meta)

    except FileNotFoundError:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(
            name, "/proc/stat not available", duration_ms=elapsed, platform=platform.system()
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_sessions
# ---------------------------------------------------------------------------

def probe_sessions() -> CheckResult:
    """Check the in-memory session store state."""
    name = "sessions"
    start = time.perf_counter()
    try:
        from ..auth import sessions as session_module
        store = getattr(session_module, "_sessions", None)
        if store is None:
            elapsed = (time.perf_counter() - start) * 1000
            return CheckResult.degraded(name, "Session store not found", duration_ms=elapsed)
        count = len(store)
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.healthy(name, f"{count} active sessions", duration_ms=elapsed, session_count=count)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Could not inspect sessions: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_rate_limits
# ---------------------------------------------------------------------------

def probe_rate_limits() -> CheckResult:
    """Inspect the rate-limiter state."""
    name = "rate_limits"
    start = time.perf_counter()
    try:
        from ..ratelimit import router as rl_module
        limiter = getattr(rl_module, "_limiter", None)
        if limiter is None:
            elapsed = (time.perf_counter() - start) * 1000
            return CheckResult.degraded(name, "Rate limiter not found", duration_ms=elapsed)

        buckets = getattr(limiter, "_buckets", {})
        bucket_count = len(buckets)
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.healthy(name, f"{bucket_count} rate-limit buckets active", duration_ms=elapsed, bucket_count=bucket_count)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Could not inspect rate limiter: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_scheduler
# ---------------------------------------------------------------------------

def probe_scheduler() -> CheckResult:
    """Check background scheduler status."""
    name = "scheduler"
    start = time.perf_counter()
    try:
        from ..scheduler import router as sched_module
        scheduler = getattr(sched_module, "_scheduler", None)
        if scheduler is None:
            elapsed = (time.perf_counter() - start) * 1000
            return CheckResult.degraded(name, "Scheduler not found", duration_ms=elapsed)

        running = getattr(scheduler, "_running", None)
        elapsed = (time.perf_counter() - start) * 1000
        if running is False:
            return CheckResult.degraded(name, "Scheduler stopped", duration_ms=elapsed)
        return CheckResult.healthy(name, "Scheduler running", duration_ms=elapsed, running=running)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Could not inspect scheduler: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_webhooks
# ---------------------------------------------------------------------------

def probe_webhooks() -> CheckResult:
    """Check webhook delivery health (failure rate)."""
    name = "webhooks"
    start = time.perf_counter()
    FAIL_RATE_WARN = 0.10
    FAIL_RATE_CRIT = 0.30
    try:
        from ..database import get_db
        conn = get_db()
        row = conn.execute(
            "SELECT "
            "COUNT(*) as total, "
            "SUM(CASE WHEN last_status != 200 THEN 1 ELSE 0 END) as failures "
            "FROM webhook_subscriptions WHERE active = 1"
        ).fetchone()
        elapsed = (time.perf_counter() - start) * 1000
        if row is None:
            return CheckResult.healthy(name, "No webhooks configured", duration_ms=elapsed)
        total = row[0] or 0
        failures = row[1] or 0
        if total == 0:
            return CheckResult.healthy(name, "No active webhooks", duration_ms=elapsed)
        fail_rate = failures / total
        meta = {"total": total, "failures": failures, "failure_rate": round(fail_rate, 4)}
        if fail_rate >= FAIL_RATE_CRIT:
            return CheckResult.unhealthy(name, f"Webhook failure rate {fail_rate:.1%}", duration_ms=elapsed, **meta)
        if fail_rate >= FAIL_RATE_WARN:
            return CheckResult.degraded(name, f"Webhook failure rate {fail_rate:.1%}", duration_ms=elapsed, **meta)
        return CheckResult.healthy(name, f"{total} webhooks, {fail_rate:.1%} failure rate", duration_ms=elapsed, **meta)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Could not query webhooks: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_cache
# ---------------------------------------------------------------------------

def probe_cache() -> CheckResult:
    """Check cache hit rates if a global CacheManager is available."""
    name = "cache"
    start = time.perf_counter()
    try:
        from ..cache.multi_tier import CacheManager
        # Try to find a module-level manager
        import sys
        manager = None
        for mod_name, mod in list(sys.modules.items()):
            if hasattr(mod, "_cache_manager"):
                manager = mod._cache_manager
                break

        elapsed = (time.perf_counter() - start) * 1000
        if manager is None:
            return CheckResult.healthy(name, "No global CacheManager found (OK)", duration_ms=elapsed)

        stats = manager.get_stats()
        hit_rates = {
            cn: cs.get("hit_rate", 0)
            for cn, cs in stats.get("per_cache", {}).items()
        }
        avg_hit_rate = sum(hit_rates.values()) / len(hit_rates) if hit_rates else 0
        if avg_hit_rate < 0.1 and sum(stats.get("per_cache", {}).values()) > 0:
            return CheckResult.degraded(name, f"Low cache hit rate: {avg_hit_rate:.1%}", duration_ms=elapsed, hit_rates=hit_rates)
        return CheckResult.healthy(name, f"Cache hit rate: {avg_hit_rate:.1%}", duration_ms=elapsed, hit_rates=hit_rates)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Cache probe error: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_dns
# ---------------------------------------------------------------------------

def probe_dns() -> CheckResult:
    """Verify DNS resolution for critical external hosts."""
    name = "dns"
    start = time.perf_counter()
    hosts = ["api.coingecko.com", "api.kraken.com", "mempool.space"]
    failed = []
    for host in hosts:
        try:
            socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
        except socket.gaierror:
            failed.append(host)

    elapsed = (time.perf_counter() - start) * 1000
    if failed:
        return CheckResult.unhealthy(
            name, f"DNS failed for: {failed}",
            duration_ms=elapsed, failed_hosts=failed, checked_hosts=hosts,
        )
    return CheckResult.healthy(
        name, f"DNS OK for {len(hosts)} hosts",
        duration_ms=elapsed, checked_hosts=hosts,
    )


# ---------------------------------------------------------------------------
# probe_ssl
# ---------------------------------------------------------------------------

def probe_ssl(warn_days: int = 14, crit_days: int = 7) -> CheckResult:
    """Check SSL certificate validity and expiry for the API host."""
    name = "ssl"
    start = time.perf_counter()
    try:
        host = "api.eclalune.com"
        port = 443
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()

        import datetime
        expiry_str = cert.get("notAfter", "")
        expiry = None
        for fmt in ("%b %d %H:%M:%S %Y %Z", "%b  %d %H:%M:%S %Y %Z"):
            try:
                expiry = datetime.datetime.strptime(expiry_str, fmt)
                break
            except ValueError:
                continue

        elapsed = (time.perf_counter() - start) * 1000
        if expiry is None:
            return CheckResult.degraded(name, f"Could not parse cert expiry: {expiry_str}", duration_ms=elapsed)

        days_left = (expiry - datetime.datetime.utcnow()).days
        meta = {"host": host, "expires": expiry_str, "days_left": days_left}
        if days_left <= crit_days:
            return CheckResult.unhealthy(name, f"SSL cert expires in {days_left} days!", duration_ms=elapsed, **meta)
        if days_left <= warn_days:
            return CheckResult.degraded(name, f"SSL cert expires in {days_left} days", duration_ms=elapsed, **meta)
        return CheckResult.healthy(name, f"SSL cert valid, {days_left} days left", duration_ms=elapsed, **meta)

    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"SSL check error: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_response_time
# ---------------------------------------------------------------------------

def probe_response_time(warn_ms: float = 500.0, crit_ms: float = 2000.0) -> CheckResult:
    """Benchmark the local API by timing a lightweight internal endpoint."""
    name = "response_time"
    start = time.perf_counter()
    try:
        from ..config import settings
        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")
        url = f"{base_url}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "HealthProbe/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            resp.read()
        elapsed = (time.perf_counter() - start) * 1000
        meta = {"response_ms": round(elapsed, 2)}
        if elapsed >= crit_ms:
            return CheckResult.unhealthy(name, f"Response time {elapsed:.0f}ms exceeds {crit_ms}ms", duration_ms=elapsed, **meta)
        if elapsed >= warn_ms:
            return CheckResult.degraded(name, f"Response time {elapsed:.0f}ms", duration_ms=elapsed, **meta)
        return CheckResult.healthy(name, f"Response time {elapsed:.0f}ms", duration_ms=elapsed, **meta)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Could not time API: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_error_rate
# ---------------------------------------------------------------------------

def probe_error_rate() -> CheckResult:
    """Check the recent HTTP 5xx error rate from the app's logging data."""
    name = "error_rate"
    start = time.perf_counter()
    WARN_RATE = 0.01
    CRIT_RATE = 0.05
    try:
        # Attempt to read from any module-level error counter
        import sys
        counter = None
        for mod_name, mod in list(sys.modules.items()):
            if hasattr(mod, "_error_counter"):
                counter = mod._error_counter
                break

        elapsed = (time.perf_counter() - start) * 1000
        if counter is None:
            return CheckResult.healthy(name, "No error counter found (OK)", duration_ms=elapsed)

        total = counter.get("total", 0)
        errors = counter.get("errors_5xx", 0)
        if total == 0:
            return CheckResult.healthy(name, "No requests yet", duration_ms=elapsed)
        rate = errors / total
        meta = {"total_requests": total, "errors_5xx": errors, "error_rate": round(rate, 5)}
        if rate >= CRIT_RATE:
            return CheckResult.unhealthy(name, f"Error rate {rate:.2%}", duration_ms=elapsed, **meta)
        if rate >= WARN_RATE:
            return CheckResult.degraded(name, f"Error rate {rate:.2%}", duration_ms=elapsed, **meta)
        return CheckResult.healthy(name, f"Error rate {rate:.2%}", duration_ms=elapsed, **meta)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.degraded(name, f"Could not read error counter: {exc}", duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_database_connections
# ---------------------------------------------------------------------------

def probe_database_connections() -> CheckResult:
    """Check that the database can be connected to from multiple threads."""
    name = "database_connections"
    start = time.perf_counter()
    import threading
    results = []
    errors = []

    def _check():
        try:
            from ..database import get_db
            conn = get_db()
            conn.execute("SELECT 1").fetchone()
            results.append(True)
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=_check) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    elapsed = (time.perf_counter() - start) * 1000
    if errors:
        return CheckResult.unhealthy(
            name, f"{len(errors)}/3 connections failed",
            duration_ms=elapsed, errors=errors,
        )
    return CheckResult.healthy(
        name, f"{len(results)}/3 connections OK",
        duration_ms=elapsed, connections_tested=len(results),
    )


# ---------------------------------------------------------------------------
# probe_migrations
# ---------------------------------------------------------------------------

def probe_migrations() -> CheckResult:
    """Check that the database schema is up to date."""
    name = "migrations"
    start = time.perf_counter()
    EXPECTED_TABLES = [
        "users", "deposits", "savings_goals", "user_preferences",
        "achievements", "webhook_subscriptions",
    ]
    try:
        from ..database import get_db
        conn = get_db()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        existing = {row[0] for row in rows}
        missing = [t for t in EXPECTED_TABLES if t not in existing]
        elapsed = (time.perf_counter() - start) * 1000
        if missing:
            return CheckResult.unhealthy(
                name,
                f"Missing schema tables: {missing}",
                duration_ms=elapsed,
                missing_tables=missing,
                existing_tables=list(existing),
            )
        return CheckResult.healthy(
            name,
            f"Schema up to date ({len(existing)} tables)",
            duration_ms=elapsed,
            table_count=len(existing),
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult.unhealthy(name, str(exc), duration_ms=elapsed)


# ---------------------------------------------------------------------------
# probe_external_connectivity
# ---------------------------------------------------------------------------

def probe_external_connectivity() -> CheckResult:
    """Verify general internet connectivity by connecting to well-known hosts."""
    name = "external_connectivity"
    start = time.perf_counter()
    TARGETS = [
        ("8.8.8.8", 53),        # Google DNS
        ("1.1.1.1", 53),        # Cloudflare DNS
        ("api.coingecko.com", 443),
    ]
    reachable = []
    unreachable = []
    for host, port in TARGETS:
        try:
            with socket.create_connection((host, port), timeout=3):
                reachable.append(f"{host}:{port}")
        except Exception:
            unreachable.append(f"{host}:{port}")

    elapsed = (time.perf_counter() - start) * 1000
    meta = {
        "reachable": reachable,
        "unreachable": unreachable,
        "total_targets": len(TARGETS),
    }
    if not reachable:
        return CheckResult.unhealthy(name, "All external targets unreachable", duration_ms=elapsed, **meta)
    if unreachable:
        return CheckResult.degraded(
            name, f"{len(unreachable)}/{len(TARGETS)} targets unreachable",
            duration_ms=elapsed, **meta,
        )
    return CheckResult.healthy(
        name, f"All {len(TARGETS)} external targets reachable",
        duration_ms=elapsed, **meta,
    )
