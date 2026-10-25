
"""Safely copy Magic Cabinet's SQLite tables to PostgreSQL."""

from magic_cabinet.database import get_connection
from magic_cabinet.postgres_database import (
    get_postgres_connection,
    initialize_postgres_database,
)

TABLES = {
    "drop_channels": [
        "guild_id", "channel1_id", "channel2_id",
        "channel3_id", "channel4_id", "channel5_id",
    ],
    "players": ["user_id", "created_at", "vault"],
    "player_vaults": ["user_id", "vault"],
    "balances": ["user_id", "glimmers"],
    "bag": ["user_id", "card_id", "quantity"],
    "daily_data": ["user_id", "last_claim_at"],
    "booster_tickets": [
        "ticket_id", "user_id", "booster_id", "received_at",
        "activated_at", "expires_at", "uses_remaining", "source",
    ],
    "player_badges": [
        "user_id", "badge_id", "badge_name", "badge_emote",
    ],
    "player_achievements": [
        "user_id", "achievement_id", "achievement_name", "global_rank",
    ],
}


def migrate_database():
    initialize_postgres_database()

    with get_connection() as sqlite:
        snapshots = {}
        for table, columns in TABLES.items():
            column_sql = ", ".join(f'"{c}"' for c in columns)
            rows = sqlite.execute(
                f'SELECT {column_sql} FROM "{table}"'
            ).fetchall()
            snapshots[table] = [
                tuple(row[column] for column in columns)
                for row in rows
            ]

    with get_postgres_connection() as postgres:
        with postgres.cursor() as cursor:
            # Safety check: do not merge into populated tables.
            for table in TABLES:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
                if count:
                    raise RuntimeError(
                        f'"{table}" already has {count} PostgreSQL rows. '
                        "Migration stopped without inserting records."
                    )

            for table, columns in TABLES.items():
                rows = snapshots[table]
                if not rows:
                    print(f"{table}: 0 rows to copy")
                    continue

                column_sql = ", ".join(f'"{c}"' for c in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                cursor.executemany(
                    f'INSERT INTO "{table}" ({column_sql}) '
                    f"VALUES ({placeholders})",
                    rows,
                )
                print(f"{table}: copied {len(rows)} rows")

            # Keep future ticket IDs above the copied IDs.
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('booster_tickets', 'ticket_id'),
                    COALESCE((SELECT MAX(ticket_id) FROM booster_tickets), 1),
                    EXISTS (SELECT 1 FROM booster_tickets)
                )
            """)

    print("Migration finished. SQLite data was preserved.")


if __name__ == "__main__":
    migrate_database()

