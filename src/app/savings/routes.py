from .projector import SavingsProjector
from .tracker import SavingsTracker

_projector = SavingsProjector()
_tracker = SavingsTracker()


def handle_projection(body: dict) -> tuple[dict, int]:
    """POST /savings/project — Public, no auth required."""
    try:
        monthly_usd = float(body.get("monthly_usd", 10))
        years = int(body.get("years", 10))

        if monthly_usd <= 0:
            return {"detail": "monthly_usd must be positive"}, 400
        if years < 1 or years > 50:
            return {"detail": "years must be between 1 and 50"}, 400

        result = _projector.project(monthly_usd=monthly_usd, years=years)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_create_goal(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /savings/goal — Requires auth."""
    try:
        monthly_target = float(body.get("monthly_target_usd", 0))
        target_years = int(body.get("target_years", 10))

        if monthly_target <= 0:
            return {"detail": "monthly_target_usd must be positive"}, 400

        result = _tracker.create_goal(pubkey, monthly_target, target_years)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_record_deposit(body: dict, pubkey: str) -> tuple[dict, int]:
    """POST /savings/deposit — Requires auth."""
    try:
        amount_usd = float(body.get("amount_usd", 0))

        if amount_usd <= 0:
            return {"detail": "amount_usd must be positive"}, 400

        result = _tracker.record_deposit(pubkey, amount_usd)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500


def handle_progress(pubkey: str) -> tuple[dict, int]:
    """GET /savings/progress — Requires auth."""
    try:
        result = _tracker.get_progress(pubkey)
        return result, 200
    except Exception as e:
        return {"detail": str(e)}, 500
