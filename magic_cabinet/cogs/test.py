"""Moderator-only Magic Cabinet testing commands."""

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.cogs.rewards import (
    add_blind_boxes,
)

MODERATOR_IDS = {
    986907099617452032,
}

EMBED_COLOR = discord.Color.from_str("#4E0017")


def is_moderator(user_id: int) -> bool:
    return user_id in MODERATOR_IDS


class Test(commands.GroupCog, name="test"):
    """Moderator-only testing commands."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if is_moderator(interaction.user.id):
            return True

        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ You don't have permission to use test commands.",
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )

        return False

    @app_commands.command(
        name="blindbox",
        description="Give yourself 1 Blind Box for testing.",
    )
    async def test_blindbox(
        self,
        interaction: discord.Interaction,
    ):
        add_blind_boxes(
            interaction.user.id,
            1,
        )

        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    "✦ **TEST**\n\n"
                    "📦 **1 Blind Box added.**\n\n"
                    "-# You can now use `/blindbox`."
                ),
                color=EMBED_COLOR,
            ),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Test(bot)
      )
