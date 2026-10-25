
"""Magic Cabinet merge command."""

import random

import discord
from discord import app_commands
from discord.ext import commands

from magic_cabinet.database import (
    get_connection,
    initialize_database,
)
from magic_cabinet.data.normal import CARDS as NORMAL_CARDS
from magic_cabinet.data.rare import CARDS as RARE_CARDS
from magic_cabinet.data.epic import CARDS as EPIC_CARDS
from magic_cabinet.data.limited import CARDS as LIMITED_CARDS


EMBED_COLOR = discord.Color.from_str("#4E0017")
GLIMMER_EMOTE = "<:glimmer:1554842064464773172>"

RARITY_ORDER = {
    "★": 1,
    "★★": 2,
    "★★★": 3,
    "★★★★": 4,
}

MERGE_REWARDS = {
    "★": 50,
    "★★": 75,
    "★★★": 100,
}

ALL_CARDS = (
    NORMAL_CARDS
    + RARE_CARDS
    + EPIC_CARDS
    + LIMITED_CARDS
)

CARD_DATA = {
    int(card["id"]): {
        **card,
        "id": int(card["id"]),
    }
    for card in ALL_CARDS
}


def merge_card(user_id: int, card_id: int):
    """Merge three duplicate copies into one higher-rarity card."""

    initialize_database()

    card = CARD_DATA.get(card_id)

    if card is None:
        return False, "That Card ID does not exist.", None, 0

    rarity = card["stars"]

    if rarity not in MERGE_REWARDS:
        return (
            False,
            "Limited cards cannot be merged.",
            None,
            0,
        )

    required_rarity = RARITY_ORDER[rarity] + 1

    eligible_cards = [
        candidate
        for candidate in ALL_CARDS
        if candidate["collection_id"] == card["collection_id"]
        and RARITY_ORDER.get(candidate["stars"], 0)
        == required_rarity
    ]

    if not eligible_cards:
        return (
            False,
            "There is no eligible higher-rarity card "
            "in this collection.",
            None,
            0,
        )

    reward = MERGE_REWARDS[rarity]

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT quantity
            FROM bag
            WHERE user_id = ? AND card_id = ?
            """,
            (user_id, card_id),
        ).fetchone()

        if row is None or row["quantity"] < 4:
            return (
                False,
                "You need at least **3 duplicate copies** "
                "of this card in your Bag to merge it. "
                "Your original copy will stay safe.",
                None,
                0,
            )

        upgraded_card = random.choice(eligible_cards)
        upgraded_id = int(upgraded_card["id"])

        # Consume exactly three duplicates.
        connection.execute(
            """
            UPDATE bag
            SET quantity = quantity - 3
            WHERE user_id = ? AND card_id = ?
            """,
            (user_id, card_id),
        )

        # Keep the original upgraded card if already owned.
        # Otherwise, establish its first permanent copy.
        connection.execute(
            """
            INSERT INTO bag (user_id, card_id, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT (user_id, card_id)
            DO UPDATE SET quantity = bag.quantity + 1
            """,
            (user_id, upgraded_id),
        )

        # Award Glimmers only after a successful merge.
        connection.execute(
            """
            INSERT INTO balances (user_id, glimmers)
            VALUES (?, ?)
            ON CONFLICT (user_id)
            DO UPDATE SET glimmers = balances.glimmers + excluded.glimmers
            """,
            (user_id, reward),
        )

    return True, "Merge successful!", upgraded_card, reward


class Merge(commands.Cog):
    """Magic Cabinet merge command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        initialize_database()

    @app_commands.command(
        name="merge",
        description="Merge three duplicate cards into a higher rarity.",
    )
    @app_commands.describe(
        card_id="The Card ID with at least three duplicates in your Bag."
    )
    async def merge(
        self,
        interaction: discord.Interaction,
        card_id: int,
    ):
        success, message, upgraded_card, reward = await __import__(
            "asyncio"
        ).to_thread(
            merge_card,
            interaction.user.id,
            card_id,
        )

        if not success:
            embed = discord.Embed(
                description=f"✦ {message}",
                color=EMBED_COLOR,
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="✧ THE MERGE IS COMPLETE ✧",
            description=(
                f"Your three duplicate copies of "
                f"**Card #{card_id}** have merged.\n\n"
                f"✦ **New Card:** #{upgraded_card['id']}\n"
                f"✦ **Rarity:** {upgraded_card['stars']}\n"
                f"✦ **Collection:** "
                f"{upgraded_card['collection_id']}\n\n"
                f"{GLIMMER_EMOTE} **Reward:** "
                f"{reward} Glimmers"
            ),
            color=EMBED_COLOR,
        )

        if upgraded_card.get("image"):
            embed.set_thumbnail(url=upgraded_card["image"])

        embed.set_footer(
            text="Your original card remains safe in your collection."
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Merge(bot))
