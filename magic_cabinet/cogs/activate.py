"""Magic Cabinet booster activation."""

import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"
EMBED_COLOR = discord.Color.from_str("#4E0017")

BOOSTER_EMOTE = "<a:heartpotion:1556018680972714095>"
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

BOOSTER_DURATION = timedelta(hours=24)

BOOSTERS = {
    "sunflare": {
        "name": "Sunflare",
        "description": "Selling eligible cards gives 2× Glimmers.",
        "uses": None,
    },
    "moonveil": {
        "name": "Moonveil",
        "description": "Next drops cannot give cards you already own.",
        "uses": 10,
    },
    "starbox": {
        "name": "Starbox",
        "description": "Choose a Card ID and receive 3 copies for a Glimmer fee.",
        "uses": 1,
    },
    "glimmerfall": {
        "name": "Glimmerfall",
        "description": "Successful card claims give 2× normal /drop Glimmer rewards.",
        "uses": None,
    },
    "dreamstep": {
        "name": "Dreamstep",
        "description": "Your next successful drop gives 1 extra card.",
        "uses": 1,
    },
}


def initialize_activate_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS booster_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booster_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                activated_at TEXT,
                expires_at TEXT,
                uses_remaining INTEGER
            )
            """
        )

        connection.commit()

        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(booster_tickets)"
            ).fetchall()
        ]

        if "uses_remaining" not in columns:
            connection.execute(
                """
                ALTER TABLE booster_tickets
                ADD COLUMN uses_remaining INTEGER
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


def get_available_tickets(user_id: int):
    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT ticket_id, booster_id, received_at
            FROM booster_tickets
            WHERE user_id = ?
            AND activated_at IS NULL
            ORDER BY ticket_id ASC
            """,
            (user_id,),
        ).fetchall()


def get_active_boosters(user_id: int):
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE) as connection:
        return connection.execute(
            """
            SELECT ticket_id, booster_id, expires_at, uses_remaining
            FROM booster_tickets
            WHERE user_id = ?
            AND activated_at IS NOT NULL
            AND expires_at > ?
            ORDER BY activated_at ASC
            """,
            (
                user_id,
                now,
            ),
        ).fetchall()


def activate_ticket(
    ticket_id: int,
    user_id: int,
    booster_id: str,
    uses_remaining: int | None,
):
    now = datetime.now(timezone.utc)
    expires_at = now + BOOSTER_DURATION

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            """
            UPDATE booster_tickets
            SET activated_at = ?,
                expires_at = ?,
                uses_remaining = ?
            WHERE ticket_id = ?
            AND user_id = ?
            AND booster_id = ?
            AND activated_at IS NULL
            """,
            (
                now.isoformat(),
                expires_at.isoformat(),
                uses_remaining,
                ticket_id,
                user_id,
                booster_id,
            ),
        )

        connection.commit()

        if cursor.rowcount != 1:
            return None

    return expires_at


class Activate(commands.GroupCog, name="activate"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_activate_database()

    @app_commands.command(
        name="boost",
        description="Activate one of your Booster Tickets.",
    )
    async def boost(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        if not is_registered(user_id):
            embed = discord.Embed(
                description=(
                    "✦ ── ⋆⋅☆⋅⋆ ── ✦\n\n"
                    "You haven't awakened your Cabinet yet.\n\n"
                    "✧ Use `/magic awaken` to begin.\n\n"
                    "✦ ── ⋆⋅☆⋅⋆ ── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        active_boosters = get_active_boosters(user_id)

        if active_boosters:
            lines = []

            for _, booster_id, expires_at, uses_remaining in active_boosters:
                booster = BOOSTERS.get(booster_id)

                if booster is None:
                    continue

                expiry = datetime.fromisoformat(expires_at)
                remaining = expiry - datetime.now(timezone.utc)

                hours = max(0, int(remaining.total_seconds()) // 3600)
                minutes = max(
                    0,
                    (int(remaining.total_seconds()) % 3600) // 60,
                )

                if uses_remaining is None:
                    usage = "∞"
                else:
                    usage = str(uses_remaining)

                lines.append(
                    f"{BOOSTER_EMOTE} **{booster['name']}**\n"
                    f"-# ✦ {hours}h {minutes}m remaining • Uses: **{usage}**"
                )

            if lines:
                embed = discord.Embed(
                    description=(
                        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                        "You already have an active booster.\n\n"
                        + "\n\n".join(lines)
                        + "\n\n"
                        "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                    ),
                    color=EMBED_COLOR,
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )
                return

        tickets = get_available_tickets(user_id)

        if not tickets:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    f"{BOOSTER_EMOTE} **No Booster Tickets**\n\n"
                    "You don't have a Booster Ticket waiting.\n\n"
                    f"✦ Earn one from `/daily` or visit "
                    "`/booster shop` to get another.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        ticket_id, booster_id, _ = tickets[0]

        booster = BOOSTERS.get(booster_id)

        if booster is None:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "This Booster Ticket could not be identified.\n\n"
                    "✦ Please try another ticket.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        expires_at = activate_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            booster_id=booster_id,
            uses_remaining=booster["uses"],
        )

        if expires_at is None:
            embed = discord.Embed(
                description=(
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                    "That Booster Ticket is no longer available.\n\n"
                    "✧ Please use `/activate boost` again.\n\n"
                    "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
                ),
                color=EMBED_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        if booster["uses"] is None:
            usage_text = "Unlimited uses during the 24-hour activation."
        else:
            usage_text = (
                f"**{booster['uses']}** use"
                f"{'s' if booster['uses'] != 1 else ''} available."
            )

        embed = discord.Embed(
            description=(
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦\n\n"
                f"{BOOSTER_EMOTE} **{booster['name']} ACTIVATED**\n\n"
                f"✧ {booster['description']}\n\n"
                f"{GLIMMER_EMOTE} **Duration**\n"
                "✦ Active for **24 hours**.\n\n"
                f"✧ **{usage_text}**\n\n"
                "-# ✦ Your Booster Ticket has been consumed.\n"
                "-# ✧ The effect begins now.\n\n"
                "✦ ───── ⋆⋅☆⋅⋆ ───── ✦"
            ),
            color=EMBED_COLOR,
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Activate(bot)
      )
