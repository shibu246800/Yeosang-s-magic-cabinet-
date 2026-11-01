
"""Turso database connections for Magic Cabinet."""

import os
from contextlib import contextmanager

import turso_serverless


def _connect():
    database_url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not database_url or not auth_token:
        raise RuntimeError(
            "TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be configured."
        )

    return turso_serverless.connect(
        database_url,
        auth_token=auth_token,
    )


class DatabaseRow:
    """Supports both row['column'] and row[0] access."""

    def __init__(self, values, description):
        self._values = tuple(values)
        self._columns = [
            column[0] for column in (description or [])
        ]

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._values[self._columns.index(key)]
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._columns

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, ValueError, IndexError):
            return default


class DatabaseCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return getattr(self._cursor, "lastrowid", None)

    def _convert(self, row):
        if row is None:
            return None
        if isinstance(row, dict):
            return DatabaseRow(
                [row.get(column[0]) for column in self.description],
                self.description,
            )
        return DatabaseRow(row, self.description)

    def fetchone(self):
        return self._convert(self._cursor.fetchone())

    def fetchall(self):
        return [
            self._convert(row)
            for row in self._cursor.fetchall()
        ]

    def fetchmany(self, size=None):
        if size is None:
            rows = self._cursor.fetchmany()
        else:
            rows = self._cursor.fetchmany(size)

        return [self._convert(row) for row in rows]


class DatabaseConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, parameters=()):
        return DatabaseCursor(
            self._connection.execute(sql, parameters)
        )

    def executemany(self, sql, parameters):
        return DatabaseCursor(
            self._connection.executemany(sql, parameters)
        )

    def cursor(self):
        return DatabaseCursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


@contextmanager
def get_connection():
    """Open a Turso connection and safely commit or roll back."""

    raw_connection = _connect()
    connection = DatabaseConnection(raw_connection)

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    """Create all known Magic Cabinet tables without deleting data."""

    statements = [
        """
        CREATE TABLE IF NOT EXISTS drop_channels (
            guild_id INTEGER PRIMARY KEY,
            channel1_id INTEGER NOT NULL,
            channel2_id INTEGER,
            channel3_id INTEGER,
            channel4_id INTEGER,
            channel5_id INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            vault TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS player_vaults (
            user_id INTEGER NOT NULL,
            vault TEXT NOT NULL,
            PRIMARY KEY (user_id, vault)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            glimmers INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bag (
            user_id INTEGER NOT NULL,
            card_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, card_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_data (
            user_id INTEGER PRIMARY KEY,
            last_claim_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS booster_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            booster_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            activated_at TEXT,
            expires_at TEXT,
            uses_remaining INTEGER,
            source TEXT NOT NULL DEFAULT 'daily'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS player_badges (
            user_id INTEGER NOT NULL,
            badge_id TEXT NOT NULL,
            badge_name TEXT NOT NULL,
            badge_emote TEXT,
            PRIMARY KEY (user_id, badge_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS player_achievements (
            user_id INTEGER NOT NULL,
            achievement_id TEXT NOT NULL,
            achievement_name TEXT NOT NULL,
            global_rank INTEGER NOT NULL,
            PRIMARY KEY (user_id, achievement_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS player_card_inventory (
            user_id INTEGER NOT NULL,
            card_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
            PRIMARY KEY (user_id, card_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS weekly_challenges (
            user_id INTEGER PRIMARY KEY,
            week_started TEXT NOT NULL,
            task_data TEXT NOT NULL,
            guaranteed_claimed INTEGER NOT NULL DEFAULT 0,
            reward_claimed INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS weekly_progress (
            user_id INTEGER NOT NULL,
            task_id TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, task_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS weekly_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS weekly_delivery (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS weekly_pending_rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_type TEXT NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            task_id TEXT,
            claimed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS earn_data (
            user_id INTEGER PRIMARY KEY,
            last_claim_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS blind_boxes (
            user_id INTEGER PRIMARY KEY,
            quantity INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collection_rewards (
            user_id INTEGER NOT NULL,
            collection_id TEXT NOT NULL,
            claimed INTEGER NOT NULL DEFAULT 0,
            claimed_at TEXT,
            PRIMARY KEY (user_id, collection_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS player_legendary (
            user_id INTEGER NOT NULL,
            collection_id TEXT NOT NULL,
            legendary_id TEXT NOT NULL,
            claimed_at TEXT,
            PRIMARY KEY (user_id, collection_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS booster_activation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticket_id INTEGER,
            activated_at TEXT
        )
        """,
    ]

    with get_connection() as connection:
        for statement in statements:
            connection.execute(statement)

        booster_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(booster_tickets)"
            ).fetchall()
        }

        if "uses_remaining" not in booster_columns:
            connection.execute("""
                ALTER TABLE booster_tickets
                ADD COLUMN uses_remaining INTEGER
            """)

        if "source" not in booster_columns:
            connection.execute("""
                ALTER TABLE booster_tickets
                ADD COLUMN source TEXT NOT NULL DEFAULT 'daily'
            """)

    print("[TURSO] Database tables initialized.")
