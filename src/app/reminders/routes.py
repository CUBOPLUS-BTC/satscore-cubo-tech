"""HTTP route handlers for remittance reminders."""

from __future__ import annotations

from .manager import RemindersManager
from ..i18n import t

_manager = RemindersManager()


def handle_list_reminders(pubkey: str) -> tuple[dict, int]:
    """GET /reminders — list reminders for the authenticated user."""
    if not pubkey:
        return {"detail": t("reminders.auth.required")}, 401
    try:
        rows = _manager.list_for_user(pubkey)
        return {"reminders": rows, "total": len(rows)}, 200
    except Exception as exc:
        return {"detail": t("reminders.list.failed", error=str(exc))}, 500


def handle_create_reminder(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /reminders — create a reminder for a recipient.

    Body:
        recipient_id  (int, required)
        cadence       (str, default "monthly")   monthly | biweekly | custom
        day_of_month  (int, default 1)           1..28
        hour_local    (int, default 9)           0..23
        timezone      (str, default "America/El_Salvador")
        channels      (list[str], default ["webhook"])
                      webhook | nostr_dm | email
    """
    if not pubkey:
        return {"detail": t("reminders.auth.required")}, 401
    if not isinstance(body, dict):
        return {"detail": t("reminders.body.invalid")}, 400

    recipient_id = body.get("recipient_id")
    if not isinstance(recipient_id, int):
        return {"detail": t("reminders.recipient_id.required")}, 400

    try:
        reminder = _manager.create(
            pubkey=pubkey,
            recipient_id=recipient_id,
            cadence=body.get("cadence", "monthly"),
            day_of_month=body.get("day_of_month", 1),
            hour_local=body.get("hour_local", 9),
            timezone=body.get("timezone", "America/El_Salvador"),
            channels=body.get("channels") or ["webhook"],
        )
        return {"reminder": reminder, "message": t("reminders.created")}, 201
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("reminders.create.failed", error=str(exc))}, 500


def handle_get_reminder(reminder_id: int, pubkey: str) -> tuple[dict, int]:
    """GET /reminders/:id"""
    if not pubkey:
        return {"detail": t("reminders.auth.required")}, 401
    try:
        return {"reminder": _manager.get(reminder_id, pubkey)}, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except Exception as exc:
        return {"detail": t("reminders.get.failed", error=str(exc))}, 500


def handle_update_reminder(
    reminder_id: int, body: dict, pubkey: str
) -> tuple[dict, int]:
    """PATCH /reminders/:id — edit cadence / pause / channels."""
    if not pubkey:
        return {"detail": t("reminders.auth.required")}, 401
    if not isinstance(body, dict) or not body:
        return {"detail": t("reminders.body.empty")}, 400
    try:
        reminder = _manager.update(reminder_id, pubkey, body)
        return {"reminder": reminder, "message": t("reminders.updated")}, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("reminders.update.failed", error=str(exc))}, 500


def handle_delete_reminder(reminder_id: int, pubkey: str) -> tuple[dict, int]:
    """DELETE /reminders/:id"""
    if not pubkey:
        return {"detail": t("reminders.auth.required")}, 401
    try:
        removed = _manager.delete(reminder_id, pubkey)
        if not removed:
            return {"detail": t("reminders.not_found")}, 404
        return {"message": t("reminders.deleted"), "id": reminder_id}, 200
    except Exception as exc:
        return {"detail": t("reminders.delete.failed", error=str(exc))}, 500


def handle_list_reminder_events(
    reminder_id: int, pubkey: str, query: dict
) -> tuple[dict, int]:
    """GET /reminders/:id/events — delivery history."""
    if not pubkey:
        return {"detail": t("reminders.auth.required")}, 401
    try:
        limit_raw = query.get("limit", "50")
        try:
            limit = max(1, min(int(limit_raw), 200))
        except ValueError:
            limit = 50
        events = _manager.list_events(reminder_id, pubkey, limit=limit)
        return {"events": events, "total": len(events)}, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except Exception as exc:
        return {"detail": t("reminders.events.failed", error=str(exc))}, 500
