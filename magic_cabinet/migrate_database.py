
"""Safely copy Magic Cabinet's SQLite data to Turso."""

from magic_cabinet.database import get_connection as get_turso_connection
from contextlib import closing
import os
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = Path(
    os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "cabinet.db"))
).expanduser().resolve()

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
    "player_card_inventory": ["user_id", "card_id", "quantity"],
    "weekly_challenges": [
        "user_id", "week_started", "task_data",
        "guaranteed_claimed", "reward_claimed",
    ],
    "weekly_progress": [
        "user_id", "task_id", "progress", "completed",
    ],
    "weekly_notifications": [
        "id", "user_id", "task_id", "created_at", "sent",
    ],
    "weekly_delivery": ["user_id", "guild_id", "channel_id"],
    "weekly_pending_rewards": [
        "reward_id", "user_id", "reward_type", "amount",
        "task_id", "claimed", "created_at",
    ],
    "earn_data": ["user_id", "last_claim_at"],
    "blind_boxes": ["user_id", "quantity"],
    "collection_rewards": [
        "user_id", "collection_id", "claimed", "claimed_at",
    ],
    "player_legendary": [
        "user_id", "collection_id", "legendary_id", "claimed_at",
    ],
    "booster_activation_log": [
        "id", "user_id", "ticket_id", "activated_at",
    ],
}


def migrate_database():
    if not SQLITE_PATH.is_file():
        raise FileNotFoundError(
            f"Existing SQLite database not found: {SQLITE_PATH}"
        )

    with closing(sqlite3.connect(str(SQLITE_PATH))) as sqlite:
        sqlite.row_factory = sqlite3.Row

        snapshots = {}

        for table, columns in TABLES.items():
            exists = sqlite.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=?",
                (table,),
            ).fetchone()

            if not exists:
                print(f"{table}: source table missing; skipped")
                continue

            actual_columns = {
                row["name"]
                for row in sqlite.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
            }

            missing = set(columns) - actual_columns
            if missing:
                raise RuntimeError(
                    f"{table} is missing SQLite columns: {sorted(missing)}"
                )

            column_sql = ", ".join(f'"{c}"' for c in columns)
            rows = sqlite.execute(
                f'SELECT {column_sql} FROM "{table}"'
            ).fetchall()

            snapshots[table] = [
                tuple(row[column] for column in columns)
                for row in rows
            ]

    with get_turso_connection() as turso:
        # Safety check: never merge into populated Turso tables.
        for table in TABLES:
            count = turso.execute(
                f'SELECT COUNT(*) AS total FROM "{table}"'
            ).fetchone()["total"]

            if count:
                raise RuntimeError(
                    f"{table} already has {count} Turso rows. "
                    "Migration stopped without inserting records."
                )

        for table, columns in TABLES.items():
            rows = snapshots.get(table, [])

            if not rows:
                print(f"{table}: 0 rows to copy")
                continue

            column_sql = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(["?"] * len(columns))

            turso.executemany(
                f'INSERT INTO "{table}" ({column_sql}) '
                f"VALUES ({placeholders})",
                rows,
            )

            print(f"{table}: copied {len(rows)} rows")

    print("Migration finished. Original SQLite data was preserved.")


if __name__ == "__main__":
    migrate_database()
