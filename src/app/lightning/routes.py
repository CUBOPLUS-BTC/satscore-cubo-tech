"""Routes for the Lightning Network stats module."""

from .stats import LightningAnalyzer
from ..i18n import t

_analyzer = LightningAnalyzer()


def handle_lightning_overview(body: dict) -> tuple[dict, int]:
    """GET /lightning/overview — Network size and capacity snapshot."""
    try:
        result = _analyzer.get_network_overview()
        return result, 200
    except Exception as exc:
        return {"detail": t("lightning.overview.failed", error=str(exc))}, 502


def handle_lightning_compare(body: dict) -> tuple[dict, int]:
    """GET /lightning/compare — On-chain vs Lightning tradeoff comparison."""
    try:
        comparison = _analyzer.compare_layers()
        routing    = _analyzer.get_routing_analysis()
        adoption   = _analyzer.get_adoption_metrics()
        return {
            "comparison":  comparison,
            "routing":     routing,
            "adoption":    adoption,
        }, 200
    except Exception as exc:
        return {"detail": t("lightning.compare.failed", error=str(exc))}, 502


def handle_lightning_recommend(body: dict, query: dict) -> tuple[dict, int]:
    """POST /lightning/recommend — Which layer should I use?

    Body or query params:
        amount_usd (float) : Payment amount in USD.
        urgency    (str)   : "low" | "medium" | "high" | "instant"
    """
    # Accept params from both body (POST) and query string (GET fallback)
    amount_raw  = body.get("amount_usd") or query.get("amount_usd")
    urgency_raw = body.get("urgency")    or query.get("urgency", "medium")

    if amount_raw is None:
        return {
            "detail": t("lightning.amount.required")
        }, 400

    try:
        amount_usd = float(amount_raw)
    except (TypeError, ValueError):
        return {"detail": t("lightning.amount.invalid")}, 400

    if amount_usd <= 0:
        return {"detail": t("lightning.amount.positive")}, 400

    urgency = str(urgency_raw).strip().lower()
    if urgency not in ("low", "medium", "high", "instant"):
        return {
            "detail": t("lightning.urgency.invalid")
        }, 400

    try:
        result = _analyzer.recommend_layer(amount_usd, urgency)
        return result, 200
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except Exception as exc:
        return {"detail": t("lightning.recommend.failed", error=str(exc))}, 502
