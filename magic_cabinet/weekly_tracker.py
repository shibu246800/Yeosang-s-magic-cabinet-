
"""Weekly challenge progress tracker."""

import json
from datetime import datetime, timezone

from magic_cabinet.database import (
    get_connection,
    initialize_database,
)


def initialize_tracker_database():
    initialize_database()

    with get_connection() as connection:
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


def save_weekly_channel(
    user_id: int,
    guild_id: int,
    channel_id: int,
):
    if guild_id is None:
        return

    with get_connection() as connection:
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
            (user_id, guild_id, channel_id),
        )


def record_weekly_progress(
    user_id: int,
    stat: str,
    amount: int = 1,
):
    """
    Add progress to the current weekly challenge.

    Supported stats:
        new_cards
        glimmers_earned
        drops_claimed
    """

    if amount <= 0:
        return

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT task_data
            FROM weekly_challenges
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            return

        try:
            tasks = json.loads(row["task_data"])
        except (TypeError, json.JSONDecodeError):
            return

        progress_rows = connection.execute(
            """
            SELECT task_id, progress, completed
            FROM weekly_progress
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

        progress_map = {
            row["task_id"]: (
                int(row["progress"]),
                bool(row["completed"]),
            )
            for row in progress_rows
        }

        newly_completed = []

        for task in tasks:
            if task.get("stat") != stat:
                continue

            task_id = task.get("id")

            if not task_id:
                continue

            current_progress, completed = progress_map.get(
                task_id,
                (0, False),
            )

            if completed:
                continue

            target = int(task.get("amount", 0))

            if target <= 0:
                continue

            new_progress = min(
                current_progress + amount,
                target,
            )

            now_completed = new_progress >= target

            connection.execute(
                """
                INSERT INTO weekly_progress (
                    user_id,
                    task_id,
                    progress,
                    completed
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, task_id)
                DO UPDATE SET
                    progress = excluded.progress,
                    completed = excluded.completed
                """,
                (
                    user_id,
                    task_id,
                    new_progress,
                    int(now_completed),
                ),
            )

            progress_map[task_id] = (
                new_progress,
                now_completed,
            )

            if now_completed:
                newly_completed.append(task)

        for task in newly_completed:
            task_id = task["id"]
            reward = int(task.get("reward", 0))

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
                (user_id, task_id, now),
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
                VALUES (?, 'task_glimmers', ?, ?, 0, ?)
                """,
                (user_id, reward, task_id, now),
            )

        completed_row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM weekly_progress
            WHERE user_id = ?
              AND completed = 1
            """,
            (user_id,),
        ).fetchone()

        total_row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM weekly_progress
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        completed_count = completed_row["total"]
        total_tasks = total_row["total"]

        if total_tasks == 3 and completed_count == 3:
            grand_reward_exists = connection.execute(
                """
                SELECT 1
                FROM weekly_pending_rewards
                WHERE user_id = ?
                  AND reward_type = 'weekly_grand'
                  AND created_at >= (
                      SELECT week_started
                      FROM weekly_challenges
                      WHERE user_id = ?
                  )
                LIMIT 1
                """,
                (user_id, user_id),
            ).fetchone()

            if grand_reward_exists is None:
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
                    VALUES (?, 'weekly_grand', 0, NULL, 0, ?)
                    """,
                    (user_id, now),
                )

                connection.execute(
                    """
                    INSERT INTO weekly_notifications (
                        user_id,
                        task_id,
                        created_at,
                        sent
                    )
                    VALUES (?, '__weekly_complete__', ?, 0)
                    """,
                    (user_id, now),
                )


def get_pending_notifications():
    initialize_tracker_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                n.id,
                n.user_id,
                n.task_id,
                d.guild_id,
                d.channel_id
            FROM weekly_notifications AS n
            JOIN weekly_delivery AS d
                ON d.user_id = n.user_id
            WHERE n.sent = 0
            ORDER BY n.id ASC
            """
        ).fetchall()

    return [
        (
            row["id"],
            row["user_id"],
            row["task_id"],
            row["guild_id"],
            row["channel_id"],
        )
        for row in rows
    ]


def mark_notification_sent(notification_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE weekly_notifications
            SET sent = 1
            WHERE id = ?
            """,
            (notification_id,),
        )


initialize_tracker_database()
