
"""Magic Cabinet booster activation."""

from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import get_connection, initialize_database


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
    """Initialize booster tickets without removing existing data."""

    initialize_database()

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS booster_tickets (
                ticket_id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                booster_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                activated_at TEXT,
                expires_at TEXT,
                uses_remaining INTEGER
            )
            """
        )

        # Safely add the column to an existing PostgreSQL table.
        connection.execute(
            """
            ALTER TABLE booster_tickets
            ADD COLUMN IF NOT EXISTS uses_remaining INTEGER
            """
        )


def is_registered(user_id: int) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT user_id
            FROM players
            WHERE user_id = %s
            """,
            (user_id,),
        ).fetchone()

    return row is not None


def get_available_tickets(user_id: int):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT ticket_id, booster_id, received_at
            FROM booster_tickets
            WHERE user_id = %s
              AND activated_at IS NULL
            ORDER BY ticket_id ASC
            """,
            (user_id,),
        ).fetchall()


def get_active_boosters(user_id: int):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT ticket_id, booster_id, expires_at, uses_remaining
            FROM booster_tickets
            WHERE user_id = %s
              AND activated_at IS NOT NULL
              AND expires_at > %s
            ORDER BY activated_at ASC
            """,
            (user_id, now),
        ).fetchall()


def activate_ticket(
    ticket_id: int,
    user_id: int,
    booster_id: str,
    uses_remaining: int | None,
):
    now = datetime.now(timezone.utc)
    expires_at = now + BOOSTER_DURATION

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE booster_tickets
            SET activated_at = %s,
                expires_at = %s,
                uses_remaining = %s
            WHERE ticket_id = %s
              AND user_id = %s
              AND booster_id = %s
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

            for row in active_boosters:
                booster_id = row["booster_id"]
                expires_at = row["expires_at"]
                uses_remaining = row["uses_remaining"]

                booster = BOOSTERS.get(booster_id)

                if booster is None:
                    continue

                expiry = datetime.fromisoformat(expires_at)
                remaining = expiry - datetime.now(timezone.utc)

                hours = max(
                    0,
                    int(remaining.total_seconds()) // 3600,
                )
                minutes = max(
                    0,
                    (int(remaining.total_seconds()) % 3600) // 60,
                )

                usage = (
                    "∞"
                    if uses_remaining is None
                    else str(uses_remaining)
                )

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
                    "✦ Earn one from `/daily` or visit "
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

        ticket = tickets[0]
        ticket_id = ticket["ticket_id"]
        booster_id = ticket["booster_id"]
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

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Activate(bot))
