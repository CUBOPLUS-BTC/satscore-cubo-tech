"""WebhookManager — subscription CRUD and validation for the Magma API.

Manages the ``webhook_subscriptions`` table and provides helpers for
generating signing secrets and computing HMAC-SHA256 payload signatures.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import time
import urllib.parse
from typing import Dict, List, Optional

from ..database import get_conn, _is_postgres


# ---------------------------------------------------------------------------
# Supported event types
# ---------------------------------------------------------------------------
SUPPORTED_EVENTS = {
    "price_alert",
    "fee_alert",
    "deposit_confirmed",
    "achievement_earned",
    "goal_reached",
    "savings_updated",
    "score_computed",
    "session_created",
}

# Maximum subscriptions per user
MAX_SUBSCRIPTIONS_PER_USER = 10

# Maximum events per subscription
MAX_EVENTS_PER_SUBSCRIPTION = len(SUPPORTED_EVENTS)

_CREATE_WEBHOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id TEXT PRIMARY KEY,
    pubkey TEXT NOT NULL,
    url TEXT NOT NULL,
    events TEXT NOT NULL,
    secret TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    last_triggered_at INTEGER,
    failure_count INTEGER NOT NULL DEFAULT 0
)
"""

_INDEX_PUBKEY = (
    "CREATE INDEX IF NOT EXISTS idx_webhook_pubkey "
    "ON webhook_subscriptions (pubkey)"
)
_INDEX_ACTIVE = (
    "CREATE INDEX IF NOT EXISTS idx_webhook_active "
    "ON webhook_subscriptions (active)"
)


class WebhookManager:
    """Create, read, update, and delete webhook subscriptions.

    All persistent data lives in the ``webhook_subscriptions`` table.
    The manager is stateless between calls so it can be shared as a
    module-level singleton.
    """

    def __init__(self) -> None:
        self._init_table()

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def _init_table(self) -> None:
        """Create the webhooks table if it does not exist."""
        try:
            conn = get_conn()
            conn.execute(_CREATE_WEBHOOKS_TABLE)
            conn.execute(_INDEX_PUBKEY)
            conn.execute(_INDEX_ACTIVE)
            conn.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def subscribe(
        self,
        pubkey: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> dict:
        """Create a new webhook subscription.

        Parameters
        ----------
        pubkey:
            Owner's Nostr pubkey.
        url:
            Callback URL (must pass :meth:`validate_url`).
        events:
            List of event type strings to subscribe to.
        secret:
            Optional signing secret; one is generated if not provided.

        Returns
        -------
        dict
            The created subscription record.

        Raises
        ------
        ValueError
            On validation failures.
        """
        if not pubkey:
            raise ValueError("pubkey is required")
        if not url:
            raise ValueError("url is required")
        if not events:
            raise ValueError("At least one event type is required")

        if not self.validate_url(url):
            raise ValueError(f"Invalid or disallowed URL: {url!r}")

        # Normalise and validate event types.
        clean_events = list({e.strip().lower() for e in events})
        invalid = [e for e in clean_events if e not in SUPPORTED_EVENTS]
        if invalid:
            raise ValueError(
                f"Unsupported event type(s): {invalid}. "
                f"Supported: {sorted(SUPPORTED_EVENTS)}"
            )

        # Enforce per-user subscription cap.
        existing = self.list_subscriptions(pubkey)
        if len(existing) >= MAX_SUBSCRIPTIONS_PER_USER:
            raise ValueError(
                f"Maximum of {MAX_SUBSCRIPTIONS_PER_USER} subscriptions per user reached."
            )

        # Deduplicate: same pubkey + url + event set is not allowed.
        for sub in existing:
            if sub["url"] == url and set(sub["events"]) == set(clean_events):
                raise ValueError("An identical subscription already exists.")

        signing_secret = secret or self.generate_secret()
        sub_id = secrets.token_hex(16)
        now = int(time.time())
        events_json = json.dumps(sorted(clean_events))

        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        conn.execute(
            f"INSERT INTO webhook_subscriptions "
            f"(id, pubkey, url, events, secret, active, created_at, failure_count) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 1, {ph}, 0)",
            (sub_id, pubkey, url, events_json, signing_secret, now),
        )
        conn.commit()

        return {
            "id": sub_id,
            "pubkey": pubkey,
            "url": url,
            "events": clean_events,
            "active": True,
            "created_at": now,
            "last_triggered_at": None,
            "failure_count": 0,
            # Return the secret once so the caller can store it.
            "secret": signing_secret,
        }

    def unsubscribe(self, pubkey: str, subscription_id: str) -> bool:
        """Delete a subscription.

        Returns ``True`` if a row was deleted, ``False`` if not found.
        Raises ``PermissionError`` if the subscription belongs to a
        different pubkey.
        """
        sub = self._get_subscription(subscription_id)
        if sub is None:
            return False
        if sub["pubkey"] != pubkey:
            raise PermissionError("Subscription does not belong to this user.")

        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        cur = conn.execute(
            f"DELETE FROM webhook_subscriptions WHERE id = {ph}", (subscription_id,)
        )
        conn.commit()
        return (cur.rowcount or 0) > 0

    def list_subscriptions(self, pubkey: str) -> List[dict]:
        """Return all subscriptions for *pubkey* (active and inactive)."""
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        rows = conn.execute(
            f"SELECT * FROM webhook_subscriptions WHERE pubkey = {ph} "
            f"ORDER BY created_at DESC",
            (pubkey,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_subscription(
        self, pubkey: str, sub_id: str, updates: dict
    ) -> dict:
        """Partially update a subscription.

        Allowed fields: ``url``, ``events``, ``active``.
        Returns the updated subscription dict.
        """
        sub = self._get_subscription(sub_id)
        if sub is None:
            raise KeyError(f"Subscription {sub_id!r} not found.")
        if sub["pubkey"] != pubkey:
            raise PermissionError("Subscription does not belong to this user.")

        allowed_fields = {"url", "events", "active"}
        set_clauses = []
        params = []
        ph = "%s" if _is_postgres() else "?"

        if "url" in updates:
            new_url = updates["url"]
            if not self.validate_url(new_url):
                raise ValueError(f"Invalid URL: {new_url!r}")
            set_clauses.append(f"url = {ph}")
            params.append(new_url)

        if "events" in updates:
            clean = list({e.strip().lower() for e in updates["events"]})
            invalid = [e for e in clean if e not in SUPPORTED_EVENTS]
            if invalid:
                raise ValueError(f"Unsupported event type(s): {invalid}")
            set_clauses.append(f"events = {ph}")
            params.append(json.dumps(sorted(clean)))

        if "active" in updates:
            set_clauses.append(f"active = {ph}")
            params.append(1 if updates["active"] else 0)

        if not set_clauses:
            raise ValueError(f"No valid fields to update. Allowed: {allowed_fields}")

        params.append(sub_id)
        conn = get_conn()
        conn.execute(
            f"UPDATE webhook_subscriptions SET {', '.join(set_clauses)} WHERE id = {ph}",
            params,
        )
        conn.commit()

        updated = self._get_subscription(sub_id)
        if updated is None:
            raise RuntimeError("Subscription disappeared after update.")
        return updated

    # ------------------------------------------------------------------
    # Helpers used by the dispatcher
    # ------------------------------------------------------------------

    def get_subscribers_for_event(self, event_type: str) -> List[dict]:
        """Return all *active* subscriptions that include *event_type*."""
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM webhook_subscriptions WHERE active = 1"
        ).fetchall()
        result = []
        for row in rows:
            sub = self._row_to_dict(row)
            if event_type in sub["events"]:
                result.append(sub)
        return result

    def get_subscribers_for_pubkeys(
        self, event_type: str, pubkeys: List[str]
    ) -> List[dict]:
        """Return active subscriptions for specific pubkeys and event_type."""
        if not pubkeys:
            return []
        conn = get_conn()
        ph = "%s" if _is_postgres() else "?"
        placeholders = ", ".join([ph] * len(pubkeys))
        rows = conn.execute(
            f"SELECT * FROM webhook_subscriptions "
            f"WHERE active = 1 AND pubkey IN ({placeholders})",
            pubkeys,
        ).fetchall()
        result = []
        for row in rows:
            sub = self._row_to_dict(row)
            if event_type in sub["events"]:
                result.append(sub)
        return result

    def record_delivery(
        self,
        sub_id: str,
        success: bool,
    ) -> None:
        """Update last_triggered_at and failure_count after a delivery attempt."""
        ph = "%s" if _is_postgres() else "?"
        now = int(time.time())
        conn = get_conn()
        if success:
            conn.execute(
                f"UPDATE webhook_subscriptions "
                f"SET last_triggered_at = {ph}, failure_count = 0 "
                f"WHERE id = {ph}",
                (now, sub_id),
            )
        else:
            conn.execute(
                f"UPDATE webhook_subscriptions "
                f"SET failure_count = failure_count + 1 "
                f"WHERE id = {ph}",
                (sub_id,),
            )
            # Disable after 10 consecutive failures.
            conn.execute(
                f"UPDATE webhook_subscriptions "
                f"SET active = 0 "
                f"WHERE id = {ph} AND failure_count >= 10",
                (sub_id,),
            )
        conn.commit()

    # ------------------------------------------------------------------
    # URL validation
    # ------------------------------------------------------------------

    _PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
    ]

    def validate_url(self, url: str) -> bool:
        """Return ``True`` if *url* is a valid public HTTPS/HTTP callback URL.

        Rejects:
        * Non-http(s) schemes
        * ``localhost`` / ``127.x`` / private IP ranges
        * IP literals in private ranges
        * URLs without a hostname
        """
        if not url:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return False

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False

        # Block .local mDNS domains.
        if hostname.endswith(".local"):
            return False

        # Try to parse as IP and check private ranges.
        try:
            addr = ipaddress.ip_address(hostname)
            for network in self._PRIVATE_RANGES:
                if addr in network:
                    return False
        except ValueError:
            pass  # hostname is a domain name — fine

        # Must have at least one dot (prevents single-label names).
        if "." not in hostname:
            return False

        return True

    # ------------------------------------------------------------------
    # Cryptography
    # ------------------------------------------------------------------

    @staticmethod
    def generate_secret() -> str:
        """Generate a 32-byte hex webhook signing secret."""
        return secrets.token_hex(32)

    @staticmethod
    def compute_signature(payload: str, secret: str) -> str:
        """Return HMAC-SHA256 hex digest of *payload* using *secret*.

        The signature format is ``sha256=<hex>`` matching the GitHub
        webhook convention so clients can use off-the-shelf libraries.
        """
        mac = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        )
        return f"sha256={mac.hexdigest()}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_subscription(self, sub_id: str) -> Optional[dict]:
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        row = conn.execute(
            f"SELECT * FROM webhook_subscriptions WHERE id = {ph}", (sub_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    @staticmethod
    def _row_to_dict(row) -> dict:
        if row is None:
            return {}
        if hasattr(row, "keys"):
            d = dict(row)
        else:
            # psycopg2 tuple row – column order matches CREATE TABLE.
            cols = [
                "id", "pubkey", "url", "events", "secret",
                "active", "created_at", "last_triggered_at", "failure_count",
            ]
            d = dict(zip(cols, row))

        # Deserialise events JSON array.
        events_raw = d.get("events", "[]")
        if isinstance(events_raw, str):
            try:
                d["events"] = json.loads(events_raw)
            except json.JSONDecodeError:
                d["events"] = []

        d["active"] = bool(d.get("active", 1))
        return d
