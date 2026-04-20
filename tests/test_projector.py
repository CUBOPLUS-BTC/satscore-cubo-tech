import pytest

from app.savings.projector import SavingsProjector


def _linear_history(days: int, start: float, end: float) -> list[list[float]]:
    ms_per_day = 86_400_000
    return [[i * ms_per_day, start + (end - start) * i / max(days - 1, 1)] for i in range(days)]


class _FakeCoinGecko:
    def __init__(self, price: float, history: list):
        self._price = price
        self._history = history

    def get_price(self) -> float:
        return self._price

    def get_historical_prices(self, days: int = 90):
        return self._history


@pytest.fixture
def projector():
    p = SavingsProjector()
    p.coingecko = _FakeCoinGecko(50000.0, _linear_history(365, 30000.0, 50000.0))
    return p


class TestInputValidation:
    def test_rejects_zero_monthly(self, projector):
        with pytest.raises(ValueError):
            projector.project(0, years=5)

    def test_rejects_nan_monthly(self, projector):
        with pytest.raises(ValueError):
            projector.project(float("nan"), years=5)

    def test_rejects_bool_monthly(self, projector):
        with pytest.raises(ValueError):
            projector.project(True, years=5)  # type: ignore[arg-type]

    def test_rejects_zero_years(self, projector):
        with pytest.raises(ValueError):
            projector.project(100, years=0)


class TestProjection:
    def test_returns_three_scenarios(self, projector):
        result = projector.project(100, years=5)
        names = [s["name"] for s in result["scenarios"]]
        assert names == ["conservative", "moderate", "optimistic"]

    def test_totals_consistent(self, projector):
        result = projector.project(100, years=5)
        assert result["total_invested"] == 100 * 12 * 5
        for s in result["scenarios"]:
            assert s["total_invested"] == result["total_invested"]
            assert s["projected_value"] >= s["total_invested"] * 0.5

    def test_conservative_floor_applied(self, projector):
        # Flat history produces 0% annual return; conservative must hit 5% floor.
        projector.coingecko = _FakeCoinGecko(
            30000.0, _linear_history(365, 30000.0, 30000.0)
        )
        result = projector.project(100, years=5)
        conservative = next(s for s in result["scenarios"] if s["name"] == "conservative")
        assert conservative["annual_return_pct"] == 5.0

    def test_monthly_data_buckets_for_short_horizon(self, projector):
        result = projector.project(100, years=3)
        months = [m["month"] for m in result["monthly_data"]]
        # years <= 5 → bucketed every 6 months.
        assert months == [6, 12, 18, 24, 30, 36]

    def test_monthly_data_buckets_for_long_horizon(self, projector):
        result = projector.project(100, years=10)
        months = [m["month"] for m in result["monthly_data"]]
        assert months == [12, 24, 36, 48, 60, 72, 84, 96, 108, 120]

    def test_insufficient_history_raises(self, projector):
        projector.coingecko = _FakeCoinGecko(
            30000.0, _linear_history(10, 30000.0, 31000.0)
        )
        with pytest.raises(ValueError):
            projector.project(100, years=5)

    def test_zero_current_price_raises(self, projector):
        projector.coingecko = _FakeCoinGecko(
            0.0, _linear_history(365, 30000.0, 50000.0)
        )
        with pytest.raises(ValueError):
            projector.project(100, years=5)
