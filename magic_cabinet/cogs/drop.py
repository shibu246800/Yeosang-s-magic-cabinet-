"""Drop command."""

import asyncio
import random
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.card_display import create_card_strip
from magic_cabinet.data.collections import COLLECTIONS
from magic_cabinet.data.drop_rates import DROP_RATES
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS


DATABASE = "cabinet.db"

DROP_CARD_COUNT = 3
DROP_DURATION = 20

OWNER_EMOTE = "<:owner_bag:1552939106731032646>"

CABINET_COLOR = discord.Color.from_str("#4E0017")


RARITY_CARDS = {
    "★": NORMAL_CARDS,
    "★★": RARE_CARDS,
    "★★★": EPIC_CARDS,
    "★★★★": LIMITED_CARDS,
}


RARITY_EMOTES = {
    "★": "<:silver_normal:1552761791606689933>",
    "★★": "<:sapphire_rare:1552761835587899513>",
    "★★★": "<:eclipse_epic:1552761873076850758>",
    "★★★★": "<:bloodrose_limited:1552761891472810144>",
    "★★★★★": "<:golden_legendary:1552761908652671056>",
}


VAULT_SERIES = {
    "BB": "Velvet Moon",
    "GG": "Roseglass",
    "BG": "Golden Thread",
}


def initialize_bag_database():
    """Create the Bag table if it does not exist."""

    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bag (
                user_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, card_id)
            )
            """
        )

        connection.commit()


def choose_rarity() -> str:
    """Choose a rarity using configured probabilities."""

    rarities = list(DROP_RATES.keys())
    weights = list(DROP_RATES.values())

    return random.choices(
        rarities,
        weights=weights,
        k=1,
    )[0]


def choose_drop_cards() -> list[dict]:
    """Choose three different cards."""

    all_cards = [
        card
        for cards in RARITY_CARDS.values()
        for card in cards
    ]

    if len(all_cards) < DROP_CARD_COUNT:
        raise RuntimeError(
            "There are not enough cards for this drop."
        )

    selected_cards = []
    available_cards = all_cards.copy()

    for _ in range(DROP_CARD_COUNT):
        selected_rarity = choose_rarity()

        rarity_cards = [
            card
            for card in available_cards
            if card["stars"] == selected_rarity
        ]

        if rarity_cards:
            selected_card = random.choice(
                rarity_cards
            )
        else:
            selected_card = random.choice(
                available_cards
            )

        selected_cards.append(selected_card)
        available_cards.remove(selected_card)

    return selected_cards


def get_collection(
    collection_id: str,
) -> dict:
    """Return collection information."""

    return COLLECTIONS.get(
        collection_id,
        {
            "name": "Unknown Collection",
            "vault": "BB",
        },
    )


def get_collection_name(
    collection_id: str,
) -> str:
    """Return collection name."""

    return get_collection(
        collection_id
    ).get(
        "name",
        "Unknown Collection",
    )


def get_series(
    collection_id: str,
) -> str:
    """Return the series name."""

    collection = get_collection(
        collection_id
    )

    if collection.get("series"):
        return collection["series"]

    vault = collection.get(
        "vault",
        collection_id.split("_")[0],
    )

    return VAULT_SERIES.get(
        vault,
        "Unknown Series",
    )


def get_card_name(
    card: dict,
) -> str:
    """Return card name, with a safe fallback."""

    return card.get(
        "name",
        f"Card {card['id']}",
    )


def get_card_image(
    card: dict,
) -> str:
    """Return card image URL."""

    return card.get(
        "image",
        "",
    )


def format_card(
    card: dict,
) -> str:
    """Format one card for the active drop."""

    rarity_emote = RARITY_EMOTES[
        card["stars"]
    ]

    collection_name = get_collection_name(
        card["collection_id"]
    )

    card_name = get_card_name(
        card
    )

    vault = get_collection(
        card["collection_id"]
    ).get(
        "vault",
        card["collection_id"].split("_")[0],
    )

    return (
        f"{rarity_emote} ❖ "
        f"**{card_name}** ☆ "
        f"{vault} · "
        f"*{collection_name}*"
    )


def get_player_vault(
    user_id: int,
) -> str | None:
    """Return a player's selected Vault."""

    initialize_bag_database()

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT vault
            FROM players
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return row[0]


def get_bag_quantity(
    user_id: int,
    card_id: int,
) -> int:
    """Return the player's current card quantity."""

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                user_id,
                card_id,
            ),
        ).fetchone()

    if row is None:
        return 0

    return row[0]


def add_to_bag(
    user_id: int,
    card_id: int,
) -> tuple[int, bool]:
    """
    Add one card to Bag.

    Returns:
        (new_quantity, was_new_card)
    """

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                user_id,
                card_id,
            ),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO bag (
                    user_id,
                    card_id,
                    quantity
                )
                VALUES (?, ?, 1)
                """,
                (
                    user_id,
                    card_id,
                ),
            )

            connection.commit()

            return 1, True

        new_quantity = row[0] + 1

        connection.execute(
            """
            UPDATE bag
            SET quantity = ?
            WHERE user_id = ?
            AND card_id = ?
            """,
            (
                new_quantity,
                user_id,
                card_id,
            ),
        )

        connection.commit()

        return new_quantity, False


class CardButton(discord.ui.Button):
    """Button for one dropped card."""

    def __init__(
        self,
        card: dict,
        number: int,
        owner_id: int,
        view: "CardDropView",
    ):
        self.card = card
        self.number = number
        self.owner_id = owner_id
        self.card_view = view

        self.claimants: list[
            discord.Member | discord.User
        ] = []

        rarity_emote = RARITY_EMOTES[
            card["stars"]
        ]

        super().__init__(
            label="0",
            emoji=discord.PartialEmoji.from_str(
                rarity_emote
            ),
            style=discord.ButtonStyle.secondary,
            custom_id=(
                f"cabinet_card_"
                f"{card['id']}_{number}"
            ),
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        """Handle a player's card choice."""

        view = self.card_view
        user_id = interaction.user.id

        async with view.claim_lock:

            if view.expired:
                embed = discord.Embed(
                    description=(
                        "✦ This drop has already ended."
                    ),
                    color=CABINET_COLOR,
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )
                return

            is_owner = (
                user_id == view.owner_id
            )

            if not is_owner:

                if user_id in view.player_choices:
                    embed = discord.Embed(
                        description=(
                            "✦ You have already claimed "
                            "a card from this drop.\n\n"
                            "Only one card may be claimed "
                            "per player in each drop."
                        ),
                        color=CABINET_COLOR,
                    )

                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True,
                    )
                    return

                view.player_choices[user_id] = self.number

                self.claimants.append(
                    interaction.user
                )

            else:

                previous_choice = (
                    view.player_choices.get(
                        user_id
                    )
                )

                if previous_choice == self.number:
                    embed = discord.Embed(
                        description=(
                            f"{OWNER_EMOTE} You are already "
                            "claiming this card."
                        ),
                        color=CABINET_COLOR,
                    )

                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True,
                    )
                    return

                if previous_choice is not None:
                    previous_button = (
                        view.get_button(
                            previous_choice
                        )
                    )

                    if previous_button is not None:
                        previous_button.claimants = [
                            claimant
                            for claimant
                            in previous_button.claimants
                            if claimant.id != user_id
                        ]

                        previous_button.label = str(
                            len(
                                previous_button.claimants
                            )
                        )

                view.player_choices[user_id] = (
                    self.number
                )

                self.claimants.append(
                    interaction.user
                )

            self.label = str(
                len(
                    self.claimants
                )
            )

        await interaction.response.defer(
            ephemeral=True
        )

        await view.update_buttons()


class CardDropView(discord.ui.View):
    """Buttons for the three dropped cards."""

    def __init__(
        self,
        cards: list[dict],
        owner_id: int,
    ):
        super().__init__(
            timeout=DROP_DURATION
        )

        self.cards = cards
        self.owner_id = owner_id

        self.player_choices: dict[
            int,
            int,
        ] = {}

        self.expired = False

        self.message: discord.Message | None = None

        self.claim_lock = asyncio.Lock()

        for number, card in enumerate(
            cards,
            start=1,
        ):
            self.add_item(
                CardButton(
                    card,
                    number,
                    owner_id,
                    self,
                )
            )

    def get_button(
        self,
        number: int,
    ) -> CardButton | None:
        """Return a button by card number."""

        for item in self.children:
            if isinstance(
                item,
                CardButton,
            ):
                if item.number == number:
                    return item

        return None

    async def update_buttons(self):
        """Update visible counters."""

        if self.message is None:
            return

        try:
            await self.message.edit(
                view=self
            )
        except discord.NotFound:
            pass

    async def on_timeout(self):
        """Finish the drop after 20 seconds."""

        async with self.claim_lock:
            self.expired = True

            for item in self.children:
                if isinstance(
                    item,
                    CardButton,
                ):
                    item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(
                    view=self
                )
            except discord.NotFound:
                pass

            await self.send_results()

    async def send_results(self):
        """Process claims and send final results."""

        if self.message is None:
            return

        result_lines = []

        for item in self.children:

            if not isinstance(
                item,
                CardButton,
            ):
                continue

            card = item.card

            card_name = get_card_name(
                card
            )

            image_url = get_card_image(
                card
            )

            collection_id = card[
                "collection_id"
            ]

            collection_name = (
                get_collection_name(
                    collection_id
                )
            )

            series_name = get_series(
                collection_id
            )

            if not item.claimants:
                continue

            for claimant in item.claimants:

                quantity, was_new = add_to_bag(
                    claimant.id,
                    card["id"],
                )

                if was_new:
                    status = (
                        "You got a new card!"
                    )
                else:
                    status = (
                        f"You now have **{quantity}** copies!\n"
                        "You got a dupie! You can either: "
                        "`/sell` or `/merge`"
                    )

                image_line = ""

                if image_url:
                    image_line = (
                        f"\n[Card Image]({image_url})"
                    )

                result_lines.append(
                    (
                        f"**{card_name}**"
                        f"{image_line}\n"
                        f"{claimant.mention}\n"
                        f"-# ☆ Card ID: `{card['id']}` "
                        f"☆ Collection ID: `{collection_id}` "
                        f"({collection_name}) "
                        f"☆ Series: {series_name}\n\n"
                        f"{status}"
                    )
                )

        if not result_lines:
            result_lines.append(
                "No cards were claimed during this drop."
            )

        result_text = (
            "╭────────────── ✦ ──────────────╮\n"
            "           ✨ CONGRATS! The results are in.\n"
            "╰────────────── ✦ ──────────────╯\n\n"
            + "\n"
            "────────────── ✦ ──────────────\n".join(
                result_lines
            )
            + "\n"
            "╰─────── ⋆⋅☆⋅⋆ ───────╯"
        )

        result_embed = discord.Embed(
            description=result_text,
            color=CABINET_COLOR,
        )

        await self.message.reply(
            embed=result_embed
        )


class Drop(commands.Cog):
    """Commands for dropping cards."""

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

        initialize_bag_database()

    @app_commands.command(
        name="drop",
        description=(
            "Drop three cards from "
            "the Magic Cabinet."
        ),
    )
    async def drop(
        self,
        interaction: discord.Interaction,
    ):
        """Handle the /drop command."""

        cabinet = self.bot.get_cog(
            "cabinet"
        )

        if cabinet is None:
            embed = discord.Embed(
                description=(
                    "The Magic Cabinet setup is "
                    "currently unavailable."
                ),
                color=CABINET_COLOR,
            )

            await interaction.response.send_message(
                embed=embed
            )
            return

        if interaction.guild_id is None:
            embed = discord.Embed(
                description=(
                    "This command can only be used "
                    "inside a server."
                ),
                color=CABINET_COLOR,
            )

            await interaction.response.send_message(
                embed=embed
            )
            return

        allowed = cabinet.is_drop_channel(
            interaction.guild_id,
            interaction.channel_id,
        )

        if not allowed:

            with sqlite3.connect(DATABASE) as connection:
                saved_channels = connection.execute(
                    """
                    SELECT
                        channel1_id,
                        channel2_id,
                        channel3_id,
                        channel4_id,
                        channel5_id
                    FROM drop_channels
                    WHERE guild_id = ?
                    """,
                    (interaction.guild_id,),
                ).fetchone()

            channel_mentions = []

            if saved_channels:
                for channel_id in saved_channels:
                    if channel_id is None:
                        continue

                    channel = interaction.guild.get_channel(
                        channel_id
                    )

                    if channel is not None:
                        channel_mentions.append(
                            channel.mention
                        )

            if channel_mentions:
                channel_text = " • ".join(
                    channel_mentions
                )
            else:
                channel_text = (
                    "No configured Drop channels."
                )

            embed = discord.Embed(
                description=(
                    "This command can only be used "
                    "in a configured Drop channel.\n\n"
                    f"➷ {channel_text}"
                ),
                color=CABINET_COLOR,
            )

            await interaction.response.send_message(
                embed=embed
            )
            return

        player_vault = get_player_vault(
            interaction.user.id
        )

        if player_vault is None:
            embed = discord.Embed(
                description=(
                    "🔒 This vault remains sealed.\n"
                    "You haven't chosen a Vault yet.\n\n"
                    "Use `/magic awaken` to begin "
                    "your Cabinet journey."
                ),
                color=CABINET_COLOR,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        cards = choose_drop_cards()

        card_information = "\n".join(
            format_card(card)
            for card in cards
        )

        card_strip = await create_card_strip(
            cards
        )

        file = discord.File(
            card_strip,
            filename="cabinet_drop.png",
        )

        embed = discord.Embed(
            description=(
                "╭─ ⋆⋅☆⋅⋆ ─╮\n"
                "**This drop is active for 20 seconds.**\n"
                "Unlimited players may participate, but the "
                "drop owner's authority stays put.\n"
                "╰─ ⋆⋅☆⋅⋆ ─╯\n\n"
                "-# ✦ Select a card before the 20 seconds end. "
                f"**Note** : {OWNER_EMOTE} is only for "
                "the drop owner!!\n\n"
                f"{card_information}"
            ),
            color=CABINET_COLOR,
        )

        embed.set_image(
            url="attachment://cabinet_drop.png"
        )

        view = CardDropView(
            cards,
            interaction.user.id,
        )

        message = await interaction.followup.send(
            content=(
                f"**Oh {interaction.user.mention} is "
                f"dropping! Attention!**"
            ),
            embed=embed,
            file=file,
            view=view,
            wait=True,
        )

        view.message = message


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Drop(bot)
)
