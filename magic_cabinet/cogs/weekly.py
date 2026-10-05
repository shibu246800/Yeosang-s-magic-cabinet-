"""Magic Cabinet weekly challenges."""

import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from magic_cabinet.weekly_tracker import (
    get_pending_notifications,
    mark_notification_sent,
    save_weekly_channel,
)


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

WEEKLY_HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005080611.jpg"
)

WEEKLY_GUARANTEED_GLIMMERS = 10_000

WEEKLY_GRAND_GLIMMERS = 25_000

WEEKLY_RESET_DAYS = 7


# ---------------------------------------------------------
# WEEKLY TASK POOLS
# ---------------------------------------------------------

EASY_TASKS = [
    {
        "id": "collect_new_cards",
        "text": "Collect {amount} new cards",
        "stat": "new_cards",
        "minimum": 5,
        "maximum": 10,
        "reward_min": 3000,
        "reward_max": 6000,
    },
    {
        "id": "earn_glimmers",
        "text": "Earn {amount:,} Glimmers",
        "stat": "glimmers_earned",
        "minimum": 5000,
        "maximum": 10000,
        "reward_min": 3000,
        "reward_max": 6000,
    },
    {
        "id": "claim_drops",
        "text": "Claim {amount} Drops",
        "stat": "drops_claimed",
        "minimum": 2,
        "maximum": 5,
        "reward_min": 3000,
        "reward_max": 6000,
    },
]


MEDIUM_TASKS = [
    {
        "id": "collect_new_cards",
        "text": "Collect {amount} new cards",
        "stat": "new_cards",
        "minimum": 10,
        "maximum": 20,
        "reward_min": 7000,
        "reward_max": 12000,
    },
    {
        "id": "earn_glimmers",
        "text": "Earn {amount:,} Glimmers",
        "stat": "glimmers_earned",
        "minimum": 15000,
        "maximum": 25000,
        "reward_min": 7000,
        "reward_max": 12000,
    },
    {
        "id": "claim_drops",
        "text": "Claim {amount} Drops",
        "stat": "drops_claimed",
        "minimum": 6,
        "maximum": 12,
        "reward_min": 7000,
        "reward_max": 12000,
    },
]


HARD_TASKS = [
    {
        "id": "collect_new_cards",
        "text": "Collect {amount} new cards",
        "stat": "new_cards",
        "minimum": 20,
        "maximum": 35,
        "reward_min": 15000,
        "reward_max": 25000,
    },
    {
        "id": "earn_glimmers",
        "text": "Earn {amount:,} Glimmers",
        "stat": "glimmers_earned",
        "minimum": 30000,
        "maximum": 50000,
        "reward_min": 15000,
        "reward_max": 25000,
    },
    {
        "id": "claim_drops",
        "text": "Claim {amount} Drops",
        "stat": "drops_claimed",
        "minimum": 15,
        "maximum": 25,
        "reward_min": 15000,
        "reward_max": 25000,
    },
]


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def initialize_weekly_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_challenges (
                user_id INTEGER PRIMARY KEY,
                week_started TEXT NOT NULL,
                task_data TEXT NOT NULL,
                guaranteed_claimed INTEGER NOT NULL DEFAULT 0,
                reward_claimed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_progress (
                user_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, task_id)
            )
            """
        )

        connection.commit()


# ---------------------------------------------------------
# GLIMMERS
# ---------------------------------------------------------

def add_glimmers(user_id: int, amount: int):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO balances (
                user_id,
                glimmers
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                glimmers = glimmers + excluded.glimmers
            """,
            (
                user_id,
                amount,
            ),
        )

        connection.commit()


# ---------------------------------------------------------
# TASK GENERATION
# ---------------------------------------------------------

def choose_difficulty_pool():
    roll = random.random()

    if roll < 0.55:
        return EASY_TASKS

    if roll < 0.85:
        return MEDIUM_TASKS

    return HARD_TASKS


def generate_tasks():
    selected_tasks = []

    attempts = 0

    while len(selected_tasks) < 3 and attempts < 100:
        attempts += 1

        pool = choose_difficulty_pool()

        template = random.choice(pool)

        if template["id"] in {
            task["id"]
            for task in selected_tasks
        }:
            continue

        task = dict(template)

        task["amount"] = random.randint(
            template["minimum"],
            template["maximum"],
        )

        task["reward"] = random.randint(
            template["reward_min"],
            template["reward_max"],
        )

        task["difficulty"] = (
            "easy"
            if template in EASY_TASKS
            else "medium"
            if template in MEDIUM_TASKS
            else "hard"
        )

        task["display"] = template["text"].format(
            amount=task["amount"]
        )

        selected_tasks.append(task)

    return selected_tasks


# ---------------------------------------------------------
# WEEKLY CYCLE
# ---------------------------------------------------------

def get_weekly_data(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT
                week_started,
                task_data,
                guaranteed_claimed,
                reward_claimed
            FROM weekly_challenges
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row


def is_new_week(week_started: str) -> bool:
    started = datetime.fromisoformat(week_started)

    now = datetime.now(timezone.utc)

    return now >= started + timedelta(
        days=WEEKLY_RESET_DAYS
    )


def create_new_week(user_id: int):
    selected_tasks = generate_tasks()

    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            DELETE FROM weekly_progress
            WHERE user_id = ?
            """,
            (user_id,),
        )

        connection.execute(
            """
            INSERT INTO weekly_challenges (
                user_id,
                week_started,
                task_data,
                guaranteed_claimed,
                reward_claimed
            )
            VALUES (?, ?, ?, 1, 0)
            ON CONFLICT(user_id)
            DO UPDATE SET
                week_started = excluded.week_started,
                task_data = excluded.task_data,
                guaranteed_claimed = 1,
                reward_claimed = 0
            """,
            (
                user_id,
                now,
                json.dumps(selected_tasks),
            ),
        )

        for task in selected_tasks:
            connection.execute(
                """
                INSERT INTO weekly_progress (
                    user_id,
                    task_id,
                    progress,
                    completed
                )
                VALUES (?, ?, 0, 0)
                """,
                (
                    user_id,
                    task["id"],
                ),
            )

        connection.commit()

    return selected_tasks


def get_current_tasks(user_id: int):
    row = get_weekly_data(user_id)

    if row is None:
        return create_new_week(user_id)

    week_started = row[0]

    if is_new_week(week_started):
        return create_new_week(user_id)

    return json.loads(row[1])


# ---------------------------------------------------------
# PROGRESS
# ---------------------------------------------------------

def get_task_progress(
    user_id: int,
    task_id: str,
) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
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

    return 0 if row is None else row[0]


def is_task_completed(
    user_id: int,
    task_id: str,
) -> bool:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT completed
            FROM weekly_progress
            WHERE user_id = ?
            AND task_id = ?
            """,
            (
                user_id,
                task_id,
            ),
        ).fetchone()

    return bool(row and row[0])


def completed_task_count(user_id: int) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM weekly_progress
            WHERE user_id = ?
            AND completed = 1
            """,
            (user_id,),
        ).fetchone()

    return 0 if row is None else row[0]


# ---------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------

def difficulty_emote(difficulty: str) -> str:
    return {
        "easy": "🟢",
        "medium": "🟡",
        "hard": "🔴",
    }.get(difficulty, "✦")


def build_weekly_embed(
    user_id: int,
    selected_tasks: list,
) -> discord.Embed:
    completed = completed_task_count(user_id)

    description = (
        f"<@{user_id}>\n\n"
        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
        "**WEEKLY CHALLENGE**\n"
        "-# Complete all 3 challenges to unlock your\n"
        "-# full weekly reward.\n\n"
    )

    for index, task in enumerate(
        selected_tasks,
        start=1,
    ):
        progress = get_task_progress(
            user_id,
            task["id"],
        )

        progress = min(
            progress,
            task["amount"],
        )

        marker = (
            " ✓"
            if is_task_completed(
                user_id,
                task["id"],
            )
            else ""
        )

        description += (
            f"{difficulty_emote(task['difficulty'])} "
            f"**Task {index}**{marker}\n"
            f"{task['display']}\n"
            f"`{progress} / {task['amount']}`\n\n"
        )

    description += (
        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
        "**Weekly Guaranteed Reward**\n"
        f"+ **{WEEKLY_GUARANTEED_GLIMMERS:,}** "
        f"{GLIMMER_EMOTE}\n\n"
        f"-# ✧ Challenges completed: **{completed}/3**\n"
        "-# ✧ Complete all 3 challenges to unlock\n"
        "-# the full reward in `/rewards`."
    )

    return discord.Embed(
        description=description,
        color=EMBED_COLOR,
    )


# ---------------------------------------------------------
# WEEKLY COG
# ---------------------------------------------------------

class Weekly(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        initialize_weekly_database()

        self.notification_loop.start()

    def cog_unload(self):
        self.notification_loop.cancel()

    async def send_pending_notifications(self):
        notifications = get_pending_notifications()

        for (
            notification_id,
            user_id,
            task_id,
            guild_id,
            channel_id,
        ) in notifications:

            guild = self.bot.get_guild(guild_id)

            if guild is None:
                continue

            channel = guild.get_channel(channel_id)

            if channel is None:
                continue

            # -------------------------------------------------
            # FULL 3/3 WEEKLY COMPLETION
            # -------------------------------------------------

            if task_id == "__weekly_complete__":
                embed = discord.Embed(
                    description=(
                        f"<@{user_id}>\n\n"
                        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                        "**WEEKLY CHALLENGE COMPLETE!** ✦\n\n"
                        "**3 / 3 challenges completed** ✓\n\n"
                        f"+ **{WEEKLY_GRAND_GLIMMERS:,}** "
                        f"{GLIMMER_EMOTE}\n"
                        "🃏 **1 New Epic Card**\n"
                        "📦 **1 Blind Box**\n\n"
                        "-# ✧ Your full weekly reward is waiting.\n"
                        "-# ✧ Use `/rewards` to claim everything.\n\n"
                        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                    ),
                    color=EMBED_COLOR,
                )

                await channel.send(
                    content=f"<@{user_id}>",
                    embed=embed,
                )

                mark_notification_sent(
                    notification_id
                )

                continue

            # -------------------------------------------------
            # INDIVIDUAL TASK COMPLETION
            # -------------------------------------------------

            selected_tasks = get_current_tasks(
                user_id
            )

            task = next(
                (
                    item
                    for item in selected_tasks
                    if item["id"] == task_id
                ),
                None,
            )

            if task is None:
                mark_notification_sent(
                    notification_id
                )
                continue

            progress = get_task_progress(
                user_id,
                task_id,
            )

            completed = completed_task_count(
                user_id
            )

            embed = discord.Embed(
                description=(
                    f"<@{user_id}>\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "**WEEKLY CHALLENGE COMPLETE!** ✦\n\n"
                    f"{difficulty_emote(task['difficulty'])} "
                    f"**{task['display']}**\n"
                    f"`{progress} / {task['amount']}` ✓\n\n"
                    f"+ **{task['reward']:,}** "
                    f"{GLIMMER_EMOTE}\n\n"
                    f"✦ **{completed} / 3** "
                    "challenges completed\n\n"
                    "-# ✧ Use `/rewards` to view "
                    "your waiting rewards.\n"
                    "-# ✧ Claim them with the "
                    "button in `/rewards`.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await channel.send(
                content=f"<@{user_id}>",
                embed=embed,
            )

            mark_notification_sent(
                notification_id
            )

    @tasks.loop(seconds=5)
    async def notification_loop(self):
        await self.send_pending_notifications()

    @notification_loop.before_loop
    async def before_notification_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="weekly",
        description="View your weekly challenges.",
    )
    async def weekly(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        existing = get_weekly_data(user_id)

        if (
            existing is None
            or is_new_week(existing[0])
        ):
            selected_tasks = create_new_week(
                user_id
            )

            add_glimmers(
                user_id,
                WEEKLY_GUARANTEED_GLIMMERS,
            )
        else:
            selected_tasks = get_current_tasks(
                user_id
            )

        save_weekly_channel(
            user_id,
            interaction.guild_id,
            interaction.channel_id,
        )

        header = discord.Embed(
            color=EMBED_COLOR,
        )

        header.set_image(
            url=WEEKLY_HEADER_URL
        )

        weekly_embed = build_weekly_embed(
            user_id,
            selected_tasks,
        )

        await interaction.response.send_message(
            embeds=[
                header,
                weekly_embed,
            ]
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Weekly(bot)
)
