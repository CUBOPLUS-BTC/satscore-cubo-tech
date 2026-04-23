"""
Anti-Money Laundering (AML) module for Magma Bitcoin app.
Provides transaction risk scoring, pattern analysis, and sanctions checking.
Pure Python stdlib — no third-party dependencies.
"""

import time
import math
import json
import uuid
import threading
from typing import Optional

from ..database import get_conn as get_connection


# ---------------------------------------------------------------------------
# Thresholds and configuration
# ---------------------------------------------------------------------------

# US CTR threshold — transactions at or above this require a Currency Transaction Report
CTR_THRESHOLD_USD = 10_000.0

# Structuring threshold — transactions just below this are suspicious
STRUCTURING_THRESHOLD_USD = 9_000.0

# Rapid movement window in seconds (30 minutes)
RAPID_MOVEMENT_WINDOW = 1_800

# High-frequency threshold: more than this many transactions in 24 hours
HIGH_FREQUENCY_THRESHOLD = 10

# Risk tiers
RISK_LOW      = 0.0   # 0–30
RISK_MEDIUM   = 30.0  # 30–60
RISK_HIGH     = 60.0  # 60–80
RISK_CRITICAL = 80.0  # 80–100

# Known OFAC-sanctioned Bitcoin addresses (small public sample for demonstration)
# Full list: https://home.treasury.gov/policy-issues/financial-sanctions/recent-actions/20181129
_OFAC_ADDRESSES: set = {
    "149w62rY42aZBox8fGcmqNsXUzSStKeq8C",
    "1AjZPMsnmpdK2Rv9KQNfMurTXinscVro9V",
    "12QtD5BFwRsdNsAZY76UVE1xyCGNTojH9h",
    "1FEopBRJcFzsMi5MsScnsMUbnUQ17V7mj3",
    "1JHnq5YqFZNQsiS9zFmq2zFCmFnCZRGdGk",
    "1A8JiWcwvpY7tAopUkSnGuEYHmzGYfZPiq",
    "1HRJ1jSG9fKNLfETcBXjomUGkQ4bBvSYGp",
    "12jbtzBb54r97TCkknwitnessed46eAjcM5A",  # example only
}

# High-risk jurisdiction country codes
_HIGH_RISK_JURISDICTIONS = {
    "KP",  # North Korea
    "IR",  # Iran
    "SY",  # Syria
    "CU",  # Cuba
    "SD",  # Sudan
    "RU",  # Russia (elevated)
    "BY",  # Belarus
    "VE",  # Venezuela (elevated)
    "MM",  # Myanmar
    "YE",  # Yemen
}

# Risk multipliers by jurisdiction
_JURISDICTION_RISK_MULTIPLIERS = {
    "KP": 100.0,
    "IR": 90.0,
    "SY": 90.0,
    "CU": 70.0,
    "SD": 70.0,
    "RU": 40.0,
    "BY": 40.0,
    "VE": 35.0,
    "MM": 35.0,
    "YE": 40.0,
}

# Round amount patterns that may indicate structuring
_SUSPICIOUS_ROUND_AMOUNTS = {
    100, 500, 1000, 2000, 2500, 3000, 4000, 4500, 4900,
    4990, 4999, 5000, 7500, 8000, 8500, 8900, 8999, 9000,
    9100, 9200, 9300, 9400, 9500, 9600, 9700, 9800, 9900, 9990, 9999,
}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_AML_FLAGS = """
CREATE TABLE IF NOT EXISTS aml_flags (
    id             TEXT PRIMARY KEY,
    pubkey         TEXT NOT NULL,
    transaction_id TEXT NOT NULL DEFAULT '',
    reason         TEXT NOT NULL,
    risk_score     REAL NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'open',
    created_at     INTEGER NOT NULL,
    resolved_at    INTEGER NOT NULL DEFAULT 0,
    notes          TEXT NOT NULL DEFAULT ''
)
"""


def _ensure_schema(conn) -> None:
    conn.execute(_CREATE_AML_FLAGS)
    conn.commit()


# ---------------------------------------------------------------------------
# AMLChecker
# ---------------------------------------------------------------------------

class AMLChecker:
    """
    Anti-Money Laundering risk assessment engine.
    Scores transactions and user patterns on a 0-100 scale.
    """

    def __init__(self) -> None:
        try:
            conn = get_connection()
            _ensure_schema(conn)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Transaction check
    # ------------------------------------------------------------------

    def check_transaction(
        self,
        pubkey: str,
        amount: float,
        direction: str,  # "in" or "out"
        metadata: dict = None,
    ) -> dict:
        """
        Perform a full AML risk assessment on a transaction.

        Returns a structured risk assessment with score, flags, and recommended action.
        """
        metadata = metadata or {}
        risk_score = 0.0
        flags: list = []

        # 1. Amount threshold check
        if amount >= CTR_THRESHOLD_USD:
            risk_score += 30
            flags.append(f"Transaction at/above CTR threshold (${amount:,.2f})")

        # 2. Structuring detection
        recent = self._get_recent_transactions(pubkey, window=86400)
        if self._check_structuring(recent + [{"amount_usd": amount}]):
            risk_score += 40
            flags.append("Structuring pattern detected (multiple transactions near threshold)")

        # 3. Rapid in-out movement
        if direction == "out" and self._check_rapid_movement(recent):
            risk_score += 30
            flags.append("Rapid fund movement detected")

        # 4. Round amount
        if self._check_round_amounts([{"amount_usd": amount}]):
            risk_score += 15
            flags.append("Suspicious round amount")

        # 5. Unusual timing
        if self._check_unusual_timing(recent + [{"created_at": int(time.time())}]):
            risk_score += 10
            flags.append("Unusual transaction timing")

        # 6. High frequency
        if self._check_high_frequency(recent):
            risk_score += 20
            flags.append("High-frequency transaction pattern")

        # 7. Jurisdiction risk
        jurisdiction_risk = self._check_jurisdiction_risk(metadata)
        if jurisdiction_risk > 0:
            risk_score += jurisdiction_risk
            flags.append(f"Jurisdiction risk factor: {jurisdiction_risk:.0f}")

        # 8. New account with large transaction
        try:
            conn = get_connection()
            user_row = conn.execute(
                "SELECT created_at FROM users WHERE pubkey = ?", (pubkey,)
            ).fetchone()
            if user_row:
                account_age_days = (int(time.time()) - user_row[0]) / 86400
                if account_age_days < 7 and amount >= 500:
                    risk_score += 25
                    flags.append(f"New account (<7d) with large transaction (${amount:,.2f})")
        except Exception:
            pass

        risk_score = min(100.0, risk_score)
        risk_level = _score_to_level(risk_score)

        action = "allow"
        if risk_score >= RISK_CRITICAL:
            action = "block_and_report"
        elif risk_score >= RISK_HIGH:
            action = "review"
        elif risk_score >= RISK_MEDIUM:
            action = "monitor"

        return {
            "pubkey":       pubkey,
            "amount":       amount,
            "direction":    direction,
            "risk_score":   round(risk_score, 2),
            "risk_level":   risk_level,
            "flags":        flags,
            "action":       action,
            "requires_ctr": amount >= CTR_THRESHOLD_USD,
            "assessed_at":  int(time.time()),
        }

    # ------------------------------------------------------------------
    # Address check
    # ------------------------------------------------------------------

    def check_address(self, address: str) -> dict:
        """
        Check a Bitcoin address against sanctions lists and known risk patterns.
        """
        if not address:
            return {"address": address, "risk_score": 0, "flags": []}

        sanctions = SanctionsChecker()
        sanction_result = sanctions.check_address(address)

        risk_score = sanction_result.get("risk_score", 0.0)
        flags = sanction_result.get("flags", [])

        return {
            "address":    address,
            "risk_score": risk_score,
            "flags":      flags,
            "sanctioned": sanction_result.get("sanctioned", False),
        }

    # ------------------------------------------------------------------
    # Pattern analysis
    # ------------------------------------------------------------------

    def check_pattern(self, pubkey: str, transactions: list = None) -> dict:
        """
        Analyze behavioral transaction patterns for a user.
        """
        if transactions is None:
            transactions = self._get_recent_transactions(pubkey, window=30 * 86400)

        if not transactions:
            return {"pubkey": pubkey, "risk_score": 0, "patterns": []}

        patterns = []
        risk_score = 0.0

        if self._check_structuring(transactions):
            patterns.append("structuring")
            risk_score += 40

        if self._check_rapid_movement(transactions):
            patterns.append("rapid_movement")
            risk_score += 30

        if self._check_round_amounts(transactions):
            patterns.append("round_amounts")
            risk_score += 20

        if self._check_unusual_timing(transactions):
            patterns.append("unusual_timing")
            risk_score += 15

        if self._check_high_frequency(transactions):
            patterns.append("high_frequency")
            risk_score += 20

        total_volume = sum(t.get("amount_usd", 0) for t in transactions)
        if total_volume >= CTR_THRESHOLD_USD:
            patterns.append("ctr_threshold_aggregate")
            risk_score += 25

        risk_score = min(100.0, risk_score)

        return {
            "pubkey":        pubkey,
            "risk_score":    round(risk_score, 2),
            "risk_level":    _score_to_level(risk_score),
            "patterns":      patterns,
            "tx_count":      len(transactions),
            "total_volume":  round(total_volume, 2),
        }

    # ------------------------------------------------------------------
    # Flagging
    # ------------------------------------------------------------------

    def flag_suspicious(
        self,
        pubkey: str,
        transaction_id: str,
        reason: str,
        risk_score: float = 80.0,
    ) -> dict:
        """Flag a transaction as suspicious and store the flag."""
        flag_id = str(uuid.uuid4())
        now = int(time.time())

        try:
            conn = get_connection()
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO aml_flags (id, pubkey, transaction_id, reason, risk_score, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'open', ?)
                """,
                (flag_id, pubkey, transaction_id, reason, risk_score, now),
            )
            conn.commit()
        except Exception as exc:
            return {"error": str(exc)}

        return {
            "flag_id":        flag_id,
            "pubkey":         pubkey,
            "transaction_id": transaction_id,
            "reason":         reason,
            "risk_score":     risk_score,
            "status":         "open",
            "created_at":     now,
        }

    # ------------------------------------------------------------------
    # Risk score
    # ------------------------------------------------------------------

    def get_risk_score(self, pubkey: str) -> float:
        """
        Return the aggregate AML risk score for a user (0-100).
        Combines open flags, transaction patterns, and account signals.
        """
        score = 0.0

        try:
            conn = get_connection()
            _ensure_schema(conn)

            # Open flags
            flags = conn.execute(
                "SELECT risk_score FROM aml_flags WHERE pubkey = ? AND status = 'open'",
                (pubkey,),
            ).fetchall()

            if flags:
                max_flag = max(f[0] for f in flags)
                score = max(score, max_flag)

        except Exception:
            pass

        # Pattern analysis
        pattern_result = self.check_pattern(pubkey)
        score = max(score, pattern_result.get("risk_score", 0))

        return min(100.0, round(score, 2))

    # ------------------------------------------------------------------
    # Internal pattern detectors
    # ------------------------------------------------------------------

    def _check_structuring(self, transactions: list) -> bool:
        """
        Detect structuring (Smurfing): multiple transactions slightly
        below the reporting threshold designed to avoid CTR filing.
        """
        window_24h = int(time.time()) - 86400
        recent = [
            t for t in transactions
            if t.get("created_at", 0) >= window_24h or "created_at" not in t
        ]

        below_threshold = [
            t for t in recent
            if STRUCTURING_THRESHOLD_USD <= t.get("amount_usd", 0) < CTR_THRESHOLD_USD
        ]

        if len(below_threshold) >= 2:
            return True

        # Aggregate check: sum of recent transactions >= CTR threshold
        total = sum(t.get("amount_usd", 0) for t in recent)
        if total >= CTR_THRESHOLD_USD and len(recent) >= 3:
            return True

        return False

    def _check_rapid_movement(self, transactions: list) -> bool:
        """
        Detect rapid in-out movement: funds received and then quickly sent out.
        """
        if len(transactions) < 2:
            return False

        sorted_txns = sorted(transactions, key=lambda t: t.get("created_at", 0))
        for i in range(len(sorted_txns) - 1):
            curr = sorted_txns[i]
            nxt  = sorted_txns[i + 1]
            time_diff = nxt.get("created_at", 0) - curr.get("created_at", 0)
            if 0 < time_diff <= RAPID_MOVEMENT_WINDOW:
                return True

        return False

    def _check_round_amounts(self, transactions: list) -> bool:
        """Detect suspicious round-amount patterns."""
        round_count = sum(
            1 for t in transactions
            if round(t.get("amount_usd", 0)) in _SUSPICIOUS_ROUND_AMOUNTS
        )
        return round_count >= 2

    def _check_unusual_timing(self, transactions: list) -> bool:
        """
        Detect unusual timing: transactions consistently outside normal business hours
        (midnight to 5 AM local time — approximated using UTC).
        """
        unusual_count = 0
        for t in transactions:
            ts = t.get("created_at", int(time.time()))
            # Hour in UTC
            hour = (ts % 86400) // 3600
            if 0 <= hour < 5:
                unusual_count += 1

        return unusual_count >= 3

    def _check_high_frequency(self, transactions: list) -> bool:
        """Detect unusually high transaction frequency in 24 hours."""
        window_24h = int(time.time()) - 86400
        recent = [t for t in transactions if t.get("created_at", 0) >= window_24h]
        return len(recent) >= HIGH_FREQUENCY_THRESHOLD

    def _check_jurisdiction_risk(self, metadata: dict) -> float:
        """Return a risk score contribution based on jurisdiction."""
        country = metadata.get("country", metadata.get("jurisdiction", "")).upper()
        return _JURISDICTION_RISK_MULTIPLIERS.get(country, 0.0)

    def _get_recent_transactions(self, pubkey: str, window: int = 86400) -> list:
        """Retrieve recent transactions from the database."""
        since = int(time.time()) - window

        try:
            conn = get_connection()
            rows = conn.execute(
                """
                SELECT id, amount_usd, btc_price, btc_amount, created_at
                FROM savings_deposits
                WHERE pubkey = ? AND created_at >= ?
                ORDER BY created_at DESC
                """,
                (pubkey, since),
            ).fetchall()
            return [
                {"id": r[0], "amount_usd": r[1], "btc_price": r[2],
                 "btc_amount": r[3], "created_at": r[4]}
                for r in rows
            ]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# SanctionsChecker
# ---------------------------------------------------------------------------

class SanctionsChecker:
    """
    Checks Bitcoin addresses and entity names against known sanctions lists.
    Uses an in-memory set of known sanctioned addresses (public OFAC data).
    """

    def __init__(self) -> None:
        self._sanctioned_addresses = set(_OFAC_ADDRESSES)
        self._updated_at = int(time.time())

    def check_address(self, address: str) -> dict:
        """
        Check a Bitcoin address against the OFAC sanctions list.
        Returns risk assessment with sanctioned flag.
        """
        if not address:
            return {"address": address, "sanctioned": False, "risk_score": 0, "flags": []}

        address = address.strip()
        is_sanctioned = address in self._sanctioned_addresses

        flags = []
        risk_score = 0.0

        if is_sanctioned:
            flags.append("Address is on OFAC SDN list")
            risk_score = 100.0

        return {
            "address":    address,
            "sanctioned": is_sanctioned,
            "risk_score": risk_score,
            "flags":      flags,
            "list_name":  "OFAC SDN" if is_sanctioned else None,
            "checked_at": int(time.time()),
        }

    def check_entity(self, name: str) -> dict:
        """
        Entity name screening against known sanctioned entities.
        Returns a best-effort match result (name matching is approximate).
        """
        if not name:
            return {"name": name, "sanctioned": False, "risk_score": 0}

        name_lower = name.lower().strip()

        # Known sanctioned entity name fragments (illustrative)
        sanctioned_fragments = [
            "lazarus group", "kimsuky", "andariel", "bluenoroff",
            "hezbollah", "hamas", "al-qaeda", "isil", "daesh",
            "hydra market", "bitzlato",
        ]

        matched = [f for f in sanctioned_fragments if f in name_lower]

        return {
            "name":       name,
            "sanctioned": len(matched) > 0,
            "matches":    matched,
            "risk_score": 100.0 if matched else 0.0,
            "checked_at": int(time.time()),
        }

    def update_lists(self) -> None:
        """
        Refresh the sanctions list.
        In production, this would fetch from OFAC's API or a compliance data provider.
        For now it just resets the in-memory set from the hardcoded constants.
        """
        self._sanctioned_addresses = set(_OFAC_ADDRESSES)
        self._updated_at = int(time.time())

    def get_list_info(self) -> dict:
        """Return metadata about the loaded sanctions lists."""
        return {
            "ofac_addresses": len(self._sanctioned_addresses),
            "last_updated":   self._updated_at,
            "note":           "Partial list — for demonstration only. Use full OFAC SDN list in production.",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_to_level(score: float) -> str:
    if score >= RISK_CRITICAL:
        return "critical"
    if score >= RISK_HIGH:
        return "high"
    if score >= RISK_MEDIUM:
        return "medium"
    return "low"
