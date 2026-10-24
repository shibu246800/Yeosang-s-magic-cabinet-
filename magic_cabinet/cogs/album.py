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


# ── Album settings ─────────────────────────────────────

EMBED_COLOR = 0x4E0017
PAGE_SIZE = 8

ONGOING = "<:ongoing:1554879618199199804>"
UNCLAIMED = "<:rewardsu:1554880110811680798>"
CLAIMED = "<:cutepeach:1554880440534573108>"

VAULT_NAMES = {
    "BB": "VELVET MOON",
    "GG": "ROSEGLASS",
    "BG": "GOLDEN THREAD",
}

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "collections.json"

ALL_CARDS = NORMAL_CARDS + RARE_CARDS + EPIC_CARDS + LIMITED_CARDS


# ── Collection data ────────────────────────────────────

def load_collections():
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("collections", [])

    if not isinstance(data, list):
        return []

    return sorted(
        data,
        key=lambda item: (
            {"BB": 0, "GG": 1, "BG": 2}.get(
                str(item.get("vault", "")).upper(), 3
            ),
            str(item.get("id", "")),
        ),
    )


def get_collection_id(collection):
    return str(collection.get("id", collection.get("collection_id", "")))


def get_collection_name(collection):
    return str(collection.get("name", "Unnamed Collection"))


def get_collection_vault(collection):
    return str(collection.get("vault", "")).upper()


# ── Album database ─────────────────────────────────────

def ensure_album_table():
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


def get_player_progress(user_id):
    ensure_album_table()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT card_id
            FROM bag
            WHERE user_id = ? AND quantity > 0
            """,
            (user_id,),
        ).fetchall()

        claimed_rows = connection.execute(
            """
            SELECT collection_id
            FROM collection_rewards
            WHERE user_id = ? AND claimed = 1
            """,
            (user_id,),
        ).fetchall()

    owned_ids = {str(row[0]) for row in rows}
    claimed_collections = {str(row[0]) for row in claimed_rows}

    return owned_ids, claimed_collections


def get_progress(collection_id, owned_ids, claimed_collections):
    collection_cards = [
        card for card in ALL_CARDS
        if str(card.get("collection_id", "")) == collection_id
    ]

    owned_count = len({
        str(card.get("id"))
        for card in collection_cards
        if str(card.get("id")) in owned_ids
    })

    # Every collection has six base cards.
    owned_count = min(owned_count, 6)

    if collection_id in claimed_collections:
        return CLAIMED, 7, 7, "Completed · Reward Claimed"

    if owned_count >= 6:
        return UNCLAIMED, 6, 6, "Completed · Reward Unclaimed"

    return ONGOING, owned_count, 6, "Ongoing"


# ── Album embed ────────────────────────────────────────

def build_album_embed(user, page, collections):
    owned_ids, claimed_collections = get_player_progress(user.id)

    total_pages = max(1, (len(collections) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    page_collections = collections[start:start + PAGE_SIZE]

    embed = discord.Embed(
        title="📖 YOUR ALBUM",
        description=(
            "Your collections, gathered beneath\n"
            "the Cabinet's watchful pages.\n\n"
        ),
        color=EMBED_COLOR,
    )

    current_vault = None

    for collection in page_collections:
        collection_id = get_collection_id(collection)
        name = get_collection_name(collection)
        vault = get_collection_vault(collection)

        if vault != current_vault:
            current_vault = vault
            vault_name = VAULT_NAMES.get(vault, vault or "OTHER COLLECTIONS")
            embed.description += f"__**{vault_name}**__\n\n"

        emoji, count, maximum, status = get_progress(
            collection_id,
            owned_ids,
            claimed_collections,
        )

        embed.description += (
            f"{emoji} **{name}** · ID: `{collection_id}` · "
            f"{count}/{maximum} Cards\n"
        )

    if not page_collections:
        embed.description += "No collections were found in the collection data."

    embed.description += (
        "\n────────────────────────\n"
        f"{ONGOING} Ongoing\n"
        f"{UNCLAIMED} Completed · Reward Unclaimed\n"
        f"{CLAIMED} Completed · Reward Claimed\n"
        "\n╰─────── ⋆⋅☆⋅⋆ ───────╯"
    )

    embed.set_footer(text=f"Page {page + 1} / {total_pages}")
    return embed


# ── Search modal ──────────────────────────────────────

class AlbumSearchModal(discord.ui.Modal, title="Search Your Album"):
    collection_id = discord.ui.TextInput(
        label="Collection ID",
        placeholder="Example: BB_1",
        min_length=1,
        max_length=30,
        required=True,
    )

    def __init__(self, album_view):
        super().__init__()
        self.album_view = album_view

    async def on_submit(self, interaction: discord.Interaction):
        searched_id = self.collection_id.value.strip().upper()

        index = next(
            (
                i for i, collection in enumerate(self.album_view.collections)
                if get_collection_id(collection).upper() == searched_id
            ),
            None,
        )

        if index is None:
            await interaction.response.send_message(
                f"Collection `{searched_id}` was not found.",
                ephemeral=True,
            )
            return

        self.album_view.page = index // PAGE_SIZE
        await interaction.response.edit_message(
            embed=build_album_embed(
                interaction.user,
                self.album_view.page,
                self.album_view.collections,
            ),
            view=self.album_view,
        )


# ── Album buttons ─────────────────────────────────────

class AlbumView(discord.ui.View):
    def __init__(self, user_id, collections):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.collections = collections
        self.page = 0
        self.update_buttons()

    def update_buttons(self):
        total_pages = max(
            1,
            (len(self.collections) + PAGE_SIZE - 1) // PAGE_SIZE,
        )
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= total_pages - 1

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This album belongs to another player.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="‹ Previous",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=build_album_embed(
                interaction.user,
                self.page,
                self.collections,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Next ›",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=build_album_embed(
                interaction.user,
                self.page,
                self.collections,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Search",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def search_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_modal(AlbumSearchModal(self))


# ── /album command ─────────────────────────────────────

class Album(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="album",
        description="View your personal collection progress.",
    )
    async def album(self, interaction: discord.Interaction):
        collections = load_collections()

        if not collections:
            await interaction.response.send_message(
                "The Cabinet's collection data could not be found.",
                ephemeral=True,
            )
            return

        ensure_album_table()

        view = AlbumView(interaction.user.id, collections)

        await interaction.response.send_message(
            embed=build_album_embed(
                interaction.user,
                view.page,
                collections,
            ),
            view=view,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Album(bot))
