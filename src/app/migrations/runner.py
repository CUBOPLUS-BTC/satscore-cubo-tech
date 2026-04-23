"""
MigrationRunner — applies and rolls back database migrations for Magma.

The runner tracks which migrations have been applied in a `_migrations` table
that it creates on first use. All operations are thread-safe via a module-level
lock.

Usage::

    from app.migrations.runner import MigrationRunner
    from app.database import get_conn

    runner = MigrationRunner(get_conn())
    runner.apply_all()

    # Or from the CLI:
    status = runner.get_status()
    for row in status["pending"]:
        print(f"  pending: {row['id']} — {row['name']}")
"""

import threading
import time
import logging
from typing import Optional

from .registry import MIGRATIONS

logger = logging.getLogger(__name__)

_global_lock = threading.Lock()

_CREATE_MIGRATIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS _migrations (
        id          TEXT PRIMARY KEY,
        name        TEXT    NOT NULL,
        applied_at  INTEGER NOT NULL,
        duration_ms INTEGER NOT NULL DEFAULT 0
    )
"""


class MigrationError(Exception):
    """Raised when a migration cannot be applied or rolled back."""
    pass


class MigrationRunner:
    """Manages schema migrations for the Magma SQLite/PostgreSQL database.

    Args:
        conn: An active database connection (sqlite3 or psycopg2).
        is_postgres: Set to True when connecting to PostgreSQL. Defaults to
            False (SQLite mode). The runner adjusts placeholder syntax
            accordingly.
    """

    def __init__(self, conn, is_postgres: bool = False):
        self._conn = conn
        self._is_postgres = is_postgres
        self._lock = _global_lock
        self._ensure_migrations_table()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_applied(self) -> list[dict]:
        """Return a list of already-applied migrations, oldest first.

        Returns:
            List of dicts: {id, name, applied_at, duration_ms}
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, applied_at, duration_ms "
                "FROM _migrations ORDER BY applied_at ASC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_pending(self) -> list[dict]:
        """Return migrations that have not yet been applied, oldest first.

        Returns:
            List of migration dicts from the registry.
        """
        applied_ids = {m["id"] for m in self.get_applied()}
        return [m for m in MIGRATIONS if m["id"] not in applied_ids]

    def apply(self, migration_id: str) -> dict:
        """Apply a single migration by ID.

        Args:
            migration_id: The migration ID string (e.g. "0003").

        Returns:
            dict with keys: id, name, applied_at, duration_ms

        Raises:
            MigrationError: If the migration is already applied, not found,
                or SQL execution fails.
        """
        migration = self._find(migration_id)
        if migration is None:
            raise MigrationError(f"Migration {migration_id!r} not found in registry")

        applied_ids = {m["id"] for m in self.get_applied()}
        if migration_id in applied_ids:
            raise MigrationError(f"Migration {migration_id!r} is already applied")

        logger.info("Applying migration %s — %s", migration_id, migration["name"])

        with self._lock:
            start_ms = int(time.time() * 1000)
            try:
                # Execute each SQL statement individually to handle multi-statement
                # migrations (SQLite executescript semantics are different from
                # execute; we split on ";" to support both backends cleanly).
                for stmt in self._split_sql(migration["sql_up"]):
                    self._conn.execute(stmt)

                applied_at = int(time.time())
                duration_ms = int(time.time() * 1000) - start_ms

                ph = self._ph()
                self._conn.execute(
                    f"INSERT INTO _migrations (id, name, applied_at, duration_ms) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph})",
                    (migration_id, migration["name"], applied_at, duration_ms),
                )
                self._conn.commit()

                logger.info(
                    "Applied migration %s in %d ms", migration_id, duration_ms
                )
                return {
                    "id": migration_id,
                    "name": migration["name"],
                    "applied_at": applied_at,
                    "duration_ms": duration_ms,
                }
            except Exception as exc:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
                logger.error("Migration %s failed: %s", migration_id, exc)
                raise MigrationError(
                    f"Migration {migration_id!r} failed: {exc}"
                ) from exc

    def apply_all(self) -> list[dict]:
        """Apply all pending migrations in order.

        Returns:
            List of results from each apply() call.
        """
        pending = self.get_pending()
        if not pending:
            logger.info("No pending migrations")
            return []

        results = []
        for migration in pending:
            result = self.apply(migration["id"])
            results.append(result)
        return results

    def rollback(self, migration_id: str) -> dict:
        """Roll back a single migration by ID.

        The migration must be the most recently applied migration (you cannot
        roll back out of order — use rollback_to for multiple steps).

        Args:
            migration_id: The migration ID string.

        Returns:
            dict with keys: id, name, rolled_back_at

        Raises:
            MigrationError: If the migration was not applied, not found, or
                rollback SQL fails.
        """
        migration = self._find(migration_id)
        if migration is None:
            raise MigrationError(f"Migration {migration_id!r} not found in registry")

        applied = self.get_applied()
        applied_ids = [m["id"] for m in applied]
        if migration_id not in applied_ids:
            raise MigrationError(f"Migration {migration_id!r} is not applied")

        # Enforce strict ordering: only the last applied can be rolled back here
        # (for multi-step, use rollback_to)
        if applied_ids[-1] != migration_id:
            raise MigrationError(
                f"Migration {migration_id!r} is not the latest applied migration. "
                f"Latest is {applied_ids[-1]!r}. "
                f"Use rollback_to() to roll back multiple migrations."
            )

        logger.info("Rolling back migration %s — %s", migration_id, migration["name"])

        with self._lock:
            try:
                for stmt in self._split_sql(migration["sql_down"]):
                    self._conn.execute(stmt)

                ph = self._ph()
                self._conn.execute(
                    f"DELETE FROM _migrations WHERE id = {ph}", (migration_id,)
                )
                self._conn.commit()

                rolled_back_at = int(time.time())
                logger.info("Rolled back migration %s", migration_id)
                return {
                    "id": migration_id,
                    "name": migration["name"],
                    "rolled_back_at": rolled_back_at,
                }
            except Exception as exc:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
                logger.error("Rollback of %s failed: %s", migration_id, exc)
                raise MigrationError(
                    f"Rollback of {migration_id!r} failed: {exc}"
                ) from exc

    def rollback_to(self, target_migration_id: str) -> list[dict]:
        """Roll back all migrations applied after (and including) the target.

        Example: if applied = [0001, 0002, 0003, 0004] and target = "0002",
        this rolls back 0004, 0003, 0002 in reverse order.

        Args:
            target_migration_id: Roll back to just before this migration.
                All migrations >= target are reversed.

        Returns:
            List of rollback result dicts.
        """
        applied = self.get_applied()
        applied_ids = [m["id"] for m in applied]

        if target_migration_id not in applied_ids:
            raise MigrationError(
                f"Target migration {target_migration_id!r} is not in the applied set"
            )

        # Collect everything from target onwards, reversed
        target_idx = applied_ids.index(target_migration_id)
        to_rollback = list(reversed(applied_ids[target_idx:]))

        results = []
        for mid in to_rollback:
            result = self.rollback(mid)
            results.append(result)
        return results

    def get_status(self) -> dict:
        """Return a comprehensive status report of the migration state.

        Returns:
            dict with keys:
                applied: list of applied migration dicts
                pending: list of pending migration dicts
                total: total migration count in registry
                applied_count: number applied
                pending_count: number pending
                latest_applied: id of the most recently applied migration, or None
                is_up_to_date: True when no pending migrations remain
        """
        applied = self.get_applied()
        pending = self.get_pending()
        latest = applied[-1]["id"] if applied else None

        return {
            "applied": applied,
            "pending": pending,
            "total": len(MIGRATIONS),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "latest_applied": latest,
            "is_up_to_date": len(pending) == 0,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_migrations_table(self) -> None:
        """Create the _migrations tracking table if it does not exist."""
        with self._lock:
            self._conn.execute(_CREATE_MIGRATIONS_TABLE)
            self._conn.commit()

    def _find(self, migration_id: str) -> Optional[dict]:
        """Return the migration dict for the given ID, or None."""
        for m in MIGRATIONS:
            if m["id"] == migration_id:
                return m
        return None

    def _ph(self) -> str:
        """Return the SQL placeholder for the current backend."""
        return "%s" if self._is_postgres else "?"

    @staticmethod
    def _split_sql(sql: str) -> list[str]:
        """Split a multi-statement SQL string into individual statements.

        Strips comments (single-line starting with --) and empty statements.
        """
        statements = []
        for raw in sql.split(";"):
            # Strip comment lines
            lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
            stmt = " ".join(lines).strip()
            if stmt:
                statements.append(stmt)
        return statements

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a DB row (tuple or Row object) to a plain dict."""
        if hasattr(row, "keys"):
            return dict(row)
        return {
            "id": row[0],
            "name": row[1],
            "applied_at": row[2],
            "duration_ms": row[3],
        }
