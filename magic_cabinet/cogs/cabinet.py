"""Cabinet commands."""

import discord
from discord import app_commands
from discord.ext import commands


class Cabinet(commands.GroupCog, name="cabinet"):
    """Commands for Magic Cabinet."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="Set your channel/channels where Yeosang can work. It can be changed anytime."
    )
    @app_commands.describe(
        channel="Choose the channel where Yeosang can work."
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        await interaction.response.send_message(
            f"Yeosang can work in {channel.mention}."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
