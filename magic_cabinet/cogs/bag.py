"""Magic Cabinet Bag."""

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


class BagView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        cards: list[dict],
        filter_name: str = "all",
    ):
        super().__init__(timeout=300)

        self.user_id = user_id
        self.cards = cards
        self.filter_name = filter_name
        self.page = 0

        self.previous.disabled = True

        self.update_buttons()

    def update_buttons(self):
        total_pages = max(
            1,
            (len(self.cards) + CARDS_PER_PAGE - 1)
            // CARDS_PER_PAGE,
        )

        self.previous.disabled = self.page <= 0
        self.next.disabled = self.page >= total_pages - 1

    def get_page_cards(self) -> list[dict]:
        start = self.page * CARDS_PER_PAGE
        end = start + CARDS_PER_PAGE

        return self.cards[start:end]

    def build_embed(
        self,
        user: discord.User | discord.Member,
    ) -> discord.Embed:
        page_cards = self.get_page_cards()

        lines = [
            f"**{user.mention}'s BAG**",
            "",
        ]

        current_rarity = None

        for card in page_cards:
            rarity = card["stars"]

            if rarity != current_rarity:
                if current_rarity is not None:
                    lines.append("")

                lines.append(
                    f"**{rarity}**"
                )

                current_rarity = rarity

            lines.append(
                f"`[{card['id']}]` (png) "
                f"{card['vault']} × **{card['quantity']}**"
            )

        if not page_cards:
            lines.extend(
                [
                    "✦ Your Bag is empty.",
                ]
            )

        total_pages = max(
            1,
            (len(self.cards) + CARDS_PER_PAGE - 1)
            // CARDS_PER_PAGE,
        )

        lines.extend(
            [
                "",
                f"-# Page {self.page + 1}/{total_pages}",
            ]
        )

        return discord.Embed(
            description="\n".join(lines),
            color=EMBED_COLOR,
        )

    @discord.ui.button(
        label="《",
        style=discord.ButtonStyle.secondary,
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        if self.page > 0:
            self.page -= 1

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.build_embed(
                interaction.user
            ),
            view=self,
        )

    @discord.ui.button(
        label="》",
        style=discord.ButtonStyle.secondary,
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        total_pages = max(
            1,
            (len(self.cards) + CARDS_PER_PAGE - 1)
            // CARDS_PER_PAGE,
        )

        if self.page < total_pages - 1:
            self.page += 1

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.build_embed(
                interaction.user
            ),
            view=self,
        )

    @discord.ui.button(
        label="Sort",
        style=discord.ButtonStyle.danger,
    )
    async def sort_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                description="✦ Choose how you want to sort your Bag.",
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
        style=discord.ButtonStyle.danger,
    )
    async def search_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            BagSearchModal(
                self,
                interaction.user.id,
            )
        )


class SortSelect(discord.ui.Select):
    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        self.parent_view = parent_view
        self.user_id = user_id

        options = [
            discord.SelectOption(
                label="Normal",
                value="normal",
                description="Show Normal cards.",
            ),
            discord.SelectOption(
                label="Rare",
                value="rare",
                description="Show Rare cards.",
            ),
            discord.SelectOption(
                label="Epic",
                value="epic",
                description="Show Epic cards.",
            ),
            discord.SelectOption(
                label="Limited",
                value="limited",
                description="Show Limited cards.",
            ),
            discord.SelectOption(
                label="3+ Duplicates",
                value="duplicates",
                description="Show cards you own 3 or more times.",
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
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "✦ This Bag belongs to another player.",
                ephemeral=True,
            )
            return

        filtered = get_bag_cards(
            self.user_id,
            self.values[0],
        )

        self.parent_view.cards = filtered
        self.parent_view.page = 0
        self.parent_view.filter_name = self.values[0]
        self.parent_view.update_buttons()

        await interaction.response.edit_message(
            embed=self.parent_view.build_embed(
                interaction.user
            ),
            view=self.parent_view,
        )


class SortView(discord.ui.View):
    def __init__(
        self,
        parent_view: BagView,
        user_id: int,
    ):
        super().__init__(timeout=60)

        self.add_item(
            SortSelect(
                parent_view,
                user_id,
            )
        )


class BagSearchModal(discord.ui.Modal):
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
            placeholder="Example: 42 or BB_1",
            required=True,
            max_length=50,
        )

        self.add_item(self.search)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        query = self.search.value.strip()

        cards = search_bag_cards(
            self.user_id,
            query,
        )

        self.parent_view.cards = cards
        self.parent_view.page = 0
        self.parent_view.filter_name = "search"
        self.parent_view.update_buttons()

        await interaction.response.edit_message(
            embed=self.parent_view.build_embed(
                interaction.user
            ),
            view=self.parent_view,
        )


def get_card_vault(
    collection_id: str,
) -> str:
    return collection_id.split(
        "_",
        1,
    )[0]


def get_bag_cards(
    user_id: int,
    filter_name: str = "all",
) -> list[dict]:
    with sqlite3.connect(DATABASE) as connection:
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
        card_id = int(card["id"])

        if card_id not in quantities:
            continue

        quantity = quantities[card_id]

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
                "collection_id": card["collection_id"],
                "stars": card["stars"],
                "vault": get_card_vault(
                    card["collection_id"]
                ),
                "quantity": quantity,
            }
        )

    cards.sort(
        key=lambda card: (
            RARITY_ORDER[card["stars"]],
            card["id"],
        )
    )

    return cards


def search_bag_cards(
    user_id: int,
    query: str,
) -> list[dict]:
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
        if card["collection_id"].upper() == query
    ]


class Bag(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="bag",
        description="View your duplicate card inventory.",
    )
    async def bag(
        self,
        interaction: discord.Interaction,
    ):
        cards = get_bag_cards(
            interaction.user.id
        )

        view = BagView(
            interaction.user.id,
            cards,
        )

        await interaction.response.send_message(
            embed=view.build_embed(
                interaction.user
            ),
            view=view,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Bag(bot)
      )
