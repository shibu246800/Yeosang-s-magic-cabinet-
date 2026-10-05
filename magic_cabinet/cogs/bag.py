"""Bag command."""

import math
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.cards.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.cards.rare import CARDS as RARE_CARDS
from magic_cabinet.data.cards.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.cards.limited import CARDS as LIMITED_CARDS


DATABASE = "cabinet.db"
EMBED_COLOR = "#4E0017"

HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13.jpg"
)

DIVIDER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)

CARDS_PER_PAGE = 10

ALL_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
)

RARITY_ORDER = {
    "★": 1,
    "★★": 2,
    "★★★": 3,
    "★★★★": 4,
}


def get_card_vault(collection_id: str) -> str:
    """Return the vault for a collection."""
    if collection_id.startswith("BB"):
        return "BB"

    if collection_id.startswith("GG"):
        return "GG"

    if collection_id.startswith("BG"):
        return "BG"

    return ""


def get_all_card_data() -> dict:
    """Return all non-Legendary card data."""
    return {
        card["id"]: {
            **card,
            "vault": get_card_vault(card["collection_id"]),
        }
        for card in ALL_CARDS
    }


def get_bag_cards(user_id: int) -> list[dict]:
    """
    Get cards that have duplicates.

    The first copy belongs to the Collection.
    Every copy after the first is a duplicate.

    Example:
    quantity 1 -> 0 duplicates -> not shown
    quantity 2 -> 1 duplicate
    quantity 3 -> 2 duplicates
    quantity 4 -> 3 duplicates
    """
    card_data = get_all_card_data()

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT card_id, quantity
        FROM bag
        WHERE user_id = ?
          AND quantity > 1
        """,
        (user_id,),
    )

    rows = cursor.fetchall()
    connection.close()

    cards = []

    for card_id, quantity in rows:
        card = card_data.get(card_id)

        if card is None:
            continue

        duplicate_count = quantity - 1

        cards.append(
            {
                **card,
                "quantity": quantity,
                "duplicates": duplicate_count,
            }
        )

    cards.sort(
        key=lambda card: (
            RARITY_ORDER.get(card["stars"], 99),
            card["id"],
        )
    )

    return cards


def search_bag_cards(
    cards: list[dict],
    search_term: str,
) -> list[dict]:
    """Search by Card ID or Collection ID."""
    search_term = search_term.strip().upper()

    if not search_term:
        return cards

    # Card ID
    if search_term.isdigit():
        card_id = int(search_term)

        return [
            card
            for card in cards
            if card["id"] == card_id
        ]

    # Collection ID
    return [
        card
        for card in cards
        if card["collection_id"].upper() == search_term
    ]


def build_header_embed() -> discord.Embed:
    """Build the Bag header."""
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_image(url=HEADER_URL)
    return embed


def build_divider_embed() -> discord.Embed:
    """Build the Bag divider/footer."""
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_image(url=DIVIDER_URL)
    return embed


def build_bag_embed(
    cards: list[dict],
    page: int,
    total_pages: int,
) -> discord.Embed:
    """Build the Bag content."""
    embed = discord.Embed(
        title="Bag",
        color=EMBED_COLOR,
    )

    if not cards:
        embed.description = (
            "Your Bag is empty.\n\n"
            "Only duplicate copies appear here."
        )
        return embed

    start = page * CARDS_PER_PAGE
    end = start + CARDS_PER_PAGE

    page_cards = cards[start:end]

    sections = {
        "★": [],
        "★★": [],
        "★★★": [],
        "★★★★": [],
    }

    for card in page_cards:
        line = (
            f"`[{card['id']}]` "
            f"[View]({card['image']}) "
            f"{card['vault']} × **{card['duplicates']}**"
        )

        sections[card["stars"]].append(line)

    description_parts = []

    for stars in ("★", "★★", "★★★", "★★★★"):
        lines = sections[stars]

        if not lines:
            continue

        description_parts.append(
            f"{stars}\n"
            + "\n".join(lines)
        )

    embed.description = "\n\n".join(
        description_parts
    )

    embed.set_footer(
        text=f"Page {page + 1}/{total_pages}"
    )

    return embed


class BagView(discord.ui.View):
    """Main Bag controls."""

    def __init__(
        self,
        user_id: int,
        cards: list[dict],
    ):
        super().__init__(timeout=180)

        self.user_id = user_id
        self.cards = cards
        self.page = 0
        self.message = None

        self.update_buttons()

    @property
    def total_pages(self) -> int:
        return max(
            1,
            math.ceil(
                len(self.cards) / CARDS_PER_PAGE
            ),
        )

    def update_buttons(self) -> None:
        self.previous_button.disabled = (
            self.page <= 0
        )

        self.next_button.disabled = (
            self.page >= self.total_pages - 1
        )

    def get_embeds(self) -> list[discord.Embed]:
        return [
            build_header_embed(),
            build_bag_embed(
                self.cards,
                self.page,
                self.total_pages,
            ),
            build_divider_embed(),
        ]

    @discord.ui.button(
        label="《",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
            )
            return

        self.message = interaction.message

        if self.page > 0:
            self.page -= 1

        self.update_buttons()

        await interaction.response.edit_message(
            embeds=self.get_embeds(),
            view=self,
        )

    @discord.ui.button(
        label="》",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
            )
            return

        self.message = interaction.message

        if self.page < self.total_pages - 1:
            self.page += 1

        self.update_buttons()

        await interaction.response.edit_message(
            embeds=self.get_embeds(),
            view=self,
        )

    @discord.ui.button(
        label="Sort",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def sort_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
            )
            return

        self.message = interaction.message

        await interaction.response.send_message(
            "Choose a Bag filter.",
            view=SortView(self),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Search",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def search_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
            )
            return

        self.message = interaction.message

        await interaction.response.send_modal(
            BagSearchModal(self)
        )


class SortSelect(discord.ui.Select):
    """Bag filter selector."""

    def __init__(self, parent_view: BagView):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(
                label="All Duplicates",
                value="all",
                description="Show all duplicate cards.",
            ),
            discord.SelectOption(
                label="Normal",
                value="normal",
                description="Show Normal duplicates.",
            ),
            discord.SelectOption(
                label="Rare",
                value="rare",
                description="Show Rare duplicates.",
            ),
            discord.SelectOption(
                label="Epic",
                value="epic",
                description="Show Epic duplicates.",
            ),
            discord.SelectOption(
                label="Limited",
                value="limited",
                description="Show Limited duplicates.",
            ),
            discord.SelectOption(
                label="3+ Duplicates",
                value="duplicates",
                description="Show cards with 3+ duplicates.",
            ),
        ]

        super().__init__(
            placeholder="Choose a filter...",
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.parent_view

        if interaction.user.id != view.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
            )
            return

        all_cards = get_bag_cards(
            view.user_id
        )

        selected = self.values[0]

        if selected == "all":
            filtered = all_cards

        elif selected == "normal":
            filtered = [
                card
                for card in all_cards
                if card["stars"] == "★"
            ]

        elif selected == "rare":
            filtered = [
                card
                for card in all_cards
                if card["stars"] == "★★"
            ]

        elif selected == "epic":
            filtered = [
                card
                for card in all_cards
                if card["stars"] == "★★★"
            ]

        elif selected == "limited":
            filtered = [
                card
                for card in all_cards
                if card["stars"] == "★★★★"
            ]

        elif selected == "duplicates":
            filtered = [
                card
                for card in all_cards
                if card["duplicates"] >= 3
            ]

        else:
            filtered = all_cards

        view.cards = filtered
        view.page = 0
        view.update_buttons()

        if view.message is not None:
            await view.message.edit(
                embeds=view.get_embeds(),
                view=view,
            )

        await interaction.response.edit_message(
            content="Bag filter applied.",
            view=None,
        )


class SortView(discord.ui.View):
    """Temporary Bag sorting menu."""

    def __init__(self, parent_view: BagView):
        super().__init__(timeout=60)

        self.add_item(
            SortSelect(parent_view)
        )


class BagSearchModal(discord.ui.Modal):
    """Bag search modal."""

    def __init__(self, parent_view: BagView):
        super().__init__(
            title="Search Bag"
        )

        self.parent_view = parent_view

        self.search = discord.ui.TextInput(
            label="Card ID or Collection ID",
            placeholder="Example: 42 or BB_1",
            required=True,
            max_length=50,
        )

        self.add_item(self.search)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        view = self.parent_view

        if interaction.user.id != view.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
            )
            return

        all_cards = get_bag_cards(
            view.user_id
        )

        results = search_bag_cards(
            all_cards,
            str(self.search.value),
        )

        view.cards = results
        view.page = 0
        view.update_buttons()

        await interaction.response.defer(
            ephemeral=True
        )

        if view.message is not None:
            await view.message.edit(
                embeds=view.get_embeds(),
                view=view,
            )

        await interaction.followup.send(
            "Bag search applied.",
            ephemeral=True,
        )


class Bag(commands.Cog):
    """Bag command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="bag",
        description="View your duplicate card inventory.",
    )
    async def bag(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id

        cards = get_bag_cards(
            user_id
        )

        view = BagView(
            user_id=user_id,
            cards=cards,
        )

        await interaction.response.send_message(
            embeds=[
                build_header_embed(),
                build_bag_embed(
                    cards,
                    view.page,
                    view.total_pages,
                ),
                build_divider_embed(),
            ],
            view=view,
        )

        view.message = (
            await interaction.original_response()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Bag(bot))
