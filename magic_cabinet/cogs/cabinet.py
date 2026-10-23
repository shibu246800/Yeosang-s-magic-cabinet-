
import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import (
    get_connection,
    initialize_database,
)


EMBED_COLOR = discord.Color.from_str("#4E0017")


class Cabinet(commands.GroupCog, name="cabinet"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_database()

    @app_commands.command(
        name="setup",
        description="Set the channels where /drop can be used.",
    )
    @app_commands.describe(
        drop_channel1="Required: first /drop channel.",
        drop_channel2="Optional: second /drop channel.",
        drop_channel3="Optional: third /drop channel.",
        drop_channel4="Optional: fourth /drop channel.",
        drop_channel5="Optional: fifth /drop channel.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        drop_channel1: discord.TextChannel,
        drop_channel2: discord.TextChannel | None = None,
        drop_channel3: discord.TextChannel | None = None,
        drop_channel4: discord.TextChannel | None = None,
        drop_channel5: discord.TextChannel | None = None,
    ):
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        channels = [
            drop_channel1,
            drop_channel2,
            drop_channel3,
            drop_channel4,
            drop_channel5,
        ]

        unique_channels = []
        seen_ids = set()

        for channel in channels:
            if channel is not None and channel.id not in seen_ids:
                unique_channels.append(channel)
                seen_ids.add(channel.id)

        channel_ids = [channel.id for channel in unique_channels]

        while len(channel_ids) < 5:
            channel_ids.append(None)

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO drop_channels (
                    guild_id,
                    channel1_id,
                    channel2_id,
                    channel3_id,
                    channel4_id,
                    channel5_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id)
                DO UPDATE SET
                    channel1_id = excluded.channel1_id,
                    channel2_id = excluded.channel2_id,
                    channel3_id = excluded.channel3_id,
                    channel4_id = excluded.channel4_id,
                    channel5_id = excluded.channel5_id
                """,
                (
                    interaction.guild_id,
                    *channel_ids,
                ),
            )

        channel_list = "\n".join(
            f"• {channel.mention}"
            for channel in unique_channels
        )

        embed = discord.Embed(
            description=(
                "🗝️ **Drop channels saved!**\n\n"
                "➷ `/drop` can now be used only in:\n"
                f"{channel_list}\n\n"
                "❃ Players must use `/magic awaken` next.\n"
                "✦ Other player commands remain locked until "
                "their vault has been saved."
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(embed=embed)

    def is_drop_channel(
        self,
        guild_id: int,
        channel_id: int,
    ) -> bool:
        with get_connection() as connection:
            result = connection.execute(
                """
                SELECT
                    channel1_id,
                    channel2_id,
                    channel3_id,
                    channel4_id,
                    channel5_id
                FROM drop_channels
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()

        if result is None:
            return False

        return channel_id in [
            result[f"channel{number}_id"]
            for number in range(1, 6)
            if result[f"channel{number}_id"] is not None
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
