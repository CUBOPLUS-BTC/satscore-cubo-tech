"""HTTP route handlers for recipients.

Each handler returns ``(body_dict, status_code)`` to match the project
convention used across the other modules.
"""

from __future__ import annotations

from .manager import RecipientsManager
from ..i18n import t

_manager = RecipientsManager()


def handle_list_recipients(pubkey: str) -> tuple[dict, int]:
    """GET /recipients — list recipients for the authenticated user."""
    if not pubkey:
        return {"detail": t("recipients.auth.required")}, 401
    try:
        rows = _manager.list_for_user(pubkey)
        return {"recipients": rows, "total": len(rows)}, 200
    except Exception as exc:
        return {"detail": t("recipients.list.failed", error=str(exc))}, 500


def handle_create_recipient(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /recipients — create a recipient for the authenticated user."""
    if not pubkey:
        return {"detail": t("recipients.auth.required")}, 401
    if not isinstance(body, dict):
        return {"detail": t("recipients.body.invalid")}, 400

    name = body.get("name", "")
    lightning_address = body.get("lightning_address", "")
    country = body.get("country", "SV")
    amount = body.get("default_amount_usd")
    skip = bool(body.get("skip_lnurl_check", False))

    try:
        recipient = _manager.create(
            pubkey=pubkey,
            name=name,
            lightning_address=lightning_address,
            country=country,
            default_amount_usd=amount,
            skip_lnurl_check=skip,
        )
        return {"recipient": recipient, "message": t("recipients.created")}, 201
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("recipients.create.failed", error=str(exc))}, 500


def handle_get_recipient(recipient_id: int, pubkey: str) -> tuple[dict, int]:
    """GET /recipients/:id — fetch a single recipient."""
    if not pubkey:
        return {"detail": t("recipients.auth.required")}, 401
    try:
        return {"recipient": _manager.get(recipient_id, pubkey)}, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except Exception as exc:
        return {"detail": t("recipients.get.failed", error=str(exc))}, 500


def handle_update_recipient(
    recipient_id: int, body: dict, pubkey: str
) -> tuple[dict, int]:
    """PATCH /recipients/:id — partial update."""
    if not pubkey:
        return {"detail": t("recipients.auth.required")}, 401
    if not isinstance(body, dict) or not body:
        return {"detail": t("recipients.body.empty")}, 400
    try:
        updated = _manager.update(recipient_id, pubkey, body)
        return {"recipient": updated, "message": t("recipients.updated")}, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("recipients.update.failed", error=str(exc))}, 500


def handle_delete_recipient(
    recipient_id: int, pubkey: str
) -> tuple[dict, int]:
    """DELETE /recipients/:id — delete a recipient."""
    if not pubkey:
        return {"detail": t("recipients.auth.required")}, 401
    try:
        removed = _manager.delete(recipient_id, pubkey)
        if not removed:
            return {"detail": t("recipients.not_found")}, 404
        return {"message": t("recipients.deleted"), "id": recipient_id}, 200
    except Exception as exc:
        return {"detail": t("recipients.delete.failed", error=str(exc))}, 500
