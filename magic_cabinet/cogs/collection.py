"""Magic Cabinet collection browser."""

from __future__ import annotations

from io import BytesIO

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps


EMBED_COLOR = discord.Color.from_str("#4E0017")

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


async def download_cover(
    session: aiohttp.ClientSession,
) -> Image.Image:
    async with session.get(COVER_URL) as response:
        response.raise_for_status()
        data = await response.read()

    return Image.open(BytesIO(data)).convert("RGBA")


async def make_books() -> discord.File:
    async with aiohttp.ClientSession() as session:
        source = await download_cover(session)

    book_width = 105
    book_height = 150

    horizontal_gap = 110
    vertical_gap = 55

    total_width = (
        book_width * 3
        + horizontal_gap * 2
    )

    total_height = (
        book_height * 3
        + vertical_gap * 2
    )

    canvas = Image.new(
        "RGBA",
        (total_width, total_height),
        (0, 0, 0, 0),
    )

    for index in range(9):
        image = ImageOps.contain(
            source,
            (book_width, book_height),
        )

        row = index // 3
        column = index % 3

        x = column * (
            book_width + horizontal_gap
        )

        y = row * (
            book_height + vertical_gap
        )

        canvas.alpha_composite(
            image,
            (x, y),
        )

    buffer = BytesIO()

    canvas.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return discord.File(
        buffer,
        filename="collection_books.png",
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

        # Collection books
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    "attachment://collection_books.png",
                ),
            )
        )

        # Three separate rows, three buttons each
        for row_start in range(0, len(COLLECTIONS), 3):
            buttons = discord.ui.ActionRow()

            for name, collection_id in COLLECTIONS[
                row_start:row_start + 3
            ]:
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
                buttons.add_item(button)

            container.add_item(buttons)

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
        await interaction.response.defer()

        file = await make_books()

        view = CollectionView()

        await interaction.followup.send(
            file=file,
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
