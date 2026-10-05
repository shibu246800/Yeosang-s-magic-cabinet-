"""Magic Cabinet collection browser."""

from __future__ import annotations

from io import BytesIO

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps


HEADER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/cogs/profile/"
    "Untitled13_20261005205021.jpg"
)

RED_DOT = "<a:reddot:1556245637425533048>"

COVER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)

COLLECTIONS = [
    ("Royal Court", "BB_1"),
    ("Dark Academia", "BB_2"),
    ("Mafia", "BB_3"),
    ("Mythology", "BB_4"),
    ("Royal Heirs", "BB_5"),
    ("Blood Moon", "BB_6"),
    ("Velvet Night", "BB_7"),
    ("Forbidden Court", "BB_8"),
    ("Midnight Crown", "BB_9"),
]


async def make_book() -> discord.File:
    async with aiohttp.ClientSession() as session:
        async with session.get(COVER_URL) as response:
            response.raise_for_status()
            data = await response.read()

    source = Image.open(BytesIO(data)).convert("RGBA")

    image = ImageOps.contain(
        source,
        (130, 175),
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return discord.File(
        buffer,
        filename="collection_book.png",
    )


class CollectionView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=180)

        container = discord.ui.Container()

        # Header
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    HEADER_URL,
                ),
            )
        )

        # Collection entries
        for name, collection_id in COLLECTIONS:

            button = discord.ui.Button(
                emoji=RED_DOT,
                style=discord.ButtonStyle.secondary,
            )

            async def callback(
                interaction: discord.Interaction,
                name=name,
                collection_id=collection_id,
            ):
                await interaction.response.send_message(
                    f"**{name}**\n`{collection_id}`",
                    ephemeral=True,
                )

            button.callback = callback

            section = discord.ui.Section(
                discord.ui.TextDisplay(
                    f"**{name}**\n`{collection_id}`"
                ),
                accessory=button,
            )

            container.add_item(section)

        self.add_item(container)


class Collection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Browse Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        file = await make_book()

        await interaction.response.send_message(
            file=file,
            view=CollectionView(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
