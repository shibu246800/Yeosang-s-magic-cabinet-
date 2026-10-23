"""Bag command."""
"""Magic Cabinet Bag."""

import math
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.cards.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.cards.rare import CARDS as RARE_CARDS
from magic_cabinet.data.cards.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.cards.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS


DATABASE = "cabinet.db"
EMBED_COLOR = "#4E0017"
EMBED_COLOR = discord.Color.from_str("#4E0017")

HEADER_URL = (
    "https://raw.githubusercontent.com/"
@@ -30,7 +30,8 @@
    "Untitled14_20261003173415.jpg"
)

CARDS_PER_PAGE = 10
CARDS_PER_PAGE = 12

ALL_CARDS = (
    NORMAL_CARDS
@@ -39,6 +40,7 @@
    + LIMITED_CARDS
)

RARITY_ORDER = {
    "★": 1,
    "★★": 2,
@@ -47,384 +49,351 @@
}


def get_card_vault(collection_id: str) -> str:
    """Return the vault for a collection."""
    if collection_id.startswith("BB"):
        return "BB"
    if collection_id.startswith("GG"):
        return "GG"
def build_header_embed() -> discord.Embed:
    """Build the Bag header embed."""

    if collection_id.startswith("BG"):
        return "BG"
    embed = discord.Embed(
        color=EMBED_COLOR,
    )

    return ""
    embed.set_image(
        url=HEADER_URL
    )

    return embed

def get_all_card_data() -> dict:
    """Return all non-Legendary card data."""
    return {
        card["id"]: {
            **card,
            "vault": get_card_vault(card["collection_id"]),
        }
        for card in ALL_CARDS
    }

def build_divider_embed() -> discord.Embed:
    """Build the Bag bottom divider embed."""

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
    embed = discord.Embed(
        color=EMBED_COLOR,
    )

    rows = cursor.fetchall()
    connection.close()
    cards = []
    embed.set_image(
        url=DIVIDER_URL
    )

    for card_id, quantity in rows:
        card = card_data.get(card_id)
    return embed

        if card is None:
            continue

        duplicate_count = quantity - 1
class BagView(discord.ui.View):
    """Interactive Bag controls."""

        cards.append(
            {
                **card,
                "quantity": quantity,
                "duplicates": duplicate_count,
            }
    def __init__(
        self,
        user_id: int,
        cards: list[dict],
        filter_name: str = "all",
    ):
        super().__init__(
            timeout=300
        )

    cards.sort(
        key=lambda card: (
            RARITY_ORDER.get(card["stars"], 99),
            card["id"],
        )
    )
        self.user_id = user_id
        self.cards = cards
        self.filter_name = filter_name
        self.page = 0

    return cards
        self.update_buttons()

    def update_buttons(self):
        """Update pagination buttons."""

def search_bag_cards(
    cards: list[dict],
    search_term: str,
) -> list[dict]:
    """Search by Card ID or Collection ID."""
    search_term = search_term.strip().upper()
        total_pages = max(
            1,
            (
                len(self.cards)
                + CARDS_PER_PAGE
                - 1
            )
            // CARDS_PER_PAGE,
        )

    if not search_term:
        return cards
        self.previous.disabled = (
            self.page <= 0
        )

    # Card ID
    if search_term.isdigit():
        card_id = int(search_term)
        self.next.disabled = (
            self.page >= total_pages - 1
        )

        return [
            card
            for card in cards
            if card["id"] == card_id
        ]
    def get_page_cards(self) -> list[dict]:
        """Return cards for the current page."""

    # Collection ID
    return [
        card
        for card in cards
        if card["collection_id"].upper() == search_term
    ]
        start = (
            self.page
            * CARDS_PER_PAGE
        )

        end = start + CARDS_PER_PAGE

def build_header_embed() -> discord.Embed:
    """Build the Bag header."""
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_image(url=HEADER_URL)
    return embed
        return self.cards[start:end]

    def build_content_embed(
        self,
        user: discord.User | discord.Member,
    ) -> discord.Embed:
        """Build the Bag content embed."""

def build_divider_embed() -> discord.Embed:
    """Build the Bag divider/footer."""
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_image(url=DIVIDER_URL)
    return embed
        page_cards = self.get_page_cards()

        lines = [
            f"**{user.mention}'s BAG**",
            "",
        ]

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
        current_rarity = None

    if not cards:
        embed.description = (
            "Your Bag is empty.\n\n"
            "Only duplicate copies appear here."
        )
        return embed
        for card in page_cards:

    start = page * CARDS_PER_PAGE
    end = start + CARDS_PER_PAGE
            rarity = card["stars"]

    page_cards = cards[start:end]
            if rarity != current_rarity:

    sections = {
        "★": [],
        "★★": [],
        "★★★": [],
        "★★★★": [],
    }
                if current_rarity is not None:
                    lines.append("")

    for card in page_cards:
        line = (
            f"`[{card['id']}]` "
            f"[View]({card['image']}) "
            f"{card['vault']} × **{card['duplicates']}**"
        )
                lines.append(
                    f"**{rarity}**"
                )

        sections[card["stars"]].append(line)
                current_rarity = rarity

    description_parts = []
            lines.append(
                f"`[{card['id']}]` "
                f"[View]({card['image']}) "
                f"{card['vault']} × "
                f"**{card['quantity']}**"
            )

    for stars in ("★", "★★", "★★★", "★★★★"):
        lines = sections[stars]
        if not page_cards:

        if not lines:
            continue
            lines.append(
                "✦ Your Bag is empty."
            )

        description_parts.append(
            f"{stars}\n"
            + "\n".join(lines)
        total_pages = max(
            1,
            (
                len(self.cards)
                + CARDS_PER_PAGE
                - 1
            )
            // CARDS_PER_PAGE,
        )

    embed.description = "\n\n".join(
        description_parts
    )
    embed.set_footer(
        text=f"Page {page + 1}/{total_pages}"
    )
    return embed
        lines.extend(
            [
                "",
                (
                    f"-# Page "
                    f"{self.page + 1}/"
                    f"{total_pages}"
                ),
            ]
        )

class BagView(discord.ui.View):
    """Main Bag controls."""
        return discord.Embed(
            description="\n".join(lines),
            color=EMBED_COLOR,
        )

    def __init__(
    async def refresh_message(
        self,
        user_id: int,
        cards: list[dict],
        interaction: discord.Interaction,
    ):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.cards = cards
        self.page = 0
        self.message = None
        """Refresh the complete Bag message."""

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
        await interaction.edit_original_response(
            embeds=[
                build_header_embed(),
                self.build_content_embed(
                    interaction.user
                ),
                build_divider_embed(),
            ],
            view=self,
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
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        self.message = interaction.message
            return

        if self.page > 0:
            self.page -= 1

        self.update_buttons()

        await interaction.response.edit_message(
            embeds=self.get_embeds(),
            embeds=[
                build_header_embed(),
                self.build_content_embed(
                    interaction.user
                ),
                build_divider_embed(),
            ],
            view=self,
        )

    @discord.ui.button(
        label="》",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def next_button(
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        self.message = interaction.message
        total_pages = max(
            1,
            (
                len(self.cards)
                + CARDS_PER_PAGE
                - 1
            )
            // CARDS_PER_PAGE,
        )

        if self.page < self.total_pages - 1:
        if self.page < total_pages - 1:
            self.page += 1

        self.update_buttons()

        await interaction.response.edit_message(
            embeds=self.get_embeds(),
            embeds=[
                build_header_embed(),
                self.build_content_embed(
                    interaction.user
                ),
                build_divider_embed(),
            ],
            view=self,
        )

    @discord.ui.button(
        label="Sort",
        style=discord.ButtonStyle.secondary,
        row=0,
        style=discord.ButtonStyle.danger,
    )
    async def sort_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        self.message = interaction.message
            return

        await interaction.response.send_message(
            "Choose a Bag filter.",
            view=SortView(self),
            embed=discord.Embed(
                description=(
                    "✦ Choose how you want "
                    "to sort your Bag."
                ),
                color=EMBED_COLOR,
            ),
            view=SortView(
                self,
                interaction.user.id,
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Search",
        style=discord.ButtonStyle.secondary,
        row=0,
        style=discord.ButtonStyle.danger,
    )
    async def search_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        self.message = interaction.message
            return

        await interaction.response.send_modal(
            BagSearchModal(self)
            BagSearchModal(
                self,
                interaction.user.id,
            )
        )


class SortSelect(discord.ui.Select):
    """Bag filter selector."""
    """Bag sorting selector."""

    def __init__(self, parent_view: BagView):
    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        self.parent_view = parent_view
        self.user_id = user_id

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
                description="Show Normal cards.",
            ),
            discord.SelectOption(
                label="Rare",
                value="rare",
                description="Show Rare duplicates.",
                description="Show Rare cards.",
            ),
            discord.SelectOption(
                label="Epic",
                value="epic",
                description="Show Epic duplicates.",
                description="Show Epic cards.",
            ),
            discord.SelectOption(
                label="Limited",
                value="limited",
                description="Show Limited duplicates.",
                description="Show Limited cards.",
            ),
            discord.SelectOption(
                label="3+ Duplicates",
                value="duplicates",
                description="Show cards with 3+ duplicates.",
                description=(
                    "Show cards you own "
                    "3 or more times."
                ),
            ),
        ]

@@ -437,98 +406,72 @@ async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.parent_view
        if interaction.user.id != self.user_id:

        if interaction.user.id != view.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        all_cards = get_bag_cards(
            view.user_id
        self.parent_view.cards = get_bag_cards(
            self.user_id,
            self.values[0],
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
        self.parent_view.page = 0

        else:
            filtered = all_cards
        self.parent_view.filter_name = (
            self.values[0]
        )

        view.cards = filtered
        view.page = 0
        view.update_buttons()
        self.parent_view.update_buttons()

        if view.message is not None:
            await view.message.edit(
                embeds=view.get_embeds(),
                view=view,
            )
        await interaction.response.send_message(
            "✦ Bag updated.",
            ephemeral=True,
        )

        await interaction.response.edit_message(
            content="Bag filter applied.",
            view=None,
        await self.parent_view.refresh_message(
            interaction
        )


class SortView(discord.ui.View):
    """Temporary Bag sorting menu."""

    def __init__(self, parent_view: BagView):
        super().__init__(timeout=60)
    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        super().__init__(
            timeout=60
        )

        self.add_item(
            SortSelect(parent_view)
            SortSelect(
                parent_view,
                user_id,
            )
        )


class BagSearchModal(discord.ui.Modal):
    """Bag search modal."""

    def __init__(self, parent_view: BagView):
    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        super().__init__(
            title="Search Bag"
        )

        self.parent_view = parent_view
        self.user_id = user_id

        self.search = discord.ui.TextInput(
            label="Card ID or Collection ID",
@@ -537,92 +480,220 @@ def __init__(self, parent_view: BagView):
            max_length=50,
        )

        self.add_item(self.search)
        self.add_item(
            self.search
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        view = self.parent_view
        query = self.search.value.strip()

        if interaction.user.id != view.user_id:
            await interaction.response.send_message(
                "This Bag belongs to someone else.",
                ephemeral=True,
        self.parent_view.cards = (
            search_bag_cards(
                self.user_id,
                query,
            )
            return
        )

        all_cards = get_bag_cards(
            view.user_id
        self.parent_view.page = 0
        self.parent_view.filter_name = (
            "search"
        )
        self.parent_view.update_buttons()
        await interaction.response.send_message(
            "✦ Bag updated.",
            ephemeral=True,
        )

        results = search_bag_cards(
            all_cards,
            str(self.search.value),
        await self.parent_view.refresh_message(
            interaction
        )

        view.cards = results
        view.page = 0
        view.update_buttons()

        await interaction.response.defer(
            ephemeral=True
def get_card_vault(
    collection_id: str,
) -> str:
    """Return the Vault code."""
    return collection_id.split(
        "_",
        1,
    )[0]
def get_bag_cards(
    user_id: int,
    filter_name: str = "all",
) -> list[dict]:
    """Return the player's Bag cards."""
    with sqlite3.connect(
        DATABASE
    ) as connection:
        rows = connection.execute(
            """
            SELECT card_id, quantity
            FROM bag
            WHERE user_id = ?
            AND quantity > 0
            """,
            (user_id,),
        ).fetchall()
    quantities = {
        int(card_id): int(quantity)
        for card_id, quantity in rows
    }
    cards = []
    for card in ALL_CARDS:
        card_id = int(
            card["id"]
        )

        if view.message is not None:
            await view.message.edit(
                embeds=view.get_embeds(),
                view=view,
            )
        if card_id not in quantities:
            continue

        await interaction.followup.send(
            "Bag search applied.",
            ephemeral=True,
        quantity = quantities[
            card_id
        ]
        if filter_name == "normal":
            if card["stars"] != "★":
                continue
        elif filter_name == "rare":
            if card["stars"] != "★★":
                continue
        elif filter_name == "epic":
            if card["stars"] != "★★★":
                continue
        elif filter_name == "limited":
            if card["stars"] != "★★★★":
                continue
        elif filter_name == "duplicates":
            if quantity < 3:
                continue
        cards.append(
            {
                "id": card_id,
                "collection_id": (
                    card["collection_id"]
                ),
                "stars": card["stars"],
                "vault": get_card_vault(
                    card["collection_id"]
                ),
                "quantity": quantity,
                "image": card["image"],
            }
        )
    cards.sort(
        key=lambda card: (
            RARITY_ORDER[
                card["stars"]
            ],
            card["id"],
        )
    )
    return cards
def search_bag_cards(
    user_id: int,
    query: str,
) -> list[dict]:
    """Search by Card ID or Collection ID."""
    query = query.upper()
    cards = get_bag_cards(
        user_id,
        "all",
    )
    if query.isdigit():
        card_id = int(query)
        return [
            card
            for card in cards
            if card["id"] == card_id
        ]
    return [
        card
        for card in cards
        if card["collection_id"].upper()
        == query
    ]


class Bag(commands.Cog):
    """Bag command."""
    """Magic Cabinet Bag command."""

    def __init__(self, bot: commands.Bot):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="bag",
        description="View your duplicate card inventory.",
        description=(
            "View your duplicate card inventory."
        ),
    )
    async def bag(
        self,
        interaction: discord.Interaction,
    ):
        user_id = interaction.user.id
        """Show the player's Bag."""

        cards = get_bag_cards(
            user_id
            interaction.user.id
        )

        view = BagView(
            user_id=user_id,
            cards=cards,
            interaction.user.id,
            cards,
        )

        await interaction.response.send_message(
            embeds=[
                build_header_embed(),
                build_bag_embed(
                    cards,
                    view.page,
                    view.total_pages,
                view.build_content_embed(
                    interaction.user
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
async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Bag(bot)
    )
