"""Weekly challenge progress tracker."""

import json
import sqlite3

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
                from datetime import datetime, timezone

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

        connection.commit()


initialize_tracker_database()
