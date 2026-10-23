
"""Magic Cabinet Bag."""

import math
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS


DATABASE = "cabinet.db"
EMBED_COLOR = discord.Color.from_str("#4E0017")
CARDS_PER_PAGE = 12

# Keep these URLs pointed at your existing GitHub image files.
HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "main/magic_cabinet/cogs/profile/"
    "Untitled13_20261003171807.jpg"
)
DIVIDER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "main/magic_cabinet/cogs/profile/"
    "Untitled14_20261003173415.jpg"
)

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

FILTERS = {
    "all": "All Duplicates",
    "normal": "Normal",
    "rare": "Rare",
    "epic": "Epic",
    "limited": "Limited",
    "duplicates": "3+ Duplicates",
}


def get_card_vault(collection_id: str) -> str:
    """Return the vault code for a collection."""
    collection_id = collection_id.upper()

    for vault in ("BB", "GG", "BG"):
        if collection_id.startswith(vault):
            return vault

    return collection_id.split("_", 1)[0]


def get_all_card_data() -> dict[int, dict]:
    """Return card data indexed by Card ID."""
    return {
        int(card["id"]): {
            **card,
            "id": int(card["id"]),
            "vault": get_card_vault(card["collection_id"]),
        }
        for card in ALL_CARDS
    }


def build_header_embed() -> discord.Embed:
    """Build the Bag header embed."""
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_image(url=HEADER_URL)
    return embed


def build_divider_embed() -> discord.Embed:
    """Build the Bag divider embed."""
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_image(url=DIVIDER_URL)
    return embed


def get_bag_cards(
    user_id: int,
    filter_name: str = "all",
) -> list[dict]:
    """
    Return duplicate cards only.

    The first copy stays in the collection.
    Only copies after the first appear in the Bag.
    """
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT card_id, quantity
            FROM bag
            WHERE user_id = ?
              AND quantity > 1
            """,
            (user_id,),
        ).fetchall()

    quantities = {
        int(card_id): int(quantity)
        for card_id, quantity in rows
    }
    card_data = get_all_card_data()
    cards = []

    for card_id, quantity in quantities.items():
        card = card_data.get(card_id)

        if card is None:
            continue

        duplicates = quantity - 1
        stars = card["stars"]

        if filter_name == "normal" and stars != "★":
            continue
        if filter_name == "rare" and stars != "★★":
            continue
        if filter_name == "epic" and stars != "★★★":
            continue
        if filter_name == "limited" and stars != "★★★★":
            continue
        if filter_name == "duplicates" and duplicates < 3:
            continue

        cards.append(
            {
                **card,
                "quantity": quantity,
                "duplicates": duplicates,
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
    user_id: int,
    query: str,
) -> list[dict]:
    """Search duplicate cards by Card ID or Collection ID."""
    query = query.strip().upper()

    cards = get_bag_cards(user_id)

    if not query:
        return cards

    if query.isdigit():
        card_id = int(query)
        return [
            card for card in cards
            if card["id"] == card_id
        ]

    return [
        card for card in cards
        if card["collection_id"].upper() == query
    ]


class BagView(discord.ui.View):
    """Interactive Bag controls."""

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
        self.filter_name = "all"

        self.update_buttons()

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(len(self.cards) / CARDS_PER_PAGE))

    def update_buttons(self) -> None:
        """Update pagination button states."""
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.total_pages - 1

    def get_page_cards(self) -> list[dict]:
        """Return cards for the current page."""
        start = self.page * CARDS_PER_PAGE
        return self.cards[start:start + CARDS_PER_PAGE]

    def build_content_embed(
        self,
        user: discord.User | discord.Member,
    ) -> discord.Embed:
        """Build the Bag contents embed."""
        lines = [
            f"**{user.mention}'s BAG**",
            "",
        ]

        page_cards = self.get_page_cards()
        current_rarity = None

        if not page_cards:
            lines.append("✦ Your Bag is empty.")
            lines.append("")
            lines.append("Only duplicate copies appear here.")
        else:
            for card in page_cards:
                rarity = card["stars"]

                if rarity != current_rarity:
                    if current_rarity is not None:
                        lines.append("")

                    lines.append(f"**{rarity}**")
                    current_rarity = rarity

                lines.append(
                    f"`[{card['id']}]` "
                    f"[View]({card['image']}) "
                    f"{card['vault']} × "
                    f"**{card['duplicates']}**"
                )

        lines.extend(
            [
                "",
                f"-# Page {self.page + 1}/{self.total_pages}",
            ]
        )

        return discord.Embed(
            description="\n".join(lines),
            color=EMBED_COLOR,
        )

    def get_embeds(
        self,
        user: discord.User | discord.Member,
    ) -> list[discord.Embed]:
        return [
            build_header_embed(),
            self.build_content_embed(user),
            build_divider_embed(),
        ]

    async def refresh_message(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Refresh the original Bag message."""
        self.update_buttons()

        if self.message is not None:
            await self.message.edit(
                embeds=self.get_embeds(interaction.user),
                view=self,
            )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """Prevent other users from controlling this Bag."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="《",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(
            embeds=self.get_embeds(interaction.user),
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
    ) -> None:
        if self.page < self.total_pages - 1:
            self.page += 1

        await interaction.response.edit_message(
            embeds=self.get_embeds(interaction.user),
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
    ) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ Choose how you want to sort your Bag.",
                color=EMBED_COLOR,
            ),
            view=SortView(self, self.user_id),
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
    ) -> None:
        await interaction.response.send_modal(
            BagSearchModal(self, self.user_id)
        )


class SortSelect(discord.ui.Select):
    """Bag sorting selector."""

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
                description="Show cards with at least 3 extra copies.",
            ),
        ]

        super().__init__(
            placeholder="Choose a Bag filter",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        selected = self.values[0]
        view = self.parent_view

        view.filter_name = selected
        view.cards = get_bag_cards(self.user_id, selected)
        view.page = 0
        view.update_buttons()

        if view.message is not None:
            await view.message.edit(
                embeds=view.get_embeds(interaction.user),
                view=view,
            )

        await interaction.response.edit_message(
            content="✦ Bag filter applied.",
            embed=None,
            view=None,
        )


class SortView(discord.ui.View):
    """Temporary Bag sorting menu."""

    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        super().__init__(timeout=60)
        self.add_item(SortSelect(parent_view, user_id))


class BagSearchModal(discord.ui.Modal):
    """Bag search modal."""

    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        super().__init__(title="Search Bag")

        self.parent_view = parent_view
        self.user_id = user_id

        self.search = discord.ui.TextInput(
            label="Card ID or Collection ID",
            placeholder="Enter a Card ID or Collection ID",
            required=True,
            max_length=50,
        )

        self.add_item(self.search)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        view = self.parent_view
        view.cards = search_bag_cards(
            self.user_id,
            self.search.value,
        )
        view.page = 0
        view.filter_name = "search"
        view.update_buttons()

        if view.message is not None:
            await view.message.edit(
                embeds=view.get_embeds(interaction.user),
                view=view,
            )

        await interaction.response.send_message(
            "✦ Bag search applied.",
            ephemeral=True,
        )


class Bag(commands.Cog):
    """Magic Cabinet Bag command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="bag",
        description="View your duplicate card inventory.",
    )
    async def bag(
        self,
        interaction: discord.Interaction,
    ) -> None:
        user_id = interaction.user.id
        cards = get_bag_cards(user_id)

        view = BagView(
            user_id=user_id,
            cards=cards,
        )

        await interaction.response.send_message(
            embeds=view.get_embeds(interaction.user),
            view=view,
        )

        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bag(bot))
