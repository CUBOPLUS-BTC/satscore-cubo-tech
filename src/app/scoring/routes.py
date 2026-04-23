"""Routes for the Bitcoin address scoring module."""

from .analyzer import AddressAnalyzer, validate_bitcoin_address
from ..i18n import t

_analyzer = AddressAnalyzer()


def handle_score(body: dict) -> tuple[dict, int]:
    """POST /score — Full address analysis.

    Body:
        address (str): Bitcoin address to analyse.

    Returns the complete analysis dict produced by AddressAnalyzer.analyze().
    """
    address = body.get("address", "").strip()
    if not address:
        return {"detail": t("scoring.address.required")}, 400

    if not validate_bitcoin_address(address):
        return {"detail": t("scoring.address.invalid", address=address)}, 422

    try:
        result = _analyzer.analyze(address)
        return result, 200
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except RuntimeError as exc:
        return {"detail": str(exc)}, 502
    except Exception as exc:
        return {"detail": t("scoring.analysis.failed", error=str(exc))}, 500


def handle_score_summary(query: dict) -> tuple[dict, int]:
    """GET /score/summary?address=<addr> — Lightweight score summary.

    Returns only total_score, grade, and recommendations to keep
    the response small for dashboard widgets.
    """
    address = query.get("address", "").strip()
    if not address:
        return {"detail": t("scoring.address_query.required")}, 400

    if not validate_bitcoin_address(address):
        return {"detail": t("scoring.address.invalid", address=address)}, 422

    try:
        result = _analyzer.analyze(address)
        return {
            "address":         result["address"],
            "total_score":     result["total_score"],
            "grade":           result["grade"],
            "activity_score":  result["activity_score"],
            "hodl_score":      result["hodl_score"],
            "diversity_score": result["diversity_score"],
            "recommendations": result["recommendations"],
            "analyzed_at":     result["analyzed_at"],
        }, 200
    except ValueError as exc:
        return {"detail": str(exc)}, 422
    except RuntimeError as exc:
        return {"detail": str(exc)}, 502
    except Exception as exc:
        return {"detail": t("scoring.analysis.failed", error=str(exc))}, 500
