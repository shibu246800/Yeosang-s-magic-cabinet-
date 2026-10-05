"""Weekly challenge progress tracker."""

import json
import sqlite3
from datetime import datetime, timezone

DATABASE = "cabinet.db"


def initialize_tracker_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_delivery (
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL
            )
            """
        )

        connection.execute(
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
            """
        )

        connection.commit()


def save_weekly_channel(
    user_id: int,
    guild_id: int,
    channel_id: int,
):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO weekly_delivery (
                user_id,
                guild_id,
                channel_id
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                guild_id = excluded.guild_id,
                channel_id = excluded.channel_id
            """,
            (
                user_id,
                guild_id,
                channel_id,
            ),
        )

        connection.commit()


def record_weekly_progress(
    user_id: int,
    stat: str,
    amount: int = 1,
):
    """Add progress to the matching weekly challenge."""

    with sqlite3.connect(DATABASE) as connection:
        challenge = connection.execute(
            """
            SELECT task_data
            FROM weekly_challenges
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if challenge is None:
            return

        tasks = json.loads(challenge[0])

        rows = connection.execute(
            """
            SELECT task_id, progress, completed
            FROM weekly_progress
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

        for task_id, current_progress, completed in rows:
            if completed:
                continue

            task = next(
                (
                    item
                    for item in tasks
                    if item["id"] == task_id
                    and item["stat"] == stat
                ),
                None,
            )

            if task is None:
                continue

            target = task["amount"]

            new_progress = min(
                current_progress + amount,
                target,
            )

            just_completed = new_progress >= target

            connection.execute(
                """
                UPDATE weekly_progress
                SET progress = ?,
                    completed = ?
                WHERE user_id = ?
                AND task_id = ?
                """,
                (
                    new_progress,
                    1 if just_completed else 0,
                    user_id,
                    task_id,
                ),
            )

            if just_completed:
                connection.execute(
                    """
                    INSERT INTO weekly_notifications (
                        user_id,
                        task_id,
                        created_at,
                        sent
                    )
                    VALUES (?, ?, ?, 0)
                    """,
                    (
                        user_id,
                        task_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO weekly_pending_rewards (
                        user_id,
                        reward_type,
                        amount,
                        task_id,
                        claimed,
                        created_at
                    )
                    VALUES (
                        ?,
                        'task_glimmers',
                        ?,
                        ?,
                        0,
                        ?
                    )
                    """,
                    (
                        user_id,
                        task["reward"],
                        task_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

        # Check whether all three weekly challenges
        # are now complete.
        completed_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM weekly_progress
            WHERE user_id = ?
            AND completed = 1
            """,
            (user_id,),
        ).fetchone()[0]

        if completed_count == 3:
            already_queued = connection.execute(
                """
                SELECT 1
                FROM weekly_pending_rewards
                WHERE user_id = ?
                AND reward_type = 'weekly_grand'
                AND claimed = 0
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            if already_queued is None:
                connection.execute(
                    """
                    INSERT INTO weekly_pending_rewards (
                        user_id,
                        reward_type,
                        amount,
                        task_id,
                        claimed,
                        created_at
                    )
                    VALUES (
                        ?,
                        'weekly_grand',
                        0,
                        NULL,
                        0,
                        ?
                    )
                    """,
                    (
                        user_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

                # Special notification for completing
                # the entire weekly challenge.
                connection.execute(
                    """
                    INSERT INTO weekly_notifications (
                        user_id,
                        task_id,
                        created_at,
                        sent
                    )
                    VALUES (?, ?, ?, 0)
                    """,
                    (
                        user_id,
                        "__weekly_complete__",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

        connection.commit()


def get_pending_notifications():
    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT
                n.id,
                n.user_id,
                n.task_id,
                d.guild_id,
                d.channel_id
            FROM weekly_notifications n
            JOIN weekly_delivery d
                ON d.user_id = n.user_id
            WHERE n.sent = 0
            ORDER BY n.id ASC
            """
        ).fetchall()


def mark_notification_sent(notification_id: int):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            UPDATE weekly_notifications
            SET sent = 1
            WHERE id = ?
            """,
            (notification_id,),
        )

        connection.commit()


initialize_tracker_database()
