"""
System administration module for Magma Bitcoin app.
Provides system info, database stats, diagnostics, performance metrics,
configuration management, and maintenance operations.
Pure Python stdlib — no third-party dependencies.
"""

import os
import sys
import time
import platform
import threading
import json
from typing import Any, Optional

from ..database import get_conn as get_connection

# Server start time (approximation — set when module is first imported)
_SERVER_START_TIME = int(time.time())

# Runtime configuration store (in-memory; persisted keys go to DB if needed)
_runtime_config: dict = {}
_config_lock = threading.Lock()

# In-memory performance metrics ring buffer
_perf_samples: list = []  # list of {"ts": int, "latency_ms": float, "endpoint": str}
_perf_lock = threading.Lock()
_MAX_PERF_SAMPLES = 10_000

# In-memory error log ring buffer
_error_log: list = []
_error_lock = threading.Lock()
_MAX_ERROR_ENTRIES = 1_000

# In-memory slow query log
_slow_queries: list = []
_slow_lock = threading.Lock()
_MAX_SLOW_QUERIES = 500


def record_request_latency(endpoint: str, latency_ms: float) -> None:
    """Record a request latency sample (called from request handler)."""
    with _perf_lock:
        _perf_samples.append({
            "ts":          int(time.time()),
            "latency_ms":  latency_ms,
            "endpoint":    endpoint,
        })
        if len(_perf_samples) > _MAX_PERF_SAMPLES:
            del _perf_samples[:len(_perf_samples) - _MAX_PERF_SAMPLES]


def record_error(endpoint: str, status_code: int, message: str) -> None:
    """Record an error for the error log (called from request handler)."""
    with _error_lock:
        _error_log.append({
            "ts":          int(time.time()),
            "endpoint":    endpoint,
            "status_code": status_code,
            "message":     message[:500],
        })
        if len(_error_log) > _MAX_ERROR_ENTRIES:
            del _error_log[:len(_error_log) - _MAX_ERROR_ENTRIES]


def record_slow_query(query: str, params: Any, elapsed_ms: float) -> None:
    """Record a slow database query."""
    with _slow_lock:
        _slow_queries.append({
            "ts":         int(time.time()),
            "query":      query[:300],
            "params":     str(params)[:100],
            "elapsed_ms": round(elapsed_ms, 2),
        })
        if len(_slow_queries) > _MAX_SLOW_QUERIES:
            del _slow_queries[:len(_slow_queries) - _MAX_SLOW_QUERIES]


# ---------------------------------------------------------------------------
# SystemAdmin
# ---------------------------------------------------------------------------

class SystemAdmin:
    """
    Administrative system operations and diagnostics for Magma.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def get_system_info(self) -> dict:
        """
        Return comprehensive system information: OS, Python, uptime,
        memory usage, disk space, and environment details.
        """
        result: dict = {}

        # Platform info
        result["platform"] = {
            "system":    platform.system(),
            "release":   platform.release(),
            "version":   platform.version(),
            "machine":   platform.machine(),
            "processor": platform.processor(),
            "node":      platform.node(),
        }

        # Python info
        result["python"] = {
            "version":      sys.version,
            "version_info": list(sys.version_info[:3]),
            "executable":   sys.executable,
            "prefix":       sys.prefix,
        }

        # Uptime
        now = int(time.time())
        uptime_secs = now - _SERVER_START_TIME
        result["uptime"] = {
            "start_time":    _SERVER_START_TIME,
            "current_time":  now,
            "uptime_seconds": uptime_secs,
            "uptime_human":  _format_duration(uptime_secs),
        }

        # Memory (best-effort without psutil)
        result["memory"] = self._get_memory_info()

        # Disk (best-effort)
        result["disk"] = self._get_disk_info()

        # Thread count
        result["threads"] = {
            "active": threading.active_count(),
            "names":  [t.name for t in threading.enumerate()],
        }

        # Environment (sanitized — no secrets)
        result["environment"] = {
            "DATABASE_URL": "***" if os.environ.get("DATABASE_URL") else None,
            "PUBLIC_URL":   os.environ.get("PUBLIC_URL", ""),
            "PYTHON_PATH":  os.environ.get("PYTHONPATH", ""),
        }

        return result

    def _get_memory_info(self) -> dict:
        """Best-effort memory info using /proc/self/status or platform."""
        try:
            if platform.system() == "Linux":
                with open("/proc/self/status") as f:
                    status = {}
                    for line in f:
                        if ":" in line:
                            key, val = line.split(":", 1)
                            status[key.strip()] = val.strip()
                return {
                    "vm_rss_kb":  int(status.get("VmRSS", "0 kB").split()[0]),
                    "vm_size_kb": int(status.get("VmSize", "0 kB").split()[0]),
                }
        except Exception:
            pass

        return {"note": "Memory info not available on this platform"}

    def _get_disk_info(self) -> dict:
        """Best-effort disk info using os.statvfs."""
        try:
            stat = os.statvfs(".")
            total = stat.f_blocks * stat.f_frsize
            free  = stat.f_bfree  * stat.f_frsize
            used  = total - free
            return {
                "total_bytes": total,
                "used_bytes":  used,
                "free_bytes":  free,
                "usage_pct":   round(used / total * 100, 1) if total > 0 else 0,
            }
        except (AttributeError, OSError):
            return {"note": "Disk info not available on this platform"}

    # ------------------------------------------------------------------
    # Database stats
    # ------------------------------------------------------------------

    def get_database_stats(self) -> dict:
        """
        Return table sizes, row counts, and index information.
        """
        tables_to_check = [
            "users", "sessions", "savings_goals", "savings_deposits",
            "user_achievements", "user_preferences", "security_audit_log",
            "banned_users", "admin_notes",
        ]

        result: dict = {"tables": {}}

        try:
            conn = get_connection()

            for table in tables_to_check:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    result["tables"][table] = {"row_count": count}
                except Exception:
                    result["tables"][table] = {"row_count": None, "error": "table_missing"}

            # SQLite-specific: page size and total pages
            try:
                page_size = conn.execute("PRAGMA page_size").fetchone()[0]
                page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                free_pages = conn.execute("PRAGMA freelist_count").fetchone()[0]

                result["sqlite"] = {
                    "page_size_bytes": page_size,
                    "total_pages":     page_count,
                    "free_pages":      free_pages,
                    "db_size_bytes":   page_size * page_count,
                    "db_size_mb":      round(page_size * page_count / 1_048_576, 2),
                }

                # Index list
                indexes = conn.execute(
                    "SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name"
                ).fetchall()
                result["indexes"] = [{"name": r[0], "table": r[1]} for r in indexes]

            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return result

    # ------------------------------------------------------------------
    # Cache stats
    # ------------------------------------------------------------------

    def get_cache_stats(self) -> dict:
        """
        Return in-memory cache statistics for all known caches.
        """
        stats: dict = {}

        # Attempt to pull stats from known caching modules
        cache_modules = [
            ("market_cache",      "app.market"),
            ("rate_limit_cache",  "app.ratelimit"),
        ]

        for cache_name, module_path in cache_modules:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cache_obj = getattr(mod, "_cache", None) or getattr(mod, "cache", None)
                if cache_obj and hasattr(cache_obj, "__len__"):
                    stats[cache_name] = {"size": len(cache_obj)}
                else:
                    stats[cache_name] = {"available": False}
            except ImportError:
                stats[cache_name] = {"available": False}
            except Exception as exc:
                stats[cache_name] = {"error": str(exc)}

        # Threat detector in-memory state
        try:
            from ..security.threats import ThreatDetector
            td = ThreatDetector()
            stats["threat_detector"] = {
                "tracked_ips":    len(td._request_log),
                "blocked_ips":    len(td._blocked_ips),
                "threat_scores":  len(td._threat_scores),
            }
        except Exception:
            pass

        return stats

    # ------------------------------------------------------------------
    # Connection stats
    # ------------------------------------------------------------------

    def get_connection_stats(self) -> dict:
        """
        Return active database connection information.
        """
        try:
            conn = get_connection()
            # SQLite WAL stats
            wal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            cache_size = conn.execute("PRAGMA cache_size").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

            return {
                "journal_mode": wal_mode,
                "cache_size":   cache_size,
                "busy_timeout": busy_timeout,
                "thread_count": threading.active_count(),
            }
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------

    def get_background_tasks(self) -> dict:
        """
        Return status of the background scheduler if available.
        """
        try:
            from ..scheduler import scheduler as sched
            jobs = []
            if hasattr(sched, "get_jobs"):
                for job in sched.get_jobs():
                    jobs.append({
                        "id":         getattr(job, "id", str(job)),
                        "name":       getattr(job, "name", ""),
                        "next_run":   str(getattr(job, "next_run_time", "")),
                    })
            return {"scheduler_running": True, "jobs": jobs}
        except Exception:
            return {"scheduler_running": False, "jobs": []}

    # ------------------------------------------------------------------
    # Rate limit stats
    # ------------------------------------------------------------------

    def get_rate_limit_stats(self) -> dict:
        """
        Return rate-limiter statistics.
        """
        try:
            from ..ratelimit import RateLimiter
            rl = RateLimiter()
            if hasattr(rl, "_buckets"):
                return {
                    "tracked_keys": len(rl._buckets),
                    "buckets_sample": list(rl._buckets.keys())[:10],
                }
        except Exception:
            pass

        return {"note": "Rate limiter stats not available"}

    # ------------------------------------------------------------------
    # Error log
    # ------------------------------------------------------------------

    def get_error_log(self, limit: int = 100) -> list:
        """Return recent errors from the in-memory error ring buffer."""
        limit = max(1, min(limit, 1000))
        with _error_lock:
            return list(_error_log[-limit:])

    # ------------------------------------------------------------------
    # Slow queries
    # ------------------------------------------------------------------

    def get_slow_queries(self, threshold_ms: float = 100) -> list:
        """Return slow query log entries above the threshold."""
        with _slow_lock:
            return [q for q in _slow_queries if q.get("elapsed_ms", 0) >= threshold_ms]

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        """
        Return current configuration (sanitized — no secrets).
        Merges environment variables with runtime overrides.
        """
        env_config = {
            "PUBLIC_URL":    os.environ.get("PUBLIC_URL", ""),
            "DATABASE_URL":  "***",  # Always hide
            "CORS_ORIGINS":  os.environ.get("CORS_ORIGINS", ""),
            "COINGECKO_API_KEY": "***" if os.environ.get("COINGECKO_API_KEY") else "",
        }

        with _config_lock:
            merged = {**env_config, **_runtime_config}

        # Remove any that accidentally contain secret
        sanitized = {
            k: ("***" if "key" in k.lower() or "secret" in k.lower() or "password" in k.lower() else v)
            for k, v in merged.items()
        }

        return sanitized

    def update_config(self, key: str, value: Any) -> dict:
        """
        Update a runtime configuration value.
        Changes are in-memory only (not persisted across restarts).
        """
        if not key or not isinstance(key, str):
            return {"error": "key must be a non-empty string"}

        # Block sensitive keys
        blocked_keys = {"DATABASE_URL", "SECRET_KEY", "MASTER_KEY", "API_SECRET"}
        if key.upper() in blocked_keys:
            return {"error": f"Key '{key}' cannot be modified at runtime"}

        with _config_lock:
            old_value = _runtime_config.get(key)
            _runtime_config[key] = value

        # Audit the change
        try:
            from ..security.audit import SecurityAudit
            audit = SecurityAudit()
            audit.log_config_change("admin", key, old_value, value)
        except Exception:
            pass

        return {
            "key":       key,
            "old_value": old_value,
            "new_value": value,
            "updated_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def run_maintenance(self) -> dict:
        """
        Run database maintenance operations:
        VACUUM, analyze, cleanup expired sessions, and old audit entries.
        """
        results: dict = {}
        started = time.time()

        try:
            conn = get_connection()

            # Delete expired sessions
            cursor = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (int(time.time()),))
            results["expired_sessions_deleted"] = cursor.rowcount

            # Delete old audit log entries (keep 90 days)
            cutoff = int(time.time()) - (90 * 86400)
            cursor = conn.execute(
                "DELETE FROM security_audit_log WHERE timestamp < ?", (cutoff,)
            )
            results["old_audit_entries_deleted"] = cursor.rowcount

            conn.commit()

            # VACUUM (reclaim space)
            conn.execute("VACUUM")
            results["vacuum"] = "ok"

            # ANALYZE (update query planner stats)
            conn.execute("ANALYZE")
            results["analyze"] = "ok"

        except Exception as exc:
            results["error"] = str(exc)

        # Clear in-memory logs
        with _error_lock:
            cleared_errors = len(_error_log)
            _error_log.clear()
        results["error_log_cleared"] = cleared_errors

        # Purge old threat detector entries
        try:
            from ..security.threats import ThreatDetector
            cleared = ThreatDetector().purge_old_records(older_than=3600)
            results["threat_records_purged"] = cleared
        except Exception:
            pass

        elapsed = round((time.time() - started) * 1000, 1)
        results["elapsed_ms"] = elapsed
        results["completed_at"] = int(time.time())

        return results

    # ------------------------------------------------------------------
    # Migration status
    # ------------------------------------------------------------------

    def get_migration_status(self) -> dict:
        """
        Return the current database migration/schema status.
        Checks presence of all expected tables.
        """
        expected_tables = [
            "users", "sessions", "savings_goals", "savings_deposits",
            "user_achievements", "user_preferences", "security_audit_log",
            "banned_users", "admin_notes",
        ]

        found = []
        missing = []

        try:
            conn = get_connection()
            existing = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

            for table in expected_tables:
                if table in existing:
                    found.append(table)
                else:
                    missing.append(table)

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "schema_complete": len(missing) == 0,
            "tables_found":   found,
            "tables_missing": missing,
            "checked_at":     int(time.time()),
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def run_diagnostics(self) -> dict:
        """
        Run a comprehensive system diagnostics suite.
        Combines system info, DB stats, cache stats, migration status,
        and a health summary.
        """
        diag: dict = {}
        started = time.time()

        diag["system"]     = self.get_system_info()
        diag["database"]   = self.get_database_stats()
        diag["cache"]      = self.get_cache_stats()
        diag["migrations"] = self.get_migration_status()
        diag["background"] = self.get_background_tasks()
        diag["rate_limits"] = self.get_rate_limit_stats()
        diag["connections"] = self.get_connection_stats()

        # Overall health
        issues = []
        if diag["migrations"].get("tables_missing"):
            issues.append(f"Missing tables: {diag['migrations']['tables_missing']}")
        if not diag["database"].get("tables"):
            issues.append("Database not accessible")
        if diag["system"].get("uptime", {}).get("uptime_seconds", 0) < 60:
            issues.append("Server recently restarted")

        diag["health"] = {
            "healthy": len(issues) == 0,
            "issues":  issues,
        }

        diag["diagnostics_elapsed_ms"] = round((time.time() - started) * 1000, 1)
        diag["ran_at"] = int(time.time())

        return diag

    # ------------------------------------------------------------------
    # Uptime
    # ------------------------------------------------------------------

    def get_uptime(self) -> dict:
        """Return uptime information."""
        now = int(time.time())
        uptime_secs = now - _SERVER_START_TIME

        return {
            "start_time":     _SERVER_START_TIME,
            "current_time":   now,
            "uptime_seconds": uptime_secs,
            "uptime_human":   _format_duration(uptime_secs),
        }

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------

    def get_performance_metrics(self) -> dict:
        """
        Compute request latency percentiles (p50, p95, p99) from
        the in-memory performance samples buffer.
        """
        with _perf_lock:
            samples = list(_perf_samples)

        if not samples:
            return {"note": "No performance data collected yet"}

        now = int(time.time())

        # Last 5 minutes
        recent = [s["latency_ms"] for s in samples if s["ts"] >= now - 300]
        all_latencies = [s["latency_ms"] for s in samples]

        def percentile(data: list, p: float) -> float:
            if not data:
                return 0.0
            sorted_data = sorted(data)
            k = (len(sorted_data) - 1) * p / 100
            lo = int(k)
            hi = lo + 1
            if hi >= len(sorted_data):
                return sorted_data[-1]
            return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)

        # Per-endpoint breakdown
        endpoint_map: dict = {}
        for s in samples[-1000:]:
            ep = s["endpoint"]
            if ep not in endpoint_map:
                endpoint_map[ep] = []
            endpoint_map[ep].append(s["latency_ms"])

        endpoint_stats = {}
        for ep, latencies in endpoint_map.items():
            endpoint_stats[ep] = {
                "count": len(latencies),
                "p50":   round(percentile(latencies, 50), 2),
                "p95":   round(percentile(latencies, 95), 2),
                "p99":   round(percentile(latencies, 99), 2),
                "avg":   round(sum(latencies) / len(latencies), 2),
            }

        return {
            "all_time": {
                "count": len(all_latencies),
                "p50":   round(percentile(all_latencies, 50), 2),
                "p95":   round(percentile(all_latencies, 95), 2),
                "p99":   round(percentile(all_latencies, 99), 2),
                "avg":   round(sum(all_latencies) / len(all_latencies), 2) if all_latencies else 0,
            },
            "last_5m": {
                "count": len(recent),
                "p50":   round(percentile(recent, 50), 2),
                "p95":   round(percentile(recent, 95), 2),
                "p99":   round(percentile(recent, 99), 2),
                "avg":   round(sum(recent) / len(recent), 2) if recent else 0,
            },
            "by_endpoint": endpoint_stats,
            "sample_buffer_size": len(samples),
            "generated_at": now,
        }

    # ------------------------------------------------------------------
    # Webhook stats
    # ------------------------------------------------------------------

    def get_webhook_stats(self) -> dict:
        """Return webhook delivery statistics (stubbed until webhook module exposes metrics)."""
        try:
            from ..webhooks import get_stats
            return get_stats()
        except Exception:
            return {"note": "Webhook stats not available"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration string."""
    parts = []
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts) or "0s"
