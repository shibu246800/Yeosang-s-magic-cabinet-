
import os

import discord
import psycopg
from psycopg.rows import dict_row
from discord import app_commands
from discord.ext import commands


EMBED_COLOR = discord.Color.from_str("#4E0017")


def get_postgres_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        database_url,
        connect_timeout=10,
        row_factory=dict_row,
    )


class Cabinet(commands.GroupCog, name="cabinet"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        try:
            with get_postgres_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO drop_channels (
                            guild_id,
                            channel1_id,
                            channel2_id,
                            channel3_id,
                            channel4_id,
                            channel5_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET
                            channel1_id = EXCLUDED.channel1_id,
                            channel2_id = EXCLUDED.channel2_id,
                            channel3_id = EXCLUDED.channel3_id,
                            channel4_id = EXCLUDED.channel4_id,
                            channel5_id = EXCLUDED.channel5_id
                        """,
                        (interaction.guild_id, *channel_ids),
                    )

        except Exception as error:
            print(f"[CABINET SETUP] PostgreSQL error: {error}")
            await interaction.response.send_message(
                "The Cabinet couldn't save your channels. Please try again later.",
                ephemeral=True,
            )
            return

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
        with get_postgres_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        channel1_id,
                        channel2_id,
                        channel3_id,
                        channel4_id,
                        channel5_id
                    FROM drop_channels
                    WHERE guild_id = %s
                    """,
                    (guild_id,),
                )
                result = cursor.fetchone()

        if result is None:
            return False

        return channel_id in [
            result[f"channel{number}_id"]
            for number in range(1, 6)
            if result[f"channel{number}_id"] is not None
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Cabinet(bot))
