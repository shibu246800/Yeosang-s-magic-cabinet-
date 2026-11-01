
"""Magic Cabinet daily rewards."""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import (
    get_connection,
    initialize_database,
)

from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS


EMBED_COLOR = discord.Color.from_str("#4E0017")

GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
BOOSTER_EMOTE = "<a:heartpotion:1556018680972714095>"

DAILY_GLIMMERS = 1000
DAILY_COOLDOWN = 24 * 60 * 60

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005080545.jpg"
)

DIVIDER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)

BOOSTERS = [
    {
        "id": "sunflare",
        "name": "Sunflare",
        "description": "Selling eligible cards gives 2× Glimmers.",
    },
    {
        "id": "moonveil",
        "name": "Moonveil",
        "description": "Next drops cannot give cards you already own.",
    },
    {
        "id": "starbox",
        "name": "Starbox",
        "description": (
            "Choose a Card ID and receive 4 copies "
            "for a small Glimmer fee."
        ),
    },
    {
        "id": "glimmerfall",
        "name": "Glimmerfall",
        "description": (
            "Successful card claims give 2× normal "
            "/drop Glimmer rewards."
        ),
    },
    {
        "id": "dreamstep",
        "name": "Dreamstep",
        "description": "Your next successful drop gives 1 extra card.",
    },
]


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_daily_database():
    """Initialize daily rewards using the shared database."""

    initialize_database()

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_data (
                user_id INTEGER PRIMARY KEY,
                last_claim_at TEXT
            )
            """
        )


# ============================================================
# DATABASE HELPERS
# ============================================================

def is_registered(user_id: int) -> bool:
    """Check the available player registration tables."""

    with get_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        for table_name in ("players", "player_vaults"):
            if table_name not in tables:
                continue

            columns = {
                row["name"]
                for row in connection.execute(
                    f"PRAGMA table_info({table_name})"
                ).fetchall()
            }

            if "user_id" not in columns:
                continue

            row = connection.execute(
                f"""
                SELECT user_id
                FROM {table_name}
                WHERE user_id = ?
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            if row is not None:
                return True

    return False


def get_daily_claim(user_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT last_claim_at
            FROM daily_data
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return None if row is None else row["last_claim_at"]


def get_glimmers(user_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT glimmers
            FROM balances
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return 0 if row is None else row["glimmers"]


def add_glimmers(user_id: int, amount: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO balances (
                user_id,
                glimmers
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                glimmers = balances.glimmers + excluded.glimmers
            """,
            (user_id, amount),
        )


def get_card_quantity(user_id: int, card_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

    return 0 if row is None else row["quantity"]


def add_card_to_bag(
    user_id: int,
    card_id,
) -> tuple[int, bool]:
    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

        connection.execute(
            """
            INSERT INTO bag (
                user_id,
                card_id,
                quantity
            )
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, card_id)
            DO UPDATE SET
                quantity = bag.quantity + 1
            """,
            (user_id, card_id),
        )

        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

    return row["quantity"], existing is None


def choose_daily_card() -> dict:
    card_pool = NORMAL_CARDS + RARE_CARDS + EPIC_CARDS

    if not card_pool:
        raise RuntimeError("The daily card pool is empty.")

    return random.choice(card_pool)


def choose_booster() -> dict:
    return random.choice(BOOSTERS)


def save_daily_claim(
    user_id: int,
    claim_time: datetime,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO daily_data (
                user_id,
                last_claim_at
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                last_claim_at = excluded.last_claim_at
            """,
            (
                user_id,
                claim_time.isoformat(),
            ),
        )


def save_booster_ticket(
    user_id: int,
    booster_id: str,
    received_at: datetime,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO booster_tickets (
                user_id,
                booster_id,
                received_at,
                source
            )
            VALUES (?, ?, ?, 'daily')
            """,
            (
                user_id,
                booster_id,
                received_at.isoformat(),
            ),
        )


def process_daily_rewards(
    user_id: int,
    card_id,
    booster_id: str,
    claim_time: datetime,
):
    """Process the existing daily rewards outside Discord's event loop."""

    new_quantity, was_new = add_card_to_bag(
        user_id,
        card_id,
    )

    add_glimmers(
        user_id,
        DAILY_GLIMMERS,
    )

    save_booster_ticket(
        user_id,
        booster_id,
        claim_time,
    )

    save_daily_claim(
        user_id,
        claim_time,
    )

    return new_quantity, was_new


# ============================================================
# FORMATTING
# ============================================================

def format_remaining(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


# ============================================================
# DAILY COMMAND
# ============================================================

class Daily(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="daily",
        description="Claim your daily Magic Cabinet rewards.",
    )
    async def daily(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        # Acknowledge Discord immediately.
        await interaction.response.defer(thinking=True)

        try:
            registered = await asyncio.to_thread(
                is_registered,
                user_id,
            )

            if not registered:
                await interaction.delete_original_response()

                embed = discord.Embed(
                    description=(
                        "✦ ────── ⋆⋅☆⋅⋆ ────── ✦\n\n"
                        "You haven't awakened your Cabinet yet.\n\n"
                        "✦ Use `/magic awaken` to begin.\n\n"
                        "✦ ────── ⋆⋅☆⋅⋆ ────── ✦"
                    ),
                    color=EMBED_COLOR,
                )

                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True,
                )
                return

            now = datetime.now(timezone.utc)

            last_claim_at = await asyncio.to_thread(
                get_daily_claim,
                user_id,
            )

            if last_claim_at:
                last_claim = datetime.fromisoformat(last_claim_at)

                if last_claim.tzinfo is None:
                    last_claim = last_claim.replace(
                        tzinfo=timezone.utc
                    )

                next_claim = last_claim + timedelta(
                    seconds=DAILY_COOLDOWN
                )

                remaining_seconds = int(
                    (next_claim - now).total_seconds()
                )

                if remaining_seconds > 0:
                    remaining = format_remaining(
                        remaining_seconds
                    )

                    await interaction.delete_original_response()

                    embed = discord.Embed(
                        description=(
                            "✦ ────── ⋆⋅☆⋅⋆ ────── ✦\n\n"
                            "The Cabinet has already left "
                            "today's gifts.\n\n"
                            "Come back when the next day opens.\n\n"
                            f"✦ ── **{remaining}** remaining ── ✦\n\n"
                            "✦ ────── ⋆⋅☆⋅⋆ ────── ✦"
                        ),
                        color=EMBED_COLOR,
                    )

                    await interaction.followup.send(
                        embed=embed,
                        ephemeral=True,
                    )
                    return

            card = choose_daily_card()
            booster = choose_booster()

            new_quantity, was_new = await asyncio.to_thread(
                process_daily_rewards,
                user_id,
                card["id"],
                booster["id"],
                now,
            )

        except Exception as error:
            print(f"[DAILY] Error: {error}")

            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass

            await interaction.followup.send(
                "The Cabinet couldn't process your daily rewards. Please try again later.",
                ephemeral=True,
            )
            return

        # ====================================================
        # REWARD EMBED
        # ====================================================

        if was_new:
            card_status = "✦ **New card added to your Bag!**"
        else:
            card_status = (
                f"✦ **Duplicate!** You now have "
                f"**{new_quantity}** copies."
            )

        collection = card.get("collection_id", "Unknown")
        rarity = card.get("stars", "★")

        reward_embed = discord.Embed(
            description=(
                "✦ ────── ⋆⋅☆⋅⋆ ────── ✦\n\n"
                "🎴 **Daily Card**\n\n"
                f"{rarity}  •  `{collection}`\n"
                f"✦ Card ID: `{card['id']}` ✦\n\n"
                f"{card_status}\n\n"
                "╰─ ⋆⋅☆⋅⋆ ─╯\n\n"
                f"{BOOSTER_EMOTE} **Booster Ticket**\n"
                f"✦ **{booster['name']}**\n"
                f"-# {booster['description']}\n"
                "-# ✧ Ticket received. It is not active yet.\n"
                "-# ✦ Use `/activate boost` whenever you wish.\n\n"
                "╰─ ⋆⋅☆⋅☆⋅⋆ ─╯\n\n"
                f"{GLIMMER_EMOTE} **Glimmers**\n"
                f"✦ +**{DAILY_GLIMMERS:,}** {GLIMMER_EMOTE}\n\n"
                "✦ ────── ⋆⋅☆⋅⋆ ────── ✦\n"
                "-# ✧ Return after **24 hours** for your next gift."
            ),
            color=EMBED_COLOR,
        )

        reward_embed.set_image(url=card["image"])

        header_embed = discord.Embed(color=EMBED_COLOR)
        header_embed.set_image(url=HEADER_URL)

        divider_embed = discord.Embed(color=EMBED_COLOR)
        divider_embed.set_image(url=DIVIDER_URL)

        await interaction.edit_original_response(
            embeds=[
                header_embed,
                reward_embed,
                divider_embed,
            ]
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await asyncio.to_thread(initialize_daily_database)
    await bot.add_cog(Daily(bot))
