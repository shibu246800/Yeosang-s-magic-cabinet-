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
    """Choose a rarity using the configured drop probabilities."""

    rarities = list(DROP_RATES.keys())
    weights = list(DROP_RATES.values())

    return random.choices(
        rarities,
        weights=weights,
        k=1,
    )[0]


def choose_card(used_counts: dict[int, int]) -> dict:
    """Choose a card while preventing three identical cards."""

    all_cards = [
        card
        for cards in RARITY_CARDS.values()
        for card in cards
    ]

    selected_rarity = choose_rarity()

    rarity_cards = [
        card
        for card in RARITY_CARDS[selected_rarity]
        if used_counts.get(card["id"], 0) < 2
    ]

    if rarity_cards:
        return random.choice(rarity_cards)

    available_cards = [
        card
        for card in all_cards
        if used_counts.get(card["id"], 0) < 2
    ]

    if not available_cards:
        raise RuntimeError(
            "Not enough cards are available for this drop."
        )

    return random.choice(available_cards)


def choose_drop_cards() -> list[dict]:
    """Choose three cards while allowing at most two copies."""

    cards = []
    used_counts = {}

    for _ in range(DROP_CARD_COUNT):
        card = choose_card(used_counts)

        cards.append(card)

        card_id = card["id"]
        used_counts[card_id] = used_counts.get(card_id, 0) + 1

    return cards


def format_card(card: dict) -> str:
    """Format one card's information."""

    rarity_emote = RARITY_EMOTES[card["stars"]]

    return (
        f"{rarity_emote} ❖ "
        f"**Card ID : `{card['id']}`**  ·  "
        f"**Collection : `{card['collection_id']}`**"
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

        rarity_emote = RARITY_EMOTES[card["stars"]]

        super().__init__(
            label=f"{number}",
            emoji=discord.PartialEmoji.from_str(rarity_emote),
            style=discord.ButtonStyle.secondary,
            custom_id=f"cabinet_card_{card['id']}_{number}",
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        """Handle a card claim."""

        if self.card_view.expired:
            await interaction.response.send_message(
                "This drop has already ended.",
                ephemeral=True,
            )
            return

        if self.card_view.claimed[self.number]:
            await interaction.response.send_message(
                "This card has already been claimed.",
                ephemeral=True,
            )
            return

        # The drop owner has priority when they claim a card.
        if interaction.user.id == self.owner_id:
            winner = interaction.user

        else:
            # The first valid non-owner click wins.
            winner = interaction.user

        self.card_view.claimed[self.number] = winner

        self.disabled = True

        for item in self.card_view.children:
            if isinstance(item, CardButton):
                if self.card_view.claimed[item.number]:
                    item.disabled = True

        await interaction.response.send_message(
            f"🎴 {winner.mention} got **Card ID : `{self.card['id']}`**!",
        )

        await self.card_view.message.edit(
            view=self.card_view,
        )


class CardDropView(discord.ui.View):
    """Buttons for the three dropped cards."""

    def __init__(
        self,
        cards: list[dict],
        owner_id: int,
    ):
        super().__init__(timeout=DROP_DURATION)

        self.cards = cards
        self.owner_id = owner_id
        self.claimed = {
            1: None,
            2: None,
            3: None,
        }
        self.expired = False
        self.message: discord.Message | None = None

        for number, card in enumerate(cards, start=1):
            self.add_item(
                CardButton(
                    card,
                    number,
                    owner_id,
                    self,
                )
            )

    async def on_timeout(self):
        """Disable all buttons when the drop expires."""

        self.expired = True

        for item in self.children:
            if isinstance(item, CardButton):
                item.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)


class Drop(commands.Cog):
    """Commands for dropping cards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="drop",
        description="Drop three cards from the Magic Cabinet.",
    )
    async def drop(self, interaction: discord.Interaction):
        """Handle the /drop command."""

        cabinet = self.bot.get_cog("cabinet")

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
                "This command can only be used in a configured Drop channel."
            )
            return

        # Acknowledge immediately so Discord does not expire
        # the slash-command interaction while the card image is created.
        await interaction.response.defer()

        cards = choose_drop_cards()

        card_information = "\n".join(
            format_card(card)
            for card in cards
        )

        card_strip = await create_card_strip(cards)

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
            color=discord.Color.from_rgb(212, 175, 55),
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
                f"**Oh {interaction.user.mention} is dropping! "
                f"Attention!**"
            ),
            embed=embed,
            file=file,
            view=view,
            wait=True,
        )

        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(Drop(bot))
