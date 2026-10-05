"""Collection 3x3 grid test."""

import discord
from discord import app_commands
from discord.ext import commands


COVER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)

RED_DOT = "<a:reddot:1556245637425533048>"


class Collection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def make_tile(self, number: int):
        container = discord.ui.Container()

        container.add_item(
            discord.ui.MediaGallery(
                discord.ui.MediaGalleryItem(
                    media=COVER_URL,
                    description="Royal Court",
                )
            )
        )

        container.add_item(
            discord.ui.TextDisplay(
                f"**𝑹𝒐𝒚𝒂𝒍 𝑪𝒐𝒖𝒓𝒕**\n"
                f"`BB_1` • 🌙"
            )
        )

        button = discord.ui.Button(
            emoji=RED_DOT,
            style=discord.ButtonStyle.secondary,
        )

        async def callback(
            interaction: discord.Interaction,
        ):
            await interaction.response.send_message(
                f"Royal Court {number} clicked!",
                ephemeral=True,
            )

        button.callback = callback

        container.add_item(
            discord.ui.ActionRow(button)
        )

        return container

    @app_commands.command(
        name="collection",
        description="Browse collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        view = discord.ui.LayoutView()

        for row in range(3):
            for column in range(3):
                view.add_item(
                    self.make_tile(
                        row * 3 + column + 1
                    )
                )

        await interaction.response.send_message(
            view=view
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
