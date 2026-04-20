"""Savings goal and deposit tracking."""

import time
from datetime import datetime, timezone, timedelta

from ..database import get_conn, _is_postgres
from ..services.coingecko_client import CoinGeckoClient


def _ph() -> str:
    return "%s" if _is_postgres() else "?"


class SavingsTracker:
    def __init__(self):
        self.coingecko = CoinGeckoClient()

    def create_goal(
        self, pubkey: str, monthly_target: float, target_years: int
    ) -> dict:
        """Create or update a savings goal."""
        now = int(time.time())
        conn = get_conn()
        p = _ph()

        row = conn.execute(
            f"SELECT pubkey FROM savings_goals WHERE pubkey = {p}", (pubkey,)
        ).fetchone()

        if row:
            conn.execute(
                f"UPDATE savings_goals SET monthly_target_usd = {p}, target_years = {p}, updated_at = {p} WHERE pubkey = {p}",
                (monthly_target, target_years, now, pubkey),
            )
        else:
            conn.execute(
                f"INSERT INTO savings_goals (pubkey, monthly_target_usd, target_years, created_at, updated_at) VALUES ({p}, {p}, {p}, {p}, {p})",
                (pubkey, monthly_target, target_years, now, now),
            )
        conn.commit()

        return {
            "monthly_target_usd": monthly_target,
            "target_years": target_years,
            "updated_at": now,
        }

    def record_deposit(self, pubkey: str, amount_usd: float) -> dict:
        """Record a savings deposit with real-time BTC price."""
        btc_price = self.coingecko.get_price()
        btc_amount = amount_usd / btc_price if btc_price > 0 else 0.0
        now = int(time.time())

        conn = get_conn()
        p = _ph()
        conn.execute(
            f"INSERT INTO savings_deposits (pubkey, amount_usd, btc_price, btc_amount, created_at) VALUES ({p}, {p}, {p}, {p}, {p})",
            (pubkey, amount_usd, btc_price, btc_amount, now),
        )
        conn.commit()

        return {
            "amount_usd": amount_usd,
            "btc_price": round(btc_price, 2),
            "btc_amount": round(btc_amount, 8),
            "created_at": now,
        }

    def get_progress(self, pubkey: str) -> dict:
        """Get savings progress with streak and projections."""
        conn = get_conn()
        p = _ph()

        goal_row = conn.execute(
            f"SELECT monthly_target_usd, target_years, created_at FROM savings_goals WHERE pubkey = {p}",
            (pubkey,),
        ).fetchone()

        if not goal_row:
            return {"has_goal": False}

        goal = {
            "monthly_target_usd": goal_row[0]
            if isinstance(goal_row, tuple)
            else goal_row["monthly_target_usd"],
            "target_years": goal_row[1]
            if isinstance(goal_row, tuple)
            else goal_row["target_years"],
            "created_at": goal_row[2]
            if isinstance(goal_row, tuple)
            else goal_row["created_at"],
        }

        deposits = conn.execute(
            f"SELECT amount_usd, btc_price, btc_amount, created_at FROM savings_deposits WHERE pubkey = {p} ORDER BY created_at DESC",
            (pubkey,),
        ).fetchall()

        total_usd = sum(
            d[0] if isinstance(d, tuple) else d["amount_usd"] for d in deposits
        )
        total_btc = sum(
            d[2] if isinstance(d, tuple) else d["btc_amount"] for d in deposits
        )

        try:
            current_price = self.coingecko.get_price()
        except Exception:
            current_price = 0.0

        current_value = total_btc * current_price
        roi = ((current_value - total_usd) / total_usd * 100) if total_usd > 0 else 0.0

        streak = self._calculate_streak(deposits)

        recent = [
            {
                "amount_usd": d[0] if isinstance(d, tuple) else d["amount_usd"],
                "btc_price": round(d[1] if isinstance(d, tuple) else d["btc_price"], 2),
                "btc_amount": round(
                    d[2] if isinstance(d, tuple) else d["btc_amount"], 8
                ),
                "created_at": d[3] if isinstance(d, tuple) else d["created_at"],
            }
            for d in deposits[:10]
        ]

        milestones = [
            {"name": "First deposit", "target": 1, "reached": len(deposits) >= 1},
            {"name": "$100 saved", "target": 100, "reached": total_usd >= 100},
            {"name": "$500 saved", "target": 500, "reached": total_usd >= 500},
            {"name": "$1,000 saved", "target": 1000, "reached": total_usd >= 1000},
            {"name": "3-month streak", "target": 3, "reached": streak >= 3},
            {"name": "6-month streak", "target": 6, "reached": streak >= 6},
            {"name": "12-month streak", "target": 12, "reached": streak >= 12},
        ]

        next_milestone = next((m for m in milestones if not m["reached"]), None)

        return {
            "has_goal": True,
            "goal": goal,
            "total_invested_usd": round(total_usd, 2),
            "total_btc": round(total_btc, 8),
            "current_value_usd": round(current_value, 2),
            "roi_percent": round(roi, 2),
            "current_btc_price": round(current_price, 2),
            "streak_months": streak,
            "deposit_count": len(deposits),
            "recent_deposits": recent,
            "milestones": milestones,
            "next_milestone": next_milestone,
        }

    def _calculate_streak(self, deposits: list, now: float | None = None) -> int:
        """Consecutive calendar months with deposits, counting backwards.

        A month counts when at least one deposit lands within that UTC
        calendar month. The walk stops at the first missing month.
        """
        if not deposits:
            return 0

        current_ts = time.time() if now is None else now
        cursor = datetime.fromtimestamp(current_ts, timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        months_with_deposits: set[tuple[int, int]] = set()
        for d in deposits:
            ts = d[3] if isinstance(d, tuple) else d["created_at"]
            if not isinstance(ts, (int, float)):
                continue
            dt = datetime.fromtimestamp(ts, timezone.utc)
            months_with_deposits.add((dt.year, dt.month))

        streak = 0
        for _ in range(120):  # cap look-back at 10 years
            if (cursor.year, cursor.month) in months_with_deposits:
                streak += 1
                cursor = (cursor - timedelta(days=1)).replace(day=1)
            else:
                break
        return streak
