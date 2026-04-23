"""
Migration registry for Magma.

Each migration is a dict:
    {
        "id":         str   — zero-padded monotonic counter, e.g. "0001"
        "name":       str   — human-readable description
        "sql_up":     str   — SQL to apply the migration
        "sql_down":   str   — SQL to reverse the migration
        "created_at": str   — ISO-8601 date string
    }

Rules:
- Migrations are append-only; never modify an existing entry.
- sql_down must cleanly reverse sql_up.
- Every migration must be idempotent when applied via the runner (the runner
  tracks applied migrations in the _migrations table and will not re-apply).
"""

MIGRATIONS: list[dict] = [
    # ------------------------------------------------------------------
    # 0001 — core users table
    # ------------------------------------------------------------------
    {
        "id": "0001",
        "name": "create_users_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS users (
                pubkey      TEXT PRIMARY KEY,
                auth_method TEXT NOT NULL DEFAULT 'lnurl',
                created_at  INTEGER NOT NULL
            );
        """,
        "sql_down": "DROP TABLE IF EXISTS users;",
        "created_at": "2025-01-01",
    },
    # ------------------------------------------------------------------
    # 0002 — user preferences
    # ------------------------------------------------------------------
    {
        "id": "0002",
        "name": "create_user_preferences_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS user_preferences (
                pubkey         TEXT PRIMARY KEY,
                fee_alert_low  INTEGER NOT NULL DEFAULT 5,
                fee_alert_high INTEGER NOT NULL DEFAULT 50,
                price_alerts   TEXT    NOT NULL DEFAULT '[]',
                alerts_enabled INTEGER NOT NULL DEFAULT 1,
                updated_at     INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
        """,
        "sql_down": "DROP TABLE IF EXISTS user_preferences;",
        "created_at": "2025-01-01",
    },
    # ------------------------------------------------------------------
    # 0003 — savings goals
    # ------------------------------------------------------------------
    {
        "id": "0003",
        "name": "create_savings_goals_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS savings_goals (
                pubkey             TEXT PRIMARY KEY,
                monthly_target_usd REAL    NOT NULL,
                target_years       INTEGER NOT NULL DEFAULT 10,
                created_at         INTEGER NOT NULL,
                updated_at         INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
        """,
        "sql_down": "DROP TABLE IF EXISTS savings_goals;",
        "created_at": "2025-01-01",
    },
    # ------------------------------------------------------------------
    # 0004 — savings deposits
    # ------------------------------------------------------------------
    {
        "id": "0004",
        "name": "create_savings_deposits_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS savings_deposits (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey     TEXT    NOT NULL,
                amount_usd REAL    NOT NULL,
                btc_price  REAL    NOT NULL,
                btc_amount REAL    NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_savings_deposits_pubkey
                ON savings_deposits (pubkey);
            CREATE INDEX IF NOT EXISTS idx_savings_deposits_created_at
                ON savings_deposits (created_at);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_savings_deposits_created_at;
            DROP INDEX IF EXISTS idx_savings_deposits_pubkey;
            DROP TABLE IF EXISTS savings_deposits;
        """,
        "created_at": "2025-01-01",
    },
    # ------------------------------------------------------------------
    # 0005 — user achievements
    # ------------------------------------------------------------------
    {
        "id": "0005",
        "name": "create_user_achievements_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS user_achievements (
                pubkey         TEXT    NOT NULL,
                achievement_id TEXT    NOT NULL,
                awarded_at     INTEGER NOT NULL,
                PRIMARY KEY (pubkey, achievement_id),
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_user_achievements_pubkey
                ON user_achievements (pubkey);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_user_achievements_pubkey;
            DROP TABLE IF EXISTS user_achievements;
        """,
        "created_at": "2025-01-01",
    },
    # ------------------------------------------------------------------
    # 0006 — scoring history
    # ------------------------------------------------------------------
    {
        "id": "0006",
        "name": "create_scoring_history_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS scoring_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey     TEXT    NOT NULL,
                address    TEXT    NOT NULL,
                score      INTEGER NOT NULL,
                grade      TEXT    NOT NULL,
                checked_at INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_scoring_history_pubkey
                ON scoring_history (pubkey);
            CREATE INDEX IF NOT EXISTS idx_scoring_history_address
                ON scoring_history (address);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_scoring_history_address;
            DROP INDEX IF EXISTS idx_scoring_history_pubkey;
            DROP TABLE IF EXISTS scoring_history;
        """,
        "created_at": "2025-01-15",
    },
    # ------------------------------------------------------------------
    # 0007 — analytics events
    # ------------------------------------------------------------------
    {
        "id": "0007",
        "name": "create_analytics_events_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey     TEXT,
                event_type TEXT    NOT NULL,
                event_data TEXT    NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_analytics_events_type
                ON analytics_events (event_type);
            CREATE INDEX IF NOT EXISTS idx_analytics_events_pubkey
                ON analytics_events (pubkey);
            CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at
                ON analytics_events (created_at);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_analytics_events_created_at;
            DROP INDEX IF EXISTS idx_analytics_events_pubkey;
            DROP INDEX IF EXISTS idx_analytics_events_type;
            DROP TABLE IF EXISTS analytics_events;
        """,
        "created_at": "2025-02-01",
    },
    # ------------------------------------------------------------------
    # 0008 — scheduled tasks
    # ------------------------------------------------------------------
    {
        "id": "0008",
        "name": "create_scheduled_tasks_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name    TEXT    NOT NULL,
                cron_expr    TEXT    NOT NULL,
                last_run_at  INTEGER,
                next_run_at  INTEGER NOT NULL,
                is_enabled   INTEGER NOT NULL DEFAULT 1,
                run_count    INTEGER NOT NULL DEFAULT 0,
                error_count  INTEGER NOT NULL DEFAULT 0,
                last_error   TEXT,
                created_at   INTEGER NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_tasks_name
                ON scheduled_tasks (task_name);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_scheduled_tasks_name;
            DROP TABLE IF EXISTS scheduled_tasks;
        """,
        "created_at": "2025-02-15",
    },
    # ------------------------------------------------------------------
    # 0009 — webhook subscriptions
    # ------------------------------------------------------------------
    {
        "id": "0009",
        "name": "create_webhook_subscriptions_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS webhook_subscriptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey      TEXT NOT NULL,
                url         TEXT NOT NULL,
                event_types TEXT NOT NULL DEFAULT '[]',
                secret      TEXT NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  INTEGER NOT NULL,
                updated_at  INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_webhook_subs_pubkey
                ON webhook_subscriptions (pubkey);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_webhook_subs_pubkey;
            DROP TABLE IF EXISTS webhook_subscriptions;
        """,
        "created_at": "2025-03-01",
    },
    # ------------------------------------------------------------------
    # 0010 — rate limits
    # ------------------------------------------------------------------
    {
        "id": "0010",
        "name": "create_rate_limits_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS rate_limits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier  TEXT    NOT NULL,
                endpoint    TEXT    NOT NULL,
                request_count INTEGER NOT NULL DEFAULT 0,
                window_start  INTEGER NOT NULL,
                window_end    INTEGER NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limits_identifier_endpoint
                ON rate_limits (identifier, endpoint, window_start);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_rate_limits_identifier_endpoint;
            DROP TABLE IF EXISTS rate_limits;
        """,
        "created_at": "2025-03-15",
    },
    # ------------------------------------------------------------------
    # 0011 — add last_login to users
    # ------------------------------------------------------------------
    {
        "id": "0011",
        "name": "add_last_login_to_users",
        "sql_up": """
            ALTER TABLE users ADD COLUMN last_login_at INTEGER;
        """,
        "sql_down": """
            -- SQLite does not support DROP COLUMN on older versions;
            -- create new table without the column and rename.
            CREATE TABLE users_backup AS SELECT pubkey, auth_method, created_at FROM users;
            DROP TABLE users;
            ALTER TABLE users_backup RENAME TO users;
        """,
        "created_at": "2025-04-01",
    },
    # ------------------------------------------------------------------
    # 0012 — add note to savings_deposits
    # ------------------------------------------------------------------
    {
        "id": "0012",
        "name": "add_note_to_savings_deposits",
        "sql_up": """
            ALTER TABLE savings_deposits ADD COLUMN note TEXT;
        """,
        "sql_down": """
            CREATE TABLE savings_deposits_backup AS
                SELECT id, pubkey, amount_usd, btc_price, btc_amount, created_at
                FROM savings_deposits;
            DROP TABLE savings_deposits;
            ALTER TABLE savings_deposits_backup RENAME TO savings_deposits;
        """,
        "created_at": "2025-04-15",
    },
]
