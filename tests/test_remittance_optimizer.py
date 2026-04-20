import pytest

from app.remittance.optimizer import REFERENCE_CHANNELS, RemittanceOptimizer


class _Static:
    def __init__(self, value):
        self._value = value

    def __call__(self, *a, **kw):
        return self._value


@pytest.fixture
def optimizer():
    opt = RemittanceOptimizer()

    class _CG:
        def get_price(self):
            return 50000.0

    class _MP:
        def get_recommended_fees(self):
            return {"halfHourFee": 20, "economyFee": 5}

    class _Wise:
        def __init__(self):
            self.response = None

        def get_comparison(self, amount_usd):
            return self.response

    class _FT:
        def get_best_send_time(self):
            return {
                "best_time": "Weekends",
                "current_fee_sat_vb": 20,
                "estimated_low_fee_sat_vb": 10,
            }

    opt.coingecko = _CG()
    opt.mempool = _MP()
    opt.wise = _Wise()
    opt.fee_tracker = _FT()
    return opt


class TestCompare:
    def test_returns_all_reference_channels_plus_lightning(self, optimizer):
        result = optimizer.compare(100, "monthly")
        names = [c.name for c in result.channels]
        for ref_name, _, _ in REFERENCE_CHANNELS:
            assert ref_name in names
        assert "Lightning Network" in names

    def test_lightning_is_recommended(self, optimizer):
        result = optimizer.compare(100)
        ln = next(c for c in result.channels if c.name == "Lightning Network")
        assert ln.is_recommended is True
        assert ln.is_live is True

    def test_worst_excludes_lightning(self, optimizer):
        result = optimizer.compare(100)
        # Worst is the reference with the highest fee % (Western Union @ 7.5%).
        assert result.worst_channel_name == "Western Union"
        assert result.savings_vs_worst > 0

    def test_annual_savings_frequency_multiplier(self, optimizer):
        monthly = optimizer.compare(100, "monthly").annual_savings
        weekly = optimizer.compare(100, "weekly").annual_savings
        assert weekly == pytest.approx(monthly * 4)

    def test_unknown_frequency_falls_back_to_monthly(self, optimizer):
        monthly = optimizer.compare(100, "monthly").annual_savings
        other = optimizer.compare(100, "nonsense").annual_savings
        assert other == pytest.approx(monthly)

    def test_wise_live_overrides_reference(self, optimizer):
        optimizer.wise.response = [
            {
                "name": "Remitly",
                "fee_percent": 1.0,
                "fee_usd": 1.0,
                "amount_received": 99.0,
                "estimated_time": "Minutes",
            }
        ]
        result = optimizer.compare(100)
        remitly = next(c for c in result.channels if c.name == "Remitly")
        assert remitly.is_live is True
        assert remitly.fee_usd == 1.0

    def test_extra_wise_providers_appended(self, optimizer):
        optimizer.wise.response = [
            {
                "name": "Wise",
                "fee_percent": 0.5,
                "fee_usd": 0.5,
                "amount_received": 99.5,
                "estimated_time": "Hours",
            }
        ]
        names = [c.name for c in optimizer.compare(100).channels]
        assert "Wise" in names

    def test_zero_price_does_not_crash(self, optimizer):
        optimizer.coingecko.get_price = lambda: 0.0
        result = optimizer.compare(100)
        # Lightning still present with floor on-chain fee fallback.
        ln = next(c for c in result.channels if c.name == "Lightning Network")
        assert ln.fee_usd > 0

    def test_send_time_savings_percent(self, optimizer):
        result = optimizer.compare(100)
        assert result.best_time is not None
        # (20 - 10) / 20 * 100 = 50
        assert result.best_time.savings_percent == pytest.approx(50.0)
