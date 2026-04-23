"""
Security audit logging system for Magma Bitcoin app.
Records all security-relevant events to a dedicated database table.
Provides querying, summarisation, brute-force detection, and report generation.
Pure Python stdlib — no third-party dependencies.
"""

import json
import time
import uuid
import threading
from typing import Any, Optional

from ..database import get_conn as get_connection


# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------

class Severity:
    DEBUG     = "DEBUG"
    INFO      = "INFO"
    WARNING   = "WARNING"
    CRITICAL  = "CRITICAL"
    EMERGENCY = "EMERGENCY"

    _ORDER = {DEBUG: 0, INFO: 1, WARNING: 2, CRITICAL: 3, EMERGENCY: 4}

    @classmethod
    def at_least(cls, level: str, minimum: str) -> bool:
        return cls._ORDER.get(level, 0) >= cls._ORDER.get(minimum, 0)


# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

class EventType:
    AUTH_SUCCESS        = "AUTH_SUCCESS"
    AUTH_FAILURE        = "AUTH_FAILURE"
    RATE_LIMIT          = "RATE_LIMIT"
    SUSPICIOUS          = "SUSPICIOUS"
    DATA_ACCESS         = "DATA_ACCESS"
    CONFIG_CHANGE       = "CONFIG_CHANGE"
    INJECTION_ATTEMPT   = "INJECTION_ATTEMPT"
    BRUTE_FORCE         = "BRUTE_FORCE"
    SESSION_CREATED     = "SESSION_CREATED"
    SESSION_REVOKED     = "SESSION_REVOKED"
    ACCOUNT_LOCKED      = "ACCOUNT_LOCKED"
    PERMISSION_DENIED   = "PERMISSION_DENIED"
    EXPORT_REQUESTED    = "EXPORT_REQUESTED"
    ADMIN_ACTION        = "ADMIN_ACTION"
    API_ABUSE           = "API_ABUSE"
    UNKNOWN             = "UNKNOWN"

    ALL = [
        AUTH_SUCCESS, AUTH_FAILURE, RATE_LIMIT, SUSPICIOUS, DATA_ACCESS,
        CONFIG_CHANGE, INJECTION_ATTEMPT, BRUTE_FORCE, SESSION_CREATED,
        SESSION_REVOKED, ACCOUNT_LOCKED, PERMISSION_DENIED, EXPORT_REQUESTED,
        ADMIN_ACTION, API_ABUSE, UNKNOWN,
    ]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS security_audit_log (
    id          TEXT PRIMARY KEY,
    timestamp   INTEGER NOT NULL,
    event_type  TEXT NOT NULL,
    severity    TEXT NOT NULL,
    source_ip   TEXT NOT NULL DEFAULT '',
    pubkey      TEXT NOT NULL DEFAULT '',
    action      TEXT NOT NULL DEFAULT '',
    details     TEXT NOT NULL DEFAULT '{}',
    request_id  TEXT NOT NULL DEFAULT ''
)
"""

_CREATE_AUDIT_IDX_TIMESTAMP   = "CREATE INDEX IF NOT EXISTS idx_audit_timestamp   ON security_audit_log(timestamp)"
_CREATE_AUDIT_IDX_IP          = "CREATE INDEX IF NOT EXISTS idx_audit_ip           ON security_audit_log(source_ip)"
_CREATE_AUDIT_IDX_PUBKEY      = "CREATE INDEX IF NOT EXISTS idx_audit_pubkey       ON security_audit_log(pubkey)"
_CREATE_AUDIT_IDX_EVENT_TYPE  = "CREATE INDEX IF NOT EXISTS idx_audit_event_type  ON security_audit_log(event_type)"
_CREATE_AUDIT_IDX_SEVERITY    = "CREATE INDEX IF NOT EXISTS idx_audit_severity     ON security_audit_log(severity)"


def _ensure_schema(conn) -> None:
    cursor = conn.cursor()
    cursor.execute(_CREATE_AUDIT_TABLE)
    for ddl in (
        _CREATE_AUDIT_IDX_TIMESTAMP,
        _CREATE_AUDIT_IDX_IP,
        _CREATE_AUDIT_IDX_PUBKEY,
        _CREATE_AUDIT_IDX_EVENT_TYPE,
        _CREATE_AUDIT_IDX_SEVERITY,
    ):
        cursor.execute(ddl)
    conn.commit()


# ---------------------------------------------------------------------------
# SecurityAudit
# ---------------------------------------------------------------------------

class SecurityAudit:
    """
    Central security audit logging system.

    Usage::

        audit = SecurityAudit()
        audit.log_auth_attempt("1.2.3.4", "abc123...", "nostr", True, "OK")
    """

    _instance: Optional["SecurityAudit"] = None
    _lock = threading.Lock()

    # Minimum severity level to persist (can be raised in production)
    min_severity: str = Severity.DEBUG

    def __new__(cls) -> "SecurityAudit":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            try:
                conn = get_connection()
                _ensure_schema(conn)
            except Exception:
                pass  # Best-effort schema creation
            self._initialized = True

    # ------------------------------------------------------------------
    # Core log method
    # ------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        severity: str,
        source_ip: str = "",
        pubkey: str = "",
        action: str = "",
        details: Any = None,
        request_id: str = "",
    ) -> None:
        """
        Persist a security event to the audit log.
        Never raises — all errors are silently swallowed to prevent
        audit logging from breaking the main request flow.
        """
        if not Severity.at_least(severity, self.min_severity):
            return

        if details is None:
            details = {}

        if not request_id:
            request_id = str(uuid.uuid4())

        record_id = str(uuid.uuid4())
        ts = int(time.time())

        try:
            details_json = json.dumps(details, ensure_ascii=False)
        except Exception:
            details_json = "{}"

        try:
            conn = get_connection()
            conn.execute(
                """
                INSERT INTO security_audit_log
                    (id, timestamp, event_type, severity, source_ip, pubkey,
                     action, details, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id, ts, event_type, severity,
                    source_ip or "", pubkey or "", action or "",
                    details_json, request_id,
                ),
            )
            conn.commit()
        except Exception:
            pass  # Never propagate audit errors

    # ------------------------------------------------------------------
    # Convenience logging methods
    # ------------------------------------------------------------------

    def log_auth_attempt(
        self,
        ip: str,
        pubkey: str,
        method: str,
        success: bool,
        reason: str = "",
    ) -> None:
        """Log an authentication attempt (success or failure)."""
        event_type = EventType.AUTH_SUCCESS if success else EventType.AUTH_FAILURE
        severity   = Severity.INFO if success else Severity.WARNING

        self.log_event(
            event_type=event_type,
            severity=severity,
            source_ip=ip,
            pubkey=pubkey,
            action=f"AUTH:{method.upper()}",
            details={
                "method": method,
                "success": success,
                "reason": reason,
                "timestamp": int(time.time()),
            },
        )

    def log_access(
        self,
        ip: str,
        pubkey: str,
        resource: str,
        action: str,
        extra: dict = None,
    ) -> None:
        """Log resource access."""
        self.log_event(
            event_type=EventType.DATA_ACCESS,
            severity=Severity.INFO,
            source_ip=ip,
            pubkey=pubkey,
            action=action,
            details={
                "resource": resource,
                "action": action,
                **(extra or {}),
            },
        )

    def log_rate_limit(
        self,
        ip: str,
        endpoint: str,
        limit: int,
        current: int,
    ) -> None:
        """Log a rate-limit event."""
        self.log_event(
            event_type=EventType.RATE_LIMIT,
            severity=Severity.WARNING,
            source_ip=ip,
            pubkey="",
            action=f"RATE_LIMIT:{endpoint}",
            details={
                "endpoint": endpoint,
                "limit": limit,
                "current": current,
            },
        )

    def log_suspicious_activity(
        self,
        ip: str,
        activity_type: str,
        details: dict = None,
    ) -> None:
        """Log suspicious activity."""
        self.log_event(
            event_type=EventType.SUSPICIOUS,
            severity=Severity.CRITICAL,
            source_ip=ip,
            pubkey="",
            action=f"SUSPICIOUS:{activity_type}",
            details={
                "activity_type": activity_type,
                **(details or {}),
            },
        )

    def log_data_access(
        self,
        pubkey: str,
        data_type: str,
        fields_accessed: list,
    ) -> None:
        """Log user data access (for GDPR/compliance tracking)."""
        self.log_event(
            event_type=EventType.DATA_ACCESS,
            severity=Severity.INFO,
            pubkey=pubkey,
            action=f"DATA_ACCESS:{data_type}",
            details={
                "data_type": data_type,
                "fields": fields_accessed,
                "count": len(fields_accessed),
            },
        )

    def log_injection_attempt(
        self,
        ip: str,
        pubkey: str,
        injection_type: str,
        field: str,
        snippet: str = "",
    ) -> None:
        """Log a detected injection attack attempt."""
        self.log_event(
            event_type=EventType.INJECTION_ATTEMPT,
            severity=Severity.CRITICAL,
            source_ip=ip,
            pubkey=pubkey,
            action=f"INJECTION:{injection_type}",
            details={
                "type": injection_type,
                "field": field,
                "snippet": snippet[:100] if snippet else "",
            },
        )

    def log_config_change(
        self,
        pubkey: str,
        setting: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Log a configuration change."""
        self.log_event(
            event_type=EventType.CONFIG_CHANGE,
            severity=Severity.WARNING,
            pubkey=pubkey,
            action=f"CONFIG:{setting}",
            details={
                "setting": setting,
                "old_value": str(old_value),
                "new_value": str(new_value),
            },
        )

    def log_admin_action(
        self,
        admin_pubkey: str,
        target_pubkey: str,
        action: str,
        details: dict = None,
    ) -> None:
        """Log an administrative action."""
        self.log_event(
            event_type=EventType.ADMIN_ACTION,
            severity=Severity.WARNING,
            pubkey=admin_pubkey,
            action=f"ADMIN:{action}",
            details={
                "admin": admin_pubkey,
                "target": target_pubkey,
                "action": action,
                **(details or {}),
            },
        )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_audit_log(
        self,
        filters: dict = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """
        Retrieve audit log entries with optional filters.

        Supported filters (all optional):
          - event_type: str
          - severity: str (minimum severity)
          - source_ip: str
          - pubkey: str
          - from_ts: int (Unix timestamp)
          - to_ts: int (Unix timestamp)
          - action_prefix: str
        """
        filters = filters or {}
        limit   = max(1, min(limit, 1000))
        offset  = max(0, offset)

        where_clauses = []
        params = []

        if "event_type" in filters:
            where_clauses.append("event_type = ?")
            params.append(filters["event_type"])

        if "source_ip" in filters:
            where_clauses.append("source_ip = ?")
            params.append(filters["source_ip"])

        if "pubkey" in filters:
            where_clauses.append("pubkey = ?")
            params.append(filters["pubkey"])

        if "from_ts" in filters:
            where_clauses.append("timestamp >= ?")
            params.append(int(filters["from_ts"]))

        if "to_ts" in filters:
            where_clauses.append("timestamp <= ?")
            params.append(int(filters["to_ts"]))

        if "action_prefix" in filters:
            where_clauses.append("action LIKE ?")
            params.append(filters["action_prefix"] + "%")

        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params += [limit, offset]

        try:
            conn = get_connection()
            rows = conn.execute(
                f"""
                SELECT id, timestamp, event_type, severity, source_ip,
                       pubkey, action, details, request_id
                FROM security_audit_log
                {where}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        except Exception:
            return []

        result = []
        for row in rows:
            try:
                details = json.loads(row[7])
            except Exception:
                details = {}

            result.append({
                "id":         row[0],
                "timestamp":  row[1],
                "event_type": row[2],
                "severity":   row[3],
                "source_ip":  row[4],
                "pubkey":     row[5],
                "action":     row[6],
                "details":    details,
                "request_id": row[8],
            })

        return result

    def get_security_summary(self, hours: int = 24) -> dict:
        """
        Return a summary of security events for the past N hours.
        """
        since = int(time.time()) - (hours * 3600)

        try:
            conn = get_connection()

            total = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE timestamp >= ?",
                (since,),
            ).fetchone()[0]

            by_type = conn.execute(
                """
                SELECT event_type, COUNT(*) as cnt
                FROM security_audit_log
                WHERE timestamp >= ?
                GROUP BY event_type
                ORDER BY cnt DESC
                """,
                (since,),
            ).fetchall()

            by_severity = conn.execute(
                """
                SELECT severity, COUNT(*) as cnt
                FROM security_audit_log
                WHERE timestamp >= ?
                GROUP BY severity
                """,
                (since,),
            ).fetchall()

            auth_failures = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE timestamp >= ? AND event_type = ?
                """,
                (since, EventType.AUTH_FAILURE),
            ).fetchone()[0]

            injection_attempts = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE timestamp >= ? AND event_type = ?
                """,
                (since, EventType.INJECTION_ATTEMPT),
            ).fetchone()[0]

            unique_ips = conn.execute(
                """
                SELECT COUNT(DISTINCT source_ip) FROM security_audit_log
                WHERE timestamp >= ? AND source_ip != ''
                """,
                (since,),
            ).fetchone()[0]

        except Exception:
            return {}

        return {
            "period_hours":       hours,
            "total_events":       total,
            "auth_failures":      auth_failures,
            "injection_attempts": injection_attempts,
            "unique_ips":         unique_ips,
            "by_event_type":      dict(by_type),
            "by_severity":        dict(by_severity),
            "generated_at":       int(time.time()),
        }

    def get_ip_reputation(self, ip: str) -> dict:
        """
        Return historical security activity for a given IP address.
        """
        if not ip:
            return {}

        since_7d = int(time.time()) - (7 * 86400)

        try:
            conn = get_connection()

            total = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE source_ip = ?",
                (ip,),
            ).fetchone()[0]

            recent = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE source_ip = ? AND timestamp >= ?
                """,
                (ip, since_7d),
            ).fetchone()[0]

            failures = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE source_ip = ? AND event_type = ?
                """,
                (ip, EventType.AUTH_FAILURE),
            ).fetchone()[0]

            critical = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE source_ip = ? AND severity IN (?, ?)
                """,
                (ip, Severity.CRITICAL, Severity.EMERGENCY),
            ).fetchone()[0]

            last_seen = conn.execute(
                """
                SELECT MAX(timestamp) FROM security_audit_log WHERE source_ip = ?
                """,
                (ip,),
            ).fetchone()[0]

        except Exception:
            return {}

        risk_score = min(100, (failures * 5) + (critical * 20))

        return {
            "ip":           ip,
            "total_events": total,
            "recent_7d":    recent,
            "auth_failures": failures,
            "critical_events": critical,
            "last_seen":    last_seen,
            "risk_score":   risk_score,
            "reputation":   (
                "high_risk" if risk_score >= 70
                else "medium_risk" if risk_score >= 30
                else "low_risk"
            ),
        }

    def get_user_security_profile(self, pubkey: str) -> dict:
        """
        Return the security profile for a user identified by pubkey.
        """
        if not pubkey:
            return {}

        try:
            conn = get_connection()

            total = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()[0]

            auth_ok = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE pubkey = ? AND event_type = ?",
                (pubkey, EventType.AUTH_SUCCESS),
            ).fetchone()[0]

            auth_fail = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE pubkey = ? AND event_type = ?",
                (pubkey, EventType.AUTH_FAILURE),
            ).fetchone()[0]

            first_seen = conn.execute(
                "SELECT MIN(timestamp) FROM security_audit_log WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()[0]

            last_seen = conn.execute(
                "SELECT MAX(timestamp) FROM security_audit_log WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()[0]

            unique_ips = conn.execute(
                """
                SELECT COUNT(DISTINCT source_ip) FROM security_audit_log
                WHERE pubkey = ? AND source_ip != ''
                """,
                (pubkey,),
            ).fetchone()[0]

            suspicious_count = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE pubkey = ? AND event_type = ?",
                (pubkey, EventType.SUSPICIOUS),
            ).fetchone()[0]

        except Exception:
            return {}

        return {
            "pubkey":          pubkey,
            "total_events":    total,
            "auth_successes":  auth_ok,
            "auth_failures":   auth_fail,
            "suspicious_events": suspicious_count,
            "unique_ips":      unique_ips,
            "first_seen":      first_seen,
            "last_seen":       last_seen,
            "risk_score":      min(100, auth_fail * 10 + suspicious_count * 25),
        }

    # ------------------------------------------------------------------
    # Threat detection helpers
    # ------------------------------------------------------------------

    def detect_brute_force(self, ip: str, window: int = 300) -> bool:
        """
        Return True if the IP has >= 10 AUTH_FAILURE events in the past
        ``window`` seconds (default 5 minutes).
        """
        since = int(time.time()) - window

        try:
            conn = get_connection()
            count = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE source_ip = ? AND event_type = ? AND timestamp >= ?
                """,
                (ip, EventType.AUTH_FAILURE, since),
            ).fetchone()[0]
            return count >= 10
        except Exception:
            return False

    def detect_account_takeover(self, pubkey: str) -> dict:
        """
        Heuristic account takeover detection.
        Flags unusual patterns: many IPs in short window, spike in failures.
        """
        now = int(time.time())
        window_1h = now - 3600
        window_24h = now - 86400

        try:
            conn = get_connection()

            ips_1h = conn.execute(
                """
                SELECT COUNT(DISTINCT source_ip) FROM security_audit_log
                WHERE pubkey = ? AND timestamp >= ? AND source_ip != ''
                """,
                (pubkey, window_1h),
            ).fetchone()[0]

            failures_1h = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE pubkey = ? AND event_type = ? AND timestamp >= ?
                """,
                (pubkey, EventType.AUTH_FAILURE, window_1h),
            ).fetchone()[0]

            sessions_24h = conn.execute(
                """
                SELECT COUNT(*) FROM security_audit_log
                WHERE pubkey = ? AND event_type = ? AND timestamp >= ?
                """,
                (pubkey, EventType.SESSION_CREATED, window_24h),
            ).fetchone()[0]

        except Exception:
            return {"risk": "unknown", "indicators": []}

        indicators = []
        risk_score = 0

        if ips_1h >= 3:
            indicators.append(f"Multiple IPs ({ips_1h}) in last hour")
            risk_score += 30 * ips_1h

        if failures_1h >= 5:
            indicators.append(f"{failures_1h} auth failures in last hour")
            risk_score += 10 * failures_1h

        if sessions_24h >= 10:
            indicators.append(f"Unusual number of sessions ({sessions_24h}) in 24h")
            risk_score += 5 * sessions_24h

        risk_score = min(100, risk_score)
        risk_level = (
            "high"   if risk_score >= 70 else
            "medium" if risk_score >= 30 else
            "low"
        )

        return {
            "pubkey":      pubkey,
            "risk":        risk_level,
            "risk_score":  risk_score,
            "indicators":  indicators,
            "ips_last_1h": ips_1h,
            "failures_1h": failures_1h,
            "sessions_24h": sessions_24h,
        }

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_security_report(self, date_from: int, date_to: int) -> dict:
        """
        Generate a structured security report for a time range.
        Includes event counts, top offenders, and trend analysis.
        """
        try:
            conn = get_connection()

            total = conn.execute(
                "SELECT COUNT(*) FROM security_audit_log WHERE timestamp BETWEEN ? AND ?",
                (date_from, date_to),
            ).fetchone()[0]

            by_type = dict(conn.execute(
                """
                SELECT event_type, COUNT(*) FROM security_audit_log
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY event_type ORDER BY 2 DESC
                """,
                (date_from, date_to),
            ).fetchall())

            top_ips = conn.execute(
                """
                SELECT source_ip, COUNT(*) as cnt FROM security_audit_log
                WHERE timestamp BETWEEN ? AND ? AND source_ip != ''
                GROUP BY source_ip ORDER BY cnt DESC LIMIT 10
                """,
                (date_from, date_to),
            ).fetchall()

            top_events = conn.execute(
                """
                SELECT event_type, severity, action, source_ip, pubkey, timestamp
                FROM security_audit_log
                WHERE timestamp BETWEEN ? AND ? AND severity IN (?, ?)
                ORDER BY timestamp DESC LIMIT 20
                """,
                (date_from, date_to, Severity.CRITICAL, Severity.EMERGENCY),
            ).fetchall()

            hourly_trend = conn.execute(
                """
                SELECT (timestamp / 3600) * 3600 as hour_bucket, COUNT(*)
                FROM security_audit_log
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY hour_bucket ORDER BY hour_bucket
                """,
                (date_from, date_to),
            ).fetchall()

        except Exception:
            return {}

        return {
            "period": {"from": date_from, "to": date_to},
            "summary": {
                "total_events":  total,
                "event_types":   by_type,
            },
            "top_source_ips": [
                {"ip": row[0], "event_count": row[1]} for row in top_ips
            ],
            "critical_events": [
                {
                    "event_type": row[0],
                    "severity":   row[1],
                    "action":     row[2],
                    "source_ip":  row[3],
                    "pubkey":     row[4],
                    "timestamp":  row[5],
                }
                for row in top_events
            ],
            "hourly_trend": [
                {"hour": row[0], "count": row[1]} for row in hourly_trend
            ],
            "generated_at": int(time.time()),
        }
