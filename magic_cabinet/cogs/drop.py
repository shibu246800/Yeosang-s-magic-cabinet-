"""Drop command."""

import random

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


DROP_CARD_COUNT = 3
DROP_DURATION = 30


def choose_rarity() -> str:
    """Choose a rarity using the configured probabilities."""

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


def get_collection_name(
    collection_id: str,
) -> str:
    """Return the collection name."""

    collection = COLLECTIONS.get(
        collection_id
    )

    if collection is None:
        return "Unknown Collection"

    return collection["name"]


def format_card(card: dict) -> str:
    """Format one card's information."""

    rarity_emote = RARITY_EMOTES[
        card["stars"]
    ]

    collection_name = get_collection_name(
        card["collection_id"]
    )

    return (
        f"{rarity_emote} ❖ "
        f"**Card ID : `{card['id']}`**  ·  "
        f"**CL : `{card['collection_id']}`** "
        f"· *{collection_name}*"
    )


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
        self.claim_count = 0
        self.claimants: list[discord.Member | discord.User] = []

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
        """Record a claim without announcing it."""

        if self.card_view.expired:
            await interaction.response.send_message(
                "This drop has already ended.",
                ephemeral=True,
            )
            return

        if interaction.user.id in self.card_view.claimed_users:
            await interaction.response.send_message(
                "You have already claimed a card from this drop.",
                ephemeral=True,
            )
            return

        self.card_view.claimed_users.add(
            interaction.user.id
        )

        self.claim_count += 1
        self.claimants.append(
            interaction.user
        )

        self.label = str(
            self.claim_count
        )

        # Private confirmation only.
        await interaction.response.defer(
            ephemeral=True
        )

        await self.card_view.update_buttons()


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

        self.claimed_users: set[int] = set()

        self.expired = False
        self.message: discord.Message | None = None

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

    async def update_buttons(self):
        """Update claim counters."""

        if self.message is None:
            return

        await self.message.edit(
            view=self
        )

    async def on_timeout(self):
        """Finish the drop after 30 seconds."""

        self.expired = True

        for item in self.children:
            if isinstance(
                item,
                CardButton,
            ):
                item.disabled = True

        if self.message is not None:
            await self.message.edit(
                view=self
            )

            await self.send_results()

    async def send_results(self):
        """Send the private results summary."""

        if self.message is None:
            return

        result_embed = discord.Embed(
            title="✨ Congrats! The results are:",
            color=discord.Color.from_rgb(
                212,
                175,
                55,
            ),
        )

        result_lines = []

        for number, item in enumerate(
            self.children,
            start=1,
        ):
            if not isinstance(
                item,
                CardButton,
            ):
                continue

            card = item.card

            collection_name = get_collection_name(
                card["collection_id"]
            )

            claimants = item.claimants

            if claimants:
                claimant_text = "\n".join(
                    user.mention
                    for user in claimants
                )
            else:
                claimant_text = "No claims"

            result_lines.append(
                (
                    f"**Card {number}**\n"
                    f"Card ID: `{card['id']}`\n"
                    f"CL: `{card['collection_id']}`\n"
                    f"*{collection_name}*\n\n"
                    f"{claimant_text}"
                )
            )

        for index, result in enumerate(
            result_lines,
            start=1,
        ):
            result_embed.add_field(
                name=f"Card {index}",
                value=result,
                inline=True,
            )

        result_embed.set_footer(
            text="Claim results were revealed after the 30-second drop."
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
            await interaction.response.send_message(
                "Magic Cabinet setup is currently unavailable."
            )
            return

        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used inside a server."
            )
            return

        allowed = cabinet.is_drop_channel(
            interaction.guild_id,
            interaction.channel_id,
        )

        if not allowed:
            await interaction.response.send_message(
                "This command can only be used in "
                "a configured Drop channel."
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
                "**This drop is active for 30 seconds.**\n"
                "Unlimited players can participate, but the "
                "drop owner's authority stays put.\n"
                "╰─ ⋆⋅☆⋅⋆ ─╯\n\n"
                f"{card_information}"
            ),
            color=discord.Color.from_rgb(
                212,
                175,
                55,
            ),
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
