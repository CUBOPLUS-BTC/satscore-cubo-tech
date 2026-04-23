"""
Compliance rules engine for Magma Bitcoin app.
Evaluates transactions against a configurable set of AML/compliance rules.
Pure Python stdlib — no third-party dependencies.
"""

import time
import uuid
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Rule result
# ---------------------------------------------------------------------------

class RuleResult:
    """Result of evaluating a single compliance rule."""

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        triggered: bool,
        severity: str = "medium",
        message: str = "",
        recommended_action: str = "monitor",
        score_contribution: float = 0.0,
    ) -> None:
        self.rule_id             = rule_id
        self.rule_name           = rule_name
        self.triggered           = triggered
        self.severity            = severity
        self.message             = message
        self.recommended_action  = recommended_action
        self.score_contribution  = score_contribution

    def to_dict(self) -> dict:
        return {
            "rule_id":            self.rule_id,
            "rule_name":          self.rule_name,
            "triggered":          self.triggered,
            "severity":           self.severity,
            "message":            self.message,
            "recommended_action": self.recommended_action,
            "score_contribution": self.score_contribution,
        }


# ---------------------------------------------------------------------------
# Rule class
# ---------------------------------------------------------------------------

class Rule:
    """
    A single compliance rule definition.

    ``evaluate_fn`` receives ``(transaction: dict, user_profile: dict)`` and
    returns a ``RuleResult``.
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: str,
        evaluate_fn: Callable,
        enabled: bool = True,
        conditions: dict = None,
        actions: list = None,
    ) -> None:
        self.id          = rule_id
        self.name        = name
        self.description = description
        self.severity    = severity
        self._evaluate   = evaluate_fn
        self.enabled     = enabled
        self.conditions  = conditions or {}
        self.actions     = actions or []

    def evaluate(self, context: dict) -> RuleResult:
        """Evaluate this rule against the given context dict."""
        if not self.enabled:
            return RuleResult(self.id, self.name, False, self.severity, "Rule disabled")

        try:
            return self._evaluate(context)
        except Exception as exc:
            return RuleResult(
                self.id, self.name, False, "low",
                f"Rule evaluation error: {exc}"
            )


# ---------------------------------------------------------------------------
# Predefined rule implementations
# ---------------------------------------------------------------------------

def _make_large_transaction_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        amount = float(ctx.get("transaction", {}).get("amount_usd", 0))
        threshold = 10_000.0
        triggered = amount >= threshold
        return RuleResult(
            "RULE_LARGE_TX", "Large Transaction",
            triggered=triggered,
            severity="high",
            message=f"Transaction of ${amount:,.2f} exceeds ${threshold:,.0f} CTR threshold" if triggered else "",
            recommended_action="file_ctr" if triggered else "allow",
            score_contribution=40.0 if triggered else 0.0,
        )
    return Rule("RULE_LARGE_TX", "Large Transaction",
                "Transaction at or above CTR reporting threshold", "high", evaluate)


def _make_structuring_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        tx_history = ctx.get("tx_history", [])
        current_amount = float(ctx.get("transaction", {}).get("amount_usd", 0))
        window_24h = int(time.time()) - 86400

        recent = [
            t for t in tx_history
            if t.get("created_at", 0) >= window_24h
               and 5_000 <= float(t.get("amount_usd", 0)) < 10_000
        ]

        all_near_threshold = recent + ([{"amount_usd": current_amount}]
                                       if 5_000 <= current_amount < 10_000 else [])

        triggered = len(all_near_threshold) >= 2
        total = sum(float(t.get("amount_usd", 0)) for t in all_near_threshold)

        return RuleResult(
            "RULE_STRUCTURING", "Structuring Detection",
            triggered=triggered,
            severity="critical",
            message=f"Possible structuring: {len(all_near_threshold)} transactions totalling ${total:,.2f} in 24h" if triggered else "",
            recommended_action="block_and_report" if triggered else "allow",
            score_contribution=60.0 if triggered else 0.0,
        )
    return Rule("RULE_STRUCTURING", "Structuring Detection",
                "Multiple transactions just below reporting threshold (smurfing)", "critical", evaluate)


def _make_rapid_succession_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        tx_history = ctx.get("tx_history", [])
        window_1h = int(time.time()) - 3600
        recent = [t for t in tx_history if t.get("created_at", 0) >= window_1h]
        triggered = len(recent) >= 5
        return RuleResult(
            "RULE_RAPID_SUCCESSION", "Rapid Succession Transactions",
            triggered=triggered,
            severity="high",
            message=f"{len(recent)} transactions in the last hour" if triggered else "",
            recommended_action="review" if triggered else "allow",
            score_contribution=30.0 if triggered else 0.0,
        )
    return Rule("RULE_RAPID_SUCCESSION", "Rapid Succession Transactions",
                "More than 5 transactions in 1 hour", "high", evaluate)


def _make_new_account_large_tx_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        amount = float(ctx.get("transaction", {}).get("amount_usd", 0))
        account_age_days = float(ctx.get("user_profile", {}).get("account_age_days", 9999))
        triggered = account_age_days < 7 and amount >= 500
        return RuleResult(
            "RULE_NEW_ACCOUNT_LARGE", "New Account Large Transaction",
            triggered=triggered,
            severity="high",
            message=f"New account (<7d, age={account_age_days:.1f}d) attempting ${amount:,.2f} transaction" if triggered else "",
            recommended_action="enhanced_due_diligence" if triggered else "allow",
            score_contribution=35.0 if triggered else 0.0,
        )
    return Rule("RULE_NEW_ACCOUNT_LARGE", "New Account Large Transaction",
                "Large transaction from account less than 7 days old", "high", evaluate)


def _make_round_amount_rule() -> Rule:
    _suspicious = {100, 500, 1000, 2000, 2500, 4000, 4500, 4900, 4990,
                   4999, 5000, 7500, 8000, 8500, 8900, 8999, 9000,
                   9500, 9900, 9990, 9999}

    def evaluate(ctx: dict) -> RuleResult:
        tx_history = ctx.get("tx_history", [])
        current = float(ctx.get("transaction", {}).get("amount_usd", 0))
        all_amounts = [float(t.get("amount_usd", 0)) for t in tx_history] + [current]
        round_count = sum(1 for a in all_amounts if round(a) in _suspicious)
        triggered = round_count >= 3
        return RuleResult(
            "RULE_ROUND_AMOUNTS", "Round Amount Pattern",
            triggered=triggered,
            severity="medium",
            message=f"{round_count} suspicious round-amount transactions detected" if triggered else "",
            recommended_action="monitor" if triggered else "allow",
            score_contribution=20.0 if triggered else 0.0,
        )
    return Rule("RULE_ROUND_AMOUNTS", "Round Amount Pattern",
                "Multiple transactions with suspiciously round amounts", "medium", evaluate)


def _make_cross_border_rule() -> Rule:
    _high_risk = {"KP", "IR", "SY", "CU", "SD", "RU", "BY", "VE", "MM", "YE"}

    def evaluate(ctx: dict) -> RuleResult:
        country = ctx.get("transaction", {}).get("country", "").upper()
        user_country = ctx.get("user_profile", {}).get("country", "").upper()
        triggered = country in _high_risk or user_country in _high_risk
        risky = country if country in _high_risk else user_country
        return RuleResult(
            "RULE_CROSS_BORDER", "Cross-Border / High-Risk Jurisdiction",
            triggered=triggered,
            severity="critical" if risky in ("KP", "IR", "SY") else "high",
            message=f"Transaction involving high-risk jurisdiction: {risky}" if triggered else "",
            recommended_action="block" if risky in ("KP", "IR", "SY") else "review",
            score_contribution=70.0 if risky in ("KP", "IR", "SY") else 40.0 if triggered else 0.0,
        )
    return Rule("RULE_CROSS_BORDER", "Cross-Border High-Risk Jurisdiction",
                "Transaction involving a high-risk or sanctioned country", "critical", evaluate)


def _make_dormant_account_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        last_tx_ts = ctx.get("user_profile", {}).get("last_tx_timestamp", 0)
        current_ts = int(time.time())
        days_dormant = (current_ts - last_tx_ts) / 86400 if last_tx_ts else 0
        amount = float(ctx.get("transaction", {}).get("amount_usd", 0))
        triggered = days_dormant >= 180 and amount >= 100
        return RuleResult(
            "RULE_DORMANT_ACCOUNT", "Dormant Account Activation",
            triggered=triggered,
            severity="medium",
            message=f"Account dormant for {days_dormant:.0f} days now making ${amount:,.2f} transaction" if triggered else "",
            recommended_action="enhanced_due_diligence" if triggered else "allow",
            score_contribution=25.0 if triggered else 0.0,
        )
    return Rule("RULE_DORMANT_ACCOUNT", "Dormant Account Activation",
                "Account inactive for 6+ months suddenly becomes active", "medium", evaluate)


def _make_unusual_time_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        tx_history = ctx.get("tx_history", [])
        unusual = sum(
            1 for t in tx_history
            if 0 <= ((t.get("created_at", 0) % 86400) // 3600) < 5
        )
        triggered = unusual >= 3
        return RuleResult(
            "RULE_UNUSUAL_TIME", "Unusual Time-of-Day Activity",
            triggered=triggered,
            severity="low",
            message=f"{unusual} transactions between midnight and 5 AM UTC" if triggered else "",
            recommended_action="monitor" if triggered else "allow",
            score_contribution=10.0 if triggered else 0.0,
        )
    return Rule("RULE_UNUSUAL_TIME", "Unusual Time-of-Day Activity",
                "Transactions consistently at unusual hours (midnight to 5 AM)", "low", evaluate)


def _make_velocity_change_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        tx_history = ctx.get("tx_history", [])
        now_ts = int(time.time())
        last_30d = [t for t in tx_history if t.get("created_at", 0) >= now_ts - 2592000]
        last_7d  = [t for t in tx_history if t.get("created_at", 0) >= now_ts - 604800]
        vol_30d  = sum(float(t.get("amount_usd", 0)) for t in last_30d)
        vol_7d   = sum(float(t.get("amount_usd", 0)) for t in last_7d)
        expected_7d = vol_30d / 4 if vol_30d > 0 else 0
        triggered = expected_7d > 0 and vol_7d > (expected_7d * 5)
        return RuleResult(
            "RULE_VELOCITY_CHANGE", "Velocity Change Detection",
            triggered=triggered,
            severity="high",
            message=f"7-day volume ${vol_7d:,.2f} is {vol_7d/expected_7d:.1f}x normal" if triggered and expected_7d > 0 else "",
            recommended_action="review" if triggered else "allow",
            score_contribution=35.0 if triggered else 0.0,
        )
    return Rule("RULE_VELOCITY_CHANGE", "Velocity Change Detection",
                "Transaction volume suddenly 5x higher than normal weekly average", "high", evaluate)


def _make_multiple_accounts_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        shared_ips = ctx.get("user_profile", {}).get("shared_ip_accounts", 0)
        triggered = shared_ips >= 3
        return RuleResult(
            "RULE_MULTIPLE_ACCOUNTS", "Multiple Account Linkage",
            triggered=triggered,
            severity="high",
            message=f"IP shared with {shared_ips} other accounts" if triggered else "",
            recommended_action="review" if triggered else "allow",
            score_contribution=30.0 if triggered else 0.0,
        )
    return Rule("RULE_MULTIPLE_ACCOUNTS", "Multiple Account Linkage",
                "Multiple accounts sharing the same IP address", "high", evaluate)


def _make_sanctioned_address_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        from .aml import SanctionsChecker
        destination = ctx.get("transaction", {}).get("destination_address", "")
        source      = ctx.get("transaction", {}).get("source_address", "")

        checker = SanctionsChecker()
        for addr in filter(None, [destination, source]):
            result = checker.check_address(addr)
            if result.get("sanctioned"):
                return RuleResult(
                    "RULE_SANCTIONED_ADDR", "Sanctioned Address",
                    triggered=True,
                    severity="critical",
                    message=f"Address {addr[:16]}... is on OFAC SDN list",
                    recommended_action="block_and_report",
                    score_contribution=100.0,
                )
        return RuleResult("RULE_SANCTIONED_ADDR", "Sanctioned Address",
                          triggered=False, score_contribution=0.0)
    return Rule("RULE_SANCTIONED_ADDR", "Sanctioned Address",
                "Address is on OFAC or other sanctions list", "critical", evaluate)


def _make_high_risk_profile_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        risk_score = float(ctx.get("user_profile", {}).get("risk_score", 0))
        triggered = risk_score >= 70
        return RuleResult(
            "RULE_HIGH_RISK_PROFILE", "High-Risk User Profile",
            triggered=triggered,
            severity="high",
            message=f"User risk score {risk_score:.0f}/100" if triggered else "",
            recommended_action="enhanced_due_diligence" if triggered else "allow",
            score_contribution=risk_score * 0.5 if triggered else 0.0,
        )
    return Rule("RULE_HIGH_RISK_PROFILE", "High-Risk User Profile",
                "User has a risk score >= 70 from prior AML signals", "high", evaluate)


def _make_atypical_amount_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        tx_history = ctx.get("tx_history", [])
        current_amount = float(ctx.get("transaction", {}).get("amount_usd", 0))

        if len(tx_history) < 5:
            return RuleResult("RULE_ATYPICAL_AMOUNT", "Atypical Transaction Amount",
                              triggered=False, score_contribution=0.0)

        amounts = [float(t.get("amount_usd", 0)) for t in tx_history]
        avg = sum(amounts) / len(amounts)
        variance = sum((a - avg) ** 2 for a in amounts) / len(amounts)
        std_dev = variance ** 0.5

        triggered = std_dev > 0 and abs(current_amount - avg) > (3 * std_dev)

        return RuleResult(
            "RULE_ATYPICAL_AMOUNT", "Atypical Transaction Amount",
            triggered=triggered,
            severity="medium",
            message=f"Amount ${current_amount:,.2f} is {abs(current_amount - avg) / std_dev:.1f} std devs from mean ${avg:,.2f}" if triggered else "",
            recommended_action="monitor" if triggered else "allow",
            score_contribution=25.0 if triggered else 0.0,
        )
    return Rule("RULE_ATYPICAL_AMOUNT", "Atypical Transaction Amount",
                "Transaction amount is statistically anomalous (> 3 sigma from user's mean)", "medium", evaluate)


def _make_weekend_large_tx_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        import datetime
        amount = float(ctx.get("transaction", {}).get("amount_usd", 0))
        ts = ctx.get("transaction", {}).get("created_at", int(time.time()))
        weekday = datetime.datetime.utcfromtimestamp(ts).weekday()  # 5=Sat, 6=Sun
        triggered = weekday >= 5 and amount >= 5_000
        return RuleResult(
            "RULE_WEEKEND_LARGE_TX", "Weekend Large Transaction",
            triggered=triggered,
            severity="low",
            message=f"${amount:,.2f} transaction on weekend (day {weekday})" if triggered else "",
            recommended_action="monitor" if triggered else "allow",
            score_contribution=10.0 if triggered else 0.0,
        )
    return Rule("RULE_WEEKEND_LARGE_TX", "Weekend Large Transaction",
                "Large transaction occurring on a weekend", "low", evaluate)


def _make_low_btc_price_large_usd_rule() -> Rule:
    def evaluate(ctx: dict) -> RuleResult:
        btc_price = float(ctx.get("transaction", {}).get("btc_price", 99999))
        amount_usd = float(ctx.get("transaction", {}).get("amount_usd", 0))
        # Suspicious if buying large USD worth of BTC when price is very low (< $10k)
        triggered = btc_price < 10_000 and amount_usd >= 5_000
        return RuleResult(
            "RULE_LOW_PRICE_LARGE_BUY", "Large Buy at Unusually Low BTC Price",
            triggered=triggered,
            severity="low",
            message=f"${amount_usd:,.2f} buy at BTC price ${btc_price:,.0f} (suspiciously low)" if triggered else "",
            recommended_action="monitor" if triggered else "allow",
            score_contribution=10.0 if triggered else 0.0,
        )
    return Rule("RULE_LOW_PRICE_LARGE_BUY", "Large Buy at Low BTC Price",
                "Large USD purchase when BTC price is abnormally low", "low", evaluate)


# ---------------------------------------------------------------------------
# RulesEngine
# ---------------------------------------------------------------------------

class RulesEngine:
    """
    Configurable compliance rules engine.
    Evaluates a list of Rule objects against transaction context and returns
    a list of RuleResult objects, one per triggered rule.
    """

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}
        self._load_default_rules()

    # ------------------------------------------------------------------
    # Default rules
    # ------------------------------------------------------------------

    def _load_default_rules(self) -> None:
        """Load the predefined set of compliance rules."""
        default_rules = [
            _make_large_transaction_rule(),
            _make_structuring_rule(),
            _make_rapid_succession_rule(),
            _make_new_account_large_tx_rule(),
            _make_round_amount_rule(),
            _make_cross_border_rule(),
            _make_dormant_account_rule(),
            _make_unusual_time_rule(),
            _make_velocity_change_rule(),
            _make_multiple_accounts_rule(),
            _make_sanctioned_address_rule(),
            _make_high_risk_profile_rule(),
            _make_atypical_amount_rule(),
            _make_weekend_large_tx_rule(),
            _make_low_btc_price_large_usd_rule(),
        ]

        for rule in default_rules:
            self._rules[rule.id] = rule

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, transaction: dict, user_profile: dict) -> list:
        """
        Evaluate all enabled rules against the given transaction and user profile.

        Returns a list of RuleResult objects for triggered rules only.

        Context passed to each rule::

            {
                "transaction":  transaction dict,
                "user_profile": user_profile dict,
                "tx_history":   list of prior transactions (auto-fetched if pubkey present),
            }
        """
        pubkey = transaction.get("pubkey", "")
        tx_history = self._fetch_tx_history(pubkey)

        context = {
            "transaction":  transaction,
            "user_profile": user_profile,
            "tx_history":   tx_history,
        }

        triggered_results = []
        total_score = 0.0

        for rule in self._rules.values():
            result = rule.evaluate(context)
            if result.triggered:
                triggered_results.append(result)
                total_score += result.score_contribution

        total_score = min(100.0, total_score)

        # Sort by score contribution descending
        triggered_results.sort(key=lambda r: r.score_contribution, reverse=True)

        return triggered_results

    def evaluate_full(self, transaction: dict, user_profile: dict) -> dict:
        """
        Full evaluation with summary including aggregate risk score.
        """
        results = self.evaluate(transaction, user_profile)
        total_score = min(100.0, sum(r.score_contribution for r in results))

        return {
            "triggered_rules": [r.to_dict() for r in results],
            "total_rules":     len(self._rules),
            "triggered_count": len(results),
            "aggregate_score": round(total_score, 2),
            "risk_level":      _score_to_level(total_score),
            "recommended_action": (
                "block_and_report" if total_score >= 80 else
                "review"           if total_score >= 50 else
                "monitor"          if total_score >= 30 else
                "allow"
            ),
            "evaluated_at":    int(time.time()),
        }

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: Rule) -> None:
        """Add or replace a rule in the engine."""
        self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if removed."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rules(self) -> list:
        """Return info about all registered rules."""
        return [
            {
                "id":          rule.id,
                "name":        rule.name,
                "description": rule.description,
                "severity":    rule.severity,
                "enabled":     rule.enabled,
            }
            for rule in self._rules.values()
        ]

    def update_rule(self, rule_id: str, updates: dict) -> dict:
        """
        Update rule properties (enabled/disabled, etc.).
        Returns the updated rule info or an error dict.
        """
        if rule_id not in self._rules:
            return {"error": f"Rule {rule_id!r} not found"}

        rule = self._rules[rule_id]

        if "enabled" in updates:
            rule.enabled = bool(updates["enabled"])

        if "severity" in updates and updates["severity"] in ("low", "medium", "high", "critical"):
            rule.severity = updates["severity"]

        return {
            "id":       rule.id,
            "name":     rule.name,
            "enabled":  rule.enabled,
            "severity": rule.severity,
            "updated_at": int(time.time()),
        }

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule without removing it."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Re-enable a previously disabled rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_tx_history(self, pubkey: str, window_days: int = 30) -> list:
        """Fetch recent transaction history for a user from the database."""
        if not pubkey:
            return []

        since = int(time.time()) - (window_days * 86400)

        try:
            from ..database import get_conn as get_connection
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
# Helpers
# ---------------------------------------------------------------------------

def _score_to_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
