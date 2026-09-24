"""Drop command."""

import discord
from discord import app_commands
from discord.ext import commands


class Drop(commands.Cog):
    """Commands for dropping cards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="drop",
        description="Drop a card from the Magic Cabinet.",
    )
    async def drop(self, interaction: discord.Interaction):
        """Handle the /drop command."""

        cabinet = self.bot.get_cog("Cabinet")

        if cabinet is None:
            await interaction.response.send_message(
                "Magic Cabinet setup is currently unavailable."
            )
            return

        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used inside a server."
            )
            return

        allowed = cabinet.is_drop_channel(
            interaction.guild_id,
            interaction.channel_id,
        )

        if not allowed:
            await interaction.response.send_message(
                "This command can only be used in a configured Drop channel."
            )
            return

        await interaction.response.send_message(
            "🎴 Drop channel confirmed! The card system is coming next."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Drop(bot))
