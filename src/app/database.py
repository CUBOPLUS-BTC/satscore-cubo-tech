import sqlite3
import threading
from .config import settings

_local = threading.local()

_CREATE_USERS = """
    CREATE TABLE IF NOT EXISTS users (
        pubkey TEXT PRIMARY KEY,
        created_at INTEGER NOT NULL
    )
"""


def _is_postgres() -> bool:
    return settings.DATABASE_URL.startswith("postgresql://") or \
           settings.DATABASE_URL.startswith("postgres://")


def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        if _is_postgres():
            import psycopg2
            import psycopg2.extras
            _local.conn = psycopg2.connect(settings.DATABASE_URL)
            _local.conn.autocommit = False
        else:
            url = settings.DATABASE_URL
            path = url[len("sqlite:///"):] if url.startswith("sqlite:///") else "./vulk.db"
            _local.conn = sqlite3.connect(path, check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    conn = get_conn()
    conn.execute(_CREATE_USERS)
    conn.commit()
