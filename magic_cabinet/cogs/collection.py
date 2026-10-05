"""Magic Cabinet collection browser."""

from __future__ import annotations

from io import BytesIO

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps


DATABASE = "cabinet.db"
EMBED_COLOR = discord.Color.from_str("#4E0017")

RED_DOT = "<a:reddot:1556245637425533048>"

ROYAL_COURT_COVER = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)

COLLECTIONS = [
    {
        "id": "BB_1",
        "name": "Royal Court",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_2",
        "name": "Dark Academia",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_3",
        "name": "Mafia",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_4",
        "name": "Mythology",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_5",
        "name": "Royal Heirs",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_6",
        "name": "Blood Moon",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_7",
        "name": "Velvet Night",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_8",
        "name": "Forbidden Court",
        "cover": ROYAL_COURT_COVER,
    },
    {
        "id": "BB_9",
        "name": "Midnight Crown",
        "cover": ROYAL_COURT_COVER,
    },
]


async def download_cover(
    session: aiohttp.ClientSession,
    url: str,
) -> Image.Image:
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.read()

    return Image.open(BytesIO(data)).convert("RGBA")


async def build_collection_image(
    collections: list[dict],
) -> discord.File:
    """Build transparent collection books."""

    async with aiohttp.ClientSession() as session:
        images = [
            await download_cover(session, collection["cover"])
            for collection in collections
        ]

    book_width = 120
    book_height = 170

    horizontal_gap = 70
    vertical_gap = 45

    row_width = (
        book_width * 3
        + horizontal_gap * 2
    )

    rows = (len(images) + 2) // 3

    total_height = (
        rows * book_height
        + (rows - 1) * vertical_gap
    )

    canvas = Image.new(
        "RGBA",
        (row_width, total_height),
        (0, 0, 0, 0),
    )

    for index, image in enumerate(images):
        fitted = ImageOps.contain(
            image,
            (book_width, book_height),
        )

        book = Image.new(
            "RGBA",
            (book_width, book_height),
            (0, 0, 0, 0),
        )

        x = (book_width - fitted.width) // 2
        y = (book_height - fitted.height) // 2

        book.alpha_composite(
            fitted,
            (x, y),
        )

        row = index // 3
        column = index % 3

        items_in_row = min(
            3,
            len(images) - row * 3,
        )

        actual_row_width = (
            items_in_row * book_width
            + (items_in_row - 1) * horizontal_gap
        )

        row_start = (
            row_width - actual_row_width
        ) // 2

        canvas_x = (
            row_start
            + column * (book_width + horizontal_gap)
        )

        canvas_y = (
            row * (book_height + vertical_gap)
        )

        canvas.alpha_composite(
            book,
            (canvas_x, canvas_y),
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


class CollectionButtons(discord.ui.View):
    def __init__(
        self,
        collections: list[dict],
    ):
        super().__init__(timeout=180)

        for index, collection in enumerate(collections):
            button = discord.ui.Button(
                emoji=RED_DOT,
                style=discord.ButtonStyle.secondary,
                row=index // 3,
            )

            async def callback(
                interaction: discord.Interaction,
                collection=collection,
            ):
                await interaction.response.send_message(
                    f"**{collection['name']}**\n"
                    f"`{collection['id']}`",
                    ephemeral=True,
                )

            button.callback = callback

            self.add_item(button)


class Collection(commands.Cog):
    """Collection browser."""

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

        visible = COLLECTIONS[:9]

        file = await build_collection_image(
            visible
        )

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection_books.png"
        )

        await interaction.followup.send(
            embed=embed,
            file=file,
            view=CollectionButtons(visible),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
