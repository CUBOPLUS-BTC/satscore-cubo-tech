from app.gamification.achievements import AchievementEngine


class TestGetCandidates:
    def setup_method(self):
        self.engine = AchievementEngine()

    def test_unknown_event_returns_empty(self):
        assert self.engine._get_candidates("unknown", {}) == []

    def test_score_low(self):
        assert self.engine._get_candidates("score", {"total_score": 100}) == [
            "first_score"
        ]

    def test_score_500(self):
        got = self.engine._get_candidates("score", {"total_score": 500})
        assert "score_500" in got
        assert "score_700" not in got

    def test_score_700_includes_500(self):
        got = self.engine._get_candidates("score", {"total_score": 800})
        assert {"first_score", "score_500", "score_700"}.issubset(got)

    def test_deposit_first(self):
        assert self.engine._get_candidates("deposit", {}) == ["first_save"]

    def test_deposit_with_streak_and_amount(self):
        got = self.engine._get_candidates(
            "deposit", {"total_invested_usd": 1500, "streak_months": 6}
        )
        assert {
            "first_save",
            "saved_100",
            "saved_1000",
            "streak_3",
            "streak_6",
        }.issubset(got)
        assert "streak_12" not in got

    def test_remittance(self):
        assert self.engine._get_candidates("remittance", {}) == ["first_remittance"]

    def test_missing_event_data_defaults_to_zero(self):
        assert self.engine._get_candidates("score", {}) == ["first_score"]
        assert self.engine._get_candidates("deposit", {}) == ["first_save"]
