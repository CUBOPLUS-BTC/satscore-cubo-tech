"""Achievement system — lightweight gamification layer."""

import time
from ..database import get_conn, _is_postgres

ACHIEVEMENT_DEFS = [
    {
        "id": "first_score",
        "name": "First Check",
        "desc": "Analyzed your first Bitcoin address",
        "xp": 10,
    },
    {
        "id": "first_save",
        "name": "Saver",
        "desc": "Recorded your first savings deposit",
        "xp": 20,
    },
    {
        "id": "first_remittance",
        "name": "Global",
        "desc": "Compared remittance channels",
        "xp": 15,
    },
    {
        "id": "streak_3",
        "name": "Consistent",
        "desc": "3-month savings streak",
        "xp": 50,
    },
    {
        "id": "streak_6",
        "name": "Disciplined",
        "desc": "6-month savings streak",
        "xp": 100,
    },
    {
        "id": "streak_12",
        "name": "Diamond Hands",
        "desc": "12-month savings streak",
        "xp": 200,
    },
    {"id": "score_500", "name": "Rising", "desc": "Bitcoin score above 500", "xp": 30},
    {"id": "score_700", "name": "Strong", "desc": "Bitcoin score above 700", "xp": 75},
    {"id": "saved_100", "name": "Centurion", "desc": "Saved over $100", "xp": 40},
    {"id": "saved_1000", "name": "Stacker", "desc": "Saved over $1,000", "xp": 150},
]

_DEFS_BY_ID = {d["id"]: d for d in ACHIEVEMENT_DEFS}

LEVEL_THRESHOLDS = [0, 25, 75, 150, 300, 500]


class AchievementEngine:
    def check_and_award(
        self, pubkey: str, event_type: str, event_data: dict
    ) -> list[dict]:
        """Check if user earned new achievements. Returns newly awarded list."""
        existing = self._get_existing(pubkey)
        newly_awarded = []

        candidates = self._get_candidates(event_type, event_data)

        for achievement_id in candidates:
            if achievement_id in existing:
                continue
            if achievement_id not in _DEFS_BY_ID:
                continue

            self._award(pubkey, achievement_id)
            newly_awarded.append(_DEFS_BY_ID[achievement_id])

        return newly_awarded

    def get_user_achievements(self, pubkey: str) -> dict:
        """Get all achievements and XP/level for a user."""
        existing = self._get_existing(pubkey)

        achievements = []
        total_xp = 0
        for d in ACHIEVEMENT_DEFS:
            earned = d["id"] in existing
            achievements.append(
                {
                    **d,
                    "earned": earned,
                    "awarded_at": existing.get(d["id"]),
                }
            )
            if earned:
                total_xp += d["xp"]

        level = 0
        for i, threshold in enumerate(LEVEL_THRESHOLDS):
            if total_xp >= threshold:
                level = i + 1

        next_level_xp = (
            LEVEL_THRESHOLDS[level] if level < len(LEVEL_THRESHOLDS) else None
        )

        return {
            "achievements": achievements,
            "total_xp": total_xp,
            "level": level,
            "next_level_xp": next_level_xp,
            "earned_count": len(existing),
            "total_count": len(ACHIEVEMENT_DEFS),
        }

    def _get_candidates(self, event_type: str, data: dict) -> list[str]:
        """Determine which achievements to check based on event type."""
        candidates = []

        if event_type == "score":
            candidates.append("first_score")
            score = data.get("total_score", 0)
            if score >= 500:
                candidates.append("score_500")
            if score >= 700:
                candidates.append("score_700")

        elif event_type == "deposit":
            candidates.append("first_save")
            total_usd = data.get("total_invested_usd", 0)
            if total_usd >= 100:
                candidates.append("saved_100")
            if total_usd >= 1000:
                candidates.append("saved_1000")
            streak = data.get("streak_months", 0)
            if streak >= 3:
                candidates.append("streak_3")
            if streak >= 6:
                candidates.append("streak_6")
            if streak >= 12:
                candidates.append("streak_12")

        elif event_type == "remittance":
            candidates.append("first_remittance")

        return candidates

    def _get_existing(self, pubkey: str) -> dict[str, int]:
        """Get existing achievements for a user. Returns {id: awarded_at}."""
        conn = get_conn()
        ph = "%s" if _is_postgres() else "?"
        rows = conn.execute(
            f"SELECT achievement_id, awarded_at FROM user_achievements WHERE pubkey = {ph}",
            (pubkey,),
        ).fetchall()
        return {
            (r[0] if isinstance(r, tuple) else r["achievement_id"]): (
                r[1] if isinstance(r, tuple) else r["awarded_at"]
            )
            for r in rows
        }

    def _award(self, pubkey: str, achievement_id: str) -> None:
        """Award an achievement to a user."""
        conn = get_conn()
        now = int(time.time())
        if _is_postgres():
            conn.execute(
                "INSERT INTO user_achievements (pubkey, achievement_id, awarded_at) VALUES (%s, %s, %s) ON CONFLICT (pubkey, achievement_id) DO NOTHING",
                (pubkey, achievement_id, now),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO user_achievements (pubkey, achievement_id, awarded_at) VALUES (?, ?, ?)",
                (pubkey, achievement_id, now),
            )
        conn.commit()
