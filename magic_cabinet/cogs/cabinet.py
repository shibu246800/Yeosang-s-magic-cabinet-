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
        channel1="Required: choose the main channel where Yeosang can work.",
        channel2="Optional: choose another Cabinet channel.",
        channel3="Optional: choose another Cabinet channel.",
        channel4="Optional: choose another Cabinet channel.",
        channel5="Optional: choose another Cabinet channel.",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channel1: discord.TextChannel,
        channel2: discord.TextChannel | None = None,
        channel3: discord.TextChannel | None = None,
        channel4: discord.TextChannel | None = None,
        channel5: discord.TextChannel | None = None,
    ):
        selected_channels = [
            channel
            for channel in (
                channel1,
                channel2,
                channel3,
                channel4,
                channel5,
            )
            if channel is not None
        ]

        channel_list = "\n".join(
            f"• {channel.mention}"
            for channel in selected_channels
        )

        await interaction.response.send_message(
            f"Magic Cabinet setup received!\n\n"
            f"Yeosang now works in:\n{channel_list}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
