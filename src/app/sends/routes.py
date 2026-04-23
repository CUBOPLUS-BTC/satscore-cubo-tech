"""Route handlers for /sends endpoints."""

from __future__ import annotations

from .executor import SendExecutor
from ..i18n import t


def handle_execute_send(
    body: dict,
    pubkey: str,
    executor: SendExecutor,
) -> tuple[dict, int]:
    """POST /sends/execute

    Body:
        recipient_id (int, required)
        amount_usd   (float, required)
        comment      (str, optional, max 144 chars)
    """
    if not pubkey:
        return {"detail": t("sends.auth.required")}, 401
    if not isinstance(body, dict):
        return {"detail": t("sends.body.invalid")}, 400

    recipient_id = body.get("recipient_id")
    amount_usd = body.get("amount_usd")
    comment = body.get("comment")

    if not isinstance(recipient_id, int):
        return {"detail": t("sends.recipient_id.required")}, 400
    try:
        amount_usd = float(amount_usd)
    except (TypeError, ValueError):
        return {"detail": t("sends.amount.required")}, 400

    try:
        result = executor.build_invoice(
            recipient_id=recipient_id,
            pubkey=pubkey,
            amount_usd=amount_usd,
            comment=comment if isinstance(comment, str) else None,
        )
        return result, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("sends.invoice.failed", error=str(exc))}, 500
