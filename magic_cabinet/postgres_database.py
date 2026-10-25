
"""PostgreSQL database helpers for Magic Cabinet."""

import os

import psycopg


def get_postgres_connection():
    """Open a connection to PostgreSQL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(database_url, connect_timeout=10)


def initialize_postgres_database():
    """Create the inventory table without changing SQLite data."""

    with get_postgres_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_card_inventory (
                    user_id BIGINT NOT NULL,
                    card_id BIGINT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1
                        CHECK (quantity >= 1),
                    PRIMARY KEY (user_id, card_id)
                )
            """)

        connection.commit()
