from .achievements import AchievementEngine

_engine = AchievementEngine()


def handle_achievements(pubkey: str) -> tuple[dict, int]:
    """GET /achievements — Requires auth."""
    return _engine.get_user_achievements(pubkey), 200
