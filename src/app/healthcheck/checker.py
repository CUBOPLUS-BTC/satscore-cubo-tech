"""
Health-check framework for the Magma Bitcoin application.

Provides:
  - CheckResult     — outcome of a single check
  - HealthReport    — aggregated outcome of all checks
  - HealthChecker   — registry and runner for health checks

All pure Python stdlib.
"""

import logging
import threading
import time
import traceback
from collections import deque
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------

class CheckResult:
    """
    Outcome of a single health probe.

    Attributes:
        name:        Probe name (e.g. ``"database"``, ``"coingecko"``).
        status:      ``"healthy"``, ``"degraded"``, or ``"unhealthy"``.
        message:     Human-readable description of the result.
        duration_ms: Time taken to run the probe (milliseconds).
        metadata:    Arbitrary extra data attached by the probe.
    """

    STATUS_HEALTHY   = "healthy"
    STATUS_DEGRADED  = "degraded"
    STATUS_UNHEALTHY = "unhealthy"

    def __init__(
        self,
        name: str,
        status: str,
        message: str = "",
        duration_ms: float = 0.0,
        metadata: Optional[Dict] = None,
    ):
        self.name = name
        self.status = status
        self.message = message
        self.duration_ms = round(duration_ms, 3)
        self.metadata = metadata or {}
        self.timestamp = time.time()

    @classmethod
    def healthy(cls, name: str, message: str = "OK", duration_ms: float = 0.0, **metadata) -> "CheckResult":
        return cls(name, cls.STATUS_HEALTHY, message, duration_ms, metadata or None)

    @classmethod
    def degraded(cls, name: str, message: str, duration_ms: float = 0.0, **metadata) -> "CheckResult":
        return cls(name, cls.STATUS_DEGRADED, message, duration_ms, metadata or None)

    @classmethod
    def unhealthy(cls, name: str, message: str, duration_ms: float = 0.0, **metadata) -> "CheckResult":
        return cls(name, cls.STATUS_UNHEALTHY, message, duration_ms, metadata or None)

    def is_healthy(self) -> bool:
        return self.status == self.STATUS_HEALTHY

    def is_degraded(self) -> bool:
        return self.status == self.STATUS_DEGRADED

    def is_unhealthy(self) -> bool:
        return self.status == self.STATUS_UNHEALTHY

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def __repr__(self):
        return f"<CheckResult name='{self.name}' status='{self.status}' {self.duration_ms}ms>"


# ---------------------------------------------------------------------------
# HealthReport
# ---------------------------------------------------------------------------

class HealthReport:
    """
    Aggregated result of all registered health checks.

    The overall ``status`` is derived from individual check results:
    - All healthy  → ``"healthy"``
    - Any critical check unhealthy → ``"unhealthy"``
    - Any check degraded (non-critical unhealthy) → ``"degraded"``
    """

    def __init__(
        self,
        checks: List[CheckResult],
        duration_ms: float,
        critical_names: Optional[List[str]] = None,
    ):
        self.checks = checks
        self.duration_ms = round(duration_ms, 3)
        self.timestamp = time.time()
        self._critical_names = set(critical_names or [])
        self.status = self._derive_status()

    def _derive_status(self) -> str:
        for check in self.checks:
            if check.is_unhealthy() and check.name in self._critical_names:
                return "unhealthy"
        for check in self.checks:
            if check.is_unhealthy() or check.is_degraded():
                return "degraded"
        return "healthy"

    def is_healthy(self) -> bool:
        return self.status == "healthy"

    def get_failed_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.is_healthy()]

    def get_critical_failures(self) -> List[CheckResult]:
        return [
            c for c in self.checks
            if c.name in self._critical_names and c.is_unhealthy()
        ]

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "checks": [c.to_dict() for c in self.checks],
            "summary": {
                "total": len(self.checks),
                "healthy": sum(1 for c in self.checks if c.is_healthy()),
                "degraded": sum(1 for c in self.checks if c.is_degraded()),
                "unhealthy": sum(1 for c in self.checks if c.is_unhealthy()),
            },
        }

    def __repr__(self):
        return (
            f"<HealthReport status='{self.status}' "
            f"checks={len(self.checks)} "
            f"{self.duration_ms}ms>"
        )


# ---------------------------------------------------------------------------
# HealthChecker
# ---------------------------------------------------------------------------

class _RegisteredCheck:
    """Internal descriptor for a registered health check."""
    __slots__ = ("name", "check_fn", "critical", "timeout", "enabled")

    def __init__(self, name, check_fn, critical, timeout):
        self.name = name
        self.check_fn = check_fn
        self.critical = critical
        self.timeout = timeout
        self.enabled = True


class HealthChecker:
    """
    Registry and runner for named health checks.

    Usage::

        checker = HealthChecker()
        checker.register_check("database", probe_database, critical=True)
        checker.register_check("coingecko", probe_coingecko, critical=False)

        report = checker.run_all()
        print(report.status)  # "healthy" | "degraded" | "unhealthy"
    """

    def __init__(self):
        self._checks: Dict[str, _RegisteredCheck] = {}
        self._lock = threading.RLock()
        self._started_at = time.time()
        self._history: deque = deque(maxlen=100)  # last 100 HealthReports
        self._run_count = 0

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], CheckResult],
        critical: bool = False,
        timeout: int = 5,
    ) -> None:
        """
        Register a health-check probe.

        Args:
            name:     Unique check name.
            check_fn: Zero-argument callable returning a :class:`CheckResult`.
            critical: If True, an unhealthy result marks the whole app unhealthy.
            timeout:  Max seconds to wait for the probe (unused in stdlib; kept
                      for API symmetry – callers should implement timeouts in
                      their ``check_fn`` if needed).
        """
        with self._lock:
            self._checks[name] = _RegisteredCheck(name, check_fn, critical, timeout)
            logger.debug("HealthChecker: registered check '%s' (critical=%s)", name, critical)

    def unregister_check(self, name: str) -> bool:
        """Remove a registered check. Returns True if it existed."""
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                return True
            return False

    def enable_check(self, name: str) -> None:
        with self._lock:
            if name in self._checks:
                self._checks[name].enabled = True

    def disable_check(self, name: str) -> None:
        with self._lock:
            if name in self._checks:
                self._checks[name].enabled = False

    def run_check(self, name: str) -> CheckResult:
        """
        Run a single registered check by name.

        Args:
            name: Check name.

        Returns:
            :class:`CheckResult`.
        """
        with self._lock:
            registered = self._checks.get(name)

        if registered is None:
            return CheckResult.unhealthy(name, f"Check '{name}' is not registered")

        if not registered.enabled:
            return CheckResult.healthy(name, "Check is disabled", metadata={"disabled": True})

        start = time.perf_counter()
        try:
            result = registered.check_fn()
            elapsed = (time.perf_counter() - start) * 1000
            result.duration_ms = round(elapsed, 3)
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("HealthChecker: check '%s' raised an exception: %s", name, exc)
            return CheckResult.unhealthy(
                name,
                f"Exception: {exc}",
                duration_ms=elapsed,
                traceback=traceback.format_exc(),
            )

    def run_all(self) -> HealthReport:
        """
        Execute all enabled checks sequentially and return a :class:`HealthReport`.

        Returns:
            Aggregated :class:`HealthReport`.
        """
        start = time.perf_counter()
        with self._lock:
            checks_snapshot = list(self._checks.values())

        results = []
        for reg in checks_snapshot:
            if reg.enabled:
                results.append(self.run_check(reg.name))

        elapsed = (time.perf_counter() - start) * 1000
        critical_names = [r.name for r in checks_snapshot if r.critical]
        report = HealthReport(results, elapsed, critical_names)

        with self._lock:
            self._history.append(report)
            self._run_count += 1

        logger.info(
            "HealthChecker.run_all: %s (%d checks, %.1fms)",
            report.status, len(results), elapsed,
        )
        return report

    def get_status(self) -> str:
        """
        Return the last known overall health status string.

        Returns:
            ``"healthy"``, ``"degraded"``, ``"unhealthy"``, or ``"unknown"``.
        """
        with self._lock:
            if not self._history:
                return "unknown"
            return self._history[-1].status

    def get_uptime(self) -> Dict:
        """Return uptime information."""
        uptime_sec = time.time() - self._started_at
        days, remainder = divmod(int(uptime_sec), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return {
            "started_at": self._started_at,
            "uptime_seconds": round(uptime_sec, 1),
            "uptime_human": f"{days}d {hours}h {minutes}m {seconds}s",
            "run_count": self._run_count,
        }

    def get_history(self, limit: int = 10) -> List[Dict]:
        """
        Return the last ``limit`` health reports as dicts.

        Args:
            limit: Maximum number of reports to return.

        Returns:
            List of report dicts (most recent last).
        """
        with self._lock:
            recent = list(self._history)[-limit:]
        return [r.to_dict() for r in recent]

    def get_registered_checks(self) -> List[Dict]:
        """Return metadata about all registered checks."""
        with self._lock:
            return [
                {
                    "name": r.name,
                    "critical": r.critical,
                    "timeout": r.timeout,
                    "enabled": r.enabled,
                }
                for r in self._checks.values()
            ]

    def __repr__(self):
        with self._lock:
            return (
                f"<HealthChecker checks={len(self._checks)} "
                f"runs={self._run_count} "
                f"status='{self.get_status()}'>"
            )


# ---------------------------------------------------------------------------
# Module-level default checker instance
# ---------------------------------------------------------------------------

_default_checker: Optional[HealthChecker] = None


def get_default_checker() -> HealthChecker:
    """Return (or lazily create) the module-level default HealthChecker."""
    global _default_checker
    if _default_checker is None:
        _default_checker = HealthChecker()
    return _default_checker
