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
    # ------------------------------------------------------------------
    # 0013 — remittance recipients
    # ------------------------------------------------------------------
    {
        "id": "0013",
        "name": "create_recipients_table",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS recipients (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey              TEXT    NOT NULL,
                name                TEXT    NOT NULL,
                lightning_address   TEXT    NOT NULL,
                country             TEXT    NOT NULL DEFAULT 'SV',
                default_amount_usd  REAL,
                min_sendable_msat   INTEGER,
                max_sendable_msat   INTEGER,
                created_at          INTEGER NOT NULL,
                updated_at          INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_recipients_pubkey
                ON recipients (pubkey);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_recipients_pubkey;
            DROP TABLE IF EXISTS recipients;
        """,
        "created_at": "2026-04-23",
    },
    # ------------------------------------------------------------------
    # 0014 — remittance reminders
    # ------------------------------------------------------------------
    {
        "id": "0014",
        "name": "create_reminders_and_events_tables",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS reminders (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey         TEXT    NOT NULL,
                recipient_id   INTEGER NOT NULL,
                cadence        TEXT    NOT NULL DEFAULT 'monthly',
                day_of_month   INTEGER NOT NULL DEFAULT 1,
                hour_local     INTEGER NOT NULL DEFAULT 9,
                timezone       TEXT    NOT NULL DEFAULT 'America/El_Salvador',
                channels       TEXT    NOT NULL DEFAULT '["webhook"]',
                paused         INTEGER NOT NULL DEFAULT 0,
                next_fire_at   INTEGER NOT NULL,
                last_fired_at  INTEGER,
                fire_count     INTEGER NOT NULL DEFAULT 0,
                created_at     INTEGER NOT NULL,
                updated_at     INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE,
                FOREIGN KEY (recipient_id) REFERENCES recipients(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_reminders_pubkey
                ON reminders (pubkey);
            CREATE INDEX IF NOT EXISTS idx_reminders_next_fire
                ON reminders (next_fire_at, paused);
            CREATE TABLE IF NOT EXISTS reminder_events (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id   INTEGER NOT NULL,
                channel       TEXT    NOT NULL,
                status        TEXT    NOT NULL,
                error         TEXT,
                fired_at      INTEGER NOT NULL,
                FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_reminder_events_reminder
                ON reminder_events (reminder_id);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_reminder_events_reminder;
            DROP TABLE IF EXISTS reminder_events;
            DROP INDEX IF EXISTS idx_reminders_next_fire;
            DROP INDEX IF EXISTS idx_reminders_pubkey;
            DROP TABLE IF EXISTS reminders;
        """,
        "created_at": "2026-04-23",
    },
    # ------------------------------------------------------------------
    # 0015 — email opt-in on user_preferences (for reminder email channel)
    # ------------------------------------------------------------------
    {
        "id": "0015",
        "name": "add_email_to_user_preferences",
        "sql_up": """
            ALTER TABLE user_preferences ADD COLUMN email TEXT;
        """,
        "sql_down": """
            CREATE TABLE user_preferences_backup AS
                SELECT pubkey, fee_alert_low, fee_alert_high,
                       price_alerts, alerts_enabled, updated_at
                FROM user_preferences;
            DROP TABLE user_preferences;
            ALTER TABLE user_preferences_backup RENAME TO user_preferences;
        """,
        "created_at": "2026-04-23",
    },
    # ------------------------------------------------------------------
    # 0016 — education progress + gamification state
    # ------------------------------------------------------------------
    {
        "id": "0016",
        "name": "create_education_progress_and_state",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS education_progress (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey          TEXT    NOT NULL,
                lesson_id       TEXT    NOT NULL,
                score_pct       REAL    NOT NULL,
                xp_earned       INTEGER NOT NULL DEFAULT 0,
                hearts_lost     INTEGER NOT NULL DEFAULT 0,
                completed_at    INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_education_progress_pubkey
                ON education_progress (pubkey);
            CREATE INDEX IF NOT EXISTS idx_education_progress_lesson
                ON education_progress (pubkey, lesson_id);
            CREATE TABLE IF NOT EXISTS education_state (
                pubkey                  TEXT PRIMARY KEY,
                xp_total                INTEGER NOT NULL DEFAULT 0,
                hearts                  INTEGER NOT NULL DEFAULT 5,
                hearts_max              INTEGER NOT NULL DEFAULT 5,
                hearts_last_refill_at   INTEGER NOT NULL DEFAULT 0,
                streak_days             INTEGER NOT NULL DEFAULT 0,
                streak_last_day         TEXT,
                daily_xp_goal           INTEGER NOT NULL DEFAULT 30,
                daily_xp_today          INTEGER NOT NULL DEFAULT 0,
                daily_xp_day            TEXT,
                created_at              INTEGER NOT NULL,
                updated_at              INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
        """,
        "sql_down": """
            DROP TABLE IF EXISTS education_state;
            DROP INDEX IF EXISTS idx_education_progress_lesson;
            DROP INDEX IF EXISTS idx_education_progress_pubkey;
            DROP TABLE IF EXISTS education_progress;
        """,
        "created_at": "2026-04-23",
    },
    # ------------------------------------------------------------------
    # 0017 — education game runs (Magma Miner)
    # ------------------------------------------------------------------
    {
        "id": "0017",
        "name": "create_education_game_runs",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS education_game_runs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey              TEXT    NOT NULL,
                score               INTEGER NOT NULL DEFAULT 0,
                blocks_mined        INTEGER NOT NULL DEFAULT 0,
                halvings_survived   INTEGER NOT NULL DEFAULT 0,
                duration_seconds    INTEGER NOT NULL DEFAULT 0,
                xp_earned           INTEGER NOT NULL DEFAULT 0,
                completed_at        INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_game_runs_pubkey
                ON education_game_runs (pubkey);
            CREATE INDEX IF NOT EXISTS idx_game_runs_score
                ON education_game_runs (score DESC);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_game_runs_score;
            DROP INDEX IF EXISTS idx_game_runs_pubkey;
            DROP TABLE IF EXISTS education_game_runs;
        """,
        "created_at": "2026-04-24",
    },
    # ------------------------------------------------------------------
    # 0018 — split profiles + rules (non-custodial remittance router)
    # ------------------------------------------------------------------
    {
        "id": "0018",
        "name": "create_split_profiles_and_rules",
        "sql_up": """
            CREATE TABLE IF NOT EXISTS split_profiles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey      TEXT    NOT NULL,
                label       TEXT    NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  INTEGER NOT NULL,
                updated_at  INTEGER NOT NULL,
                FOREIGN KEY (pubkey) REFERENCES users(pubkey) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_split_profiles_pubkey
                ON split_profiles (pubkey);

            CREATE TABLE IF NOT EXISTS split_rules (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id      INTEGER NOT NULL,
                recipient_id    INTEGER NOT NULL,
                percentage      INTEGER NOT NULL,
                priority        INTEGER NOT NULL DEFAULT 0,
                label           TEXT,
                created_at      INTEGER NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES split_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_id) REFERENCES recipients(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_split_rules_profile
                ON split_rules (profile_id);
        """,
        "sql_down": """
            DROP INDEX IF EXISTS idx_split_rules_profile;
            DROP TABLE IF EXISTS split_rules;
            DROP INDEX IF EXISTS idx_split_profiles_pubkey;
            DROP TABLE IF EXISTS split_profiles;
        """,
        "created_at": "2026-04-24",
    },
]
