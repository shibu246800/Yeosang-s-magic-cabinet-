
"""Magic Cabinet purse command."""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import get_connection


EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"


def get_glimmers(user_id: int) -> int:
    """Return the player's current Glimmer balance."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT glimmers
            FROM balances
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return 0

    return row["glimmers"]


class Purse(commands.Cog):
    """Magic Cabinet purse commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="purse",
        description="View your current Glimmer balance.",
    )
    async def purse(self, interaction: discord.Interaction):
        """Show the player's current Glimmers."""

        await interaction.response.defer(thinking=True)

        try:
            glimmers = await asyncio.to_thread(
                get_glimmers,
                interaction.user.id,
            )

            embed = discord.Embed(
                description=(
                    f"{GLIMMER_EMOTE} **Glimmers**\n"
                    f"**{glimmers:,}** {GLIMMER_EMOTE}"
                ),
                color=EMBED_COLOR,
            )

            await interaction.edit_original_response(embed=embed)

        except Exception:
            await interaction.edit_original_response(
                content="Something went wrong while checking your purse. Please try again.",
                embed=None,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Purse(bot))
