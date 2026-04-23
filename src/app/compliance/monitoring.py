"""
Transaction monitoring for Magma Bitcoin app.
Real-time monitoring of deposits and withdrawals with alert generation and SAR drafting.
Pure Python stdlib — no third-party dependencies.
"""

import time
import uuid
import json
from typing import Optional

from ..database import get_conn as get_connection
from .aml import AMLChecker, CTR_THRESHOLD_USD


# ---------------------------------------------------------------------------
# Alert statuses and severities
# ---------------------------------------------------------------------------

class AlertStatus:
    PENDING  = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FALSE_POSITIVE = "false_positive"


class AlertSeverity:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_COMPLIANCE_ALERTS = """
CREATE TABLE IF NOT EXISTS compliance_alerts (
    id            TEXT PRIMARY KEY,
    pubkey        TEXT NOT NULL,
    alert_type    TEXT NOT NULL,
    severity      TEXT NOT NULL DEFAULT 'medium',
    description   TEXT NOT NULL DEFAULT '',
    details       TEXT NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    INTEGER NOT NULL,
    resolved_at   INTEGER NOT NULL DEFAULT 0,
    resolved_by   TEXT NOT NULL DEFAULT '',
    resolution    TEXT NOT NULL DEFAULT '',
    notes         TEXT NOT NULL DEFAULT ''
)
"""

_CREATE_RISK_PROFILES = """
CREATE TABLE IF NOT EXISTS user_risk_profiles (
    pubkey          TEXT PRIMARY KEY,
    risk_score      REAL NOT NULL DEFAULT 0,
    risk_level      TEXT NOT NULL DEFAULT 'low',
    last_calculated INTEGER NOT NULL,
    signals         TEXT NOT NULL DEFAULT '[]',
    review_count    INTEGER NOT NULL DEFAULT 0,
    sar_count       INTEGER NOT NULL DEFAULT 0
)
"""


def _ensure_schema(conn) -> None:
    conn.execute(_CREATE_COMPLIANCE_ALERTS)
    conn.execute(_CREATE_RISK_PROFILES)
    conn.commit()


# ---------------------------------------------------------------------------
# TransactionMonitor
# ---------------------------------------------------------------------------

class TransactionMonitor:
    """
    Real-time compliance monitoring for all financial transactions.
    Generates alerts and maintains risk profiles for each user.
    """

    def __init__(self) -> None:
        self._aml = AMLChecker()
        try:
            conn = get_connection()
            _ensure_schema(conn)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Deposit monitoring
    # ------------------------------------------------------------------

    def monitor_deposit(
        self,
        pubkey: str,
        amount: float,
        source: str = "",
    ) -> dict:
        """
        Monitor an incoming deposit for AML/compliance issues.
        Automatically generates alerts for flagged transactions.

        Returns the monitoring result with alert IDs if any were created.
        """
        assessment = self._aml.check_transaction(
            pubkey=pubkey,
            amount=amount,
            direction="in",
            metadata={"source": source},
        )

        alerts_created = []

        # Generate alert if risk is elevated
        if assessment["risk_score"] >= 30:
            severity = _risk_to_severity(assessment["risk_score"])
            alert = self._create_alert(
                pubkey=pubkey,
                alert_type="suspicious_deposit",
                severity=severity,
                description=f"Suspicious deposit: ${amount:,.2f}",
                details={
                    "amount":     amount,
                    "source":     source,
                    "risk_score": assessment["risk_score"],
                    "flags":      assessment["flags"],
                },
            )
            alerts_created.append(alert["id"])

        # CTR threshold alert
        if amount >= CTR_THRESHOLD_USD:
            alert = self._create_alert(
                pubkey=pubkey,
                alert_type="ctr_threshold",
                severity=AlertSeverity.HIGH,
                description=f"Deposit at/above CTR threshold: ${amount:,.2f}",
                details={"amount": amount, "threshold": CTR_THRESHOLD_USD},
            )
            alerts_created.append(alert["id"])

        # Update risk profile
        self.update_risk_score(pubkey)

        return {
            "pubkey":         pubkey,
            "amount":         amount,
            "assessment":     assessment,
            "alerts_created": alerts_created,
            "monitored_at":   int(time.time()),
        }

    # ------------------------------------------------------------------
    # Withdrawal monitoring
    # ------------------------------------------------------------------

    def monitor_withdrawal(
        self,
        pubkey: str,
        amount: float,
        destination: str = "",
    ) -> dict:
        """
        Monitor an outgoing withdrawal for AML/compliance issues.
        """
        from .aml import SanctionsChecker
        sanctions = SanctionsChecker()

        alerts_created = []

        # Check destination address against sanctions
        if destination:
            sanction_result = sanctions.check_address(destination)
            if sanction_result["sanctioned"]:
                alert = self._create_alert(
                    pubkey=pubkey,
                    alert_type="sanctioned_address",
                    severity=AlertSeverity.CRITICAL,
                    description=f"Withdrawal to sanctioned address: {destination[:20]}...",
                    details={
                        "address":      destination,
                        "sanction_info": sanction_result,
                        "amount":       amount,
                    },
                )
                alerts_created.append(alert["id"])

        assessment = self._aml.check_transaction(
            pubkey=pubkey,
            amount=amount,
            direction="out",
            metadata={"destination": destination},
        )

        if assessment["risk_score"] >= 50:
            alert = self._create_alert(
                pubkey=pubkey,
                alert_type="suspicious_withdrawal",
                severity=_risk_to_severity(assessment["risk_score"]),
                description=f"Suspicious withdrawal: ${amount:,.2f}",
                details={
                    "amount":      amount,
                    "destination": destination,
                    "risk_score":  assessment["risk_score"],
                    "flags":       assessment["flags"],
                },
            )
            alerts_created.append(alert["id"])

        self.update_risk_score(pubkey)

        return {
            "pubkey":         pubkey,
            "amount":         amount,
            "destination":    destination,
            "assessment":     assessment,
            "alerts_created": alerts_created,
            "monitored_at":   int(time.time()),
        }

    # ------------------------------------------------------------------
    # Alert management
    # ------------------------------------------------------------------

    def get_alerts(self, status: str = "pending", limit: int = 100) -> list:
        """Return compliance alerts filtered by status."""
        limit = max(1, min(limit, 1000))

        try:
            conn = get_connection()
            _ensure_schema(conn)

            if status == "all":
                rows = conn.execute(
                    "SELECT id, pubkey, alert_type, severity, description, details, status, created_at FROM compliance_alerts ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, pubkey, alert_type, severity, description, details, status, created_at FROM compliance_alerts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
        except Exception:
            return []

        result = []
        for row in rows:
            try:
                details = json.loads(row[5])
            except Exception:
                details = {}
            result.append({
                "id":          row[0],
                "pubkey":      row[1],
                "alert_type":  row[2],
                "severity":    row[3],
                "description": row[4],
                "details":     details,
                "status":      row[6],
                "created_at":  row[7],
            })

        return result

    def resolve_alert(
        self,
        alert_id: str,
        resolution: str,
        notes: str = "",
        resolved_by: str = "compliance_officer",
    ) -> dict:
        """Resolve a compliance alert."""
        now = int(time.time())

        try:
            conn = get_connection()
            _ensure_schema(conn)

            cursor = conn.execute(
                """
                UPDATE compliance_alerts
                SET status = 'resolved', resolved_at = ?, resolved_by = ?,
                    resolution = ?, notes = ?
                WHERE id = ?
                """,
                (now, resolved_by, resolution, notes, alert_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                return {"error": "alert_not_found"}

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "alert_id":    alert_id,
            "status":      "resolved",
            "resolution":  resolution,
            "resolved_at": now,
        }

    def get_monitoring_summary(self) -> dict:
        """Return a summary of the monitoring dashboard."""
        try:
            conn = get_connection()
            _ensure_schema(conn)

            pending = conn.execute(
                "SELECT COUNT(*) FROM compliance_alerts WHERE status = 'pending'"
            ).fetchone()[0]

            critical = conn.execute(
                "SELECT COUNT(*) FROM compliance_alerts WHERE status = 'pending' AND severity = 'critical'"
            ).fetchone()[0]

            today = int(time.time()) - 86400
            alerts_today = conn.execute(
                "SELECT COUNT(*) FROM compliance_alerts WHERE created_at >= ?", (today,)
            ).fetchone()[0]

            by_type = dict(conn.execute(
                "SELECT alert_type, COUNT(*) FROM compliance_alerts WHERE status = 'pending' GROUP BY alert_type"
            ).fetchall())

            high_risk_users = conn.execute(
                "SELECT COUNT(*) FROM user_risk_profiles WHERE risk_score >= 70"
            ).fetchone()[0]

        except Exception:
            return {}

        return {
            "pending_alerts":  pending,
            "critical_alerts": critical,
            "alerts_today":    alerts_today,
            "by_type":         by_type,
            "high_risk_users": high_risk_users,
            "generated_at":    int(time.time()),
        }

    # ------------------------------------------------------------------
    # Risk profiles
    # ------------------------------------------------------------------

    def get_user_risk_profile(self, pubkey: str) -> dict:
        """Return the current risk profile for a user."""
        try:
            conn = get_connection()
            _ensure_schema(conn)

            row = conn.execute(
                "SELECT risk_score, risk_level, last_calculated, signals, review_count, sar_count FROM user_risk_profiles WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()

        except Exception:
            return {}

        if not row:
            return {
                "pubkey":          pubkey,
                "risk_score":      0.0,
                "risk_level":      "low",
                "last_calculated": 0,
                "signals":         [],
            }

        try:
            signals = json.loads(row[3])
        except Exception:
            signals = []

        return {
            "pubkey":          pubkey,
            "risk_score":      row[0],
            "risk_level":      row[1],
            "last_calculated": row[2],
            "signals":         signals,
            "review_count":    row[4],
            "sar_count":       row[5],
        }

    def update_risk_score(self, pubkey: str) -> float:
        """Recalculate and persist the risk score for a user."""
        score = self._aml.get_risk_score(pubkey)
        level = _score_to_level(score)
        now   = int(time.time())

        # Build signal list
        pattern = self._aml.check_pattern(pubkey)
        signals = pattern.get("patterns", [])

        try:
            conn = get_connection()
            _ensure_schema(conn)

            # Get existing counts
            existing = conn.execute(
                "SELECT review_count, sar_count FROM user_risk_profiles WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()
            review_count = existing[0] if existing else 0
            sar_count    = existing[1] if existing else 0

            conn.execute(
                """
                INSERT INTO user_risk_profiles
                    (pubkey, risk_score, risk_level, last_calculated, signals, review_count, sar_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pubkey) DO UPDATE SET
                    risk_score = excluded.risk_score,
                    risk_level = excluded.risk_level,
                    last_calculated = excluded.last_calculated,
                    signals = excluded.signals
                """,
                (pubkey, score, level, now, json.dumps(signals), review_count, sar_count),
            )
            conn.commit()
        except Exception:
            pass

        return score

    def get_high_risk_users(self, threshold: float = 70) -> list:
        """Return all users with risk score at or above the threshold."""
        try:
            conn = get_connection()
            _ensure_schema(conn)

            rows = conn.execute(
                "SELECT pubkey, risk_score, risk_level, last_calculated, signals FROM user_risk_profiles WHERE risk_score >= ? ORDER BY risk_score DESC",
                (threshold,),
            ).fetchall()
        except Exception:
            return []

        result = []
        for row in rows:
            try:
                signals = json.loads(row[4])
            except Exception:
                signals = []
            result.append({
                "pubkey":     row[0],
                "risk_score": row[1],
                "risk_level": row[2],
                "last_calculated": row[3],
                "signals":    signals,
            })

        return result

    # ------------------------------------------------------------------
    # SAR generation
    # ------------------------------------------------------------------

    def generate_sar(self, pubkey: str, details: dict = None) -> dict:
        """
        Draft a Suspicious Activity Report for a user.
        Returns a structured SAR that can be reviewed and filed by a compliance officer.
        """
        details = details or {}
        now = int(time.time())

        # Gather supporting data
        risk_profile = self.get_user_risk_profile(pubkey)
        aml_pattern  = self._aml.check_pattern(pubkey)

        # Get recent alerts
        try:
            conn = get_connection()
            _ensure_schema(conn)

            alerts = conn.execute(
                "SELECT id, alert_type, severity, description, created_at FROM compliance_alerts WHERE pubkey = ? ORDER BY created_at DESC LIMIT 10",
                (pubkey,),
            ).fetchall()

            # Increment SAR count
            conn.execute(
                "UPDATE user_risk_profiles SET sar_count = sar_count + 1 WHERE pubkey = ?",
                (pubkey,),
            )
            conn.commit()
        except Exception:
            alerts = []

        sar_id = str(uuid.uuid4())

        return {
            "sar_id":     sar_id,
            "report_type": "SAR",
            "status":      "draft",
            "subject": {
                "pubkey":    pubkey,
                "risk_score": risk_profile.get("risk_score", 0),
                "risk_level": risk_profile.get("risk_level", "unknown"),
            },
            "suspicious_activity": {
                "patterns":    aml_pattern.get("patterns", []),
                "tx_count":    aml_pattern.get("tx_count", 0),
                "total_volume": aml_pattern.get("total_volume", 0),
                "description": details.get("description", "Suspicious transaction patterns detected"),
            },
            "supporting_alerts": [
                {"id": r[0], "type": r[1], "severity": r[2], "description": r[3], "at": r[4]}
                for r in alerts
            ],
            "additional_details": details,
            "drafted_at":  now,
            "instructions": "Review this SAR draft and file with FinCEN (US) or applicable regulator within 30 days of detection.",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_alert(
        self,
        pubkey: str,
        alert_type: str,
        severity: str,
        description: str,
        details: dict = None,
    ) -> dict:
        """Create and persist a compliance alert."""
        alert_id = str(uuid.uuid4())
        now = int(time.time())

        try:
            conn = get_connection()
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO compliance_alerts
                    (id, pubkey, alert_type, severity, description, details, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (alert_id, pubkey, alert_type, severity, description,
                 json.dumps(details or {}), now),
            )
            conn.commit()
        except Exception:
            pass

        return {
            "id":          alert_id,
            "pubkey":      pubkey,
            "alert_type":  alert_type,
            "severity":    severity,
            "description": description,
            "status":      "pending",
            "created_at":  now,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _risk_to_severity(score: float) -> str:
    if score >= 80:
        return AlertSeverity.CRITICAL
    if score >= 60:
        return AlertSeverity.HIGH
    if score >= 30:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW


def _score_to_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
