import pytest

from app.services.price_aggregator import (
    PriceAggregator,
    PriceUnavailableError,
    _median,
)


class TestMedian:
    def test_single_value(self):
        assert _median([42.0]) == 42.0

    def test_odd_length(self):
        assert _median([3.0, 1.0, 2.0]) == 2.0

    def test_even_length_averages(self):
        assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _median([])


class TestGetVerifiedPrice:
    def _patch(self, aggregator, cg_result, kr_result):
        def _cg():
            if isinstance(cg_result, BaseException):
                raise cg_result
            return cg_result

        def _kr():
            if isinstance(kr_result, BaseException):
                raise kr_result
            return kr_result

        aggregator.coingecko.get_price = _cg
        aggregator.kraken.get_price = _kr

    def test_both_sources_success(self):
        agg = PriceAggregator()
        self._patch(agg, 50_000.0, 50_200.0)
        result = agg.get_verified_price()
        assert result["sources_count"] == 2
        assert result["price_usd"] == pytest.approx(50_100.0)
        assert result["has_warning"] is False
        assert result["deviation"] > 0

    def test_single_source_warns(self):
        agg = PriceAggregator()
        self._patch(agg, 50_000.0, RuntimeError("kraken down"))
        result = agg.get_verified_price()
        assert result["sources_count"] == 1
        assert result["has_warning"] is True

    def test_all_sources_fail(self):
        agg = PriceAggregator()
        self._patch(agg, RuntimeError("x"), RuntimeError("y"))
        with pytest.raises(PriceUnavailableError):
            agg.get_verified_price()

    def test_ignores_non_positive_value(self):
        agg = PriceAggregator()
        self._patch(agg, 0.0, 50_000.0)
        result = agg.get_verified_price()
        assert result["sources_count"] == 1
        assert result["price_usd"] == 50_000.0

    def test_ignores_nan(self):
        agg = PriceAggregator()
        self._patch(agg, float("nan"), 50_000.0)
        result = agg.get_verified_price()
        assert result["sources_count"] == 1
