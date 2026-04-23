"""
Structured logging for Magma.

Provides:
- StructuredLogger: wraps Python logging with JSON-formatted entries.
- RequestLogger:    logs HTTP request/response details.
- AuditLogger:      logs security-relevant events.
- PerformanceLogger: tracks slow operations.
- setup_logging():  configures the root logger with file rotation.

Example::

    from app.logging_config import setup_logging, StructuredLogger

    setup_logging(log_dir="/var/log/magma", level="INFO")
    log = StructuredLogger("app.savings")
    log.info("deposit_recorded", amount_usd=100.0, pubkey="abc...")
"""

import json
import logging
import logging.handlers
import os
import threading
import time
import traceback
import uuid
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_setup_done = False
_setup_lock = threading.Lock()

# Per-request context stored in thread-local storage.
_request_ctx = threading.local()

# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Formats log records as compact JSON lines.

    Each line is a self-contained JSON object with the following guaranteed
    fields:
        timestamp   ISO-8601 UTC time string
        level       Log level name (INFO, WARNING, …)
        logger      Logger name
        message     The log message
        module      Source module name
        lineno      Source line number

    Additional keyword arguments passed via the ``extra`` dict are merged
    into the root of the JSON object.
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        entry: dict[str, Any] = {
            "timestamp": self._utc_iso(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "lineno": record.lineno,
        }

        # Thread-local request context
        request_id = getattr(_request_ctx, "request_id", None)
        if request_id:
            entry["request_id"] = request_id

        # Extra fields injected via logger.info(..., extra={...})
        for key, val in record.__dict__.items():
            if key not in _LOGGING_RESERVED and not key.startswith("_"):
                entry[key] = val

        # Exception info
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str, separators=(",", ":"))

    @staticmethod
    def _utc_iso(timestamp: float) -> str:
        import datetime
        dt = datetime.datetime.utcfromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Fields that belong to the standard LogRecord and should not be
# duplicated in the extra payload.
_LOGGING_RESERVED = frozenset({
    "name", "msg", "args", "created", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs",
    "pathname", "process", "processName", "relativeCreated",
    "thread", "threadName", "exc_info", "exc_text", "stack_info",
    "message",
})

# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------


class StructuredLogger:
    """Convenience wrapper around a standard Python logger that emits
    structured (JSON) log entries.

    Usage::

        log = StructuredLogger("app.pension")
        log.info("projection_calculated", monthly_usd=200, years=20)
        log.warning("price_source_unavailable", source="kraken")
        log.error("db_error", table="users", error=str(exc))

    The first positional argument is the *event* (analogous to a log
    message); subsequent keyword arguments become extra JSON fields.
    """

    def __init__(self, name: str, level: Optional[str] = None):
        self._logger = logging.getLogger(name)
        if level:
            self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # -- Public methods -- #

    def debug(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, event, **kwargs)

    def error(self, event: str, exc: Optional[Exception] = None, **kwargs: Any) -> None:
        if exc is not None:
            kwargs["error_type"] = type(exc).__name__
            kwargs["error_message"] = str(exc)
        self._emit(logging.ERROR, event, exc_info=exc is not None, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.CRITICAL, event, **kwargs)

    def timed(self, event: str, start_time: float, **kwargs: Any) -> None:
        """Log an event with an automatically computed duration_ms field."""
        duration_ms = int((time.time() - start_time) * 1000)
        self._emit(logging.INFO, event, duration_ms=duration_ms, **kwargs)

    # -- Internals -- #

    def _emit(
        self,
        level: int,
        event: str,
        exc_info: bool = False,
        **extra: Any,
    ) -> None:
        if not self._logger.isEnabledFor(level):
            return
        extra["event"] = event
        self._logger.log(level, event, exc_info=exc_info, extra=extra)

    @property
    def name(self) -> str:
        return self._logger.name

    def set_level(self, level: str) -> None:
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))


# ---------------------------------------------------------------------------
# RequestLogger
# ---------------------------------------------------------------------------


class RequestLogger:
    """Middleware-style logger that records HTTP request and response details.

    Designed to be used with the pure-stdlib HTTP server in main.py.

    Usage::

        rlog = RequestLogger()

        # At the start of a request handler:
        request_id = rlog.start_request(method, path, headers)

        # At the end:
        rlog.end_request(request_id, status_code=200)
    """

    _log = StructuredLogger("magma.request")

    def start_request(
        self,
        method: str,
        path: str,
        remote_addr: str = "",
        headers: Optional[dict] = None,
    ) -> str:
        """Record the start of an incoming HTTP request.

        Returns a request_id that should be passed to end_request().
        """
        request_id = uuid.uuid4().hex
        _request_ctx.request_id = request_id
        _request_ctx.start_time = time.time()

        self._log.info(
            "request_started",
            request_id=request_id,
            method=method,
            path=path,
            remote_addr=remote_addr,
            content_type=(headers or {}).get("Content-Type", ""),
        )
        return request_id

    def end_request(
        self,
        request_id: str,
        status_code: int,
        response_size_bytes: int = 0,
    ) -> None:
        """Record the completion of an HTTP request."""
        start_time = getattr(_request_ctx, "start_time", None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0

        level = logging.INFO
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING

        self._log._emit(
            level,
            "request_completed",
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            response_bytes=response_size_bytes,
        )

        # Clear context
        _request_ctx.request_id = None
        _request_ctx.start_time = None

    def log_error(self, request_id: str, exc: Exception) -> None:
        """Log an unhandled exception during request processing."""
        self._log.error(
            "request_error",
            exc=exc,
            request_id=request_id,
            traceback=traceback.format_exc(),
        )


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Logs security-relevant events to a dedicated audit logger.

    Events are always logged at INFO level regardless of the root log level
    so that the audit trail is complete.

    Usage::

        audit = AuditLogger()
        audit.auth_attempt(pubkey="abc...", method="lnurl", success=True)
        audit.session_created(pubkey="abc...", token_prefix="deadbeef")
        audit.session_expired(pubkey="abc...")
        audit.permission_denied(pubkey="abc...", resource="/admin/users")
    """

    _log = StructuredLogger("magma.audit")

    def auth_attempt(
        self,
        pubkey: str,
        method: str,
        success: bool,
        remote_addr: str = "",
        failure_reason: str = "",
    ) -> None:
        event = "auth_success" if success else "auth_failure"
        self._log.info(
            event,
            pubkey=pubkey[:16] + "...",
            method=method,
            success=success,
            remote_addr=remote_addr,
            failure_reason=failure_reason,
        )

    def session_created(self, pubkey: str, token_prefix: str = "") -> None:
        self._log.info(
            "session_created",
            pubkey=pubkey[:16] + "...",
            token_prefix=token_prefix[:8] if token_prefix else "",
        )

    def session_expired(self, pubkey: str) -> None:
        self._log.info("session_expired", pubkey=pubkey[:16] + "...")

    def permission_denied(self, pubkey: str, resource: str) -> None:
        self._log.warning(
            "permission_denied",
            pubkey=pubkey[:16] + "...",
            resource=resource,
        )

    def data_access(self, pubkey: str, resource: str, action: str) -> None:
        """Log data access (read/write/delete) for GDPR / compliance trails."""
        self._log.info(
            "data_access",
            pubkey=pubkey[:16] + "...",
            resource=resource,
            action=action,
        )

    def user_deleted(self, deleted_by: str, target_pubkey: str) -> None:
        self._log.warning(
            "user_deleted",
            deleted_by=deleted_by[:16] + "...",
            target_pubkey=target_pubkey[:16] + "...",
        )

    def rate_limit_exceeded(self, identifier: str, endpoint: str) -> None:
        self._log.warning(
            "rate_limit_exceeded",
            identifier=identifier,
            endpoint=endpoint,
        )


# ---------------------------------------------------------------------------
# PerformanceLogger
# ---------------------------------------------------------------------------


class PerformanceLogger:
    """Tracks and logs slow operations.

    Wrap any code block with start_timer() / stop_timer(), or use the
    context-manager / decorator via timed_block().

    Usage::

        perf = PerformanceLogger(slow_threshold_ms=200)

        timer_id = perf.start("coingecko_price_fetch")
        price = client.get_price()
        perf.stop(timer_id, operation="coingecko_price_fetch")
    """

    _log = StructuredLogger("magma.perf")

    def __init__(self, slow_threshold_ms: int = 500):
        self._threshold_ms = slow_threshold_ms
        self._timers: dict[str, float] = {}
        self._lock = threading.Lock()

    def start(self, operation: str) -> str:
        """Start a timer. Returns a timer_id to pass to stop()."""
        timer_id = uuid.uuid4().hex
        with self._lock:
            self._timers[timer_id] = time.time()
        return timer_id

    def stop(
        self,
        timer_id: str,
        operation: str = "",
        **extra: Any,
    ) -> int:
        """Stop a timer and log if the duration exceeds the threshold.

        Returns the duration in milliseconds.
        """
        with self._lock:
            start = self._timers.pop(timer_id, None)

        if start is None:
            return 0

        duration_ms = int((time.time() - start) * 1000)
        is_slow = duration_ms >= self._threshold_ms

        if is_slow:
            self._log.warning(
                "slow_operation",
                operation=operation,
                duration_ms=duration_ms,
                threshold_ms=self._threshold_ms,
                **extra,
            )
        else:
            self._log.debug(
                "operation_completed",
                operation=operation,
                duration_ms=duration_ms,
                **extra,
            )

        return duration_ms

    class _TimedBlock:
        """Context manager returned by timed_block()."""

        def __init__(self, perf: "PerformanceLogger", operation: str, extra: dict):
            self._perf = perf
            self._operation = operation
            self._extra = extra
            self._timer_id: Optional[str] = None
            self.duration_ms: int = 0

        def __enter__(self) -> "PerformanceLogger._TimedBlock":
            self._timer_id = self._perf.start(self._operation)
            return self

        def __exit__(self, *_) -> None:
            if self._timer_id:
                self.duration_ms = self._perf.stop(
                    self._timer_id, operation=self._operation, **self._extra
                )

    def timed_block(self, operation: str, **extra: Any) -> "_TimedBlock":
        """Return a context manager that times the wrapped block.

        Usage::

            with perf.timed_block("db_query", table="users") as t:
                result = conn.execute(...).fetchall()
            print(t.duration_ms)
        """
        return self._TimedBlock(self, operation, extra)

    def record(self, operation: str, duration_ms: int, **extra: Any) -> None:
        """Record a duration directly (e.g. from an external timer)."""
        is_slow = duration_ms >= self._threshold_ms
        event = "slow_operation" if is_slow else "operation_completed"
        level = logging.WARNING if is_slow else logging.DEBUG
        self._log._emit(
            level,
            event,
            operation=operation,
            duration_ms=duration_ms,
            threshold_ms=self._threshold_ms,
            **extra,
        )


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


def setup_logging(
    log_dir: str = "./logs",
    level: str = "INFO",
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,   # 10 MB
    backup_count: int = 5,
    module_levels: Optional[dict[str, str]] = None,
) -> None:
    """Configure the root logger with optional JSON formatting and rotation.

    Args:
        log_dir:       Directory for log files. Created if it does not exist.
        level:         Root log level string, e.g. "INFO", "DEBUG".
        json_format:   Use JSONFormatter when True, plain text when False.
        max_bytes:     Maximum size of a single log file before rotation.
        backup_count:  Number of rotated backup files to keep.
        module_levels: Per-module log level overrides, e.g.
                       {"app.services": "DEBUG", "app.auth": "WARNING"}.
    """
    global _setup_done
    with _setup_lock:
        if _setup_done:
            return

        numeric_level = getattr(logging, level.upper(), logging.INFO)

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

        formatter: logging.Formatter
        if json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        # Console handler — always plain text for readability
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s  %(levelname)-8s  %(name)-25s  %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        console_handler.setLevel(numeric_level)

        # Rotating file handler — JSON for structured ingestion
        app_log_path = os.path.join(log_dir, "magma.log")
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)

        # Dedicated audit log (never rotated away; separate file)
        audit_log_path = os.path.join(log_dir, "audit.log")
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        audit_handler.setFormatter(formatter)
        audit_handler.setLevel(logging.DEBUG)  # capture everything in audit

        # Error-only handler for quick error scanning
        error_log_path = os.path.join(log_dir, "errors.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)

        # Root logger
        root = logging.getLogger()
        root.setLevel(numeric_level)
        root.addHandler(console_handler)
        root.addHandler(file_handler)
        root.addHandler(error_handler)

        # Audit logger — dedicated handler
        audit_logger = logging.getLogger("magma.audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = True  # also goes to root handlers

        # Per-module level overrides
        if module_levels:
            for mod_name, mod_level in module_levels.items():
                mod_numeric = getattr(logging, mod_level.upper(), logging.INFO)
                logging.getLogger(mod_name).setLevel(mod_numeric)

        # Silence noisy third-party loggers
        for noisy in ("urllib3", "urllib", "httpx", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

        _setup_done = True


# ---------------------------------------------------------------------------
# Module-level singleton instances for import convenience
# ---------------------------------------------------------------------------

request_logger = RequestLogger()
audit_logger = AuditLogger()
perf_logger = PerformanceLogger(slow_threshold_ms=300)
