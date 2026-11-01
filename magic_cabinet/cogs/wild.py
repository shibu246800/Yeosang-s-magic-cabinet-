
"""Claim Legendary collection rewards."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import get_connection, initialize_database
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.legendary import CARDS as LEGENDARY_CARDS


EMBED_COLOR = discord.Color.from_str("#4E0017")
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
GLIMMER_REWARD = 100_000

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


def initialize_wild_database():
    initialize_database()


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


def process_wild_claim(user_id: int, collection_id: str):
    """Perform all Wild command database work in a worker thread."""

    collections = load_collections()

    collection = next(
        (
            item for item in collections
            if get_collection_id(item).upper() == collection_id
        ),
        None,
    )

    if collection is None:
        return {"status": "collection_missing"}

    legendary = next(
        (
            card for card in LEGENDARY_CARDS
            if str(card.get("collection_id", "")).upper()
            == collection_id
        ),
        None,
    )

    if legendary is None:
        return {"status": "legendary_missing"}

    vault = str(collection.get("vault", "")).upper()

    collection_cards = [
        card for card in BASE_CARDS
        if str(card.get("collection_id", "")).upper()
        == collection_id
    ]

    with get_connection() as connection:
        selected = connection.execute(
            """
            SELECT vault FROM player_vaults
            WHERE user_id = ? AND vault = ?
            """,
            (user_id, vault),
        ).fetchone()

        if selected is None:
            return {"status": "vault_missing"}

        rows = connection.execute(
            """
            SELECT card_id
            FROM bag
            WHERE user_id = ? AND quantity > 0
            """,
            (user_id,),
        ).fetchall()

    owned_ids = {str(row["card_id"]) for row in rows}

    count = len({
        str(card["id"])
        for card in collection_cards
        if str(card.get("id")) in owned_ids
    })

    if count < 6:
        return {
            "status": "incomplete",
            "count": count,
            "collection": collection,
        }

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
            return {"status": "already_claimed"}

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

    return {
        "status": "success",
        "collection": collection,
        "legendary": legendary,
        "balance": balance,
    }


class Wild(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            result = await asyncio.to_thread(
                process_wild_claim,
                user_id,
                collection_id,
            )

            status = result["status"]

            if status == "collection_missing":
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        description=f"Collection `{collection_id}` was not found.",
                        color=EMBED_COLOR,
                    )
                )
                return

            if status == "legendary_missing":
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        description=(
                            "The Legendary reward for this collection "
                            "has not been configured yet."
                        ),
                        color=EMBED_COLOR,
                    )
                )
                return

            if status == "vault_missing":
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        description="You have not selected this collection's Vault.",
                        color=EMBED_COLOR,
                    )
                )
                return

            if status == "incomplete":
                collection = result["collection"]

                await interaction.edit_original_response(
                    embed=discord.Embed(
                        description=(
                            f"**{collection.get('name', collection_id)}**\n"
                            f"Progress: **{result['count']}/6 Cards**\n\n"
                            "You need all six base cards before claiming this reward."
                        ),
                        color=EMBED_COLOR,
                    )
                )
                return

            if status == "already_claimed":
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        description="You have already claimed this reward.",
                        color=EMBED_COLOR,
                    )
                )
                return

            collection = result["collection"]
            legendary = result["legendary"]
            balance = result["balance"]

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

            await interaction.edit_original_response(embed=embed)

        except Exception:
            await interaction.edit_original_response(
                content="Something went wrong while claiming your Legendary reward. Please try again.",
                embed=None,
            )


async def setup(bot: commands.Bot):
    await asyncio.to_thread(initialize_wild_database)
    await bot.add_cog(Wild(bot))
