"""Magic Cabinet setup commands."""

import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"


def initialize_database():
    """Create the Cabinet database if it does not exist."""
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cabinet_channels (
                guild_id INTEGER PRIMARY KEY,
                channel1_id INTEGER NOT NULL,
                channel2_id INTEGER,
                channel3_id INTEGER,
                channel4_id INTEGER,
                channel5_id INTEGER
            )
            """
        )
        connection.commit()


class Cabinet(commands.GroupCog, name="cabinet"):
    """Commands for Magic Cabinet."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_database()

    @app_commands.command(
        name="setup",
        description=(
            "Set your channel/channels where Yeosang can work. "
            "It can be changed anytime."
        ),
    )
    @app_commands.describe(
        channel1="Required: choose the main channel where Yeosang can work.",
        channel2="Optional: choose another Cabinet channel.",
        channel3="Optional: choose another Cabinet channel.",
        channel4="Optional: choose another Cabinet channel.",
        channel5="Optional: choose another Cabinet channel.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        channel1: discord.TextChannel,
        channel2: discord.TextChannel | None = None,
        channel3: discord.TextChannel | None = None,
        channel4: discord.TextChannel | None = None,
        channel5: discord.TextChannel | None = None,
    ):
        """Save or update the Cabinet channels."""

        channels = [
            channel1,
            channel2,
            channel3,
            channel4,
            channel5,
        ]

        # Remove empty slots.
        selected_channels = [
            channel for channel in channels
            if channel is not None
        ]

        # Remove duplicate channels while keeping their order.
        unique_channels = []
        seen_ids = set()

        for channel in selected_channels:
            if channel.id not in seen_ids:
                unique_channels.append(channel)
                seen_ids.add(channel.id)

        channel_ids = [channel.id for channel in unique_channels]

        while len(channel_ids) < 5:
            channel_ids.append(None)

        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """
                INSERT INTO cabinet_channels (
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
                    channel_ids[0],
                    channel_ids[1],
                    channel_ids[2],
                    channel_ids[3],
                    channel_ids[4],
                ),
            )
            connection.commit()

        channel_list = "\n".join(
            f"• {channel.mention}"
            for channel in unique_channels
        )

        await interaction.response.send_message(
            "🔐 **Magic Cabinet channels updated!**\n\n"
            "Yeosang can work in:\n"
            f"{channel_list}\n\n"
            "You can change these channels anytime by using "
            "`/cabinet setup` again."
        )

    def is_cabinet_channel(
        self,
        guild_id: int,
        channel_id: int,
    ) -> bool:
        """Return True if the channel is configured for Magic Cabinet."""

        with sqlite3.connect(DATABASE) as connection:
            result = connection.execute(
                """
                SELECT
                    channel1_id,
                    channel2_id,
                    channel3_id,
                    channel4_id,
                    channel5_id
                FROM cabinet_channels
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()

        if result is None:
            return False

        return channel_id in result

    def get_cabinet_channels(
        self,
        guild_id: int,
    ) -> list[int]:
        """Return all configured Cabinet channel IDs."""

        with sqlite3.connect(DATABASE) as connection:
            result = connection.execute(
                """
                SELECT
                    channel1_id,
                    channel2_id,
                    channel3_id,
                    channel4_id,
                    channel5_id
                FROM cabinet_channels
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()

        if result is None:
            return []

        return [
            channel_id
            for channel_id in result
            if channel_id is not None
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
