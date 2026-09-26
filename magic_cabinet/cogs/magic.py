import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"


class Magic(commands.GroupCog, name="magic"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="awaken",
        description="Awaken your place within the Magic Cabinet.",
    )
    async def awaken(self, interaction: discord.Interaction):

        user_id = interaction.user.id

        with sqlite3.connect(DATABASE) as connection:
            existing_player = connection.execute(
                """
                SELECT user_id
                FROM players
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if existing_player is not None:
                await interaction.response.send_message(
                    "🔐 **Your Cabinet is already awakened.**\n\n"
                    "Your player record already exists.",
                    ephemeral=True,
                )
                return

            connection.execute(
                """
                INSERT INTO players (
                    user_id,
                    created_at
                )
                VALUES (?, ?)
                """,
                (
                    user_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            connection.commit()

        await interaction.response.send_message(
            f"🗝️ **The Cabinet has awakened for {interaction.user.mention}.**\n\n"
            "Your place within the Cabinet has been recorded.\n"
            "Your journey begins now."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Magic(bot))
