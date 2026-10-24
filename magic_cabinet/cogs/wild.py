"""Collection reward claims: Legendary card + 100,000 Glimmers."""

from datetime import datetime, timezone
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import get_connection
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.legendary import CARDS as LEGENDARY_CARDS


EMBED_COLOR = 0x4E0017
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"
GLIMMER_REWARD = 100_000

ALL_BASE_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
)

DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "collections.json"
)


def load_collections():
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("collections", [])

    return data if isinstance(data, list) else []


def collection_id_of(collection):
    return str(
        collection.get("id", collection.get("collection_id", ""))
    )


def ensure_reward_tables():
    with get_connection() as connection:
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

        connection.commit()


def find_collection(collection_id):
    return next(
        (
            collection
            for collection in load_collections()
            if collection_id_of(collection).upper()
            == collection_id.upper()
        ),
        None,
    )


def find_legendary(collection_id):
    return next(
        (
            card for card in LEGENDARY_CARDS
            if str(card.get("collection_id", "")).upper()
            == collection_id.upper()
        ),
        None,
    )


def get_owned_base_count(user_id, collection_id):
    owned_cards = [
        card for card in ALL_BASE_CARDS
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
        for card in owned_cards
        if str(card.get("id")) in owned_ids
    })


def get_balance(user_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT glimmers FROM balances WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return int(row["glimmers"]) if row else 0


def claim_collection_reward(user_id, collection_id, legendary):
    """
    Atomically record the claim and award Glimmers.
    Legendary ownership is recorded separately from bag.
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
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

        connection.execute("BEGIN IMMEDIATE")

        existing = connection.execute(
            """
            SELECT claimed
            FROM collection_rewards
            WHERE user_id = ? AND collection_id = ?
            """,
            (user_id, collection_id),
        ).fetchone()

        if existing and int(existing["claimed"]) == 1:
            connection.rollback()
            return False, "already_claimed"

        # Require a matching Legendary reward entry.
        if not legendary:
            connection.rollback()
            return False, "legendary_missing"

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

        connection.commit()

    return True, "success"


class Wild(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        ensure_reward_tables()

    @app_commands.command(
        name="wild",
        description="Claim the Legendary reward for a completed collection.",
    )
    @app_commands.describe(
        collection_id="The completed collection ID, for example BB_1."
    )
    async def wild(
        self,
        interaction: discord.Interaction,
        collection_id: str,
    ):
        collection_id = collection_id.strip().upper()

        collection = find_collection(collection_id)

        if collection is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"🔎 Collection `{collection_id}` was not found."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        vault = str(collection.get("vault", "")).upper()

        with get_connection() as connection:
            selected_vaults = connection.execute(
                """
                SELECT vault
                FROM player_vaults
                WHERE user_id = ?
                """,
                (interaction.user.id,),
            ).fetchall()

        if vault not in {row["vault"] for row in selected_vaults}:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "🔒 This collection belongs to a Vault "
                        "you have not selected."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        owned_count = get_owned_base_count(
            interaction.user.id,
            collection_id,
        )

        if owned_count < 6:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "╭────────────── ✦ ──────────────╮\n"
                        "                 **THE REWARD IS SEALED**\n"
                        "╰────────────── ✦ ──────────────╯\n\n"
                        f"Collection: **{collection.get('name', collection_id)}**\n"
                        f"Progress: **{owned_count}/6 Cards**\n\n"
                        "Collect all six base cards before using `/wild`."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        legendary = find_legendary(collection_id)

        if legendary is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "⚠️ The Legendary reward for this collection "
                        "has not been configured yet."
                    ),
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        success, reason = claim_collection_reward(
            interaction.user.id,
            collection_id,
            legendary,
        )

        if not success:
            if reason == "already_claimed":
                message = (
                    "✨ You have already claimed this collection's "
                    "Legendary and Glimmer reward."
                )
            else:
                message = (
                    "⚠️ The Legendary reward is not configured correctly."
                )

            await interaction.response.send_message(
                embed=discord.Embed(
                    description=message,
                    color=EMBED_COLOR,
                ),
                ephemeral=True,
            )
            return

        balance = get_balance(interaction.user.id)
        collection_name = collection.get("name", collection_id)

        embed = discord.Embed(
            description=(
                "╭────────────── ✦ ──────────────╮\n"
                "                 **THE REWARD IS YOURS**\n"
                "╰────────────── ✦ ──────────────╯\n\n"
                f"**{collection_name}** · `{collection_id}`\n\n"
                "You have completed all six base cards.\n"
                "The Cabinet releases your Legendary reward.\n\n"
                f"✦ **Legendary:** {legendary['id']}\n"
                f"✦ **Glimmers received:** {GLIMMER_EMOTE} "
                f"**{GLIMMER_REWARD:,}**\n\n"
                f"Your balance: {GLIMMER_EMOTE} **{balance:,}**\n\n"
                "Your claim has been recorded. This reward "
                "cannot be claimed again."
            ),
            color=EMBED_COLOR,
        )

        if legendary.get("image"):
            embed.set_image(url=legendary["image"])

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Wild(bot))
