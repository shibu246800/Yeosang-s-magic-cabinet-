"""Magic Cabinet rewards command."""

import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"


def get_pending_rewards(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
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

    return rows


def claim_rewards(user_id: int):
    rewards = get_pending_rewards(user_id)

    if not rewards:
        return None

    total_glimmers = sum(
        reward[2]
        for reward in rewards
        if reward[1] == "task_glimmers"
    )

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

    return {
        "total_glimmers": total_glimmers,
        "reward_count": len(rewards),
    }


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

        total = result["total_glimmers"]

        embed = discord.Embed(
            description=(
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                "**REWARDS CLAIMED!** ✦\n\n"
                f"+ **{total:,}** {GLIMMER_EMOTE}\n\n"
                "-# ✧ Your waiting rewards have been "
                "added to your purse.\n\n"
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

        total_glimmers = sum(
            reward[2]
            for reward in rewards
            if reward[1] == "task_glimmers"
        )

        description = (
            "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
            "**WAITING REWARDS**\n\n"
            f"{GLIMMER_EMOTE} "
            f"**{total_glimmers:,}** Glimmers\n\n"
            f"-# ✧ {len(rewards)} reward"
            f"{'s' if len(rewards) != 1 else ''} "
            "waiting to be claimed.\n\n"
            "-# ✧ Press the button below to claim "
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
