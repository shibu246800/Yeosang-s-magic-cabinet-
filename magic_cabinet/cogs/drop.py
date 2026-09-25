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


def choose_rarity() -> str:
    """Choose a rarity using the configured drop probabilities."""

    rarities = list(DROP_RATES.keys())
    weights = list(DROP_RATES.values())

    return random.choices(
        rarities,
        weights=weights,
        k=1,
    )[0]


def choose_card() -> dict:
    """Choose one random card using the rarity system."""

    rarity = choose_rarity()
    available_cards = RARITY_CARDS[rarity]

    return random.choice(available_cards)


def format_card(card: dict) -> str:
    """Format one card's information."""

    rarity_emote = RARITY_EMOTES[card["stars"]]

    return (
        f"{rarity_emote} "
        f"-#**Card ID : `{card['id']}`** "
        f"**Collection: `{card['collection_id']}`**"
    )


class CardButton(discord.ui.Button):
    """Button for one dropped card."""

    def __init__(self, card: dict, number: int):
        self.card = card

        rarity_emote = RARITY_EMOTES[card["stars"]]

        super().__init__(
            label=f"{number}",
            emoji=discord.PartialEmoji.from_str(rarity_emote),
            style=discord.ButtonStyle.secondary,
            custom_id=f"cabinet_card_{card['id']}_{number}",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"You selected **Card ID : {self.card['id']}**.",
            ephemeral=True,
        )


class CardDropView(discord.ui.View):
    """Buttons for the three dropped cards."""

    def __init__(self, cards: list[dict]):
        super().__init__(timeout=60)

        for number, card in enumerate(cards, start=1):
            self.add_item(CardButton(card, number))


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

        cards = [
            choose_card(),
            choose_card(),
            choose_card(),
        ]

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
            description=card_information,
        )

        embed.set_image(
            url="attachment://cabinet_drop.png"
        )

        view = CardDropView(cards)

        await interaction.response.send_message(
            content=(
                f"**Oh {interaction.user.mention} is dropping! "
                f"Attention!**"
            ),
            embed=embed,
            file=file,
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Drop(bot))
