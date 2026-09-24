"""Cabinet commands."""

import discord
from discord import app_commands
from discord.ext import commands


class Cabinet(commands.Cog):
    """Commands for Magic Cabinet setup."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="cabinet",
        description="Magic Cabinet commands."
    )
    async def cabinet(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Magic Cabinet is ready."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
