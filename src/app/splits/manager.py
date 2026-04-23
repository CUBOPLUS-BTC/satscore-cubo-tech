"""CRUD for split profiles and rules."""

from __future__ import annotations

import time
from typing import Optional

from ..database import _is_postgres, get_conn
from .schemas import validate_label, validate_percentage, validate_rules_total


class SplitsManager:
    """Persists split profiles and their distribution rules."""

    def __init__(self, recipients_manager) -> None:
        self.recipients = recipients_manager

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------

    def create_profile(self, pubkey: str, label: str) -> dict:
        label = validate_label(label)
        now = int(time.time())
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()

        if _is_postgres():
            cur = conn.cursor()
            cur.execute(
                f"""INSERT INTO split_profiles
                    (pubkey, label, is_active, created_at, updated_at)
                    VALUES ({ph},{ph},1,{ph},{ph}) RETURNING id""",
                (pubkey, label, now, now),
            )
            row = cur.fetchone()
            new_id = row[0] if not hasattr(row, "keys") else row["id"]
            conn.commit()
        else:
            cur = conn.execute(
                f"""INSERT INTO split_profiles
                    (pubkey, label, is_active, created_at, updated_at)
                    VALUES ({ph},{ph},1,{ph},{ph})""",
                (pubkey, label, now, now),
            )
            new_id = cur.lastrowid
            conn.commit()

        return self.get_profile(new_id, pubkey)

    def list_profiles(self, pubkey: str) -> list[dict]:
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        rows = conn.execute(
            f"SELECT * FROM split_profiles WHERE pubkey={ph} ORDER BY created_at DESC",
            (pubkey,),
        ).fetchall()
        profiles = [self._row_to_dict(r) for r in rows]
        for p in profiles:
            p["rules"] = self._rules_for_profile(p["id"])
        return profiles

    def get_profile(self, profile_id: int, pubkey: str) -> dict:
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        row = conn.execute(
            f"SELECT * FROM split_profiles WHERE id={ph} AND pubkey={ph}",
            (profile_id, pubkey),
        ).fetchone()
        if row is None:
            raise KeyError(f"Split profile {profile_id!r} no encontrado")
        profile = self._row_to_dict(row)
        profile["rules"] = self._rules_for_profile(profile_id)
        return profile

    def delete_profile(self, profile_id: int, pubkey: str) -> bool:
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        cur = conn.execute(
            f"DELETE FROM split_profiles WHERE id={ph} AND pubkey={ph}",
            (profile_id, pubkey),
        )
        conn.commit()
        return (cur.rowcount or 0) > 0

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def set_rules(
        self, profile_id: int, pubkey: str, rules: list[dict]
    ) -> list[dict]:
        """Replace all rules for a profile atomically.

        Each rule dict: {recipient_id, percentage, priority?, label?}
        """
        self.get_profile(profile_id, pubkey)  # ownership check

        if not rules:
            raise ValueError("Se requiere al menos una regla")

        clean_rules = []
        for r in rules:
            rid = r.get("recipient_id")
            if not isinstance(rid, int):
                raise ValueError("recipient_id inválido en regla")
            # Verify recipient belongs to this user
            self.recipients.get(rid, pubkey)
            clean_rules.append({
                "recipient_id": rid,
                "percentage": validate_percentage(r.get("percentage")),
                "priority": int(r.get("priority", 0)),
                "label": validate_label(r["label"]) if r.get("label") else None,
            })

        validate_rules_total(clean_rules)

        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        now = int(time.time())

        # Delete old rules
        conn.execute(
            f"DELETE FROM split_rules WHERE profile_id={ph}", (profile_id,)
        )

        # Insert new rules
        for cr in clean_rules:
            conn.execute(
                f"""INSERT INTO split_rules
                    (profile_id, recipient_id, percentage, priority, label, created_at)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph})""",
                (
                    profile_id,
                    cr["recipient_id"],
                    cr["percentage"],
                    cr["priority"],
                    cr["label"],
                    now,
                ),
            )

        # Update profile timestamp
        conn.execute(
            f"UPDATE split_profiles SET updated_at={ph} WHERE id={ph}",
            (now, profile_id),
        )
        conn.commit()

        return self._rules_for_profile(profile_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rules_for_profile(self, profile_id: int) -> list[dict]:
        ph = "%s" if _is_postgres() else "?"
        conn = get_conn()
        rows = conn.execute(
            f"""SELECT sr.*, r.name AS recipient_name,
                       r.lightning_address AS recipient_ln
                FROM split_rules sr
                JOIN recipients r ON r.id = sr.recipient_id
                WHERE sr.profile_id={ph}
                ORDER BY sr.priority ASC""",
            (profile_id,),
        ).fetchall()
        return [self._rule_row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row) -> dict:
        if row is None:
            return {}
        if hasattr(row, "keys"):
            return dict(row)
        cols = [
            "id", "pubkey", "label", "is_active",
            "created_at", "updated_at",
        ]
        return dict(zip(cols, row))

    @staticmethod
    def _rule_row_to_dict(row) -> dict:
        if row is None:
            return {}
        if hasattr(row, "keys"):
            return dict(row)
        cols = [
            "id", "profile_id", "recipient_id", "percentage",
            "priority", "label", "created_at",
            "recipient_name", "recipient_ln",
        ]
        return dict(zip(cols, row))
