"""Routes for the Liquid Network module."""

from .engine import LiquidAnalyzer
from ..i18n import t

_analyzer = LiquidAnalyzer()


def handle_liquid_overview(body: dict) -> tuple[dict, int]:
    """GET /liquid/overview — Liquid Network status and metrics."""
    try:
        result = _analyzer.get_network_overview()
        return result, 200
    except Exception as exc:
        return {"detail": t("liquid.overview.failed", error=str(exc))}, 502


def handle_liquid_assets(body: dict) -> tuple[dict, int]:
    """GET /liquid/assets — Key Liquid assets info (L-BTC, USDt)."""
    try:
        result = _analyzer.get_assets_info()
        return result, 200
    except Exception as exc:
        return {"detail": t("liquid.assets.failed", error=str(exc))}, 502


def handle_liquid_compare(body: dict) -> tuple[dict, int]:
    """GET /liquid/compare — On-chain vs Lightning vs Liquid comparison."""
    try:
        result = _analyzer.compare_with_other_layers()
        return result, 200
    except Exception as exc:
        return {"detail": t("liquid.compare.failed", error=str(exc))}, 502


def handle_liquid_peg(body: dict) -> tuple[dict, int]:
    """GET /liquid/peg-info — Peg-in/peg-out process and wallets."""
    try:
        result = _analyzer.get_peg_info()
        return result, 200
    except Exception as exc:
        return {"detail": t("liquid.peg.failed", error=str(exc))}, 502


def handle_liquid_recommend(body: dict, query: dict) -> tuple[dict, int]:
    """POST /liquid/recommend — Recommend best layer (includes Liquid).

    Body or query params:
        amount_usd (float): Payment amount in USD.
        urgency (str): "low" | "medium" | "high" | "instant"
        privacy (str): "normal" | "high" | "confidential"
    """
    amount_raw = body.get("amount_usd") or query.get("amount_usd")
    urgency_raw = body.get("urgency") or query.get("urgency", "medium")
    privacy_raw = body.get("privacy") or query.get("privacy", "normal")

    if amount_raw is None:
        return {"detail": t("liquid.amount.required")}, 400

    try:
        amount_usd = float(amount_raw)
    except (TypeError, ValueError):
        return {"detail": t("liquid.amount.invalid")}, 400

    if amount_usd <= 0:
        return {"detail": t("liquid.amount.positive")}, 400

    urgency = str(urgency_raw).strip().lower()
    if urgency not in ("low", "medium", "high", "instant"):
        return {"detail": t("liquid.urgency.invalid")}, 400

    privacy = str(privacy_raw).strip().lower()
    if privacy not in ("normal", "high", "confidential"):
        return {"detail": t("liquid.privacy.invalid")}, 400

    try:
        result = _analyzer.recommend_layer(amount_usd, urgency, privacy)
        return result, 200
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("liquid.recommend.failed", error=str(exc))}, 502
