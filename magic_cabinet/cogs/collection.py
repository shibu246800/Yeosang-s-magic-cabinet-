"""Collection 3-book layout test."""

from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageOps
import aiohttp


COVER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)

RED_DOT = "<a:reddot:1556245637425533048>"


async def make_book_row(urls: list[str]) -> discord.File:
    """Create a small 3-book row like the Drop display."""

    async with aiohttp.ClientSession() as session:
        images = []

        for url in urls:
            async with session.get(url) as response:
                data = await response.read()

            image = Image.open(BytesIO(data)).convert("RGB")
            images.append(image)

    book_width = 180
    book_height = 240
    gap = 24

    resized = []

    for image in images:
        fitted = ImageOps.contain(
            image,
            (book_width, book_height),
        )

        canvas = Image.new(
            "RGB",
            (book_width, book_height),
            "white",
        )

        x = (book_width - fitted.width) // 2
        y = (book_height - fitted.height) // 2

        canvas.paste(fitted, (x, y))
        resized.append(canvas)

    row = Image.new(
        "RGB",
        (
            book_width * 3 + gap * 2,
            book_height,
        ),
        "#2B0010",
    )

    for index, image in enumerate(resized):
        x = index * (book_width + gap)
        row.paste(image, (x, 0))

    buffer = BytesIO()
    row.save(buffer, format="PNG")
    buffer.seek(0)

    return discord.File(
        buffer,
        filename="collection_books.png",
    )


class CollectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

        for index in range(3):
            button = discord.ui.Button(
                emoji=RED_DOT,
                style=discord.ButtonStyle.secondary,
            )

            async def callback(
                interaction: discord.Interaction,
                index=index,
            ):
                await interaction.response.send_message(
                    f"Royal Court book {index + 1} opened.",
                    ephemeral=True,
                )

            button.callback = callback
            self.add_item(button)


class Collection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Test collection bookshelf.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        file = await make_book_row(
            [
                COVER_URL,
                COVER_URL,
                COVER_URL,
            ]
        )

        embed = discord.Embed(
            color=discord.Color.from_str("#4E0017"),
        )

        embed.set_image(
            url="attachment://collection_books.png"
        )

        await interaction.followup.send(
            embed=embed,
            file=file,
            view=CollectionView(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
