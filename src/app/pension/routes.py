from .calculator import PensionCalculator
from ..i18n import t

_calculator = PensionCalculator()


def handle_projection(body: dict) -> tuple[dict, int]:
    monthly = body.get("monthly_saving_usd", 0)
    years = body.get("years", 0)

    if not monthly or monthly <= 0:
        return {"detail": t("error.amount.negative")}, 400
    if not years or years <= 0 or years > 50:
        return {"detail": t("error.validation.range", field="years", min=1, max=50)}, 400

    try:
        projection = _calculator.project(float(monthly), int(years))
        return projection.to_dict(), 200
    except Exception as e:
        return {"detail": str(e)}, 500
