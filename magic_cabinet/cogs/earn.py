"""Magic Cabinet earn command."""

import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"

EMBED_COLOR = discord.Color.from_str("#4E0017")
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

COOLDOWN_SECONDS = 60 * 60
FIRST_EARNING = 100
EARNING_INCREASE = 10


def initialize_earn_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS earn_data (
                user_id INTEGER PRIMARY KEY,
                last_earn_at TEXT,
                daily_earnings INTEGER NOT NULL DEFAULT 100,
                reset_date TEXT
            )
            """
        )
        connection.commit()


def is_registered(user_id: int) -> bool:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT user_id
            FROM players
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row is not None


def get_balance(user_id: int) -> int:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT glimmers
            FROM balances
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return 0 if row is None else row[0]


def add_glimmers(user_id: int, amount: int) -> int:
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT INTO balances (user_id, glimmers)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET glimmers = glimmers + excluded.glimmers
            """,
            (user_id, amount),
        )
        connection.commit()

    return get_balance(user_id)


def get_earn_data(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT last_earn_at, daily_earnings, reset_date
            FROM earn_data
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return row


def reset_daily_earnings_if_needed(user_id: int):
    today = datetime.now(timezone.utc).date().isoformat()

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT reset_date
            FROM earn_data
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO earn_data (
                    user_id,
                    daily_earnings,
                    reset_date
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    FIRST_EARNING,
                    today,
                ),
            )
        elif row[0] != today:
            connection.execute(
                """
                UPDATE earn_data
                SET daily_earnings = ?,
                    reset_date = ?
                WHERE user_id = ?
                """,
                (
                    FIRST_EARNING,
                    today,
                    user_id,
                ),
            )

        connection.commit()


class Earn(commands.Cog):
    """Magic Cabinet earning commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_earn_database()

    @app_commands.command(
        name="earn",
        description="Earn hourly Glimmers.",
    )
    async def earn(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        if not is_registered(user_id):
            embed = discord.Embed(
                description=(
                    "You haven't awakened your Cabinet yet.\n\n"
                    "-# ✦ Use `/magic awaken` to begin."
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        reset_daily_earnings_if_needed(user_id)

        data = get_earn_data(user_id)

        last_earn_at = data[0]
        earning_amount = data[1]

        now = datetime.now(timezone.utc)

        if last_earn_at:
            last_earn = datetime.fromisoformat(last_earn_at)

            elapsed = (
                now - last_earn
            ).total_seconds()

            if elapsed < COOLDOWN_SECONDS:
                remaining = int(
                    COOLDOWN_SECONDS - elapsed
                )

                hours = remaining // 3600
                minutes = (remaining % 3600) // 60

                if hours:
                    cooldown_text = f"{hours}h {minutes}m"
                else:
                    cooldown_text = f"{minutes}m"

                embed = discord.Embed(
                    description=(
                        "Your purse is still resting. ✦\n\n"
                        f"-# Come back in **{cooldown_text}** "
                        "to `/earn` again."
                    ),
                    color=EMBED_COLOR,
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )
                return

        new_balance = add_glimmers(
            user_id,
            earning_amount,
        )

        next_amount = earning_amount + EARNING_INCREASE

        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """
                UPDATE earn_data
                SET last_earn_at = ?,
                    daily_earnings = ?
                WHERE user_id = ?
                """,
                (
                    now.isoformat(),
                    next_amount,
                    user_id,
                ),
            )
            connection.commit()

        embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                f"You earned **{earning_amount}** "
                f"{GLIMMER_EMOTE} Glimmers!\n\n"
                f"**New balance:** {new_balance:,} "
                f"{GLIMMER_EMOTE}\n\n"
                "-# ✦ Come back after 1 hour to `/earn` again."
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Earn(bot))
