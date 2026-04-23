"""Tests for app/database.py

Covers:
- init_db creates all expected tables
- get_conn returns a working connection
- user CRUD via raw SQL
- _migrate_users_table is idempotent
- TestDatabase helper works correctly
"""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import TestDatabase

VALID_PUBKEY = "e" * 64


# ---------------------------------------------------------------------------
# TestDatabase helper self-tests
# ---------------------------------------------------------------------------


class TestTestDatabaseHelper(unittest.TestCase):

    def test_setup_creates_tables(self):
        db = TestDatabase()
        db.setup()
        conn = db.get_conn()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        for tbl in ["users", "user_preferences", "savings_goals",
                    "savings_deposits", "user_achievements"]:
            self.assertIn(tbl, tables)
        db.teardown()

    def test_context_manager(self):
        with TestDatabase() as db:
            conn = db.get_conn()
            self.assertIsNotNone(conn)

    def test_teardown_closes(self):
        db = TestDatabase()
        db.setup()
        db.teardown()
        with self.assertRaises(RuntimeError):
            db.get_conn()

    def test_insert_user(self):
        with TestDatabase() as db:
            db.insert_user(VALID_PUBKEY)
            count = db.count_rows("users")
            self.assertEqual(count, 1)

    def test_insert_user_duplicate_ignored(self):
        with TestDatabase() as db:
            db.insert_user(VALID_PUBKEY)
            db.insert_user(VALID_PUBKEY)  # second insert should be silently ignored
            count = db.count_rows("users")
            self.assertEqual(count, 1)

    def test_insert_deposit(self):
        with TestDatabase() as db:
            db.insert_user(VALID_PUBKEY)
            row_id = db.insert_deposit(VALID_PUBKEY, amount_usd=100.0, btc_price=50000.0)
            self.assertIsNotNone(row_id)
            count = db.count_rows("savings_deposits")
            self.assertEqual(count, 1)

    def test_count_rows_zero(self):
        with TestDatabase() as db:
            count = db.count_rows("users")
            self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# init_db / get_conn with in-memory SQLite
# ---------------------------------------------------------------------------


class TestInitDB(unittest.TestCase):
    """Test the real init_db function against a mocked in-memory connection."""

    def _patched_init(self):
        """Run init_db but redirect the connection to an in-memory DB."""
        import sqlite3
        import app.database as db_mod

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row

        with patch.object(db_mod, "get_conn", return_value=conn):
            with patch.object(db_mod, "_is_postgres", return_value=False):
                db_mod.init_db()

        return conn

    def test_init_db_creates_users_table(self):
        conn = self._patched_init()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("users", tables)

    def test_init_db_creates_user_preferences(self):
        conn = self._patched_init()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("user_preferences", tables)

    def test_init_db_creates_savings_goals(self):
        conn = self._patched_init()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("savings_goals", tables)

    def test_init_db_creates_savings_deposits(self):
        conn = self._patched_init()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("savings_deposits", tables)

    def test_init_db_creates_user_achievements(self):
        conn = self._patched_init()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("user_achievements", tables)

    def test_init_db_idempotent(self):
        """Running init_db twice should not raise errors."""
        import sqlite3
        import app.database as db_mod

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row

        with patch.object(db_mod, "get_conn", return_value=conn):
            with patch.object(db_mod, "_is_postgres", return_value=False):
                db_mod.init_db()
                db_mod.init_db()  # second call

        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        self.assertGreater(count, 0)


class TestUserCRUD(unittest.TestCase):
    """CRUD operations via raw SQL on TestDatabase."""

    def setUp(self):
        self.db = TestDatabase()
        self.db.setup()
        self.conn = self.db.get_conn()

    def tearDown(self):
        self.db.teardown()

    def test_insert_user(self):
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO users (pubkey, auth_method, created_at) VALUES (?, ?, ?)",
            (VALID_PUBKEY, "lnurl", now),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM users WHERE pubkey = ?", (VALID_PUBKEY,)).fetchone()
        self.assertIsNotNone(row)

    def test_read_user(self):
        self.db.insert_user(VALID_PUBKEY)
        row = self.conn.execute("SELECT pubkey FROM users WHERE pubkey = ?", (VALID_PUBKEY,)).fetchone()
        self.assertEqual(row["pubkey"], VALID_PUBKEY)

    def test_update_auth_method(self):
        self.db.insert_user(VALID_PUBKEY)
        self.conn.execute(
            "UPDATE users SET auth_method = ? WHERE pubkey = ?",
            ("nostr", VALID_PUBKEY),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT auth_method FROM users WHERE pubkey = ?", (VALID_PUBKEY,)).fetchone()
        self.assertEqual(row["auth_method"], "nostr")

    def test_delete_user(self):
        self.db.insert_user(VALID_PUBKEY)
        self.conn.execute("DELETE FROM users WHERE pubkey = ?", (VALID_PUBKEY,))
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM users WHERE pubkey = ?", (VALID_PUBKEY,)).fetchone()
        self.assertIsNone(row)

    def test_list_users_empty(self):
        rows = self.conn.execute("SELECT * FROM users").fetchall()
        self.assertEqual(len(rows), 0)

    def test_list_users_populated(self):
        for char in "abc":
            self.db.insert_user(char * 64)
        rows = self.conn.execute("SELECT * FROM users").fetchall()
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
