import json
import random
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.postgres_database import (
    get_postgres_connection,
    initialize_postgres_database,
)
from magic_cabinet.weekly_tracker import (
    initialize_tracker_database,
    save_weekly_channel,
)


WEEKLY_TASKS = {
    "drops": {
        "name": "Join Drops",
        "description": "Claim cards from drops.",
        "target": 5,
        "reward": 2500,
    },
    "daily": {
        "name": "Daily Magic",
        "description": "Claim your daily reward.",
        "target": 3,
        "reward": 2500,
    },
    "earn": {
        "name": "Gather Glimmers",
        "description": "Use /earn to collect Glimmers.",
        "target": 5,
        "reward": 2500,
    },
}


def initialize_weekly_database():
    initialize_postgres_database()
    initialize_tracker_database()

    with get_postgres_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_challenges (
                user_id BIGINT PRIMARY KEY,
                week_started TEXT NOT NULL,
                task_data TEXT NOT NULL,
                guaranteed_claimed INTEGER NOT NULL DEFAULT 0,
                reward_claimed INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_progress (
                user_id BIGINT NOT NULL,
                task_id TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, task_id)
            )
        """)


def get_week_start():
    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday.isoformat()


def add_glimmers(user_id, amount):
    with get_postgres_connection() as conn:
        conn.execute(
            """
            INSERT INTO balances (user_id, glimmers)
            VALUES (%s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET glimmers = balances.glimmers + EXCLUDED.glimmers
            """,
            (user_id, amount),
        )


def get_or_create_weekly_challenge(user_id):
    initialize_weekly_database()
    week_start = get_week_start()

    with get_postgres_connection() as conn:
        row = conn.execute(
            """
            SELECT week_started, task_data, guaranteed_claimed,
                   reward_claimed
            FROM weekly_challenges
            WHERE user_id = %s
            """,
            (user_id,),
        ).fetchone()

        if row and row["week_started"] == week_start:
            return row

        chosen = random.sample(list(WEEKLY_TASKS.keys()), 3)
        tasks = {task_id: WEEKLY_TASKS[task_id].copy() for task_id in chosen}

        conn.execute(
            """
            INSERT INTO weekly_challenges
                (user_id, week_started, task_data,
                 guaranteed_claimed, reward_claimed)
            VALUES (%s, %s, %s, 0, 0)
            ON CONFLICT (user_id)
            DO UPDATE SET
                week_started = EXCLUDED.week_started,
                task_data = EXCLUDED.task_data,
                guaranteed_claimed = 0,
                reward_claimed = 0
            """,
            (user_id, week_start, json.dumps(tasks)),
        )

        conn.execute(
            "DELETE FROM weekly_progress WHERE user_id = %s",
            (user_id,),
        )

        add_glimmers(user_id, 10000)

        return {
            "week_started": week_start,
            "task_data": json.dumps(tasks),
            "guaranteed_claimed": 0,
            "reward_claimed": 0,
        }


class Weekly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        initialize_weekly_database()

    @app_commands.command(
        name="weekly",
        description="View your weekly challenges and rewards.",
    )
    async def weekly(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        challenge = get_or_create_weekly_challenge(user_id)
        task_data = challenge["task_data"]

        if isinstance(task_data, str):
            task_data = json.loads(task_data)

        with get_postgres_connection() as conn:
            progress_rows = conn.execute(
                """
                SELECT task_id, progress, completed
                FROM weekly_progress
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchall()

        progress = {
            row["task_id"]: row
            for row in progress_rows
        }

        embed = discord.Embed(
            title="✦ Weekly Challenges ✦",
            description=(
                "Complete your challenges to earn Glimmers "
                "and unlock the grand reward."
            ),
            color=discord.Color.from_str("#4E0017"),
        )

        for task_id, task in task_data.items():
            row = progress.get(task_id)
            current = row["progress"] if row else 0
            completed = bool(row["completed"]) if row else False

            status = "✓ Completed" if completed else f"{current}/{task['target']}"

            embed.add_field(
                name=f"{task['name']} — {status}",
                value=(
                    f"{task['description']}\n"
                    f"Reward: **{task['reward']:,} Glimmers**"
                ),
                inline=False,
            )

        completed_count = sum(
            1 for row in progress_rows if row["completed"]
        )

        embed.add_field(
            name="Grand Reward",
            value=(
                f"Challenges completed: **{completed_count}/3**\n"
                "Complete all three to unlock **25,000 Glimmers, "
                "1 Epic card, and 1 Blind Box**."
            ),
            inline=False,
        )

        embed.set_footer(text="A new weekly set begins on Monday (UTC).")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

        try:
            save_weekly_channel(
                user_id,
                interaction.guild_id,
                interaction.channel_id,
            )
        except Exception:
            pass


async def setup(bot):
    initialize_weekly_database()
    await bot.add_cog(Weekly(bot))
