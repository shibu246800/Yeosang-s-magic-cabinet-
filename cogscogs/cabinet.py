"""Cabinet commands."""

import discord
from discord import app_commands
from discord.ext import commands


class Cabinet(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    cabinet = app_commands.Group(
        name="cabinet",
        description="Magic Cabinet settings.",
    )

    @cabinet.command(
        name="setup",
        description="Set the channels where Magic Cabinet can be used.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Cabinet setup is ready. Channel selection will be added next."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
