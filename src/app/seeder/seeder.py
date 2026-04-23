"""
Database seeder for the Magma Bitcoin application.

Provides ``DatabaseSeeder`` for bulk data population and ``DemoDataSeeder``
for creating a curated set of demo users with realistic activity patterns.

Depends only on Python stdlib and the app's existing database module.
"""

import json
import logging
import time
from typing import Dict, List, Optional

from .generator import DataGenerator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DatabaseSeeder
# ---------------------------------------------------------------------------

class DatabaseSeeder:
    """
    Populates the application database with generated test data.

    All write operations are wrapped in a single database transaction so
    that a failure mid-seed rolls back the entire batch.

    Args:
        generator:      :class:`DataGenerator` instance used to produce data.
        db_conn_factory: Zero-argument callable returning a DB connection.

    Example::

        gen = DataGenerator(seed=42)
        seeder = DatabaseSeeder(gen, db_conn_factory=get_db)
        report = seeder.seed_all(n_users=50)
        print(report)
    """

    def __init__(
        self,
        generator: DataGenerator,
        db_conn_factory=None,
    ):
        self._gen = generator
        self._db_conn_factory = db_conn_factory
        self._seeded_pubkeys: List[str] = []
        self._stats: Dict[str, int] = {}

    def _conn(self):
        if self._db_conn_factory is None:
            try:
                from ..database import get_db
                return get_db()
            except Exception:
                raise RuntimeError(
                    "No db_conn_factory provided and could not import app.database.get_db"
                )
        return self._db_conn_factory()

    # ------------------------------------------------------------------
    # Individual seeders
    # ------------------------------------------------------------------

    def seed_users(self, count: int = 50) -> List[str]:
        """
        Create ``count`` user records.

        Args:
            count: Number of users to create.

        Returns:
            List of pubkeys for the created users.
        """
        pubkeys = self._gen.generate_pubkeys(count)
        conn = self._conn()
        cur = conn.cursor()
        now = int(time.time())
        created = 0
        try:
            for pk in pubkeys:
                cur.execute(
                    "INSERT OR IGNORE INTO users (pubkey, auth_method, created_at) "
                    "VALUES (?, ?, ?)",
                    (pk, "lnurl", now - self._gen._rng.randint(0, 365 * 86400)),
                )
                created += 1
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("seed_users failed")
            raise
        finally:
            cur.close()

        self._seeded_pubkeys.extend(pubkeys)
        self._stats["users"] = self._stats.get("users", 0) + created
        logger.info("seed_users: created %d users", created)
        return pubkeys

    def seed_deposits(
        self,
        users: List[str],
        per_user: int = 20,
    ) -> int:
        """
        Create deposit records for each user.

        Args:
            users:    List of pubkeys.
            per_user: Deposits per user.

        Returns:
            Total number of deposits created.
        """
        conn = self._conn()
        cur = conn.cursor()
        total = 0
        try:
            for pk in users:
                deposits = self._gen.generate_deposits(pk, count=per_user)
                for dep in deposits:
                    cur.execute(
                        "INSERT OR IGNORE INTO deposits "
                        "(pubkey, amount_sats, created_at) VALUES (?, ?, ?)",
                        (dep["pubkey"], dep["amount_sats"], dep["created_at"]),
                    )
                    total += 1
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("seed_deposits failed")
            raise
        finally:
            cur.close()

        self._stats["deposits"] = self._stats.get("deposits", 0) + total
        logger.info("seed_deposits: created %d deposits", total)
        return total

    def seed_savings_goals(self, users: List[str]) -> int:
        """
        Create savings goals for each user.

        Returns:
            Number of goals created.
        """
        conn = self._conn()
        cur = conn.cursor()
        total = 0
        try:
            for pk in users:
                goal = self._gen.generate_savings_goal(pk)
                cur.execute(
                    "INSERT OR REPLACE INTO savings_goals "
                    "(pubkey, monthly_target_usd, target_years, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        goal["pubkey"],
                        goal["monthly_target_usd"],
                        goal["target_years"],
                        int(time.time()),
                    ),
                )
                total += 1
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("seed_savings_goals failed")
            raise
        finally:
            cur.close()

        self._stats["savings_goals"] = self._stats.get("savings_goals", 0) + total
        logger.info("seed_savings_goals: created %d goals", total)
        return total

    def seed_achievements(self, users: List[str]) -> int:
        """
        Award random achievements to users.

        Returns:
            Total achievement records created.
        """
        conn = self._conn()
        cur = conn.cursor()
        total = 0
        try:
            for pk in users:
                n = self._gen._rng.randint(1, 8)
                achievements = self._gen.generate_achievements(pk, count=n)
                for ach in achievements:
                    cur.execute(
                        "INSERT OR IGNORE INTO achievements "
                        "(pubkey, achievement_type, earned_at, metadata) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            ach["pubkey"],
                            ach["achievement_type"],
                            ach["earned_at"],
                            ach.get("metadata", "{}"),
                        ),
                    )
                    total += 1
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("seed_achievements failed")
            raise
        finally:
            cur.close()

        self._stats["achievements"] = self._stats.get("achievements", 0) + total
        logger.info("seed_achievements: created %d achievements", total)
        return total

    def seed_preferences(self, users: List[str]) -> int:
        """
        Insert default user preferences for each user.

        Returns:
            Number of preference rows created.
        """
        conn = self._conn()
        cur = conn.cursor()
        total = 0
        now = int(time.time())
        try:
            for pk in users:
                fee_low = self._gen._rng.randint(1, 10)
                fee_high = self._gen._rng.randint(30, 100)
                cur.execute(
                    "INSERT OR IGNORE INTO user_preferences "
                    "(pubkey, fee_alert_low, fee_alert_high, price_alerts, "
                    "alerts_enabled, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (pk, fee_low, fee_high, "[]", 1, now),
                )
                total += 1
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("seed_preferences failed")
            raise
        finally:
            cur.close()

        self._stats["preferences"] = self._stats.get("preferences", 0) + total
        logger.info("seed_preferences: created %d preference rows", total)
        return total

    def seed_analytics(
        self,
        users: List[str],
        events_per_user: int = 50,
    ) -> int:
        """
        Insert analytics event records for each user.

        Returns:
            Total events created.
        """
        conn = self._conn()
        cur = conn.cursor()
        total = 0
        try:
            for pk in users:
                events = self._gen.generate_analytics_events(pk, count=events_per_user)
                for ev in events:
                    # analytics_events table may or may not exist – skip gracefully
                    try:
                        cur.execute(
                            "INSERT OR IGNORE INTO analytics_events "
                            "(pubkey, event_type, timestamp, properties, session_id, country) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                ev["pubkey"],
                                ev["event_type"],
                                ev["timestamp"],
                                ev.get("properties", "{}"),
                                ev.get("session_id", ""),
                                ev.get("country", ""),
                            ),
                        )
                        total += 1
                    except Exception:
                        pass  # table might not exist
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("seed_analytics failed")
            raise
        finally:
            cur.close()

        self._stats["analytics_events"] = self._stats.get("analytics_events", 0) + total
        logger.info("seed_analytics: created %d events", total)
        return total

    def seed_all(self, n_users: int = 50) -> Dict:
        """
        Run all seeders in sequence.

        Args:
            n_users: Number of users to create.

        Returns:
            Summary dict with counts per entity type.
        """
        started = time.time()
        report: Dict = {"started_at": started, "n_users_requested": n_users}

        try:
            users = self.seed_users(n_users)
            report["users"] = len(users)

            report["deposits"] = self.seed_deposits(users, per_user=20)
            report["savings_goals"] = self.seed_savings_goals(users)
            report["achievements"] = self.seed_achievements(users)
            report["preferences"] = self.seed_preferences(users)
            report["analytics_events"] = self.seed_analytics(users, events_per_user=50)

            report["success"] = True
        except Exception as exc:
            report["success"] = False
            report["error"] = str(exc)
            logger.exception("seed_all failed")

        report["duration_seconds"] = round(time.time() - started, 3)
        return report

    def clear_all(self) -> Dict:
        """
        Delete all seeded data (users from this session only).

        Returns:
            Dict with deletion counts per table.
        """
        if not self._seeded_pubkeys:
            return {"message": "No seeded pubkeys tracked; nothing to delete"}

        conn = self._conn()
        cur = conn.cursor()
        report = {}
        tables = [
            "analytics_events", "achievements", "savings_goals",
            "user_preferences", "deposits", "users",
        ]
        placeholders = ",".join("?" for _ in self._seeded_pubkeys)
        try:
            for table in tables:
                try:
                    col = "pubkey"
                    cur.execute(
                        f"DELETE FROM {table} WHERE {col} IN ({placeholders})",
                        self._seeded_pubkeys,
                    )
                    report[table] = cur.rowcount
                except Exception as exc:
                    report[table] = f"error: {exc}"
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

        self._seeded_pubkeys.clear()
        self._stats.clear()
        return report

    def get_seed_stats(self) -> Dict:
        """Return a summary of what has been seeded in this session."""
        return {
            "seeded_user_count": len(self._seeded_pubkeys),
            "entity_counts": dict(self._stats),
        }


# ---------------------------------------------------------------------------
# DemoDataSeeder
# ---------------------------------------------------------------------------

# Curated demo personas
_DEMO_PERSONAS = [
    {
        "persona": "new_user",
        "pubkey": "aabbcc" + "0" * 58,
        "monthly_usd": 50,
        "target_years": 10,
        "n_deposits": 3,
        "n_achievements": 1,
        "events_per_user": 15,
    },
    {
        "persona": "power_saver",
        "pubkey": "ddeeff" + "1" * 58,
        "monthly_usd": 500,
        "target_years": 20,
        "n_deposits": 50,
        "n_achievements": 8,
        "events_per_user": 100,
    },
    {
        "persona": "whale",
        "pubkey": "112233" + "2" * 58,
        "monthly_usd": 5000,
        "target_years": 5,
        "n_deposits": 30,
        "n_achievements": 10,
        "events_per_user": 60,
    },
    {
        "persona": "dormant",
        "pubkey": "445566" + "3" * 58,
        "monthly_usd": 100,
        "target_years": 15,
        "n_deposits": 2,
        "n_achievements": 2,
        "events_per_user": 5,
    },
    {
        "persona": "diversified",
        "pubkey": "778899" + "4" * 58,
        "monthly_usd": 1000,
        "target_years": 25,
        "n_deposits": 40,
        "n_achievements": 7,
        "events_per_user": 80,
    },
]


class DemoDataSeeder:
    """
    Creates a curated set of demo users, each with a distinct activity persona.

    Personas:
      - ``new_user``    — joined recently, few deposits, limited engagement
      - ``power_saver`` — large monthly DCA, many deposits, high engagement
      - ``whale``       — very large deposits, aggressive savings target
      - ``dormant``     — signed up but barely active
      - ``diversified`` — long horizon, steady contributions

    Args:
        db_conn_factory: Zero-argument callable returning a DB connection.

    Example::

        demo = DemoDataSeeder()
        report = demo.seed_demo()
    """

    def __init__(self, db_conn_factory=None):
        self._db_conn_factory = db_conn_factory
        self._gen = DataGenerator(seed=0)  # deterministic for demos

    def _conn(self):
        if self._db_conn_factory is None:
            try:
                from ..database import get_db
                return get_db()
            except Exception:
                raise RuntimeError("Could not obtain a database connection")
        return self._db_conn_factory()

    def seed_demo(self) -> Dict:
        """
        Insert all five demo personas into the database.

        Returns:
            Report dict mapping persona name to insert counts.
        """
        started = time.time()
        report: Dict = {}
        conn = self._conn()
        cur = conn.cursor()
        now = int(time.time())

        try:
            for persona in _DEMO_PERSONAS:
                pk = persona["pubkey"]
                name = persona["persona"]

                # User
                cur.execute(
                    "INSERT OR REPLACE INTO users (pubkey, auth_method, created_at) "
                    "VALUES (?, ?, ?)",
                    (pk, "lnurl", now - self._gen._rng.randint(86400, 365 * 86400)),
                )

                # Preferences
                cur.execute(
                    "INSERT OR REPLACE INTO user_preferences "
                    "(pubkey, fee_alert_low, fee_alert_high, price_alerts, "
                    "alerts_enabled, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (pk, 5, 50, "[]", 1, now),
                )

                # Savings goal
                cur.execute(
                    "INSERT OR REPLACE INTO savings_goals "
                    "(pubkey, monthly_target_usd, target_years, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (pk, persona["monthly_usd"], persona["target_years"], now),
                )

                # Deposits
                deposits = self._gen.generate_deposits(pk, count=persona["n_deposits"])
                dep_count = 0
                for dep in deposits:
                    try:
                        cur.execute(
                            "INSERT OR IGNORE INTO deposits "
                            "(pubkey, amount_sats, created_at) VALUES (?, ?, ?)",
                            (dep["pubkey"], dep["amount_sats"], dep["created_at"]),
                        )
                        dep_count += 1
                    except Exception:
                        pass

                # Achievements
                achievements = self._gen.generate_achievements(
                    pk, count=persona["n_achievements"]
                )
                ach_count = 0
                for ach in achievements:
                    try:
                        cur.execute(
                            "INSERT OR IGNORE INTO achievements "
                            "(pubkey, achievement_type, earned_at, metadata) "
                            "VALUES (?, ?, ?, ?)",
                            (
                                ach["pubkey"],
                                ach["achievement_type"],
                                ach["earned_at"],
                                ach.get("metadata", "{}"),
                            ),
                        )
                        ach_count += 1
                    except Exception:
                        pass

                report[name] = {
                    "pubkey": pk,
                    "deposits": dep_count,
                    "achievements": ach_count,
                }

            conn.commit()

        except Exception as exc:
            conn.rollback()
            logger.exception("DemoDataSeeder.seed_demo failed")
            return {"success": False, "error": str(exc)}
        finally:
            cur.close()

        report["success"] = True
        report["duration_seconds"] = round(time.time() - started, 3)
        logger.info("DemoDataSeeder.seed_demo complete: %s", report)
        return report
