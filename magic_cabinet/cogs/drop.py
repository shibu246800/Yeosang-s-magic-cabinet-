"""Drop command."""

import random

import discord
from discord import app_commands
from discord.ext import commands

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


def format_card(card: dict, number: int) -> str:
    """Format one dropped card for display."""

    collection_id = card["collection_id"]
    collection = COLLECTIONS[collection_id]

    return (
        f"**{number}.** {card['stars']} 》"
        f"**{collection['name']}** "
        f"(ID: `{card['id']}`) "
        f"(`{collection_id}`)"
    )


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

        embeds = []

        for number, card in enumerate(cards, start=1):
            collection_id = card["collection_id"]
            collection = COLLECTIONS[collection_id]

            embed = discord.Embed(
                title=(
                    f"{number}. {card['stars']} 》"
                    f"{collection['name']}"
                ),
                description=(
                    f"**Card ID:** `{card['id']}`\n"
                    f"**Collection:** `{collection_id}`"
                ),
            )

            embed.set_image(url=card["image"])

            embeds.append(embed)

        await interaction.response.send_message(
            content=(
                f"**Oh {interaction.user.mention} is dropping! Attention!**"
            ),
            embeds=embeds,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Drop(bot))
