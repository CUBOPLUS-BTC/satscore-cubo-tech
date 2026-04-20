from datetime import datetime, timezone

from app.savings.tracker import SavingsTracker


def _ts(year: int, month: int, day: int = 15) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())


def _now(year: int, month: int, day: int = 15) -> float:
    return datetime(year, month, day, 12, 0, tzinfo=timezone.utc).timestamp()


class TestCalculateStreak:
    def setup_method(self):
        self.tracker = SavingsTracker.__new__(SavingsTracker)

    def test_empty(self):
        assert self.tracker._calculate_streak([]) == 0

    def test_single_deposit_current_month(self):
        deposits = [(100, 30000, 0.003, _ts(2026, 4))]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 1

    def test_consecutive_calendar_months(self):
        deposits = [
            (100, 30000, 0.003, _ts(2026, 4, 5)),
            (100, 30000, 0.003, _ts(2026, 3, 28)),
            (100, 30000, 0.003, _ts(2026, 2, 14)),
        ]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 3

    def test_gap_breaks_streak(self):
        deposits = [
            (100, 30000, 0.003, _ts(2026, 4, 5)),
            (100, 30000, 0.003, _ts(2026, 2, 5)),  # skips March
        ]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 1

    def test_no_deposit_this_month_is_zero(self):
        deposits = [(100, 30000, 0.003, _ts(2026, 3, 20))]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 0

    def test_year_boundary(self):
        # Dec -> Jan must be counted as consecutive.
        deposits = [
            (100, 30000, 0.003, _ts(2026, 1, 5)),
            (100, 30000, 0.003, _ts(2025, 12, 20)),
        ]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 1)) == 2

    def test_multiple_deposits_same_month_counts_once(self):
        deposits = [
            (100, 30000, 0.003, _ts(2026, 4, 2)),
            (100, 30000, 0.003, _ts(2026, 4, 18)),
            (100, 30000, 0.003, _ts(2026, 4, 29)),
        ]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 1

    def test_end_of_month_deposit_counts(self):
        # The old 30-day-bucket implementation misassigned day 31.
        deposits = [
            (100, 30000, 0.003, _ts(2026, 3, 31)),
            (100, 30000, 0.003, _ts(2026, 4, 1)),
        ]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4, 1)) == 2

    def test_dict_rows_supported(self):
        deposits = [{"amount_usd": 100, "btc_price": 30000, "btc_amount": 0.003, "created_at": _ts(2026, 4, 1)}]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 1

    def test_invalid_timestamp_ignored(self):
        deposits = [
            (100, 30000, 0.003, "not-a-ts"),
            (100, 30000, 0.003, _ts(2026, 4, 1)),
        ]
        assert self.tracker._calculate_streak(deposits, now=_now(2026, 4)) == 1
