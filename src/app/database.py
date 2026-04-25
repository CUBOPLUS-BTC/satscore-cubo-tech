import sqlite3
import threading
from .config import settings

_local = threading.local()


def _pg_sql(sql: str) -> str:
    """Adapt SQLite SQL to PostgreSQL: AUTOINCREMENT -> SERIAL, REAL -> DOUBLE PRECISION."""
    s = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    s = s.replace("REAL", "DOUBLE PRECISION")
    return s


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


def _is_postgres() -> bool:
    return settings.DATABASE_URL.startswith(
        "postgresql://"
    ) or settings.DATABASE_URL.startswith("postgres://")


class _PgCursorWrapper:
    """Wraps a psycopg2 cursor so fetchall/fetchone return tuple-indexable rows."""

    def __init__(self, cur):
        self._cur = cur

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", -1)

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        self._cur.close()


class PgConnWrapper:
    """Wraps a psycopg2 connection so conn.execute() works like SQLite."""

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        cur.execute(_pg_sql(sql), params)
        return _PgCursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()

    @property
    def autocommit(self):
        return self._conn.autocommit

    @autocommit.setter
    def autocommit(self, val):
        self._conn.autocommit = val


def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        if _is_postgres():
            import psycopg2

            raw = psycopg2.connect(settings.DATABASE_URL)
            raw.autocommit = False
            _local.conn = PgConnWrapper(raw)
        else:
            url = settings.DATABASE_URL
            path = (
                url[len("sqlite:///") :]
                if url.startswith("sqlite:///")
                else "./magma.db"
            )
            _local.conn = sqlite3.connect(path, check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
    return _local.conn


def _migrate_users_table(conn) -> None:
    """Add auth_method column if upgrading from old schema."""
    try:
        conn.execute("SELECT auth_method FROM users LIMIT 1")
    except Exception:
        conn.rollback()
        conn.execute(
            "ALTER TABLE users ADD COLUMN auth_method TEXT NOT NULL DEFAULT 'lnurl'"
        )
        conn.commit()


def init_db() -> None:
    conn = get_conn()
    conn.execute(_CREATE_USERS)
    conn.execute(_CREATE_USER_PREFERENCES)
    conn.execute(_CREATE_SAVINGS_GOALS)
    conn.execute(_pg_sql(_CREATE_SAVINGS_DEPOSITS) if _is_postgres() else _CREATE_SAVINGS_DEPOSITS)
    conn.execute(_CREATE_USER_ACHIEVEMENTS)
    conn.commit()
    _migrate_users_table(conn)
