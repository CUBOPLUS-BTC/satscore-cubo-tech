"""Game completion handler for Magma Miner.

Awards XP based on game performance and records the run.
"""

from __future__ import annotations

import time
from ..database import _is_postgres, get_conn
from .progress import EducationProgressManager

_progress = EducationProgressManager()

# XP rewards (capped to prevent grinding)
XP_GAME_BASE = 5
XP_PER_BLOCK = 2
XP_PER_HALVING = 5
XP_GAME_MAX = 40


def handle_game_complete(body: dict, pubkey: str | None = None) -> tuple[dict, int]:
    """POST /education/game/complete

    Body:
      - score           : int — total sats mined
      - blocks_mined    : int
      - halvings_survived : int
      - duration_seconds : int (optional)

    Returns XP earned and updated education state.
    """
    try:
        score = int(body.get("score", 0))
        blocks_mined = int(body.get("blocks_mined", 0))
        halvings_survived = int(body.get("halvings_survived", 0))
        duration_seconds = int(body.get("duration_seconds", 0))

        if score < 0 or blocks_mined < 0 or halvings_survived < 0:
            return {"detail": "Invalid game data"}, 400

        # Calculate XP
        xp_earned = min(
            XP_GAME_MAX,
            XP_GAME_BASE + blocks_mined * XP_PER_BLOCK + halvings_survived * XP_PER_HALVING,
        )

        response: dict = {
            "score": score,
            "blocks_mined": blocks_mined,
            "halvings_survived": halvings_survived,
            "xp_earned": xp_earned,
        }

        if pubkey:
            try:
                # Record game run
                now = int(time.time())
                ph = "%s" if _is_postgres() else "?"
                conn = get_conn()
                conn.execute(
                    f"""
                    INSERT INTO education_game_runs
                        (pubkey, score, blocks_mined, halvings_survived,
                         duration_seconds, xp_earned, completed_at)
                    VALUES ({', '.join([ph] * 7)})
                    """,
                    (pubkey, score, blocks_mined, halvings_survived,
                     duration_seconds, xp_earned, now),
                )
                conn.commit()

                # Award XP via existing system
                state = _progress.add_xp(pubkey, xp_earned)
                response["state"] = state

                # Fetch high score
                high_row = conn.execute(
                    f"SELECT MAX(score) FROM education_game_runs WHERE pubkey = {ph}",
                    (pubkey,),
                ).fetchone()
                response["high_score"] = high_row[0] if high_row and high_row[0] else score

            except Exception:
                # Never fail on gamification glitch
                pass

        return response, 200

    except Exception as exc:
        return {"detail": f"Game completion error: {exc}"}, 500
