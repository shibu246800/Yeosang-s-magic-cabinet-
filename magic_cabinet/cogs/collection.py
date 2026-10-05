"""Magic Cabinet collection browser."""

from io import BytesIO

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps


EMBED_COLOR = discord.Color.from_str("#4E0017")

RED_DOT = "<a:reddot:1556245637425533048>"

ROYAL_COURT_COVER = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)

COLLECTIONS = [
    ("Royal Court", "BB_1", ROYAL_COURT_COVER),
    ("Dark Academia", "BB_2", ROYAL_COURT_COVER),
    ("Mafia", "BB_3", ROYAL_COURT_COVER),
    ("Mythology", "BB_4", ROYAL_COURT_COVER),
    ("Royal Heirs", "BB_5", ROYAL_COURT_COVER),
    ("Blood Moon", "BB_6", ROYAL_COURT_COVER),
    ("Velvet Night", "BB_7", ROYAL_COURT_COVER),
    ("Forbidden Court", "BB_8", ROYAL_COURT_COVER),
    ("Midnight Crown", "BB_9", ROYAL_COURT_COVER),
]


async def download_image(
    session: aiohttp.ClientSession,
    url: str,
) -> Image.Image:
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.read()

    return Image.open(BytesIO(data)).convert("RGB")


async def make_books_image() -> discord.File:
    """Create the 3 × 3 small-book display."""

    async with aiohttp.ClientSession() as session:
        images = []

        for _, _, url in COLLECTIONS:
            images.append(
                await download_image(session, url)
            )

    book_width = 150
    book_height = 200

    column_gap = 18
    row_gap = 24

    row_width = (
        book_width * 3
        + column_gap * 2
    )

    total_height = (
        book_height * 3
        + row_gap * 2
    )

    canvas = Image.new(
        "RGB",
        (row_width, total_height),
        "#2B0010",
    )

    for index, image in enumerate(images):
        fitted = ImageOps.contain(
            image,
            (book_width, book_height),
        )

        book = Image.new(
            "RGB",
            (book_width, book_height),
            "#FFFFFF",
        )

        x = (book_width - fitted.width) // 2
        y = (book_height - fitted.height) // 2

        book.paste(
            fitted,
            (x, y),
        )

        row = index // 3
        column = index % 3

        canvas_x = column * (
            book_width + column_gap
        )

        canvas_y = row * (
            book_height + row_gap
        )

        canvas.paste(
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
    def __init__(self):
        super().__init__(timeout=180)

        for index, (
            name,
            collection_id,
            _,
        ) in enumerate(COLLECTIONS):

            button = discord.ui.Button(
                emoji=RED_DOT,
                style=discord.ButtonStyle.secondary,
                row=index // 3,
            )

            async def callback(
                interaction: discord.Interaction,
                collection_id=collection_id,
                name=name,
            ):
                await interaction.response.send_message(
                    f"**{name}**\n"
                    f"`{collection_id}`",
                    ephemeral=True,
                )

            button.callback = callback

            self.add_item(button)


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

        file = await make_books_image()

        embed = discord.Embed(
            color=EMBED_COLOR,
        )

        embed.set_image(
            url="attachment://collection_books.png"
        )

        await interaction.followup.send(
            embed=embed,
            file=file,
            view=CollectionButtons(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
