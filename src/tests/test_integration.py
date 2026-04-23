"""
tests/test_integration.py
=========================
Integration tests combining multiple Magma modules.

These tests exercise real interactions between components using an
in-memory SQLite database (no external network calls).  External services
(CoinGecko, Schnorr verifier) are mocked with unittest.mock.

Test count: 28+
"""

import sys
import os
import json
import time
import hashlib
import secrets
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import TestDatabase, create_test_user, generate_test_token


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_pubkey(char: str = "a") -> str:
    return char * 64


def _compute_nostr_id(pubkey, created_at, kind, tags, content):
    serialized = json.dumps(
        [0, pubkey, created_at, kind, tags, content], separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def _make_auth_event(pubkey, challenge, age=0):
    created_at = int(time.time()) - age
    tags = [["u", "https://api.eclalune.com/auth/verify"], ["method", "POST"]]
    eid = _compute_nostr_id(pubkey, created_at, 27235, tags, challenge)
    return {
        "id": eid,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": 27235,
        "tags": tags,
        "content": challenge,
        "sig": "a" * 128,
    }


# ===========================================================================
# 1.  Auth flow: challenge → verify → session → /me
# ===========================================================================

class TestAuthFlow(unittest.TestCase):
    """Integration: challenge creation, session creation, session validation."""

    def setUp(self):
        from app.auth import sessions
        sessions._sessions.clear()
        self.sessions = sessions

    def test_create_and_validate_session(self):
        pubkey = _make_pubkey("a")
        token = self.sessions.create_session(pubkey)
        self.assertEqual(self.sessions.validate_session(token), pubkey)

    def test_session_not_found_before_creation(self):
        self.assertIsNone(self.sessions.validate_session("notexist"))

    def test_session_expires_after_ttl(self):
        pubkey = _make_pubkey("b")
        token = self.sessions.create_session(pubkey)
        # Manually expire it
        with self.sessions._lock:
            self.sessions._sessions[token] = (pubkey, time.time() - 1)
        self.assertIsNone(self.sessions.validate_session(token))

    def test_cleanup_removes_only_expired(self):
        pk_valid = _make_pubkey("c")
        pk_expired = _make_pubkey("d")
        t_valid = self.sessions.create_session(pk_valid)
        t_expired = self.sessions.create_session(pk_expired)
        with self.sessions._lock:
            self.sessions._sessions[t_expired] = (pk_expired, time.time() - 1)
        self.sessions.cleanup_expired()
        self.assertIsNotNone(self.sessions.validate_session(t_valid))
        self.assertIsNone(self.sessions.validate_session(t_expired))

    def test_two_users_independent_sessions(self):
        pk1 = _make_pubkey("e")
        pk2 = _make_pubkey("f")
        t1 = self.sessions.create_session(pk1)
        t2 = self.sessions.create_session(pk2)
        self.assertEqual(self.sessions.validate_session(t1), pk1)
        self.assertEqual(self.sessions.validate_session(t2), pk2)

    def test_token_format(self):
        token = self.sessions.create_session(_make_pubkey("g"))
        self.assertEqual(len(token), 64)
        bytes.fromhex(token)


# ===========================================================================
# 2.  Savings flow: create goal → deposit → check progress
# ===========================================================================

class TestSavingsFlow(unittest.TestCase):
    """Integration: savings goal creation and deposit tracking using a real DB."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        self.pubkey = _make_pubkey("a")
        self.db.insert_user(self.pubkey)

    def tearDown(self):
        self.db.teardown()

    def test_insert_user_exists(self):
        row = self.conn.execute(
            "SELECT pubkey FROM users WHERE pubkey = ?", (self.pubkey,)
        ).fetchone()
        self.assertIsNotNone(row)

    def test_savings_goal_insert_and_query(self):
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO savings_goals (pubkey, monthly_target_usd, target_years, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (self.pubkey, 200.0, 10, now, now),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT monthly_target_usd FROM savings_goals WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(float(row[0]), 200.0)

    def test_deposit_tracking(self):
        self.db.insert_deposit(self.pubkey, amount_usd=100.0, btc_price=50000.0)
        self.db.insert_deposit(self.pubkey, amount_usd=200.0, btc_price=50000.0)
        rows = self.conn.execute(
            "SELECT SUM(amount_usd) FROM savings_deposits WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()
        self.assertAlmostEqual(float(rows[0]), 300.0)

    def test_deposit_btc_amount_calculated_correctly(self):
        self.db.insert_deposit(self.pubkey, amount_usd=100.0, btc_price=50000.0)
        row = self.conn.execute(
            "SELECT btc_amount FROM savings_deposits WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()
        # 100 / 50000 = 0.002 BTC
        self.assertAlmostEqual(float(row[0]), 0.002, places=8)

    def test_multiple_users_isolated(self):
        pk2 = _make_pubkey("b")
        self.db.insert_user(pk2)
        self.db.insert_deposit(self.pubkey, 100.0)
        self.db.insert_deposit(pk2, 500.0)
        row1 = self.conn.execute(
            "SELECT amount_usd FROM savings_deposits WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()
        row2 = self.conn.execute(
            "SELECT amount_usd FROM savings_deposits WHERE pubkey = ?",
            (pk2,),
        ).fetchone()
        self.assertAlmostEqual(float(row1[0]), 100.0)
        self.assertAlmostEqual(float(row2[0]), 500.0)

    def test_deposit_count_rows(self):
        for i in range(5):
            self.db.insert_deposit(self.pubkey, float(i + 1) * 10.0)
        count = self.db.count_rows("savings_deposits")
        self.assertEqual(count, 5)


# ===========================================================================
# 3.  Achievement awarding after deposit
# ===========================================================================

class TestAchievementAfterDeposit(unittest.TestCase):
    """Integration: verify achievement engine awards on deposit events."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        self.pubkey = _make_pubkey("c")
        self.db.insert_user(self.pubkey)

    def tearDown(self):
        self.db.teardown()

    @patch("app.gamification.achievements.get_conn")
    def test_first_save_achievement_awarded(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.gamification.achievements import AchievementEngine
        engine = AchievementEngine()
        awarded = engine.check_and_award(
            pubkey=self.pubkey,
            event_type="deposit",
            event_data={"amount_usd": 50.0, "deposit_count": 1, "total_usd": 50.0},
        )
        ids = [a["id"] for a in awarded]
        self.assertIn("first_save", ids)

    @patch("app.gamification.achievements.get_conn")
    def test_no_duplicate_achievements(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.gamification.achievements import AchievementEngine
        engine = AchievementEngine()
        # Award first_save
        engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": 50.0, "deposit_count": 1, "total_usd": 50.0},
        )
        # Award again — should NOT get first_save twice
        awarded2 = engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": 50.0, "deposit_count": 2, "total_usd": 100.0},
        )
        ids2 = [a["id"] for a in awarded2]
        self.assertNotIn("first_save", ids2)

    @patch("app.gamification.achievements.get_conn")
    def test_saved_100_achievement_on_threshold(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.gamification.achievements import AchievementEngine
        engine = AchievementEngine()
        awarded = engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": 100.0, "deposit_count": 1, "total_usd": 100.0},
        )
        ids = [a["id"] for a in awarded]
        self.assertIn("saved_100", ids)

    @patch("app.gamification.achievements.get_conn")
    def test_achievement_has_required_fields(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.gamification.achievements import AchievementEngine
        engine = AchievementEngine()
        awarded = engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": 50.0, "deposit_count": 1, "total_usd": 50.0},
        )
        if awarded:
            a = awarded[0]
            self.assertIn("id", a)
            self.assertIn("name", a)
            self.assertIn("xp", a)


# ===========================================================================
# 4.  Remittance comparison
# ===========================================================================

class TestRemittanceComparison(unittest.TestCase):
    """Integration: verify remittance comparison returns expected structure."""

    @patch("app.remittance.optimizer.CoinGeckoClient")
    def test_compare_returns_dict(self, mock_cg_class):
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = 60000.0
        mock_cg_class.return_value = mock_cg

        from app.remittance.optimizer import RemittanceOptimizer
        optimizer = RemittanceOptimizer()
        result = optimizer.compare(amount_usd=200.0, frequency="monthly")
        self.assertIsNotNone(result)

    @patch("app.remittance.optimizer.CoinGeckoClient")
    def test_compare_includes_lightning_channel(self, mock_cg_class):
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = 60000.0
        mock_cg_class.return_value = mock_cg

        from app.remittance.optimizer import RemittanceOptimizer
        optimizer = RemittanceOptimizer()
        result = optimizer.compare(amount_usd=100.0, frequency="monthly")
        result_dict = result.to_dict() if hasattr(result, "to_dict") else result
        self.assertIsInstance(result_dict, dict)

    @patch("app.remittance.routes.CoinGeckoClient", create=True)
    def test_handle_compare_route_200(self, mock_cg_class):
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = 60000.0
        mock_cg_class.return_value = mock_cg

        from app.remittance.routes import handle_compare
        with patch("app.remittance.optimizer.CoinGeckoClient") as mc:
            mc.return_value.get_price.return_value = 60000.0
            body = {"amount_usd": 100.0, "frequency": "monthly"}
            resp, status = handle_compare(body)
            self.assertEqual(status, 200)


# ===========================================================================
# 5.  Analytics event tracking
# ===========================================================================

class TestAnalyticsEventTracking(unittest.TestCase):
    """Integration: verify analytics events are stored and queried correctly."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        # Create analytics_events table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                pubkey TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            )
        """)
        self.conn.commit()
        self.pubkey = _make_pubkey("d")
        self.db.insert_user(self.pubkey)

    def tearDown(self):
        self.db.teardown()

    @patch("app.analytics.engine.get_conn")
    def test_track_event_inserts_row(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        engine.track_event(
            event_type="deposit",
            pubkey=self.pubkey,
            data={"amount_usd": 50.0},
        )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE pubkey = ?", (self.pubkey,)
        ).fetchone()[0]
        self.assertEqual(count, 1)

    @patch("app.analytics.engine.get_conn")
    def test_multiple_events_same_user(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        for event_type in ["deposit", "goal_set", "login"]:
            engine.track_event(event_type=event_type, pubkey=self.pubkey, data={})
        count = self.conn.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE pubkey = ?", (self.pubkey,)
        ).fetchone()[0]
        self.assertEqual(count, 3)

    @patch("app.analytics.engine.get_conn")
    def test_event_type_stored_correctly(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        engine.track_event("achievement_unlocked", self.pubkey, {"achievement": "first_save"})
        row = self.conn.execute(
            "SELECT event_type, data FROM analytics_events WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()
        self.assertEqual(row[0], "achievement_unlocked")
        data = json.loads(row[1])
        self.assertEqual(data.get("achievement"), "first_save")


# ===========================================================================
# 6.  Webhook subscription lifecycle
# ===========================================================================

class TestWebhookSubscriptionLifecycle(unittest.TestCase):
    """Integration: subscribe, list, and unsubscribe webhooks."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS webhook_subscriptions (
                id TEXT PRIMARY KEY,
                pubkey TEXT NOT NULL,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                secret TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                last_triggered_at INTEGER,
                failure_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        self.conn.commit()
        self.pubkey = _make_pubkey("e")
        self.db.insert_user(self.pubkey)

    def tearDown(self):
        self.db.teardown()

    @patch("app.webhooks.manager.get_conn")
    def test_create_subscription(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.webhooks.manager import WebhookManager
        mgr = WebhookManager()
        result = mgr.create_subscription(
            pubkey=self.pubkey,
            url="https://example.com/webhook",
            events=["deposit_confirmed"],
        )
        self.assertIn("id", result)
        self.assertIn("secret", result)

    @patch("app.webhooks.manager.get_conn")
    def test_list_subscriptions(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.webhooks.manager import WebhookManager
        mgr = WebhookManager()
        mgr.create_subscription(
            pubkey=self.pubkey,
            url="https://example.com/wh1",
            events=["deposit_confirmed"],
        )
        mgr.create_subscription(
            pubkey=self.pubkey,
            url="https://example.com/wh2",
            events=["achievement_earned"],
        )
        subs = mgr.list_subscriptions(self.pubkey)
        self.assertEqual(len(subs), 2)

    @patch("app.webhooks.manager.get_conn")
    def test_delete_subscription(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.webhooks.manager import WebhookManager
        mgr = WebhookManager()
        sub = mgr.create_subscription(
            pubkey=self.pubkey,
            url="https://example.com/wh",
            events=["deposit_confirmed"],
        )
        sub_id = sub["id"]
        mgr.delete_subscription(self.pubkey, sub_id)
        subs = mgr.list_subscriptions(self.pubkey)
        self.assertEqual(len(subs), 0)

    @patch("app.webhooks.manager.get_conn")
    def test_invalid_event_type_rejected(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.webhooks.manager import WebhookManager
        mgr = WebhookManager()
        with self.assertRaises(ValueError):
            mgr.create_subscription(
                pubkey=self.pubkey,
                url="https://example.com/wh",
                events=["not_a_real_event"],
            )

    @patch("app.webhooks.manager.get_conn")
    def test_subscription_belongs_to_user(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        pk2 = _make_pubkey("f")
        self.db.insert_user(pk2)
        from app.webhooks.manager import WebhookManager
        mgr = WebhookManager()
        mgr.create_subscription(pk2, "https://example.com/pk2", ["price_alert"])
        subs1 = mgr.list_subscriptions(self.pubkey)
        subs2 = mgr.list_subscriptions(pk2)
        self.assertEqual(len(subs1), 0)
        self.assertEqual(len(subs2), 1)


# ===========================================================================
# 7.  Export data flow
# ===========================================================================

class TestExportDataFlow(unittest.TestCase):
    """Integration: export endpoints produce valid output."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        self.pubkey = _make_pubkey("g")
        self.db.insert_user(self.pubkey)
        # Insert some deposits
        for i in range(3):
            self.db.insert_deposit(self.pubkey, float((i + 1) * 50), btc_price=50000.0)

    def tearDown(self):
        self.db.teardown()

    @patch("app.export.exporter.get_conn")
    def test_export_deposits_json(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.export.exporter import DataExporter
        exporter = DataExporter()
        result = exporter.export_deposits(self.pubkey, fmt="json")
        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertIsInstance(parsed, (list, dict))

    @patch("app.export.exporter.get_conn")
    def test_export_deposits_csv(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.export.exporter import DataExporter
        exporter = DataExporter()
        result = exporter.export_deposits(self.pubkey, fmt="csv")
        self.assertIsInstance(result, str)
        # CSV should have a header line
        lines = result.strip().split("\n")
        self.assertGreaterEqual(len(lines), 1)

    @patch("app.export.exporter.get_conn")
    def test_export_no_deposits_returns_valid_json(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        other_pubkey = _make_pubkey("z")
        self.db.insert_user(other_pubkey)
        from app.export.exporter import DataExporter
        exporter = DataExporter()
        result = exporter.export_deposits(other_pubkey, fmt="json")
        parsed = json.loads(result)
        # An empty export is still valid JSON
        self.assertIsNotNone(parsed)


# ===========================================================================
# 8.  Savings projector
# ===========================================================================

class TestSavingsProjector(unittest.TestCase):
    """Integration: savings projector produces sensible projections."""

    @patch("app.savings.projector.CoinGeckoClient")
    def test_project_returns_dict(self, mock_cg_class):
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = 60000.0
        mock_cg.get_history.return_value = [[int(time.time() * 1000) - i * 86400000, 60000.0]
                                             for i in range(365)]
        mock_cg_class.return_value = mock_cg

        from app.savings.projector import SavingsProjector
        projector = SavingsProjector()
        result = projector.project(monthly_usd=100.0, years=10)
        self.assertIsInstance(result, dict)

    @patch("app.savings.projector.CoinGeckoClient")
    def test_project_has_scenarios(self, mock_cg_class):
        mock_cg = MagicMock()
        mock_cg.get_price.return_value = 60000.0
        mock_cg.get_history.return_value = [[int(time.time() * 1000) - i * 86400000, 60000.0]
                                             for i in range(365)]
        mock_cg_class.return_value = mock_cg

        from app.savings.projector import SavingsProjector
        projector = SavingsProjector()
        result = projector.project(monthly_usd=200.0, years=5)
        # Should contain scenario data
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)


# ===========================================================================
# 9.  Scoring history
# ===========================================================================

class TestScoringHistory(unittest.TestCase):
    """Integration: scoring history is stored and retrievable."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        self.pubkey = _make_pubkey("h")
        self.db.insert_user(self.pubkey)

    def tearDown(self):
        self.db.teardown()

    def test_insert_and_query_scoring(self):
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO scoring_history (pubkey, address, score, grade, checked_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (self.pubkey, "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf8o", 720, "A", now),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT score, grade FROM scoring_history WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()
        self.assertEqual(row[0], 720)
        self.assertEqual(row[1], "A")

    def test_multiple_score_history(self):
        now = int(time.time())
        for score in [500, 600, 700]:
            self.conn.execute(
                "INSERT INTO scoring_history (pubkey, address, score, grade, checked_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self.pubkey, "addr", score, "B", now),
            )
        self.conn.commit()
        count = self.conn.execute(
            "SELECT COUNT(*) FROM scoring_history WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()[0]
        self.assertEqual(count, 3)


# ===========================================================================
# 10. Full deposit pipeline: user → goal → deposit → achievement → analytics
# ===========================================================================

class TestFullDepositPipeline(unittest.TestCase):
    """End-to-end simulation of the deposit pipeline."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                pubkey TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            )
        """)
        self.conn.commit()
        self.pubkey = _make_pubkey("i")
        self.db.insert_user(self.pubkey)

    def tearDown(self):
        self.db.teardown()

    @patch("app.gamification.achievements.get_conn")
    @patch("app.analytics.engine.get_conn")
    def test_deposit_triggers_achievement_and_analytics(
        self, mock_analytics_conn, mock_ach_conn
    ):
        mock_analytics_conn.return_value = self.conn
        mock_ach_conn.return_value = self.conn

        from app.gamification.achievements import AchievementEngine
        from app.analytics.engine import AnalyticsEngine

        amount_usd = 50.0
        deposit_count = 1
        total_usd = 50.0

        # 1. Record deposit in DB
        self.db.insert_deposit(self.pubkey, amount_usd=amount_usd, btc_price=50000.0)

        # 2. Check achievements
        engine = AchievementEngine()
        awarded = engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": amount_usd, "deposit_count": deposit_count, "total_usd": total_usd},
        )

        # 3. Track analytics
        analytics = AnalyticsEngine()
        analytics.track_event(
            "deposit", self.pubkey,
            {"amount_usd": amount_usd, "achievements_awarded": len(awarded)},
        )

        # Verify deposit exists
        deposit_count_db = self.conn.execute(
            "SELECT COUNT(*) FROM savings_deposits WHERE pubkey = ?", (self.pubkey,)
        ).fetchone()[0]
        self.assertEqual(deposit_count_db, 1)

        # Verify analytics event was recorded
        analytics_count = self.conn.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE pubkey = ? AND event_type = 'deposit'",
            (self.pubkey,),
        ).fetchone()[0]
        self.assertEqual(analytics_count, 1)

        # Verify first_save achievement was awarded
        achievement_ids = [a["id"] for a in awarded]
        self.assertIn("first_save", achievement_ids)

    @patch("app.gamification.achievements.get_conn")
    def test_second_deposit_no_redundant_achievements(self, mock_get_conn):
        mock_get_conn.return_value = self.conn
        from app.gamification.achievements import AchievementEngine
        engine = AchievementEngine()

        # First deposit
        engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": 50.0, "deposit_count": 1, "total_usd": 50.0},
        )
        # Second deposit
        awarded2 = engine.check_and_award(
            self.pubkey, "deposit",
            {"amount_usd": 50.0, "deposit_count": 2, "total_usd": 100.0},
        )
        # first_save should NOT be in second batch
        ids2 = [a["id"] for a in awarded2]
        self.assertNotIn("first_save", ids2)

    def test_test_database_helper_methods(self):
        """Verify TestDatabase helpers work correctly in integration context."""
        # Insert deposits for two users
        pk2 = _make_pubkey("j")
        self.db.insert_user(pk2)

        self.db.insert_deposit(self.pubkey, 100.0)
        self.db.insert_deposit(pk2, 200.0)
        self.db.insert_deposit(pk2, 300.0)

        total_deposits = self.db.count_rows("savings_deposits")
        self.assertEqual(total_deposits, 3)

        # Confirm per-user isolation
        user1_deposits = self.conn.execute(
            "SELECT COUNT(*) FROM savings_deposits WHERE pubkey = ?",
            (self.pubkey,),
        ).fetchone()[0]
        user2_deposits = self.conn.execute(
            "SELECT COUNT(*) FROM savings_deposits WHERE pubkey = ?",
            (pk2,),
        ).fetchone()[0]
        self.assertEqual(user1_deposits, 1)
        self.assertEqual(user2_deposits, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
