"""Collection gallery test."""

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

    @app_commands.command(
        name="collection",
        description="Browse Magic Cabinet collections.",
    )
    async def collection(
        self,
        interaction: discord.Interaction,
    ):
        view = discord.ui.LayoutView()

        container = discord.ui.Container()

        # Book 1
        book_1 = discord.ui.Section(
            discord.ui.TextDisplay(
                "### 𝑹𝒐𝒚𝒂𝒍 𝑪𝒐𝒖𝒓𝒕\n"
                "`BB_1`"
            ),
            accessory=discord.ui.Thumbnail(COVER_URL),
        )

        button_1 = discord.ui.Button(
            emoji=RED_DOT,
            style=discord.ButtonStyle.secondary,
        )

        async def open_1(
            button_interaction: discord.Interaction,
        ):
            await button_interaction.response.send_message(
                "Royal Court opened.",
                ephemeral=True,
            )

        button_1.callback = open_1

        # Book 2
        book_2 = discord.ui.Section(
            discord.ui.TextDisplay(
                "### 𝑫𝒂𝒓𝒌 𝑨𝒄𝒂𝒅𝒆𝒎𝒊𝒂\n"
                "`BB_2`"
            ),
            accessory=discord.ui.Thumbnail(COVER_URL),
        )

        button_2 = discord.ui.Button(
            emoji=RED_DOT,
            style=discord.ButtonStyle.secondary,
        )

        async def open_2(
            button_interaction: discord.Interaction,
        ):
            await button_interaction.response.send_message(
                "Dark Academia opened.",
                ephemeral=True,
            )

        button_2.callback = open_2

        # Book 3
        book_3 = discord.ui.Section(
            discord.ui.TextDisplay(
                "### 𝑴𝒂𝒇𝒊𝒂\n"
                "`BB_3`"
            ),
            accessory=discord.ui.Thumbnail(COVER_URL),
        )

        button_3 = discord.ui.Button(
            emoji=RED_DOT,
            style=discord.ButtonStyle.secondary,
        )

        async def open_3(
            button_interaction: discord.Interaction,
        ):
            await button_interaction.response.send_message(
                "Mafia opened.",
                ephemeral=True,
            )

        button_3.callback = open_3

        container.add_item(book_1)
        container.add_item(
            discord.ui.ActionRow(button_1)
        )

        container.add_item(book_2)
        container.add_item(
            discord.ui.ActionRow(button_2)
        )

        container.add_item(book_3)
        container.add_item(
            discord.ui.ActionRow(button_3)
        )

        view.add_item(container)

        await interaction.response.send_message(
            view=view
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
