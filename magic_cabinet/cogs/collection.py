"""Magic Cabinet collection browser."""

from __future__ import annotations

import math
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


DATABASE = "cabinet.db"
EMBED_COLOR = discord.Color.from_str("#4E0017")

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005205021.jpg"
)

ROYAL_COURT_COVER = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)

ROYAL_COURT_BOARD = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_images/"
    "file_00000000081482119ec7774250ae06af.png"
)

VAULT_NAMES = {
    "BB": "🌙 Velvet Moon",
    "GG": "🌹 Roseglass",
    "BG": "🪡 Golden Thread",
}

FANCY_NAMES = {
    "Royal Court": "𝑹𝒐𝒚𝒂𝒍 𝑪𝒐𝒖𝒓𝒕",
}

COLLECTIONS = [
    {
        "id": "BB_1",
        "name": "Royal Court",
        "vault": "BB",
        "series": "Velvet Moon",
        "cover": ROYAL_COURT_COVER,
        "board": ROYAL_COURT_BOARD,
        "total_cards": 7,
    },
]


def fancy_name(name: str) -> str:
    return FANCY_NAMES.get(name, name)


def get_collected_ids(user_id: int) -> set[int]:
    """Return card IDs owned by a user."""
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """
            )

            tables = {row[0] for row in cursor.fetchall()}

            if "inventory" not in tables:
                return set()

            cursor.execute(
                """
                SELECT card_id
                FROM inventory
                WHERE user_id = ?
                """,
                (user_id,),
            )

            return {int(row[0]) for row in cursor.fetchall()}

    except (sqlite3.Error, ValueError, TypeError):
        return set()


class CollectionView(discord.ui.View):
    def __init__(
        self,
        cog: "Collection",
        user: discord.User | discord.Member,
        vault: str = "ALL",
        page: int = 0,
    ):
        super().__init__(timeout=180)

        self.cog = cog
        self.user = user
        self.vault = vault
        self.page = page

        self._build_buttons()

    def _build_buttons(self) -> None:
        self.clear_items()

        # Vault filters
        for vault_code, label in (
            ("ALL", "✦ All"),
            ("BB", "🌙 BB"),
            ("GG", "🌹 GG"),
            ("BG", "🪡 BG"),
        ):
            button = discord.ui.Button(
                label=label,
                style=(
                    discord.ButtonStyle.danger
                    if self.vault == vault_code
                    else discord.ButtonStyle.secondary
                ),
                row=0,
            )

            button.callback = self._vault_callback(vault_code)
            self.add_item(button)

        # Search
        search = discord.ui.Button(
            label="Search Collection",
            emoji="🔎",
            style=discord.ButtonStyle.secondary,
            row=1,
        )

        search.callback = self.search_callback
        self.add_item(search)

        # One View button for each visible collection.
        collections = self.cog.filtered_collections(self.vault)

        start = self.page * 3
        visible = collections[start:start + 3]

        for index, collection in enumerate(visible):
            button = discord.ui.Button(
                label=f"View {fancy_name(collection['name'])}",
                emoji="📖",
                style=discord.ButtonStyle.danger,
                row=2,
            )

            button.callback = self._collection_callback(collection)
            self.add_item(button)

        # Pagination
        max_page = max(0, math.ceil(len(collections) / 3) - 1)

        previous = discord.ui.Button(
            label="《",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0,
            row=3,
        )

        previous.callback = self.previous_callback
        self.add_item(previous)

        indicator = discord.ui.Button(
            label=f"{self.page + 1} / {max_page + 1}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=3,
        )

        self.add_item(indicator)

        next_button = discord.ui.Button(
            label="》",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= max_page,
            row=3,
        )

        next_button.callback = self.next_callback
        self.add_item(next_button)

    def _vault_callback(self, vault_code: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message(
                    "This collection menu belongs to someone else.",
                    ephemeral=True,
                )
                return

            self.vault = vault_code
            self.page = 0
            self._build_buttons()

            await self.cog.refresh_browser(interaction, self)

        return callback

    def _collection_callback(self, collection: dict):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message(
                    "This collection menu belongs to someone else.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                embeds=self.cog.build_inside_collection(
                    collection,
                    interaction.user,
                ),
                ephemeral=True,
            )

        return callback

    async def search_callback(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This collection menu belongs to someone else.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            CollectionSearchModal(
                self.cog,
                self,
            )
        )

    async def previous_callback(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This collection menu belongs to someone else.",
                ephemeral=True,
            )
            return

        self.page -= 1
        self._build_buttons()

        await self.cog.refresh_browser(
            interaction,
            self,
        )

    async def next_callback(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This collection menu belongs to someone else.",
                ephemeral=True,
            )
            return

        self.page += 1
        self._build_buttons()

        await self.cog.refresh_browser(
            interaction,
            self,
        )


class CollectionSearchModal(
    discord.ui.Modal,
    title="Search Collection",
):
    search = discord.ui.TextInput(
        label="Collection ID or name",
        placeholder="Example: BB_1 or Royal Court",
        required=True,
        max_length=100,
    )

    def __init__(
        self,
        cog: "Collection",
        view: CollectionView,
    ):
        super().__init__()

        self.cog = cog
        self.collection_view = view

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        query = self.search.value.strip().lower()

        matches = [
            collection
            for collection in self.cog.filtered_collections(
                self.collection_view.vault
            )
            if (
                query in collection["id"].lower()
                or query in collection["name"].lower()
            )
        ]

        if not matches:
            await interaction.response.send_message(
                "No collection found.",
                ephemeral=True,
            )
            return

        collection = matches[0]

        await interaction.response.send_message(
            embeds=self.cog.build_inside_collection(
                collection,
                interaction.user,
            ),
            ephemeral=True,
        )


class Collection(commands.Cog):
    """Collection browser."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @staticmethod
    def filtered_collections(
        vault: str,
    ) -> list[dict]:
        if vault == "ALL":
            return COLLECTIONS

        return [
            collection
            for collection in COLLECTIONS
            if collection["vault"] == vault
        ]

    def build_browser_embed(
        self,
        user: discord.User | discord.Member,
        view: CollectionView,
    ) -> discord.Embed:
        collections = self.filtered_collections(view.vault)

        start = view.page * 3
        visible = collections[start:start + 3]

        embed = discord.Embed(
            color=EMBED_COLOR,
            title="𝑪𝒐𝒍𝒍𝒆𝒄𝒕𝒊𝒐𝒏𝒔",
        )

        if not visible:
            embed.description = "No collections are available yet."
            return embed

        # Discord embeds can display one large collection image.
        # The View buttons below correspond to the visible collections.
        collection = visible[0]

        embed.set_image(url=collection["cover"])

        embed.description = (
            f"**{fancy_name(collection['name'])}**\n"
            f"`{collection['id']}` • "
            f"{VAULT_NAMES[collection['vault']]}"
        )

        if len(visible) > 1:
            for collection in visible[1:]:
                embed.add_field(
                    name=fancy_name(collection["name"]),
                    value=(
                        f"`{collection['id']}` • "
                        f"{VAULT_NAMES[collection['vault']]}"
                    ),
                    inline=False,
                )

        embed.set_footer(
            text="Select a collection to open its card board."
        )

        return embed

    def build_inside_collection(
        self,
        collection: dict,
        user: discord.User | discord.Member,
    ) -> list[discord.Embed]:
        collected_ids = get_collected_ids(user.id)

        owned = sum(
            1
            for card_id in range(
                1,
                collection["total_cards"] + 1,
            )
            if card_id in collected_ids
        )

        header = discord.Embed(
            color=EMBED_COLOR,
        )

        header.set_image(url=HEADER_URL)

        embed = discord.Embed(
            color=EMBED_COLOR,
            title=fancy_name(collection["name"]),
            description=(
                f"**Collection ID:** `{collection['id']}`\n"
                f"**Vault:** {VAULT_NAMES[collection['vault']]}\n"
                f"**Progress:** {owned}/{collection['total_cards']}"
            ),
        )

        embed.set_image(url=collection["board"])

        embed.set_footer(
            text=f"{collection['id']} • {collection['name']}"
        )

        return [
            header,
            embed,
        ]

    async def send_browser(
        self,
        interaction: discord.Interaction,
        view: CollectionView,
    ):
        header = discord.Embed(
            color=EMBED_COLOR,
        )

        header.set_image(url=HEADER_URL)

        content = self.build_browser_embed(
            interaction.user,
            view,
        )

        await interaction.response.send_message(
            embeds=[
                header,
                content,
            ],
            view=view,
        )

    async def refresh_browser(
        self,
        interaction: discord.Interaction,
        view: CollectionView,
    ):
        header = discord.Embed(
            color=EMBED_COLOR,
        )

        header.set_image(url=HEADER_URL)

        content = self.build_browser_embed(
            interaction.user,
            view,
        )

        await interaction.response.edit_message(
            embeds=[
                header,
                content,
            ],
            view=view,
        )

    @app_commands.command(
        name="collection",
        description="Browse the Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        view = CollectionView(
            self,
            interaction.user,
        )

        await self.send_browser(
            interaction,
            view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Collection(bot)
            )
