"""Collection layout test."""

import discord
from discord import app_commands
from discord.ext import commands


COVER_URL = (
    "https://raw.githubusercontent.com/"
    "shibu246800/Yeosang-s-magic-cabinet-/"
    "refs/heads/main/magic_cabinet/collection_covers/"
    "grok_1791211167707.jpg"
)


class Collection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Test collection layout.",
    )
    async def collection(self, interaction: discord.Interaction):

        view = discord.ui.LayoutView()

        container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### 𝑹𝒐𝒚𝒂𝒍 𝑪𝒐𝒖𝒓𝒕\n"
                    "`BB_1` • 🌙 Velvet Moon"
                ),
                accessory=discord.ui.Thumbnail(
                    COVER_URL
                ),
            ),
        )

        button = discord.ui.Button(
            emoji="<a:reddot:1556245637425533048>",
            style=discord.ButtonStyle.secondary,
        )

        async def button_callback(
            button_interaction: discord.Interaction,
        ):
            await button_interaction.response.send_message(
                "Royal Court button works!",
                ephemeral=True,
            )

        button.callback = button_callback

        container.add_item(
            discord.ui.ActionRow(button)
        )

        view.add_item(container)

        await interaction.response.send_message(
            view=view
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Collection(bot))
