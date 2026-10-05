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
    """
    Add progress to the current weekly challenge.

    Supported stats currently include:
        new_cards
        glimmers_earned
        drops_claimed
    """

    if amount <= 0:
        return

    now = datetime.now(
        timezone.utc
    ).isoformat()

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT
                task_data
            FROM weekly_challenges
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            return

        try:
            tasks = json.loads(row[0])
        except (
            TypeError,
            json.JSONDecodeError,
        ):
            return

        progress_rows = connection.execute(
            """
            SELECT
                task_id,
                progress,
                completed
            FROM weekly_progress
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

        progress_map = {
            task_id: (
                int(progress),
                bool(completed),
            )
            for task_id, progress, completed
            in progress_rows
        }

        newly_completed = []

        for task in tasks:
            if task.get("stat") != stat:
                continue

            task_id = task.get("id")

            if not task_id:
                continue

            current_progress, completed = (
                progress_map.get(
                    task_id,
                    (0, False),
                )
            )

            if completed:
                continue

            target = int(
                task.get(
                    "amount",
                    0,
                )
            )

            new_progress = min(
                current_progress + amount,
                target,
            )

            now_completed = (
                target > 0
                and new_progress >= target
            )

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
                    1 if now_completed else 0,
                    user_id,
                    task_id,
                ),
            )

            if now_completed:
                newly_completed.append(
                    task
                )

        for task in newly_completed:
            task_id = task["id"]
            reward = int(
                task.get(
                    "reward",
                    0,
                )
            )

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
                    now,
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
                    reward,
                    task_id,
                    now,
                ),
            )

        completed_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM weekly_progress
            WHERE user_id = ?
            AND completed = 1
            """,
            (user_id,),
        ).fetchone()[0]

        total_tasks = connection.execute(
            """
            SELECT COUNT(*)
            FROM weekly_progress
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()[0]

        if (
            total_tasks == 3
            and completed_count == 3
        ):
            grand_reward_exists = connection.execute(
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
                        now,
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO weekly_notifications (
                        user_id,
                        task_id,
                        created_at,
                        sent
                    )
                    VALUES (
                        ?,
                        '__weekly_complete__',
                        ?,
                        0
                    )
                    """,
                    (
                        user_id,
                        now,
                    ),
                )

        connection.commit()


def get_pending_notifications():
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
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

    return rows


def mark_notification_sent(
    notification_id: int,
):
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
