"""User preferences manager — reads and writes the user_preferences table."""

import json
import time
import uuid
from ..database import get_conn, _is_postgres

# Sensible bounds for fee thresholds (sat/vB)
_FEE_MIN = 1
_FEE_MAX = 5000

# Maximum number of active price alerts per user
_MAX_PRICE_ALERTS = 20

_DEFAULTS = {
    "fee_alert_low":   5,
    "fee_alert_high":  50,
    "price_alerts":    [],
    "alerts_enabled":  True,
}


class PreferencesManager:
    """CRUD layer for user_preferences with validation and alert helpers."""

    # ------------------------------------------------------------------
    # Core read / write
    # ------------------------------------------------------------------

    def get_preferences(self, pubkey: str) -> dict:
        """Return the stored preferences for *pubkey*, falling back to defaults."""
        conn = get_conn()
        ph   = "%s" if _is_postgres() else "?"
        row  = conn.execute(
            f"SELECT fee_alert_low, fee_alert_high, price_alerts, alerts_enabled, updated_at "
            f"FROM user_preferences WHERE pubkey = {ph}",
            (pubkey,),
        ).fetchone()

        if row is None:
            return {
                "pubkey":         pubkey,
                "fee_alert_low":  _DEFAULTS["fee_alert_low"],
                "fee_alert_high": _DEFAULTS["fee_alert_high"],
                "price_alerts":   [],
                "alerts_enabled": True,
                "updated_at":     None,
            }

        if isinstance(row, tuple):
            fee_low, fee_high, alerts_raw, enabled, updated_at = row
        else:
            fee_low     = row["fee_alert_low"]
            fee_high    = row["fee_alert_high"]
            alerts_raw  = row["price_alerts"]
            enabled     = row["alerts_enabled"]
            updated_at  = row["updated_at"]

        try:
            price_alerts = json.loads(alerts_raw or "[]")
        except (TypeError, json.JSONDecodeError):
            price_alerts = []

        return {
            "pubkey":         pubkey,
            "fee_alert_low":  fee_low,
            "fee_alert_high": fee_high,
            "price_alerts":   price_alerts,
            "alerts_enabled": bool(enabled),
            "updated_at":     updated_at,
        }

    def update_preferences(self, pubkey: str, updates: dict) -> dict:
        """Upsert preferences for *pubkey*.

        Only recognised keys are applied; unknown keys are silently ignored.
        Returns the full updated preferences dict.
        """
        valid, err = self.validate_preferences(updates)
        if not valid:
            raise ValueError(err)

        current = self.get_preferences(pubkey)

        fee_low  = int(updates.get("fee_alert_low",  current["fee_alert_low"]))
        fee_high = int(updates.get("fee_alert_high", current["fee_alert_high"]))
        enabled  = int(bool(updates.get("alerts_enabled", current["alerts_enabled"])))
        now      = int(time.time())

        conn = get_conn()
        ph   = "%s" if _is_postgres() else "?"

        if _is_postgres():
            conn.execute(
                """
                INSERT INTO user_preferences
                    (pubkey, fee_alert_low, fee_alert_high, price_alerts, alerts_enabled, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (pubkey) DO UPDATE SET
                    fee_alert_low  = EXCLUDED.fee_alert_low,
                    fee_alert_high = EXCLUDED.fee_alert_high,
                    alerts_enabled = EXCLUDED.alerts_enabled,
                    updated_at     = EXCLUDED.updated_at
                """,
                (
                    pubkey,
                    fee_low,
                    fee_high,
                    json.dumps(current["price_alerts"]),
                    enabled,
                    now,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO user_preferences
                    (pubkey, fee_alert_low, fee_alert_high, price_alerts, alerts_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(pubkey) DO UPDATE SET
                    fee_alert_low  = excluded.fee_alert_low,
                    fee_alert_high = excluded.fee_alert_high,
                    alerts_enabled = excluded.alerts_enabled,
                    updated_at     = excluded.updated_at
                """,
                (
                    pubkey,
                    fee_low,
                    fee_high,
                    json.dumps(current["price_alerts"]),
                    enabled,
                    now,
                ),
            )
        conn.commit()
        return self.get_preferences(pubkey)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_preferences(self, data: dict) -> tuple[bool, str]:
        """Validate preference update payload.

        Returns (True, "") on success or (False, "<reason>") on failure.
        """
        if "fee_alert_low" in data:
            val = data["fee_alert_low"]
            if not isinstance(val, (int, float)) or val != int(val):
                return False, "fee_alert_low must be an integer"
            if not (_FEE_MIN <= int(val) <= _FEE_MAX):
                return False, f"fee_alert_low must be between {_FEE_MIN} and {_FEE_MAX}"

        if "fee_alert_high" in data:
            val = data["fee_alert_high"]
            if not isinstance(val, (int, float)) or val != int(val):
                return False, "fee_alert_high must be an integer"
            if not (_FEE_MIN <= int(val) <= _FEE_MAX):
                return False, f"fee_alert_high must be between {_FEE_MIN} and {_FEE_MAX}"

        low  = int(data.get("fee_alert_low",  _DEFAULTS["fee_alert_low"]))
        high = int(data.get("fee_alert_high", _DEFAULTS["fee_alert_high"]))
        if "fee_alert_low" in data and "fee_alert_high" in data:
            if low >= high:
                return False, "fee_alert_low must be less than fee_alert_high"

        if "alerts_enabled" in data:
            if not isinstance(data["alerts_enabled"], bool):
                return False, "alerts_enabled must be a boolean"

        return True, ""

    # ------------------------------------------------------------------
    # Price alert management
    # ------------------------------------------------------------------

    def add_price_alert(
        self, pubkey: str, price_usd: float, direction: str
    ) -> dict:
        """Append a new price alert for *pubkey*.

        Args:
            price_usd:  Target price in USD (must be positive).
            direction:  "above" — trigger when price rises above target;
                        "below" — trigger when price falls below target.

        Returns the newly created alert dict.
        Raises ValueError for invalid inputs or when the alert cap is reached.
        """
        if not isinstance(price_usd, (int, float)) or price_usd <= 0:
            raise ValueError("price_usd must be a positive number")
        if direction not in ("above", "below"):
            raise ValueError('direction must be "above" or "below"')

        prefs = self.get_preferences(pubkey)
        alerts: list = prefs["price_alerts"]

        if len(alerts) >= _MAX_PRICE_ALERTS:
            raise ValueError(
                f"Maximum of {_MAX_PRICE_ALERTS} price alerts allowed. "
                "Remove an existing alert before adding a new one."
            )

        new_alert = {
            "id":         str(uuid.uuid4()),
            "price_usd":  float(price_usd),
            "direction":  direction,
            "created_at": int(time.time()),
            "triggered":  False,
        }
        alerts.append(new_alert)
        self._save_alerts(pubkey, alerts)
        return new_alert

    def remove_price_alert(self, pubkey: str, alert_id: str) -> dict:
        """Remove the alert with the given *alert_id*.

        Returns the removed alert dict.
        Raises KeyError if the alert is not found.
        """
        if not alert_id or not isinstance(alert_id, str):
            raise ValueError("alert_id must be a non-empty string")

        prefs  = self.get_preferences(pubkey)
        alerts = prefs["price_alerts"]

        target = next((a for a in alerts if a.get("id") == alert_id), None)
        if target is None:
            raise KeyError(f"Alert {alert_id!r} not found for this user")

        updated = [a for a in alerts if a.get("id") != alert_id]
        self._save_alerts(pubkey, updated)
        return target

    def get_triggered_alerts(self, pubkey: str, current_price: float) -> list:
        """Return the list of price alerts that have triggered at *current_price*.

        An alert triggers when:
          - direction == "above" and current_price >= alert.price_usd
          - direction == "below" and current_price <= alert.price_usd

        Triggered alerts are marked with triggered=True in the database.
        """
        if not isinstance(current_price, (int, float)) or current_price <= 0:
            return []

        prefs   = self.get_preferences(pubkey)
        alerts  = prefs["price_alerts"]
        fired   = []
        changed = False

        for alert in alerts:
            if alert.get("triggered"):
                continue
            direction = alert.get("direction")
            threshold = alert.get("price_usd", 0)

            hit = (
                (direction == "above" and current_price >= threshold)
                or (direction == "below" and current_price <= threshold)
            )
            if hit:
                alert["triggered"]    = True
                alert["triggered_at"] = int(time.time())
                fired.append(alert)
                changed = True

        if changed:
            self._save_alerts(pubkey, alerts)

        return fired

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_alerts(self, pubkey: str, alerts: list) -> None:
        """Persist the price_alerts list for *pubkey*."""
        now  = int(time.time())
        conn = get_conn()
        ph   = "%s" if _is_postgres() else "?"

        if _is_postgres():
            conn.execute(
                """
                INSERT INTO user_preferences
                    (pubkey, fee_alert_low, fee_alert_high, price_alerts, alerts_enabled, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (pubkey) DO UPDATE SET
                    price_alerts = EXCLUDED.price_alerts,
                    updated_at   = EXCLUDED.updated_at
                """,
                (pubkey, _DEFAULTS["fee_alert_low"], _DEFAULTS["fee_alert_high"],
                 json.dumps(alerts), 1, now),
            )
        else:
            conn.execute(
                """
                INSERT INTO user_preferences
                    (pubkey, fee_alert_low, fee_alert_high, price_alerts, alerts_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(pubkey) DO UPDATE SET
                    price_alerts = excluded.price_alerts,
                    updated_at   = excluded.updated_at
                """,
                (pubkey, _DEFAULTS["fee_alert_low"], _DEFAULTS["fee_alert_high"],
                 json.dumps(alerts), 1, now),
            )
        conn.commit()
