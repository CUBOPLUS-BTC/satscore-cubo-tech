"""Routes for user preferences and price-alert management."""

from .manager import PreferencesManager

_manager = PreferencesManager()


def handle_get_preferences(pubkey: str) -> tuple[dict, int]:
    """GET /preferences — Return the authenticated user's preferences."""
    if not pubkey:
        return {"detail": "Authentication required"}, 401
    try:
        return _manager.get_preferences(pubkey), 200
    except Exception as exc:
        return {"detail": f"Could not load preferences: {exc}"}, 500


def handle_update_preferences(body: dict, pubkey: str) -> tuple[dict, int]:
    """PATCH /preferences — Update fee thresholds and alert toggle.

    Body (all fields optional):
        fee_alert_low  (int)  : Low fee threshold in sat/vB.
        fee_alert_high (int)  : High fee threshold in sat/vB.
        alerts_enabled (bool) : Master switch for all alerts.
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401
    if not body:
        return {"detail": "Request body must not be empty"}, 400

    # Strip price_alerts from direct PATCH — use dedicated endpoints for that
    updates = {k: v for k, v in body.items()
               if k in ("fee_alert_low", "fee_alert_high", "alerts_enabled")}
    if not updates:
        return {
            "detail": "No valid fields provided. "
                      "Accepted: fee_alert_low, fee_alert_high, alerts_enabled"
        }, 400

    try:
        result = _manager.update_preferences(pubkey, updates)
        return result, 200
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": f"Could not update preferences: {exc}"}, 500


def handle_add_price_alert(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /preferences/alerts — Add a price alert.

    Body:
        price_usd  (float) : Target Bitcoin price in USD.
        direction  (str)   : "above" or "below".
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    price_raw  = body.get("price_usd")
    direction  = body.get("direction", "").strip().lower()

    if price_raw is None:
        return {"detail": "price_usd is required"}, 400
    try:
        price_usd = float(price_raw)
    except (TypeError, ValueError):
        return {"detail": "price_usd must be a number"}, 400

    if not direction:
        return {"detail": "direction is required"}, 400

    try:
        alert = _manager.add_price_alert(pubkey, price_usd, direction)
        return {"alert": alert, "message": "Price alert created"}, 201
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": f"Could not add alert: {exc}"}, 500


def handle_remove_price_alert(body: dict, pubkey: str) -> tuple[dict, int]:
    """DELETE /preferences/alerts — Remove a price alert by ID.

    Body:
        alert_id (str): UUID of the alert to remove.
    """
    if not pubkey:
        return {"detail": "Authentication required"}, 401

    alert_id = body.get("alert_id", "").strip()
    if not alert_id:
        return {"detail": "alert_id is required"}, 400

    try:
        removed = _manager.remove_price_alert(pubkey, alert_id)
        return {"removed": removed, "message": "Price alert removed"}, 200
    except ValueError as exc:
        return {"detail": str(exc)}, 400
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except Exception as exc:
        return {"detail": f"Could not remove alert: {exc}"}, 500
