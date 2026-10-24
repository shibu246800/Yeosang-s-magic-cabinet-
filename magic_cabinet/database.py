
"""Shared SQLite database for Magic Cabinet."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Use one consistent database path for the whole project.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "cabinet.db"))
).expanduser().resolve()


@contextmanager
def get_connection():
    """Open a SQLite connection and safely close it afterward."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
    )
    connection.row_factory = sqlite3.Row

    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    """Create shared tables and safely add missing columns."""

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS drop_channels (
                guild_id INTEGER PRIMARY KEY,
                channel1_id INTEGER NOT NULL,
                channel2_id INTEGER,
                channel3_id INTEGER,
                channel4_id INTEGER,
                channel5_id INTEGER
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                vault TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS player_vaults (
                user_id INTEGER NOT NULL,
                vault TEXT NOT NULL,
                PRIMARY KEY (user_id, vault)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                glimmers INTEGER NOT NULL DEFAULT 0
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bag (
                user_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, card_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS daily_data (
                user_id INTEGER PRIMARY KEY,
                last_claim_at TEXT
            )
        """)

        connection.execute("""
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
        """)

        # Safely add columns to existing SQLite databases.
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

        connection.execute("""
            CREATE TABLE IF NOT EXISTS player_badges (
                user_id INTEGER NOT NULL,
                badge_id TEXT NOT NULL,
                badge_name TEXT NOT NULL,
                badge_emote TEXT,
                PRIMARY KEY (user_id, badge_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS player_achievements (
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                global_rank INTEGER NOT NULL,
                PRIMARY KEY (user_id, achievement_id)
            )
        """)
