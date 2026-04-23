"""
Health-check package for the Magma Bitcoin application.

Provides:
  - HealthChecker / HealthReport / CheckResult
  - Individual probes for all external dependencies and system resources
  - HTTP route handlers compatible with the existing stdlib HTTP server
"""

from .checker import HealthChecker, HealthReport, CheckResult
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
    probe_ssl,
    probe_response_time,
    probe_error_rate,
    probe_database_connections,
    probe_migrations,
    probe_external_connectivity,
)
from .routes import (
    handle_health_detailed,
    handle_health_liveness,
    handle_health_readiness,
)

__all__ = [
    "HealthChecker",
    "HealthReport",
    "CheckResult",
    "probe_database",
    "probe_coingecko",
    "probe_kraken",
    "probe_mempool",
    "probe_wise",
    "probe_disk_space",
    "probe_memory",
    "probe_cpu",
    "probe_sessions",
    "probe_rate_limits",
    "probe_scheduler",
    "probe_webhooks",
    "probe_cache",
    "probe_dns",
    "probe_ssl",
    "probe_response_time",
    "probe_error_rate",
    "probe_database_connections",
    "probe_migrations",
    "probe_external_connectivity",
    "handle_health_detailed",
    "handle_health_liveness",
    "handle_health_readiness",
]
