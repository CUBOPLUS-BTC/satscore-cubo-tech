"""HTTP route handlers for the webhook management API.

All handlers follow the ``(body: dict, pubkey: str) -> tuple[dict, int]``
convention used throughout the Magma codebase.
"""

from __future__ import annotations

from typing import Optional

from .manager import WebhookManager, SUPPORTED_EVENTS
from .dispatcher import WebhookDispatcher


def handle_webhook_subscribe(
    body: dict,
    pubkey: str,
    manager: WebhookManager,
) -> tuple[dict, int]:
    """POST /webhooks/subscribe

    Body fields
    -----------
    url : str
        Callback URL (HTTPS recommended).
    events : list[str]
        One or more event type strings.
    secret : str, optional
        Custom signing secret; generated automatically if omitted.
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    url = (body.get("url") or "").strip()
    events = body.get("events") or []
    secret = body.get("secret")

    if not url:
        return {"detail": "url is required"}, 400
    if not events or not isinstance(events, list):
        return {"detail": "events must be a non-empty list"}, 400

    invalid = [e for e in events if e not in SUPPORTED_EVENTS]
    if invalid:
        return {
            "detail": f"Unsupported event type(s): {invalid}",
            "supported": sorted(SUPPORTED_EVENTS),
        }, 400

    try:
        sub = manager.subscribe(pubkey, url, events, secret)
    except ValueError as exc:
        return {"detail": str(exc)}, 400
    except Exception as exc:
        return {"detail": f"Failed to create subscription: {exc}"}, 500

    # Do not expose the secret in subsequent responses; only show it here.
    return {
        "id": sub["id"],
        "url": sub["url"],
        "events": sub["events"],
        "active": sub["active"],
        "created_at": sub["created_at"],
        "secret": sub["secret"],
        "message": "Subscription created. Store the secret — it will not be shown again.",
    }, 201


def handle_webhook_unsubscribe(
    body: dict,
    pubkey: str,
    manager: WebhookManager,
) -> tuple[dict, int]:
    """POST /webhooks/unsubscribe

    Body fields
    -----------
    subscription_id : str
        ID of the subscription to remove.
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    sub_id = (body.get("subscription_id") or "").strip()
    if not sub_id:
        return {"detail": "subscription_id is required"}, 400

    try:
        deleted = manager.unsubscribe(pubkey, sub_id)
    except PermissionError as exc:
        return {"detail": str(exc)}, 403
    except Exception as exc:
        return {"detail": f"Failed to remove subscription: {exc}"}, 500

    if not deleted:
        return {"detail": "Subscription not found"}, 404

    return {"message": "Subscription deleted", "id": sub_id}, 200


def handle_webhook_list(
    pubkey: str,
    manager: WebhookManager,
) -> tuple[dict, int]:
    """GET /webhooks

    Returns all subscriptions for the authenticated user.
    Secrets are **not** included in list responses.
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    try:
        subs = manager.list_subscriptions(pubkey)
    except Exception as exc:
        return {"detail": f"Failed to list subscriptions: {exc}"}, 500

    # Strip secrets from list view.
    safe_subs = [
        {k: v for k, v in s.items() if k != "secret"}
        for s in subs
    ]

    return {
        "subscriptions": safe_subs,
        "count": len(safe_subs),
        "supported_events": sorted(SUPPORTED_EVENTS),
    }, 200


def handle_webhook_update(
    body: dict,
    pubkey: str,
    sub_id: str,
    manager: WebhookManager,
) -> tuple[dict, int]:
    """PATCH /webhooks/<sub_id>

    Body fields (all optional)
    --------------------------
    url : str
    events : list[str]
    active : bool
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401
    if not sub_id:
        return {"detail": "subscription_id is required"}, 400

    updates = {}
    if "url" in body:
        updates["url"] = body["url"]
    if "events" in body:
        updates["events"] = body["events"]
    if "active" in body:
        updates["active"] = body["active"]

    if not updates:
        return {"detail": "No valid fields to update (url, events, active)"}, 400

    try:
        updated = manager.update_subscription(pubkey, sub_id, updates)
    except PermissionError as exc:
        return {"detail": str(exc)}, 403
    except KeyError:
        return {"detail": "Subscription not found"}, 404
    except ValueError as exc:
        return {"detail": str(exc)}, 400
    except Exception as exc:
        return {"detail": f"Update failed: {exc}"}, 500

    safe = {k: v for k, v in updated.items() if k != "secret"}
    return safe, 200


def handle_webhook_test(
    body: dict,
    pubkey: str,
    manager: WebhookManager,
    dispatcher: WebhookDispatcher,
) -> tuple[dict, int]:
    """POST /webhooks/test

    Send a test delivery to a specific subscription.

    Body fields
    -----------
    subscription_id : str
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    sub_id = (body.get("subscription_id") or "").strip()
    if not sub_id:
        return {"detail": "subscription_id is required"}, 400

    subs = manager.list_subscriptions(pubkey)
    target = next((s for s in subs if s["id"] == sub_id), None)
    if target is None:
        return {"detail": "Subscription not found"}, 404

    success = dispatcher.send_test(target)
    if success:
        return {
            "message": "Test webhook delivered successfully.",
            "url": target["url"],
        }, 200
    else:
        return {
            "message": "Test webhook delivery failed.",
            "url": target["url"],
            "hint": "Check that the URL is reachable and returns a 2xx status.",
        }, 502


def handle_webhook_delivery_log(
    pubkey: str,
    sub_id: str,
    query: dict,
    manager: WebhookManager,
    dispatcher: WebhookDispatcher,
) -> tuple[dict, int]:
    """GET /webhooks/<sub_id>/log

    Returns recent delivery attempts for a subscription.
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    subs = manager.list_subscriptions(pubkey)
    target = next((s for s in subs if s["id"] == sub_id), None)
    if target is None:
        return {"detail": "Subscription not found"}, 404

    try:
        limit = min(int(query.get("limit", 20)), 100)
    except (TypeError, ValueError):
        limit = 20

    log = dispatcher.get_delivery_log(sub_id, limit=limit)
    return {
        "subscription_id": sub_id,
        "log": log,
        "count": len(log),
    }, 200
