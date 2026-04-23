"""Route handlers for /splits endpoints."""

from __future__ import annotations

from .manager import SplitsManager
from .engine import SplitEngine
from ..i18n import t


def handle_list_profiles(
    pubkey: str, splits: SplitsManager
) -> tuple[dict, int]:
    """GET /splits"""
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401
    profiles = splits.list_profiles(pubkey)
    return {"profiles": profiles, "count": len(profiles)}, 200


def handle_create_profile(
    body: dict, pubkey: str, splits: SplitsManager
) -> tuple[dict, int]:
    """POST /splits"""
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401
    label = body.get("label")
    if not label:
        return {"detail": t("splits.label.required")}, 400
    try:
        profile = splits.create_profile(pubkey, label)
        return profile, 201
    except ValueError as exc:
        return {"detail": str(exc)}, 422


def handle_get_profile(
    profile_id: int, pubkey: str, splits: SplitsManager
) -> tuple[dict, int]:
    """GET /splits/:id"""
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401
    try:
        return splits.get_profile(profile_id, pubkey), 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404


def handle_delete_profile(
    profile_id: int, pubkey: str, splits: SplitsManager
) -> tuple[dict, int]:
    """DELETE /splits/:id"""
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401
    deleted = splits.delete_profile(profile_id, pubkey)
    if not deleted:
        return {"detail": t("splits.profile.not_found")}, 404
    return {"deleted": True}, 200


def handle_set_rules(
    profile_id: int, body: dict, pubkey: str, splits: SplitsManager
) -> tuple[dict, int]:
    """PUT /splits/:id/rules"""
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401
    rules = body.get("rules")
    if not isinstance(rules, list):
        return {"detail": t("splits.rules.required")}, 400
    try:
        result = splits.set_rules(profile_id, pubkey, rules)
        return {"rules": result}, 200
    except KeyError as exc:
        return {"detail": str(exc)}, 404
    except ValueError as exc:
        return {"detail": str(exc)}, 422


def handle_build_split(
    body: dict, pubkey: str, engine: SplitEngine
) -> tuple[dict, int]:
    """POST /splits/build

    Body: { profile_id: int, amount_usd: float, comment?: string }

    Returns multiple invoices — one per split rule. The sender pays
    each invoice directly from their wallet. Magma never custodies.
    """
    if not pubkey:
        return {"detail": t("error.unauthorized")}, 401

    profile_id = body.get("profile_id")
    amount_usd = body.get("amount_usd")
    comment = body.get("comment")

    if not isinstance(profile_id, int):
        return {"detail": t("splits.profile_id.required")}, 400
    try:
        amount_usd = float(amount_usd)
    except (TypeError, ValueError):
        return {"detail": t("splits.amount.required")}, 400

    try:
        result = engine.build_split(
            profile_id=profile_id,
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
        return {"detail": t("splits.build.failed", error=str(exc))}, 500
