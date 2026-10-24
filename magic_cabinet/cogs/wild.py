
"""Claim Legendary collection rewards."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.legendary import CARDS as LEGENDARY_CARDS


EMBED_COLOR = discord.Color.from_str("#4E0017")
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
GLIMMER_REWARD = 100_000

DATABASE = Path(__file__).resolve().parents[2] / "cabinet.db"
COLLECTIONS_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "collections.json"
)

BASE_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
)


def get_connection():
    connection = sqlite3.connect(str(DATABASE))
    connection.row_factory = sqlite3.Row
    return connection


def initialize_wild_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_legendary (
                user_id INTEGER NOT NULL,
                collection_id TEXT NOT NULL,
                legendary_id TEXT NOT NULL,
                claimed_at TEXT,
                PRIMARY KEY (user_id, collection_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_rewards (
                user_id INTEGER NOT NULL,
                collection_id TEXT NOT NULL,
                claimed INTEGER NOT NULL DEFAULT 0,
                claimed_at TEXT,
                PRIMARY KEY (user_id, collection_id)
            )
            """
        )


def load_collections():
    if not COLLECTIONS_FILE.exists():
        return []

    with COLLECTIONS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("collections", [])

    return data if isinstance(data, list) else []


def get_collection_id(collection):
    return str(collection.get("id", collection.get("collection_id", "")))


def get_owned_count(user_id: int, collection_id: str) -> int:
    collection_cards = [
        card for card in BASE_CARDS
        if str(card.get("collection_id", "")).upper()
        == collection_id.upper()
    ]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT card_id
            FROM bag
            WHERE user_id = ? AND quantity > 0
            """,
            (user_id,),
        ).fetchall()

    owned_ids = {str(row["card_id"]) for row in rows}

    return len({
        str(card["id"])
        for card in collection_cards
        if str(card.get("id")) in owned_ids
    })


class Wild(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_wild_database()

    @app_commands.command(
        name="wild",
        description="Claim a completed collection's Legendary reward.",
    )
    @app_commands.describe(
        collection_id="The completed collection ID, such as BB_1."
    )
    async def wild(
        self,
        interaction: discord.Interaction,
        collection_id: str,
    ):
        user_id = interaction.user.id
        collection_id = collection_id.strip().upper()

        collection = next(
            (
                item for item in load_collections()
                if get_collection_id(item).upper() == collection_id
            ),
            None,
        )

        if collection is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Collection `{collection_id}` was not found.",
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        legendary = next(
            (
                card for card in LEGENDARY_CARDS
                if str(card.get("collection_id", "")).upper()
                == collection_id
            ),
            None,
        )

        if legendary is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "The Legendary reward for this collection "
                        "has not been configured yet."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        vault = str(collection.get("vault", "")).upper()

        with get_connection() as connection:
            selected = connection.execute(
                """
                SELECT vault FROM player_vaults
                WHERE user_id = ? AND vault = ?
                """,
                (user_id, vault),
            ).fetchone()

        if selected is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You have not selected this collection's Vault.",
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        count = get_owned_count(user_id, collection_id)

        if count < 6:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"**{collection.get('name', collection_id)}**\n"
                        f"Progress: **{count}/6 Cards**\n\n"
                        "You need all six base cards before claiming this reward."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")

            previous_claim = connection.execute(
                """
                SELECT claimed FROM collection_rewards
                WHERE user_id = ? AND collection_id = ?
                """,
                (user_id, collection_id),
            ).fetchone()

            if previous_claim and int(previous_claim["claimed"]) == 1:
                connection.rollback()
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="You have already claimed this reward.",
                        color=EMBED_COLOR,
                    ),
                    ephemeral=True,
                )
                return

            connection.execute(
                """
                INSERT INTO balances (user_id, glimmers)
                VALUES (?, 0)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (user_id,),
            )

            connection.execute(
                """
                INSERT INTO player_legendary
                    (user_id, collection_id, legendary_id, claimed_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, collection_id, str(legendary["id"]), now),
            )

            connection.execute(
                """
                INSERT INTO collection_rewards
                    (user_id, collection_id, claimed, claimed_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, collection_id)
                DO UPDATE SET claimed = 1, claimed_at = excluded.claimed_at
                """,
                (user_id, collection_id, now),
            )

            connection.execute(
                """
                UPDATE balances
                SET glimmers = glimmers + ?
                WHERE user_id = ?
                """,
                (GLIMMER_REWARD, user_id),
            )

            balance_row = connection.execute(
                "SELECT glimmers FROM balances WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            balance = int(balance_row["glimmers"])
            connection.commit()

        embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                "                 **THE REWARD IS YOURS**\n"
                "╰────────────── ✦ ──────────────╯\n\n"
                f"**{collection.get('name', collection_id)}** · `{collection_id}`\n\n"
                f"✨ **Legendary:** `{legendary['id']}`\n"
                f"◈ **Glimmers received:** {GLIMMER_EMOTE} **100,000**\n\n"
                f"Your balance: {GLIMMER_EMOTE} **{balance:,}**\n\n"
                "Your Legendary is saved to your profile.\n"
                "This reward can only be claimed once."
            ),
            color=EMBED_COLOR,
        )

        if legendary.get("image"):
            embed.set_image(url=legendary["image"])

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Wild(bot))
