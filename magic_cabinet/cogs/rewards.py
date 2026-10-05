"""Magic Cabinet rewards command."""

import random
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.epic import CARDS as EPIC_CARDS


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

WEEKLY_GRAND_GLIMMERS = 25_000


def initialize_rewards_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_boxes (
                user_id INTEGER PRIMARY KEY,
                quantity INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.commit()


def get_pending_rewards(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT
                reward_id,
                reward_type,
                amount
            FROM weekly_pending_rewards
            WHERE user_id = ?
            AND claimed = 0
            ORDER BY reward_id ASC
            """,
            (user_id,),
        ).fetchall()


def get_blind_box_count(user_id: int) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM blind_boxes
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return 0

    return row[0]


def add_blind_boxes(
    user_id: int,
    quantity: int = 1,
):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO blind_boxes (
                user_id,
                quantity
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                quantity =
                    quantity + excluded.quantity
            """,
            (
                user_id,
                quantity,
            ),
        )

        connection.commit()


def get_bag_quantity(
    user_id: int,
    card_id: int,
) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                user_id,
                card_id,
            ),
        ).fetchone()

    if row is None:
        return 0

    return row[0]


def add_to_bag(
    user_id: int,
    card_id: int,
):
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                user_id,
                card_id,
            ),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO bag (
                    user_id,
                    card_id,
                    quantity
                )
                VALUES (?, ?, 1)
                """,
                (
                    user_id,
                    card_id,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE bag
                SET quantity = ?
                WHERE user_id = ?
                AND card_id = ?
                """,
                (
                    row[0] + 1,
                    user_id,
                    card_id,
                ),
            )

        connection.commit()


def choose_new_epic(user_id: int):
    available = [
        card
        for card in EPIC_CARDS
        if get_bag_quantity(
            user_id,
            card["id"],
        ) == 0
    ]

    if not available:
        return None

    return random.choice(available)


def claim_rewards(user_id: int):
    rewards = get_pending_rewards(user_id)

    if not rewards:
        return None

    task_glimmers = sum(
        reward[2]
        for reward in rewards
        if reward[1] == "task_glimmers"
    )

    has_grand_reward = any(
        reward[1] == "weekly_grand"
        for reward in rewards
    )

    new_epic = None

    if has_grand_reward:
        new_epic = choose_new_epic(user_id)

    total_glimmers = task_glimmers

    if has_grand_reward:
        total_glimmers += WEEKLY_GRAND_GLIMMERS

    with sqlite3.connect(DATABASE) as connection:
        if total_glimmers > 0:
            connection.execute(
                """
                INSERT INTO balances (
                    user_id,
                    glimmers
                )
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    glimmers =
                        glimmers + excluded.glimmers
                """,
                (
                    user_id,
                    total_glimmers,
                ),
            )

        reward_ids = [
            reward[0]
            for reward in rewards
        ]

        placeholders = ",".join(
            "?" for _ in reward_ids
        )

        connection.execute(
            f"""
            UPDATE weekly_pending_rewards
            SET claimed = 1
            WHERE reward_id IN ({placeholders})
            """,
            reward_ids,
        )

        connection.commit()

    if new_epic is not None:
        add_to_bag(
            user_id,
            new_epic["id"],
        )

    if has_grand_reward:
        add_blind_boxes(
            user_id,
            1,
        )

    return {
        "task_glimmers": task_glimmers,
        "grand_reward": has_grand_reward,
        "total_glimmers": total_glimmers,
        "new_epic": new_epic,
        "blind_boxes": 1 if has_grand_reward else 0,
    }


def build_reward_text(result):
    lines = []

    if result["task_glimmers"] > 0:
        lines.append(
            f"+ **{result['task_glimmers']:,}** "
            f"{GLIMMER_EMOTE} task rewards"
        )

    if result["grand_reward"]:
        lines.append(
            f"+ **{WEEKLY_GRAND_GLIMMERS:,}** "
            f"{GLIMMER_EMOTE} weekly reward"
        )

        if result["new_epic"] is not None:
            epic = result["new_epic"]

            lines.append(
                f"🃏 **New Epic Card**\n"
                f"`{epic['id']}` • **{epic['name']}**"
            )
        else:
            lines.append(
                "🃏 **New Epic Card**\n"
                "No new Epic card was available."
            )

        lines.append(
            "📦 **1 Blind Box** added to your collection."
        )

    return "\n\n".join(lines)


class RewardsView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.danger,
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            return

        result = claim_rewards(
            self.user_id
        )

        if result is None:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "**No Rewards Waiting**\n\n"
                    "You don't have any claimable "
                    "rewards right now.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None,
            )
            return

        embed = discord.Embed(
            description=(
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                "**REWARDS CLAIMED!** ✦\n\n"
                f"{build_reward_text(result)}\n\n"
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None,
        )


class Rewards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_rewards_database()

    @app_commands.command(
        name="rewards",
        description="View and claim your waiting rewards.",
    )
    async def rewards(
        self,
        interaction: discord.Interaction,
    ):
        rewards = get_pending_rewards(
            interaction.user.id
        )

        if not rewards:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "**No Rewards Waiting**\n\n"
                    "You don't have any claimable "
                    "rewards right now.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        task_glimmers = sum(
            reward[2]
            for reward in rewards
            if reward[1] == "task_glimmers"
        )

        has_grand = any(
            reward[1] == "weekly_grand"
            for reward in rewards
        )

        description = (
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
            "**WAITING REWARDS**\n\n"
        )

        if task_glimmers:
            description += (
                f"{GLIMMER_EMOTE} "
                f"**{task_glimmers:,}** Glimmers\n"
            )

        if has_grand:
            description += (
                f"{GLIMMER_EMOTE} "
                f"**{WEEKLY_GRAND_GLIMMERS:,}** "
                "Weekly Glimmers\n"
                "🃏 **1 New Epic Card**\n"
                "📦 **1 Blind Box**\n"
            )

        description += (
            "\n-# ✧ Press the button below to claim "
            "everything at once.\n\n"
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
        )

        embed = discord.Embed(
            description=description,
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
            view=RewardsView(
                interaction.user.id
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Rewards(bot)
        )
