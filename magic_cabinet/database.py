
import os
import psycopg
from psycopg.rows import dict_row


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from environment variables.")

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        sslmode="require",
    )


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS drop_channels (
                guild_id BIGINT PRIMARY KEY,
                channel1_id BIGINT NOT NULL,
                channel2_id BIGINT,
                channel3_id BIGINT,
                channel4_id BIGINT,
                channel5_id BIGINT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                created_at TEXT NOT NULL,
                vault TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS player_vaults (
                user_id BIGINT PRIMARY KEY,
                vaults TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                user_id BIGINT PRIMARY KEY,
                glimmers BIGINT NOT NULL DEFAULT 0
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bag (
                user_id BIGINT NOT NULL,
                card_id TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, card_id)
            )
        """)
