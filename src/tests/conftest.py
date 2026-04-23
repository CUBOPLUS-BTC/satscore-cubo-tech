"""
Shared test helpers and fixtures for the Magma test suite.

Provides:
- TestDatabase: in-memory SQLite database for isolated tests
- MockHTTPResponse: simulate urllib HTTP responses
- create_test_user: insert a minimal user row
- generate_test_token: create a deterministic session token
"""

import sqlite3
import secrets
import time
import threading
from typing import Optional
from io import BytesIO


# ---------------------------------------------------------------------------
# In-memory database helper
# ---------------------------------------------------------------------------

_CREATE_USERS = """
    CREATE TABLE IF NOT EXISTS users (
        pubkey TEXT PRIMARY KEY,
        auth_method TEXT NOT NULL DEFAULT 'lnurl',
        created_at INTEGER NOT NULL
    )
"""

_CREATE_USER_PREFERENCES = """
    CREATE TABLE IF NOT EXISTS user_preferences (
        pubkey TEXT PRIMARY KEY,
        fee_alert_low INTEGER NOT NULL DEFAULT 5,
        fee_alert_high INTEGER NOT NULL DEFAULT 50,
        price_alerts TEXT NOT NULL DEFAULT '[]',
        alerts_enabled INTEGER NOT NULL DEFAULT 1,
        updated_at INTEGER NOT NULL
    )
"""

_CREATE_SAVINGS_GOALS = """
    CREATE TABLE IF NOT EXISTS savings_goals (
        pubkey TEXT PRIMARY KEY,
        monthly_target_usd REAL NOT NULL,
        target_years INTEGER NOT NULL DEFAULT 10,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )
"""

_CREATE_SAVINGS_DEPOSITS = """
    CREATE TABLE IF NOT EXISTS savings_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pubkey TEXT NOT NULL,
        amount_usd REAL NOT NULL,
        btc_price REAL NOT NULL,
        btc_amount REAL NOT NULL,
        created_at INTEGER NOT NULL
    )
"""

_CREATE_USER_ACHIEVEMENTS = """
    CREATE TABLE IF NOT EXISTS user_achievements (
        pubkey TEXT NOT NULL,
        achievement_id TEXT NOT NULL,
        awarded_at INTEGER NOT NULL,
        PRIMARY KEY (pubkey, achievement_id)
    )
"""

_CREATE_SCORING_HISTORY = """
    CREATE TABLE IF NOT EXISTS scoring_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pubkey TEXT NOT NULL,
        address TEXT NOT NULL,
        score INTEGER NOT NULL,
        grade TEXT NOT NULL,
        checked_at INTEGER NOT NULL
    )
"""


class TestDatabase:
    """Creates and manages an in-memory SQLite database for testing.

    Usage::

        db = TestDatabase()
        db.setup()
        conn = db.get_conn()
        # ... run queries ...
        db.teardown()

    Can also be used as a context manager::

        with TestDatabase() as db:
            conn = db.get_conn()
            ...
    """

    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def setup(self) -> None:
        """Create all tables in memory."""
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._apply_schema()

    def _apply_schema(self) -> None:
        assert self._conn is not None
        for ddl in [
            _CREATE_USERS,
            _CREATE_USER_PREFERENCES,
            _CREATE_SAVINGS_GOALS,
            _CREATE_SAVINGS_DEPOSITS,
            _CREATE_USER_ACHIEVEMENTS,
            _CREATE_SCORING_HISTORY,
        ]:
            self._conn.execute(ddl)
        self._conn.commit()

    def get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("TestDatabase not set up — call .setup() first")
        return self._conn

    def teardown(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "TestDatabase":
        self.setup()
        return self

    def __exit__(self, *_) -> None:
        self.teardown()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def insert_user(self, pubkey: str, auth_method: str = "lnurl") -> None:
        now = int(time.time())
        self._conn.execute(
            "INSERT OR IGNORE INTO users (pubkey, auth_method, created_at) VALUES (?, ?, ?)",
            (pubkey, auth_method, now),
        )
        self._conn.commit()

    def insert_deposit(
        self,
        pubkey: str,
        amount_usd: float = 100.0,
        btc_price: float = 50000.0,
        created_at: Optional[int] = None,
    ) -> int:
        btc_amount = amount_usd / btc_price
        ts = created_at or int(time.time())
        cur = self._conn.execute(
            "INSERT INTO savings_deposits (pubkey, amount_usd, btc_price, btc_amount, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (pubkey, amount_usd, btc_price, btc_amount, ts),
        )
        self._conn.commit()
        return cur.lastrowid

    def count_rows(self, table: str) -> int:
        row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# Mock HTTP response
# ---------------------------------------------------------------------------


class MockHTTPResponse:
    """Mimic the file-like object returned by urllib.request.urlopen.

    Usage::

        mock = MockHTTPResponse(b'{"price": 60000}', status=200)
        # patch urllib.request.urlopen to return mock
    """

    def __init__(
        self,
        body: bytes = b"",
        status: int = 200,
        headers: Optional[dict] = None,
    ):
        self.body = body
        self.status = status
        self._headers = headers or {"Content-Type": "application/json"}
        self._stream = BytesIO(body)

    # ---- file-like interface ----

    def read(self, n: int = -1) -> bytes:
        return self._stream.read(n)

    def readline(self) -> bytes:
        return self._stream.readline()

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    # ---- context manager ----

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        pass

    # ---- urllib compat ----

    def getcode(self) -> int:
        return self.status

    def getheader(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self._headers.get(name, default)

    def info(self):
        return self._headers


# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------

_VALID_PUBKEY = "a" * 64  # 64 lowercase hex chars


def create_test_user(pubkey: Optional[str] = None) -> dict:
    """Return a dict representing a minimal user row.

    Does NOT insert into any database — use TestDatabase.insert_user for that.
    """
    if pubkey is None:
        pubkey = secrets.token_hex(32)  # random valid 64-char hex pubkey
    return {
        "pubkey": pubkey,
        "auth_method": "lnurl",
        "created_at": int(time.time()),
    }


def generate_test_token() -> str:
    """Return a 64-character hex token (same format as real session tokens)."""
    return secrets.token_hex(32)


def make_hex_pubkey(char: str = "a") -> str:
    """Return a valid 64-char hex pubkey filled with the given character."""
    assert len(char) == 1 and char in "0123456789abcdefABCDEF"
    return char * 64


def make_price_history(
    start_price: float = 30000.0,
    end_price: float = 60000.0,
    num_days: int = 365,
) -> list:
    """Generate synthetic [[timestamp_ms, price], ...] data for projector tests."""
    now_ms = int(time.time() * 1000)
    step_ms = 86400 * 1000
    prices = []
    for i in range(num_days):
        ts = now_ms - (num_days - i) * step_ms
        frac = i / max(num_days - 1, 1)
        price = start_price + (end_price - start_price) * frac
        prices.append([ts, price])
    return prices
