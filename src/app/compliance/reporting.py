"""
Compliance reporting for Magma Bitcoin app.
Generates CTRs, SARs, audit trails, and regulatory reports.
Includes jurisdiction-specific thresholds for US, EU, and El Salvador.
Pure Python stdlib — no third-party dependencies.
"""

import time
import uuid
import json
from typing import Optional

from ..database import get_conn as get_connection
from .aml import CTR_THRESHOLD_USD


# ---------------------------------------------------------------------------
# Regulatory thresholds by jurisdiction
# ---------------------------------------------------------------------------

_JURISDICTION_RULES = {
    "US": {
        "name": "United States",
        "regulator": "FinCEN",
        "ctr_threshold_usd":    10_000.0,
        "sar_threshold_usd":     5_000.0,
        "kyc_required_above":    3_000.0,
        "reporting_currency":   "USD",
        "ctr_form":             "FinCEN Form 112",
        "sar_form":             "FinCEN Form 111",
        "filing_deadline_days": 30,
        "retention_years":      5,
        "notes": "All transactions >= $10,000 require CTR. Structuring is illegal.",
    },
    "EU": {
        "name": "European Union",
        "regulator": "EBA / National FIUs",
        "ctr_threshold_usd":    10_000.0,
        "sar_threshold_usd":    None,  # SAR triggered by suspicion, not amount
        "kyc_required_above":   1_000.0,
        "reporting_currency":   "EUR",
        "ctr_form":             "AMLD6 STR",
        "sar_form":             "AMLD6 STR",
        "filing_deadline_days": 30,
        "retention_years":      5,
        "notes": "6th AMLD applies. KYC mandatory for transfers > €1,000.",
    },
    "SV": {
        "name": "El Salvador",
        "regulator": "UAF",
        "ctr_threshold_usd":    5_000.0,   # Lower threshold
        "sar_threshold_usd":    2_500.0,
        "kyc_required_above":   1_000.0,
        "reporting_currency":   "USD",
        "ctr_form":             "UAF RTE-01",
        "sar_form":             "UAF ROS-01",
        "filing_deadline_days": 15,
        "retention_years":      5,
        "notes": "Bitcoin is legal tender. UAF oversees AML for VASP under Ley Bitcoin.",
    },
    "MX": {
        "name": "Mexico",
        "regulator": "CNBV / UIF",
        "ctr_threshold_usd":    7_500.0,
        "sar_threshold_usd":    3_000.0,
        "kyc_required_above":   500.0,
        "reporting_currency":   "MXN",
        "ctr_form":             "UIF Reporte de Operaciones Relevantes",
        "sar_form":             "UIF Reporte de Operaciones Inusuales",
        "filing_deadline_days": 20,
        "retention_years":      10,
        "notes": "Ley Federal de Prevención e Identificación de Operaciones con Recursos de Procedencia Ilícita.",
    },
}

# Platform default jurisdiction
_DEFAULT_JURISDICTION = "SV"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_COMPLIANCE_REPORTS = """
CREATE TABLE IF NOT EXISTS compliance_reports (
    id           TEXT PRIMARY KEY,
    report_type  TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'SV',
    pubkey       TEXT NOT NULL DEFAULT '',
    period_from  INTEGER NOT NULL DEFAULT 0,
    period_to    INTEGER NOT NULL DEFAULT 0,
    content      TEXT NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'draft',
    filed_at     INTEGER NOT NULL DEFAULT 0,
    reference    TEXT NOT NULL DEFAULT '',
    created_at   INTEGER NOT NULL,
    created_by   TEXT NOT NULL DEFAULT 'system'
)
"""


def _ensure_schema(conn) -> None:
    conn.execute(_CREATE_COMPLIANCE_REPORTS)
    conn.commit()


# ---------------------------------------------------------------------------
# ComplianceReporter
# ---------------------------------------------------------------------------

class ComplianceReporter:
    """
    Generates and manages compliance reports for regulatory submission.
    """

    def __init__(self) -> None:
        try:
            conn = get_connection()
            _ensure_schema(conn)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # CTR (Currency Transaction Report)
    # ------------------------------------------------------------------

    def generate_ctr(self, transaction: dict) -> dict:
        """
        Generate a Currency Transaction Report for a reportable transaction.

        ``transaction`` should include: pubkey, amount_usd, direction, created_at,
        source_or_destination (optional).
        """
        jurisdiction = transaction.get("jurisdiction", _DEFAULT_JURISDICTION)
        rules = _JURISDICTION_RULES.get(jurisdiction, _JURISDICTION_RULES[_DEFAULT_JURISDICTION])

        amount = float(transaction.get("amount_usd", 0))
        if amount < rules["ctr_threshold_usd"]:
            return {
                "required": False,
                "reason": f"Amount ${amount:,.2f} below CTR threshold ${rules['ctr_threshold_usd']:,.2f}",
            }

        report_id = str(uuid.uuid4())
        now = int(time.time())

        content = {
            "report_type":     "CTR",
            "form":            rules["ctr_form"],
            "jurisdiction":    jurisdiction,
            "regulator":       rules["regulator"],
            "transaction": {
                "pubkey":      transaction.get("pubkey", ""),
                "amount_usd":  amount,
                "direction":   transaction.get("direction", "in"),
                "occurred_at": transaction.get("created_at", now),
                "source_or_destination": transaction.get("source_or_destination", ""),
            },
            "filing_deadline": now + (rules["filing_deadline_days"] * 86400),
            "instructions":    f"File {rules['ctr_form']} with {rules['regulator']} within {rules['filing_deadline_days']} days.",
        }

        try:
            conn = get_connection()
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO compliance_reports
                    (id, report_type, jurisdiction, pubkey, period_from, period_to, content, status, created_at)
                VALUES (?, 'CTR', ?, ?, ?, ?, ?, 'draft', ?)
                """,
                (
                    report_id,
                    jurisdiction,
                    transaction.get("pubkey", ""),
                    transaction.get("created_at", now),
                    transaction.get("created_at", now),
                    json.dumps(content),
                    now,
                ),
            )
            conn.commit()
        except Exception:
            pass

        return {
            "required":   True,
            "report_id":  report_id,
            "report_type": "CTR",
            **content,
        }

    # ------------------------------------------------------------------
    # SAR (Suspicious Activity Report)
    # ------------------------------------------------------------------

    def generate_sar(self, activity: dict) -> dict:
        """
        Generate a Suspicious Activity Report.

        ``activity`` should include: pubkey, description, patterns, amount_usd,
        period_from, period_to, jurisdiction.
        """
        jurisdiction = activity.get("jurisdiction", _DEFAULT_JURISDICTION)
        rules = _JURISDICTION_RULES.get(jurisdiction, _JURISDICTION_RULES[_DEFAULT_JURISDICTION])

        report_id = str(uuid.uuid4())
        now = int(time.time())

        content = {
            "report_type":  "SAR",
            "form":         rules["sar_form"],
            "jurisdiction": jurisdiction,
            "regulator":    rules["regulator"],
            "subject": {
                "pubkey":   activity.get("pubkey", ""),
            },
            "suspicious_activity": {
                "description": activity.get("description", "Suspicious financial activity detected"),
                "patterns":    activity.get("patterns", []),
                "amount_usd":  activity.get("amount_usd", 0),
                "period_from": activity.get("period_from", now - 86400),
                "period_to":   activity.get("period_to", now),
            },
            "filing_deadline": now + (rules["filing_deadline_days"] * 86400),
            "instructions":    f"File {rules['sar_form']} with {rules['regulator']} within {rules['filing_deadline_days']} days of detection.",
            "notes":           activity.get("notes", ""),
        }

        try:
            conn = get_connection()
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO compliance_reports
                    (id, report_type, jurisdiction, pubkey, period_from, period_to, content, status, created_at)
                VALUES (?, 'SAR', ?, ?, ?, ?, ?, 'draft', ?)
                """,
                (
                    report_id,
                    jurisdiction,
                    activity.get("pubkey", ""),
                    activity.get("period_from", now - 86400),
                    activity.get("period_to", now),
                    json.dumps(content),
                    now,
                ),
            )
            conn.commit()
        except Exception:
            pass

        return {
            "required":    True,
            "report_id":   report_id,
            "report_type": "SAR",
            **content,
        }

    # ------------------------------------------------------------------
    # Periodic reports
    # ------------------------------------------------------------------

    def generate_daily_report(self) -> dict:
        """
        Generate a daily compliance summary report.
        """
        now   = int(time.time())
        start = now - 86400

        try:
            conn = get_connection()
            _ensure_schema(conn)

            total_deposits = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount_usd), 0) FROM savings_deposits WHERE created_at >= ?",
                (start,),
            ).fetchone()

            high_value = conn.execute(
                "SELECT COUNT(*) FROM savings_deposits WHERE created_at >= ? AND amount_usd >= ?",
                (start, CTR_THRESHOLD_USD),
            ).fetchone()[0]

            pending_alerts = conn.execute(
                "SELECT COUNT(*) FROM compliance_alerts WHERE created_at >= ? AND status = 'pending'",
                (start,),
            ).fetchone()[0]

            new_reports = conn.execute(
                "SELECT COUNT(*) FROM compliance_reports WHERE created_at >= ?",
                (start,),
            ).fetchone()[0]

        except Exception as exc:
            return {"error": str(exc)}

        report_id = str(uuid.uuid4())
        content = {
            "date":            _ts_to_date(start),
            "transactions":    {"count": total_deposits[0], "volume_usd": round(float(total_deposits[1]), 2)},
            "high_value_txns": high_value,
            "pending_alerts":  pending_alerts,
            "reports_created": new_reports,
            "ctr_required":    high_value,
        }

        return {
            "report_id":   report_id,
            "report_type": "DAILY_SUMMARY",
            "period":      {"from": start, "to": now},
            "content":     content,
            "generated_at": now,
        }

    def generate_monthly_report(self, year: int, month: int) -> dict:
        """
        Generate a monthly compliance report for the given year/month.
        """
        import calendar
        try:
            first_day = int(
                time.mktime(time.strptime(f"{year}-{month:02d}-01", "%Y-%m-%d"))
            )
            last_day_num = calendar.monthrange(year, month)[1]
            last_day = int(
                time.mktime(time.strptime(f"{year}-{month:02d}-{last_day_num:02d} 23:59:59", "%Y-%m-%d %H:%M:%S"))
            )
        except Exception:
            return {"error": "Invalid year/month"}

        try:
            conn = get_connection()
            _ensure_schema(conn)

            total_tx = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount_usd), 0), COALESCE(SUM(btc_amount), 0) FROM savings_deposits WHERE created_at BETWEEN ? AND ?",
                (first_day, last_day),
            ).fetchone()

            new_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?",
                (first_day, last_day),
            ).fetchone()[0]

            ctr_count = conn.execute(
                "SELECT COUNT(*) FROM compliance_reports WHERE report_type = 'CTR' AND created_at BETWEEN ? AND ?",
                (first_day, last_day),
            ).fetchone()[0]

            sar_count = conn.execute(
                "SELECT COUNT(*) FROM compliance_reports WHERE report_type = 'SAR' AND created_at BETWEEN ? AND ?",
                (first_day, last_day),
            ).fetchone()[0]

            alerts_count = conn.execute(
                "SELECT COUNT(*) FROM compliance_alerts WHERE created_at BETWEEN ? AND ?",
                (first_day, last_day),
            ).fetchone()[0]

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "report_type":   "MONTHLY_SUMMARY",
            "period":        {"year": year, "month": month},
            "transactions":  {
                "count":      total_tx[0],
                "volume_usd": round(float(total_tx[1]), 2),
                "volume_btc": round(float(total_tx[2]), 8),
            },
            "new_users":     new_users,
            "ctrs_filed":    ctr_count,
            "sars_filed":    sar_count,
            "alerts":        alerts_count,
            "generated_at":  int(time.time()),
        }

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def generate_audit_trail(
        self,
        pubkey: str,
        date_from: int,
        date_to: int,
    ) -> dict:
        """
        Generate a comprehensive audit trail for a specific user and time range.
        Includes transactions, alerts, and security events.
        """
        try:
            conn = get_connection()
            _ensure_schema(conn)

            deposits = conn.execute(
                "SELECT id, amount_usd, btc_price, btc_amount, created_at FROM savings_deposits WHERE pubkey = ? AND created_at BETWEEN ? AND ? ORDER BY created_at",
                (pubkey, date_from, date_to),
            ).fetchall()

            alerts = conn.execute(
                "SELECT id, alert_type, severity, description, status, created_at FROM compliance_alerts WHERE pubkey = ? AND created_at BETWEEN ? AND ?",
                (pubkey, date_from, date_to),
            ).fetchall()

            security_events = []
            try:
                security_events = conn.execute(
                    "SELECT timestamp, event_type, action, source_ip FROM security_audit_log WHERE pubkey = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
                    (pubkey, date_from, date_to),
                ).fetchall()
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "pubkey":     pubkey,
            "period":     {"from": date_from, "to": date_to},
            "deposits": [
                {"id": r[0], "amount_usd": r[1], "btc_price": r[2], "btc_amount": r[3], "at": r[4]}
                for r in deposits
            ],
            "alerts": [
                {"id": r[0], "type": r[1], "severity": r[2], "description": r[3], "status": r[4], "at": r[5]}
                for r in alerts
            ],
            "security_events": [
                {"at": r[0], "type": r[1], "action": r[2], "ip": r[3]}
                for r in security_events
            ],
            "generated_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # Risk assessment
    # ------------------------------------------------------------------

    def generate_risk_assessment(self) -> dict:
        """
        Generate a platform-wide AML/compliance risk assessment summary.
        """
        try:
            conn = get_connection()
            _ensure_schema(conn)

            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

            high_risk = conn.execute(
                "SELECT COUNT(*) FROM user_risk_profiles WHERE risk_score >= 70"
            ).fetchone()[0]

            medium_risk = conn.execute(
                "SELECT COUNT(*) FROM user_risk_profiles WHERE risk_score >= 30 AND risk_score < 70"
            ).fetchone()[0]

            open_alerts = conn.execute(
                "SELECT COUNT(*) FROM compliance_alerts WHERE status = 'pending'"
            ).fetchone()[0]

            draft_reports = conn.execute(
                "SELECT COUNT(*) FROM compliance_reports WHERE status = 'draft'"
            ).fetchone()[0]

            total_volume = conn.execute(
                "SELECT COALESCE(SUM(amount_usd), 0) FROM savings_deposits"
            ).fetchone()[0]

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "users":       {"total": total_users, "high_risk": high_risk, "medium_risk": medium_risk},
            "alerts":      {"open": open_alerts},
            "reports":     {"draft": draft_reports},
            "volume_usd":  round(float(total_volume), 2),
            "risk_level":  "high" if high_risk > 10 else "medium" if high_risk > 0 else "low",
            "generated_at": int(time.time()),
        }

    # ------------------------------------------------------------------
    # Regulatory requirements
    # ------------------------------------------------------------------

    def get_regulatory_requirements(self, jurisdiction: str = _DEFAULT_JURISDICTION) -> dict:
        """Return the regulatory requirements for a specific jurisdiction."""
        rules = _JURISDICTION_RULES.get(jurisdiction.upper())
        if not rules:
            return {"error": f"Unknown jurisdiction: {jurisdiction!r}",
                    "available": list(_JURISDICTION_RULES.keys())}
        return rules

    def check_reporting_thresholds(self, transaction: dict) -> list:
        """
        Determine which regulatory reports are required for a transaction.
        Returns a list of required report types.
        """
        required = []
        amount = float(transaction.get("amount_usd", 0))
        jurisdiction = transaction.get("jurisdiction", _DEFAULT_JURISDICTION).upper()
        rules = _JURISDICTION_RULES.get(jurisdiction, _JURISDICTION_RULES[_DEFAULT_JURISDICTION])

        if amount >= rules["ctr_threshold_usd"]:
            required.append({
                "type":     "CTR",
                "form":     rules["ctr_form"],
                "deadline_days": rules["filing_deadline_days"],
            })

        if rules["sar_threshold_usd"] and amount >= rules["sar_threshold_usd"]:
            required.append({
                "type":     "SAR_CONSIDERATION",
                "form":     rules["sar_form"],
                "deadline_days": rules["filing_deadline_days"],
                "note": "Consider SAR if activity is suspicious",
            })

        return required

    # ------------------------------------------------------------------
    # Report filing management
    # ------------------------------------------------------------------

    def get_outstanding_reports(self) -> list:
        """Return all draft/unfiled compliance reports."""
        try:
            conn = get_connection()
            _ensure_schema(conn)

            rows = conn.execute(
                "SELECT id, report_type, jurisdiction, pubkey, status, created_at, filed_at FROM compliance_reports WHERE status IN ('draft', 'pending') ORDER BY created_at DESC",
            ).fetchall()
        except Exception:
            return []

        return [
            {
                "id":           row[0],
                "report_type":  row[1],
                "jurisdiction": row[2],
                "pubkey":       row[3],
                "status":       row[4],
                "created_at":   row[5],
                "filed_at":     row[6],
            }
            for row in rows
        ]

    def mark_report_filed(self, report_id: str, reference: str = "") -> dict:
        """Mark a compliance report as filed with its regulatory reference number."""
        now = int(time.time())

        try:
            conn = get_connection()
            _ensure_schema(conn)

            cursor = conn.execute(
                "UPDATE compliance_reports SET status = 'filed', filed_at = ?, reference = ? WHERE id = ?",
                (now, reference, report_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                return {"error": "report_not_found"}

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "report_id": report_id,
            "status":    "filed",
            "filed_at":  now,
            "reference": reference,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_to_date(ts: int) -> str:
    import datetime
    try:
        return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "1970-01-01"
