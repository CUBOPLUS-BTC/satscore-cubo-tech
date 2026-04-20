import pytest

from app.pension.calculator import PensionCalculator


def _linear_history(days: int, start: float, end: float) -> list[list[float]]:
    ms_per_day = 86_400_000
    return [
        [i * ms_per_day, start + (end - start) * i / max(days - 1, 1)]
        for i in range(days)
    ]


class _FakeCoinGecko:
    def __init__(self, price, history):
        self._price = price
        self._history = history

    def get_price(self):
        return self._price

    def get_historical_prices(self, days: int = 90):
        return self._history


@pytest.fixture
def calc():
    c = PensionCalculator()
    c.coingecko = _FakeCoinGecko(50000.0, _linear_history(365, 30000.0, 50000.0))
    return c


class TestProject:
    def test_rejects_zero_monthly(self, calc):
        with pytest.raises(ValueError):
            calc.project(0, 10)

    def test_rejects_negative_years(self, calc):
        with pytest.raises(ValueError):
            calc.project(100, 0)

    def test_rejects_inf_monthly(self, calc):
        with pytest.raises(ValueError):
            calc.project(float("inf"), 10)

    def test_monthly_breakdown_length(self, calc):
        result = calc.project(100, 5)
        assert len(result.monthly_breakdown) == 60
        assert len(result.monthly_data) == 60

    def test_total_invested_matches(self, calc):
        result = calc.project(200, 3)
        assert result.total_invested_usd == 200 * 36

    def test_final_value_monotonic_increase(self, calc):
        result = calc.project(100, 5)
        values = [row["value_usd"] for row in result.monthly_breakdown]
        # Projected growth + DCA should keep total value monotonically non-decreasing.
        assert all(later >= earlier for earlier, later in zip(values, values[1:]))

    def test_zero_price_raises(self, calc):
        calc.coingecko = _FakeCoinGecko(0.0, _linear_history(365, 30000, 40000))
        with pytest.raises(ValueError):
            calc.project(100, 5)


class TestCagr:
    def test_growing_history(self, calc):
        rate = calc._calc_cagr(_linear_history(365, 100, 200))
        # ~100% over a year in roughly-linear case.
        assert 0.5 < rate < 2.0

    def test_insufficient_history(self, calc):
        with pytest.raises(ValueError):
            calc._calc_cagr(_linear_history(5, 100, 150))

    def test_invalid_history(self, calc):
        # All points share the same timestamp → days_span = 0.
        hist = [[0, 100] for _ in range(60)]
        with pytest.raises(ValueError):
            calc._calc_cagr(hist)
