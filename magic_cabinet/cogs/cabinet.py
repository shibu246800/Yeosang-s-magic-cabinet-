import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"


def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS drop_channels (
                guild_id INTEGER PRIMARY KEY,
                channel1_id INTEGER NOT NULL,
                channel2_id INTEGER,
                channel3_id INTEGER,
                channel4_id INTEGER,
                channel5_id INTEGER
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                vault TEXT
            )
            """
        )

        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(players)"
            ).fetchall()
        ]

        if "vault" not in columns:
            connection.execute(
                "ALTER TABLE players ADD COLUMN vault TEXT"
            )

        connection.commit()


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

        channels = [
            drop_channel1,
            drop_channel2,
            drop_channel3,
            drop_channel4,
            drop_channel5,
        ]

        selected_channels = [
            channel
            for channel in channels
            if channel is not None
        ]

        unique_channels = []
        seen_ids = set()

        for channel in selected_channels:
            if channel.id not in seen_ids:
                unique_channels.append(channel)
                seen_ids.add(channel.id)

        channel_ids = [
            channel.id
            for channel in unique_channels
        ]

        while len(channel_ids) < 5:
            channel_ids.append(None)

        with sqlite3.connect(DATABASE) as connection:
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

        embed = discord.Embed(
            description=(
                "🗝️ **Drop channels saved!**\n\n"
                "➷ `/drop` can now be used only in:\n"
                f"{channel_list}\n\n"
                "-# ❃ Other Magic Cabinet commands are not restricted "
                "by this setup.✒\n"
                "✦ Players can now begin with `/magic awaken`"
            ),
            color=discord.Color.from_str("#4E0017"),
        )

        await interaction.response.send_message(
            embed=embed
        )

    def is_drop_channel(
        self,
        guild_id: int,
        channel_id: int,
    ) -> bool:

        with sqlite3.connect(DATABASE) as connection:
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

        drop_channel_ids = [
            saved_id
            for saved_id in result
            if saved_id is not None
        ]

        return channel_id in drop_channel_ids


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
