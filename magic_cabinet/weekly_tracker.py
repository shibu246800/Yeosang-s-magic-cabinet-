"""Weekly challenge progress tracker."""

import sqlite3

DATABASE = "cabinet.db"


def record_weekly_progress(
    user_id: int,
    stat: str,
    amount: int = 1,
):
    """
    Add progress to the matching weekly challenge.

    Supported stats:
    - new_cards
    - glimmers_earned
    - drops_claimed
    - collections_completed
    """

    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT task_id
            FROM weekly_progress
            WHERE user_id = ?
            AND completed = 0
            """,
            (user_id,),
        ).fetchall()

        for (task_id,) in rows:
            connection.execute(
                """
                SELECT task_data
                FROM weekly_challenges
                WHERE user_id = ?
                """,
                (user_id,),
            )

            challenge = connection.execute(
                """
                SELECT task_data
                FROM weekly_challenges
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if challenge is None:
                continue

            import json

            tasks = json.loads(challenge[0])

            matching_task = next(
                (
                    task
                    for task in tasks
                    if task["id"] == task_id
                    and task["stat"] == stat
                ),
                None,
            )

            if matching_task is None:
                continue

            target = matching_task["amount"]

            current = connection.execute(
                """
                SELECT progress
                FROM weekly_progress
                WHERE user_id = ?
                AND task_id = ?
                """,
                (
                    user_id,
                    task_id,
                ),
            ).fetchone()

            current_progress = (
                0 if current is None else current[0]
            )

            new_progress = min(
                current_progress + amount,
                target,
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
                    1 if new_progress >= target else 0,
                    user_id,
                    task_id,
                ),
            )

        connection.commit()
