"""
User management for the Magma Bitcoin admin panel.
Provides listing, detailed profiles, session management, banning, and GDPR exports.
Pure Python stdlib — no third-party dependencies.
"""

import json
import time
import uuid
from typing import Optional

from ..database import get_conn as get_connection


# ---------------------------------------------------------------------------
# Schema helpers — create admin-specific tables if they don't exist
# ---------------------------------------------------------------------------

_CREATE_BANNED_USERS = """
CREATE TABLE IF NOT EXISTS banned_users (
    pubkey       TEXT PRIMARY KEY,
    reason       TEXT NOT NULL DEFAULT '',
    banned_at    INTEGER NOT NULL,
    banned_until INTEGER NOT NULL DEFAULT 0,
    banned_by    TEXT NOT NULL DEFAULT 'admin'
)
"""

_CREATE_ADMIN_NOTES = """
CREATE TABLE IF NOT EXISTS admin_notes (
    id         TEXT PRIMARY KEY,
    pubkey     TEXT NOT NULL,
    note       TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL
)
"""


def _ensure_schema(conn) -> None:
    conn.execute(_CREATE_BANNED_USERS)
    conn.execute(_CREATE_ADMIN_NOTES)
    conn.commit()


# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------

class UserManager:
    """
    Administrative user management.
    All write operations are logged to the security audit log when possible.
    """

    def __init__(self) -> None:
        try:
            conn = get_connection()
            _ensure_schema(conn)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        order: str = "desc",
        filter_by: dict = None,
    ) -> dict:
        """
        Return a paginated list of users.

        ``filter_by`` supports: created_after, created_before, auth_method, banned.
        ``sort_by`` supports: created_at, pubkey.
        ``order`` supports: asc, desc.
        """
        limit  = max(1, min(limit, 200))
        offset = max(0, offset)

        valid_sort   = {"created_at", "pubkey"}
        valid_orders = {"asc", "desc"}
        sort_col = sort_by if sort_by in valid_sort else "created_at"
        direction = order.lower() if order.lower() in valid_orders else "desc"

        filter_by = filter_by or {}
        where_clauses = []
        params: list = []

        if "auth_method" in filter_by:
            where_clauses.append("u.auth_method = ?")
            params.append(filter_by["auth_method"])

        if "created_after" in filter_by:
            where_clauses.append("u.created_at >= ?")
            params.append(int(filter_by["created_after"]))

        if "created_before" in filter_by:
            where_clauses.append("u.created_at <= ?")
            params.append(int(filter_by["created_before"]))

        if filter_by.get("banned"):
            where_clauses.append("b.pubkey IS NOT NULL")

        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        try:
            conn = get_connection()
            _ensure_schema(conn)

            total = conn.execute(
                f"""
                SELECT COUNT(*) FROM users u
                LEFT JOIN banned_users b ON u.pubkey = b.pubkey
                {where}
                """,
                params,
            ).fetchone()[0]

            rows = conn.execute(
                f"""
                SELECT u.pubkey, u.auth_method, u.created_at,
                       b.pubkey IS NOT NULL as is_banned,
                       b.reason as ban_reason, b.banned_until
                FROM users u
                LEFT JOIN banned_users b ON u.pubkey = b.pubkey
                {where}
                ORDER BY u.{sort_col} {direction}
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()

        except Exception as exc:
            return {"error": str(exc), "users": [], "total": 0}

        users = []
        for row in rows:
            pubkey, auth_method, created_at, is_banned, ban_reason, banned_until = row
            users.append({
                "pubkey":      pubkey,
                "auth_method": auth_method,
                "created_at":  created_at,
                "is_banned":   bool(is_banned),
                "ban_reason":  ban_reason or "",
                "banned_until": banned_until or 0,
            })

        return {
            "users":  users,
            "total":  total,
            "limit":  limit,
            "offset": offset,
            "pages":  max(1, (total + limit - 1) // limit),
        }

    # ------------------------------------------------------------------
    # User detail
    # ------------------------------------------------------------------

    def get_user_detail(self, pubkey: str) -> dict:
        """
        Return the full administrative profile for a user.
        Includes savings data, session count, achievement count, and ban status.
        """
        if not pubkey:
            return {"error": "pubkey required"}

        try:
            conn = get_connection()

            user_row = conn.execute(
                "SELECT pubkey, auth_method, created_at FROM users WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()

            if not user_row:
                return {"error": "user_not_found"}

            deposit_stats = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(amount_usd), 0),
                       COALESCE(SUM(btc_amount), 0), MIN(created_at), MAX(created_at)
                FROM savings_deposits WHERE pubkey = ?
                """,
                (pubkey,),
            ).fetchone()

            savings_goal = None
            try:
                goal_row = conn.execute(
                    "SELECT monthly_target_usd, target_years FROM savings_goals WHERE pubkey = ?",
                    (pubkey,),
                ).fetchone()
                if goal_row:
                    savings_goal = {"monthly_target_usd": goal_row[0], "target_years": goal_row[1]}
            except Exception:
                pass

            achievements = []
            try:
                ach_rows = conn.execute(
                    "SELECT achievement_id, awarded_at FROM user_achievements WHERE pubkey = ?",
                    (pubkey,),
                ).fetchall()
                achievements = [{"id": r[0], "awarded_at": r[1]} for r in ach_rows]
            except Exception:
                pass

            prefs = {}
            try:
                pref_row = conn.execute(
                    "SELECT fee_alert_low, fee_alert_high, alerts_enabled FROM user_preferences WHERE pubkey = ?",
                    (pubkey,),
                ).fetchone()
                if pref_row:
                    prefs = {"fee_alert_low": pref_row[0], "fee_alert_high": pref_row[1],
                             "alerts_enabled": bool(pref_row[2])}
            except Exception:
                pass

            ban_info = None
            try:
                _ensure_schema(conn)
                ban_row = conn.execute(
                    "SELECT reason, banned_at, banned_until, banned_by FROM banned_users WHERE pubkey = ?",
                    (pubkey,),
                ).fetchone()
                if ban_row:
                    ban_info = {
                        "reason":       ban_row[0],
                        "banned_at":    ban_row[1],
                        "banned_until": ban_row[2],
                        "banned_by":    ban_row[3],
                        "permanent":    ban_row[2] == 0,
                    }
            except Exception:
                pass

            active_sessions = 0
            try:
                active_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE pubkey = ? AND expires_at > ?",
                    (pubkey, int(time.time())),
                ).fetchone()[0]
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "pubkey":       user_row[0],
            "auth_method":  user_row[1],
            "created_at":   user_row[2],
            "deposits": {
                "count":       deposit_stats[0],
                "total_usd":   round(float(deposit_stats[1]), 2),
                "total_btc":   round(float(deposit_stats[2]), 8),
                "first_at":    deposit_stats[3],
                "last_at":     deposit_stats[4],
            },
            "savings_goal":    savings_goal,
            "achievements":    achievements,
            "preferences":     prefs,
            "ban_info":        ban_info,
            "active_sessions": active_sessions,
            "is_banned":       ban_info is not None,
        }

    # ------------------------------------------------------------------
    # Activity timeline
    # ------------------------------------------------------------------

    def get_user_activity(self, pubkey: str, days: int = 30) -> dict:
        """
        Return a chronological activity timeline for a user.
        """
        if not pubkey:
            return {}

        days  = max(1, min(days, 365))
        since = int(time.time()) - (days * 86400)

        try:
            conn = get_connection()

            deposits = conn.execute(
                """
                SELECT created_at, amount_usd, btc_price, btc_amount
                FROM savings_deposits
                WHERE pubkey = ? AND created_at >= ?
                ORDER BY created_at DESC
                """,
                (pubkey, since),
            ).fetchall()

            achievements = []
            try:
                achievements = conn.execute(
                    "SELECT achievement_id, awarded_at FROM user_achievements WHERE pubkey = ? AND awarded_at >= ?",
                    (pubkey, since),
                ).fetchall()
            except Exception:
                pass

            audit_events = []
            try:
                audit_events = conn.execute(
                    """
                    SELECT timestamp, event_type, action, source_ip
                    FROM security_audit_log
                    WHERE pubkey = ? AND timestamp >= ?
                    ORDER BY timestamp DESC LIMIT 50
                    """,
                    (pubkey, since),
                ).fetchall()
            except Exception:
                pass

        except Exception:
            return {}

        events = []
        for row in deposits:
            events.append({
                "type":      "deposit",
                "timestamp": row[0],
                "data": {
                    "amount_usd": row[1],
                    "btc_price":  row[2],
                    "btc_amount": row[3],
                },
            })

        for row in achievements:
            events.append({
                "type":      "achievement",
                "timestamp": row[1],
                "data":      {"achievement_id": row[0]},
            })

        for row in audit_events:
            events.append({
                "type":      "security",
                "timestamp": row[0],
                "data": {
                    "event_type": row[1],
                    "action":     row[2],
                    "ip":         row[3],
                },
            })

        events.sort(key=lambda e: e["timestamp"], reverse=True)

        return {
            "pubkey":    pubkey,
            "days":      days,
            "events":    events[:200],
            "total":     len(events),
        }

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def get_user_sessions(self, pubkey: str) -> list:
        """Return all active sessions for a user."""
        if not pubkey:
            return []

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT token, created_at, expires_at FROM sessions WHERE pubkey = ? AND expires_at > ?",
                (pubkey, int(time.time())),
            ).fetchall()
        except Exception:
            return []

        return [
            {
                "token_prefix": row[0][:8] + "..." if row[0] else "",
                "created_at":   row[1],
                "expires_at":   row[2],
            }
            for row in rows
        ]

    def revoke_session(self, pubkey: str, token: str) -> bool:
        """Revoke a specific session token."""
        try:
            conn = get_connection()
            cursor = conn.execute(
                "DELETE FROM sessions WHERE pubkey = ? AND token = ?",
                (pubkey, token),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def revoke_all_sessions(self, pubkey: str) -> int:
        """Revoke all sessions for a user. Returns count revoked."""
        try:
            conn = get_connection()
            cursor = conn.execute("DELETE FROM sessions WHERE pubkey = ?", (pubkey,))
            conn.commit()
            return cursor.rowcount
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Achievements & savings (admin view)
    # ------------------------------------------------------------------

    def get_user_achievements(self, pubkey: str) -> dict:
        """Return achievement details for a user."""
        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT achievement_id, awarded_at FROM user_achievements WHERE pubkey = ? ORDER BY awarded_at DESC",
                (pubkey,),
            ).fetchall()
        except Exception:
            return {}

        return {
            "pubkey":       pubkey,
            "count":        len(rows),
            "achievements": [{"id": r[0], "awarded_at": r[1]} for r in rows],
        }

    def get_user_savings(self, pubkey: str) -> dict:
        """Return full savings data for a user."""
        try:
            conn = get_connection()

            stats = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(amount_usd), 0), COALESCE(SUM(btc_amount), 0)
                FROM savings_deposits WHERE pubkey = ?
                """,
                (pubkey,),
            ).fetchone()

            goal = conn.execute(
                "SELECT monthly_target_usd, target_years FROM savings_goals WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()

        except Exception:
            return {}

        return {
            "pubkey":        pubkey,
            "deposit_count": stats[0],
            "total_usd":     round(float(stats[1]), 2),
            "total_btc":     round(float(stats[2]), 8),
            "goal":          {"monthly_target_usd": goal[0], "target_years": goal[1]} if goal else None,
        }

    def get_user_deposits(self, pubkey: str, limit: int = 50) -> list:
        """Return deposit history for a user."""
        limit = max(1, min(limit, 500))

        try:
            conn = get_connection()
            rows = conn.execute(
                """
                SELECT id, amount_usd, btc_price, btc_amount, created_at
                FROM savings_deposits WHERE pubkey = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (pubkey, limit),
            ).fetchall()
        except Exception:
            return []

        return [
            {
                "id":         row[0],
                "amount_usd": round(float(row[1]), 2),
                "btc_price":  round(float(row[2]), 2),
                "btc_amount": round(float(row[3]), 8),
                "created_at": row[4],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Banning
    # ------------------------------------------------------------------

    def ban_user(
        self,
        pubkey: str,
        reason: str,
        duration: int = 0,
        banned_by: str = "admin",
    ) -> dict:
        """
        Ban a user.
        ``duration`` is in seconds; 0 means permanent.
        Also revokes all sessions.
        """
        if not pubkey:
            return {"error": "pubkey required"}

        now = int(time.time())
        banned_until = (now + duration) if duration > 0 else 0

        try:
            conn = get_connection()
            _ensure_schema(conn)

            conn.execute(
                """
                INSERT OR REPLACE INTO banned_users
                    (pubkey, reason, banned_at, banned_until, banned_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pubkey, reason or "Admin ban", now, banned_until, banned_by),
            )
            conn.commit()

            # Revoke all sessions
            sessions_revoked = self.revoke_all_sessions(pubkey)

            # Log to audit
            try:
                from ..security.audit import SecurityAudit, EventType, Severity
                audit = SecurityAudit()
                audit.log_admin_action(
                    admin_pubkey=banned_by,
                    target_pubkey=pubkey,
                    action="BAN_USER",
                    details={"reason": reason, "duration": duration, "banned_until": banned_until},
                )
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "pubkey":          pubkey,
            "banned":          True,
            "reason":          reason,
            "banned_at":       now,
            "banned_until":    banned_until,
            "permanent":       banned_until == 0,
            "sessions_revoked": sessions_revoked,
        }

    def unban_user(self, pubkey: str, unbanned_by: str = "admin") -> dict:
        """Remove a ban from a user."""
        if not pubkey:
            return {"error": "pubkey required"}

        try:
            conn = get_connection()
            _ensure_schema(conn)
            cursor = conn.execute("DELETE FROM banned_users WHERE pubkey = ?", (pubkey,))
            conn.commit()

            if cursor.rowcount == 0:
                return {"error": "user_not_banned"}

            try:
                from ..security.audit import SecurityAudit
                audit = SecurityAudit()
                audit.log_admin_action(unbanned_by, pubkey, "UNBAN_USER")
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {"pubkey": pubkey, "banned": False, "unbanned_at": int(time.time())}

    def get_banned_users(self) -> list:
        """Return all currently banned users."""
        now = int(time.time())

        try:
            conn = get_connection()
            _ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT pubkey, reason, banned_at, banned_until, banned_by
                FROM banned_users
                ORDER BY banned_at DESC
                """,
            ).fetchall()
        except Exception:
            return []

        result = []
        for row in rows:
            pubkey, reason, banned_at, banned_until, banned_by = row
            # Skip expired bans
            if banned_until > 0 and banned_until < now:
                continue
            result.append({
                "pubkey":      pubkey,
                "reason":      reason,
                "banned_at":   banned_at,
                "banned_until": banned_until,
                "permanent":   banned_until == 0,
                "banned_by":   banned_by,
            })

        return result

    # ------------------------------------------------------------------
    # GDPR
    # ------------------------------------------------------------------

    def export_user_data(self, pubkey: str) -> dict:
        """
        GDPR-compliant full data export for a user.
        Returns all stored data in a structured format.
        """
        if not pubkey:
            return {"error": "pubkey required"}

        try:
            conn = get_connection()

            user = conn.execute(
                "SELECT pubkey, auth_method, created_at FROM users WHERE pubkey = ?",
                (pubkey,),
            ).fetchone()

            if not user:
                return {"error": "user_not_found"}

            deposits = conn.execute(
                "SELECT id, amount_usd, btc_price, btc_amount, created_at FROM savings_deposits WHERE pubkey = ?",
                (pubkey,),
            ).fetchall()

            goal = None
            try:
                g = conn.execute(
                    "SELECT monthly_target_usd, target_years, created_at FROM savings_goals WHERE pubkey = ?",
                    (pubkey,),
                ).fetchone()
                goal = dict(zip(["monthly_target_usd", "target_years", "created_at"], g)) if g else None
            except Exception:
                pass

            achievements = []
            try:
                achievements = [
                    {"achievement_id": r[0], "awarded_at": r[1]}
                    for r in conn.execute(
                        "SELECT achievement_id, awarded_at FROM user_achievements WHERE pubkey = ?",
                        (pubkey,),
                    ).fetchall()
                ]
            except Exception:
                pass

            prefs = {}
            try:
                p = conn.execute(
                    "SELECT fee_alert_low, fee_alert_high, alerts_enabled, updated_at FROM user_preferences WHERE pubkey = ?",
                    (pubkey,),
                ).fetchone()
                if p:
                    prefs = {"fee_alert_low": p[0], "fee_alert_high": p[1],
                             "alerts_enabled": bool(p[2]), "updated_at": p[3]}
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "export_format":  "magma-gdpr-v1",
            "exported_at":    int(time.time()),
            "pubkey":         pubkey,
            "account": {
                "auth_method": user[1],
                "created_at":  user[2],
            },
            "deposits":      [
                {"id": r[0], "amount_usd": r[1], "btc_price": r[2],
                 "btc_amount": r[3], "created_at": r[4]}
                for r in deposits
            ],
            "savings_goal":  goal,
            "achievements":  achievements,
            "preferences":   prefs,
        }

    def delete_user_data(self, pubkey: str, deleted_by: str = "gdpr_request") -> dict:
        """
        GDPR right-to-erasure: delete all user data.
        Returns summary of what was deleted.
        """
        if not pubkey:
            return {"error": "pubkey required"}

        counts: dict = {}

        try:
            conn = get_connection()

            for table in ("savings_deposits", "user_achievements",
                          "savings_goals", "user_preferences", "sessions",
                          "banned_users", "admin_notes"):
                try:
                    cursor = conn.execute(f"DELETE FROM {table} WHERE pubkey = ?", (pubkey,))
                    counts[table] = cursor.rowcount
                except Exception:
                    counts[table] = 0

            # Anonymize the user row instead of deleting (preserves referential integrity)
            conn.execute(
                "UPDATE users SET pubkey = ?, auth_method = 'deleted' WHERE pubkey = ?",
                (f"deleted_{pubkey[:8]}_{int(time.time())}", pubkey),
            )
            conn.commit()

            try:
                from ..security.audit import SecurityAudit
                audit = SecurityAudit()
                audit.log_admin_action(deleted_by, pubkey, "GDPR_DELETE", counts)
            except Exception:
                pass

        except Exception as exc:
            return {"error": str(exc)}

        return {
            "pubkey":    pubkey,
            "deleted_at": int(time.time()),
            "deleted_by": deleted_by,
            "rows_deleted": counts,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_users(self, query: str) -> list:
        """
        Search users by pubkey prefix (case-insensitive).
        Returns up to 20 matching users.
        """
        if not query or len(query) < 4:
            return []

        query = query.strip().lower()

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT pubkey, auth_method, created_at FROM users WHERE LOWER(pubkey) LIKE ? LIMIT 20",
                (query + "%",),
            ).fetchall()
        except Exception:
            return []

        return [
            {"pubkey": row[0], "auth_method": row[1], "created_at": row[2]}
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    def get_user_risk_score(self, pubkey: str) -> dict:
        """
        Return a risk assessment for a user based on behavioral signals.
        """
        if not pubkey:
            return {}

        risk_score = 0
        risk_factors = []

        try:
            conn = get_connection()

            # Check ban history
            try:
                _ensure_schema(conn)
                is_banned = conn.execute(
                    "SELECT 1 FROM banned_users WHERE pubkey = ?", (pubkey,)
                ).fetchone()
                if is_banned:
                    risk_score += 50
                    risk_factors.append("User is currently banned")
            except Exception:
                pass

            # Auth failure rate
            try:
                failures = conn.execute(
                    "SELECT COUNT(*) FROM security_audit_log WHERE pubkey = ? AND event_type = 'AUTH_FAILURE'",
                    (pubkey,),
                ).fetchone()[0]
                if failures >= 10:
                    risk_score += 30
                    risk_factors.append(f"{failures} auth failures on record")
                elif failures >= 5:
                    risk_score += 15
                    risk_factors.append(f"{failures} auth failures on record")
            except Exception:
                pass

            # Unusual deposit amounts (large single deposit)
            try:
                max_deposit = conn.execute(
                    "SELECT MAX(amount_usd) FROM savings_deposits WHERE pubkey = ?",
                    (pubkey,),
                ).fetchone()[0] or 0
                if max_deposit >= 10000:
                    risk_score += 20
                    risk_factors.append(f"Large single deposit: ${max_deposit:.0f}")
            except Exception:
                pass

            # Account age
            user_row = conn.execute(
                "SELECT created_at FROM users WHERE pubkey = ?", (pubkey,)
            ).fetchone()
            if user_row:
                age_days = (int(time.time()) - user_row[0]) / 86400
                if age_days < 1:
                    risk_score += 10
                    risk_factors.append("Account created within last 24h")

        except Exception:
            pass

        risk_score = min(100, risk_score)
        risk_level = (
            "high"   if risk_score >= 70 else
            "medium" if risk_score >= 40 else
            "low"
        )

        return {
            "pubkey":     pubkey,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors":    risk_factors,
            "assessed_at": int(time.time()),
        }
