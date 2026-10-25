
"""PostgreSQL database helpers for Magic Cabinet."""

import os
import psycopg

from magic_cabinet.database import get_connection


def get_postgres_connection():
    """Open a PostgreSQL connection."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        database_url,
        connect_timeout=10,
    )


def initialize_postgres_database():
    """Create the inventory table without changing existing data."""

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


def migrate_inventory():
    """Copy SQLite inventory into PostgreSQL safely."""

    with get_connection() as sqlite_connection:
        rows = sqlite_connection.execute("""
            SELECT user_id, card_id, quantity
            FROM bag
            WHERE quantity > 0
        """).fetchall()

        inventory = [
            (
                int(row["user_id"]),
                int(row["card_id"]),
                int(row["quantity"]),
            )
            for row in rows
        ]

    with get_postgres_connection() as postgres_connection:
        with postgres_connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM player_card_inventory
            """)
            existing_count = cursor.fetchone()[0]

            if existing_count > 0:
                raise RuntimeError(
                    "Migration stopped: PostgreSQL inventory is not empty. "
                    "No inventory records were changed."
                )

            cursor.executemany("""
                INSERT INTO player_card_inventory
                    (user_id, card_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, card_id) DO NOTHING
            """, inventory)

    print(
        f"[INVENTORY MIGRATION] Copied {len(inventory)} "
        "SQLite inventory records."
    )
