"""
HTTP route handlers for the Magma health-check endpoints.

Handlers follow the same ``(body: dict) -> (status_code: int, response: dict)``
convention used throughout the rest of the stdlib HTTP server.

Endpoints:
  GET /health            → detailed report (handle_health_detailed)
  GET /health/live       → Kubernetes liveness probe (handle_health_liveness)
  GET /health/ready      → Kubernetes readiness probe (handle_health_readiness)
"""

import logging
import time

from .checker import HealthChecker, get_default_checker
from .probes import (
    probe_database,
    probe_coingecko,
    probe_kraken,
    probe_mempool,
    probe_wise,
    probe_disk_space,
    probe_memory,
    probe_cpu,
    probe_sessions,
    probe_rate_limits,
    probe_scheduler,
    probe_webhooks,
    probe_cache,
    probe_dns,
    probe_response_time,
    probe_error_rate,
    probe_database_connections,
    probe_migrations,
    probe_external_connectivity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level checker, lazily initialised
# ---------------------------------------------------------------------------

_checker: HealthChecker = None


def _get_checker() -> HealthChecker:
    """Return (or build) the module-level HealthChecker with all probes registered."""
    global _checker
    if _checker is not None:
        return _checker

    checker = get_default_checker()

    # Critical checks – their failure makes the whole app "unhealthy"
    checker.register_check("database",             probe_database,             critical=True,  timeout=5)
    checker.register_check("migrations",           probe_migrations,           critical=True,  timeout=5)
    checker.register_check("database_connections", probe_database_connections, critical=True,  timeout=10)

    # Non-critical external dependencies
    checker.register_check("coingecko",            probe_coingecko,            critical=False, timeout=5)
    checker.register_check("kraken",               probe_kraken,               critical=False, timeout=5)
    checker.register_check("mempool",              probe_mempool,              critical=False, timeout=5)
    checker.register_check("wise",                 probe_wise,                 critical=False, timeout=5)
    checker.register_check("dns",                  probe_dns,                  critical=False, timeout=5)
    checker.register_check("external_connectivity",probe_external_connectivity,critical=False, timeout=8)

    # System resource probes
    checker.register_check("disk_space",           probe_disk_space,           critical=False, timeout=3)
    checker.register_check("memory",               probe_memory,               critical=False, timeout=3)
    checker.register_check("cpu",                  probe_cpu,                  critical=False, timeout=3)

    # Application-internal probes
    checker.register_check("sessions",             probe_sessions,             critical=False, timeout=2)
    checker.register_check("rate_limits",          probe_rate_limits,          critical=False, timeout=2)
    checker.register_check("scheduler",            probe_scheduler,            critical=False, timeout=2)
    checker.register_check("webhooks",             probe_webhooks,             critical=False, timeout=3)
    checker.register_check("cache",                probe_cache,                critical=False, timeout=2)
    checker.register_check("response_time",        probe_response_time,        critical=False, timeout=5)
    checker.register_check("error_rate",           probe_error_rate,           critical=False, timeout=2)

    _checker = checker
    logger.info("Health checker initialised with %d probes", len(checker.get_registered_checks()))
    return _checker


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_health_detailed(body: dict) -> tuple:
    """
    Run all registered health probes and return a full report.

    HTTP method: GET
    Path:        /health  or  /health/detailed

    Response body (JSON)::

        {
            "status":      "healthy" | "degraded" | "unhealthy",
            "timestamp":   1234567890.0,
            "duration_ms": 142.3,
            "uptime":      { ... },
            "checks":      [ { "name": ..., "status": ..., "message": ..., ... }, ... ],
            "summary":     { "total": 18, "healthy": 17, "degraded": 1, "unhealthy": 0 }
        }

    Returns:
        (http_status_code, response_dict) tuple.
    """
    checker = _get_checker()
    report = checker.run_all()
    report_dict = report.to_dict()
    report_dict["uptime"] = checker.get_uptime()

    # Map health status to HTTP status code
    http_status = _status_to_http(report.status)
    return http_status, report_dict


def handle_health_liveness(body: dict) -> tuple:
    """
    Kubernetes liveness probe – answers "is the process alive?".

    Only runs the absolute minimum checks (database ping + migrations).
    Returns HTTP 200 as long as the process is functional enough to respond;
    HTTP 503 if critical checks fail.

    HTTP method: GET
    Path:        /health/live

    Response body::

        { "status": "alive" | "dead", "checks": [...] }
    """
    checker = _get_checker()
    critical_names = ["database", "migrations"]
    results = []
    for name in critical_names:
        results.append(checker.run_check(name))

    all_ok = all(r.is_healthy() or r.is_degraded() for r in results)
    status = "alive" if all_ok else "dead"
    http_status = 200 if all_ok else 503

    return http_status, {
        "status": status,
        "timestamp": time.time(),
        "checks": [r.to_dict() for r in results],
    }


def handle_health_readiness(body: dict) -> tuple:
    """
    Kubernetes readiness probe – answers "can the app serve traffic?".

    Runs critical infrastructure checks (database, migrations, DNS,
    external connectivity).  Returns HTTP 200 when all pass, HTTP 503
    otherwise so the load balancer stops routing traffic to this instance.

    HTTP method: GET
    Path:        /health/ready

    Response body::

        { "status": "ready" | "not_ready", "checks": [...] }
    """
    checker = _get_checker()
    readiness_checks = [
        "database",
        "migrations",
        "database_connections",
        "dns",
        "external_connectivity",
    ]
    results = []
    for name in readiness_checks:
        results.append(checker.run_check(name))

    all_ok = all(not r.is_unhealthy() for r in results)
    status = "ready" if all_ok else "not_ready"
    http_status = 200 if all_ok else 503

    return http_status, {
        "status": status,
        "timestamp": time.time(),
        "checks": [r.to_dict() for r in results],
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _status_to_http(status: str) -> int:
    """Map a health status string to an HTTP status code."""
    return {
        "healthy":   200,
        "degraded":  200,   # degraded still serves traffic
        "unhealthy": 503,
    }.get(status, 500)
